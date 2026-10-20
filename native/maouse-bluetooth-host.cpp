// Host nativo RFCOMM do Maouse.
//
// Porque existe: `socket.AF_BLUETOOTH` e `bt_socket` so existem no Linux. No
// Windows a porta RFCOMM vive em WinRT
// (`Windows.Devices.Bluetooth.Rfcomm`) e nao ha caminho para a abrir a partir de
// Python. O Python precisa por isso de alguem que segure a porta: este
// executavel.
//
// O transporte entre os dois e deliberadamente burro — o executavel NAO
// interpreta o protocolo do rato. Recebe bytes e devolve bytes. A unica coisa
// que acrescenta e o endereco do telefone, que e o que o limitador de
// tentativas do Python nao consegue descobrir sozinho.
//
// Envelope (ambos os sentidos), little-endian:
//
//     [tamanho:4][conn:4][payload: tamanho-4]
//
// `tamanho` conta o `conn` e o `payload`. `conn == 0` e o canal de controlo
// (JSON, um evento por envelope); `conn > 0` sao dados de um telefone. Um
// envelope sem payload e a forma de parar sem ambiguidade.
//
// ── A API, e um_probe de armadilhas ─────────────────────────────────────────
// O servidor RFCOMM do Windows e `RfcommServiceProvider` + um
// `StreamSocketListener`:
//
//     RfcommServiceProvider::CreateAsync(RfcommServiceId::FromUuid(guid))
//         .StartAdvertising(listener)
//     listener.ConnectionReceived() -> StreamSocket
//
// Nao existe `StartService`, `ConnectionStatusChanged`, `RfcommStream` nem
// `CreateFromServiceIdAsync`: era a API da Windows Phone e foi removida do
// Windows Runtime. Escrever contra ela da codigo que nem compila — e foi
// exactamente o que aconteceu na primeira versao deste ficheiro.
//
// Duas coisas que custaram uma volta: `winrt::apartment_flags` nao existe nesta
// versao do C++/WinRT, e cada thread que toca em WinRT tem de ter um apartamento
// inicializado, ou o primeiro `LoadAsync` morre com `RO_E_NOT_INITIALIZED`.

#include <windows.h>

#include <winrt/Windows.Devices.Bluetooth.Rfcomm.h>
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Networking.Sockets.h>
#include <winrt/Windows.Storage.Streams.h>

#include <array>
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <mutex>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

#include "guid_texto.h"

using namespace winrt::Windows::Devices::Bluetooth::Rfcomm;
using namespace winrt::Windows::Networking::Sockets;
using namespace winrt::Windows::Storage::Streams;
using namespace winrt::Windows::Foundation;

namespace {

constexpr uint32_t CONN_CONTROLE = 0;

// Teto de um envelope vindo do Python. Nao e o mesmo numero que o `MAX_FRAME`
// de core/remote_rfcomm.py, porque sao coisas diferentes: la o limite e sobre o
// `payload` da ligacao, aqui e sobre o `tamanho`, que ainda inclui os 4 bytes
// do `conn`. Um payload no maximo do wire (65536) chega aqui como 65540, por
// isso o teto tem de ser 4 bytes maior — se nao for, a maior mensagem legal
// seria recusada.
//
// Sem teto, um `tamanho` de 0xFFFFFFFF pede ~4 GiB num `std::vector` e o
// processo morre num `__fastfail` (0xC0000409) em vez de recusar a entrada.
constexpr uint32_t MAX_ENVELOPE = 64u * 1024u + 4u;

// O mesmo UUID do BLE. Os dois transportes anunciam a mesma identidade, para o
// telefone reconhecer "isto e um Maouse" sem configuracao nova.
constexpr wchar_t SERVICO[] = L"D9905F51-F497-49A4-88DF-784D82249EFD";

std::mutex g_escrita;
std::mutex g_ligacoes;
std::unordered_map<uint32_t, StreamSocket> g_sockets;
std::atomic<uint32_t> g_proximo_conn{1};
std::atomic<bool> g_parar{false};

// ── stderr ──────────────────────────────────────────────────────────────────
// Tudo o que nao for dados vai para stderr, nunca para stdout. Uma linha de
// aviso em stdout corrompe o protocolo em vez de explicar a falha.

void aviso(const std::string& texto) {
    fprintf(stderr, "%s\n", texto.c_str());
    fflush(stderr);
}

std::string para_utf8(const winrt::hstring& s) {
    int n = WideCharToMultiByte(CP_UTF8, 0, s.c_str(), -1, nullptr, 0, nullptr, nullptr);
    std::string buf(n > 0 ? n : 1, '\0');
    if (n > 0) {
        WideCharToMultiByte(CP_UTF8, 0, s.c_str(), -1, buf.data(), n, nullptr, nullptr);
        buf.resize(n - 1);  // tira o NUL que o WideCharToMultiByte sempre poe
    }
    return buf;
}

// O endereco vem do sistema e pode trazer aspas ou barras: JSON nao e opcional.
std::string json_escapar(const std::string& s) {
    std::string out;
    out.reserve(s.size() + 8);
    for (unsigned char c : s) {
        switch (c) {
            case '"':  out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\n': out += "\\n";  break;
            case '\r': out += "\\r";  break;
            case '\t': out += "\\t";  break;
            default:
                if (c < 0x20) {
                    char tmp[8];
                    snprintf(tmp, sizeof tmp, "\\u%04x", c);
                    out += tmp;
                } else {
                    out += (char)c;
                }
        }
    }
    return out;
}

// ── stdout ──────────────────────────────────────────────────────────────────

bool escrever_tudo(HANDLE h, const uint8_t* p, size_t n) {
    size_t escrito = 0;
    while (escrito < n) {
        DWORD w = 0;
        // Um pipe pode aceitar menos bytes do que pedimos; um unico WriteFile e
        // um envelope pela metade, e metade de envelope nao e nada.
        if (!WriteFile(h, p + escrito, (DWORD)(n - escrito), &w, nullptr) || w == 0) {
            return false;
        }
        escrito += w;
    }
    return true;
}

void emitir(uint32_t conn, const std::string& payload) {
    uint32_t tamanho = 4u + (uint32_t)payload.size();
    std::vector<uint8_t> out(8 + payload.size());
    memcpy(out.data(), &tamanho, 4);
    memcpy(out.data() + 4, &conn, 4);
    if (!payload.empty()) {
        memcpy(out.data() + 8, payload.data(), payload.size());
    }
    std::lock_guard<std::mutex> lock(g_escrita);
    escrever_tudo(GetStdHandle(STD_OUTPUT_HANDLE), out.data(), out.size());
}

void evento_ligado(uint32_t conn, const std::string& endereco) {
    char cab[64];
    snprintf(cab, sizeof cab, "{\"event\":\"ligado\",\"conn\":%u,\"endereco\":\"", conn);
    emitir(CONN_CONTROLE, std::string(cab) + json_escapar(endereco) + "\"}");
}

void evento_desligado(uint32_t conn) {
    char buf[64];
    snprintf(buf, sizeof buf, "{\"event\":\"desligado\",\"conn\":%u}", conn);
    emitir(CONN_CONTROLE, buf);
}

void evento_erro(const std::string& texto) {
    emitir(CONN_CONTROLE, "{\"event\":\"erro\",\"texto\":\"" + json_escapar(texto) + "\"}");
}

// ── stdin ───────────────────────────────────────────────────────────────────

bool ler_exacto(HANDLE h, uint8_t* buf, size_t n) {
    size_t lido = 0;
    while (lido < n) {
        DWORD r = 0;
        if (!ReadFile(h, buf + lido, (DWORD)(n - lido), &r, nullptr)) {
            return false;
        }
        if (r == 0) {
            return false;  // pipe fechado
        }
        lido += r;
    }
    return true;
}

// ── ligacoes ────────────────────────────────────────────────────────────────

// Le bytes do telefone e entrega ao Python. Uma thread por ligacao: `LoadAsync`
// bloqueia, e uma ligacao parada nao pode prender as outras.
void bombeia(StreamSocket socket, uint32_t conn) {
    // Sem isto o primeiro `LoadAsync` falha com RO_E_NOT_INITIALIZED e a
    // ligacao morre logo apos abrir — so um aviso no log, sem crash.
    winrt::init_apartment(winrt::apartment_type::multi_threaded);

    try {
        DataReader reader(socket.InputStream());
        while (!g_parar.load()) {
            // `LoadAsync` devolve assim que ha pelo menos um byte. A alternativa
            // (ler um buffer cheio) esperaria ate encher, e a resposta ao `auth`
            // do telefone nunca chegaria — o telefone ficaria a olhar para o
            // ecrã e o utilizador para o rato.
            uint32_t lido = reader.LoadAsync(4096u).get();
            if (lido == 0) {
                break;  // o telefone fechou
            }
            std::vector<uint8_t> buf(lido);
            reader.ReadBytes(buf);
            emitir(conn, std::string(reinterpret_cast<char*>(buf.data()), lido));
        }
    } catch (winrt::hresult_error const& e) {
        aviso("leitura interrompida (conn " + std::to_string(conn) + "): " +
              para_utf8(e.message()));
    } catch (...) {
        aviso("leitura falhou (conn " + std::to_string(conn) + ")");
    }

    {
        std::lock_guard<std::mutex> lock(g_ligacoes);
        g_sockets.erase(conn);
    }
    try {
        socket.Close();
    } catch (...) {
    }
    evento_desligado(conn);
}

void escreve(uint32_t conn, const std::vector<uint8_t>& payload) {
    StreamSocket socket{nullptr};
    {
        std::lock_guard<std::mutex> lock(g_ligacoes);
        auto it = g_sockets.find(conn);
        if (it == g_sockets.end()) {
            return;  // ligacao ja foi abaixo; descartar e o certo
        }
        socket = it->second;
    }
    try {
        DataWriter writer(socket.OutputStream());
        writer.WriteBytes(std::vector<uint8_t>(payload));
        // `StoreAsync` e o que empurra os bytes para a ligacao; sem ele ficam
        // no buffer do escritor e o telefone nao recebe nada.
        writer.StoreAsync().get();
    } catch (winrt::hresult_error const& e) {
        aviso("escrita falhou (conn " + std::to_string(conn) + "): " +
              para_utf8(e.message()));
    }
}

}  // namespace

int main(int argc, char** argv) {
    // So `apartment_type`: o `apartment_flags` de outros exemplos do WINSDK nao
    // existe nesta versao.

    // Fronteira Python<->C++ sem Bluetooth: sem isto, o unico teste do envelope
    // seria um telemóvel na mão, e um erro de endianness aqui corrompe todos os
    // comandos sem dar erro nenhum. Escreve envelopes conhecidos e sai.
    if (argc > 1 && strcmp(argv[1], "--selftest-envelope") == 0) {
        emitir(CONN_CONTROLE, "{\"event\":\"selftest\"}");
        emitir(1, "ab");
        emitir(7, std::string("\x00\xff\x80\x7f", 4));  // apanha endianness
        emitir(0x01020304u, "x");
        emitir(2, "");
        return 0;
    }

    winrt::init_apartment(winrt::apartment_type::multi_threaded);

    HANDLE hin = GetStdHandle(STD_INPUT_HANDLE);

    // `listener` e `provider` vivem no ambito de `main`, e nao dentro do `try`.
    // Sao reference-counted: no fim do ambito seriam destruidos e o Windows
    // deixaria de anunciar o servico e de aceitar ligacoes — sem erro nenhum, so
    // com um telefone na maoa dizer que nao encontra o Maouse.
    StreamSocketListener listener;
    RfcommServiceProvider provider{nullptr};

    // Qual chamada esta a falhar. As tres do bloco seguinte falham por razoes
    // muito diferentes (adaptador/radio, nome do servico, publicacao no SDP) e o
    // HRESULT sozinho nao as separa — sem isto, um radio desligado e um
    // StartAdvertising mal formado produzem o mesmo diagnostico, e da-se tempo
    // a recuperar a coisa errada.
    const char* etapa = "preparacao";

    try {
        // O `StreamSocketListener` e quem aceita as ligacoes; o
        // `StartAdvertising` e quem publica o UUID no SDP, para o telefone
        // encontrar o servico quando procura.
        listener.ConnectionReceived(
            [](StreamSocketListener const&,
               StreamSocketListenerConnectionReceivedEventArgs const& args) {
                try {
                    StreamSocket socket = args.Socket();
                    uint32_t conn = g_proximo_conn.fetch_add(1);
                    {
                        std::lock_guard<std::mutex> lock(g_ligacoes);
                        g_sockets[conn] = socket;
                    }
                    // O endereco e o que impede o limitador de tentativas do
                    // Python de recomecar cada vez que o telefone renova a
                    // ligacao.
                    std::string endereco;
                    try {
                        // O endereco vive em `Information()`, nao no socket:
                        // `StreamSocket` nao tem `RemoteHostName()`, so
                        // `IStreamSocketInformation` tem.
                        endereco = para_utf8(
                            socket.Information().RemoteHostName().DisplayName());
                    } catch (...) {
                    }
                    evento_ligado(conn, endereco);
                    std::thread(bombeia, socket, conn).detach();
                } catch (winrt::hresult_error const& e) {
                    evento_erro("nao aceitei a ligacao: " + para_utf8(e.message()));
                }
            });

        etapa = "CreateAsync (criar RfcommServiceProvider)";
        provider =
            RfcommServiceProvider::CreateAsync(RfcommServiceId::FromUuid(guid_de(SERVICO)))
            .get();

        // O nome do servico tem de ser o `ServiceId` do provider — e nao um
        // nome vazio ou arbitrario. E assim que o Windows sabe que este
        // listener e um canal RFCOMM e nao um porto TCP efemeiro. Com o nome
        // errado, `StartAdvertising` falha com E_INVALIDDATA (0x8007000D); sem
        // nenhum bind, falha com "must be bound". Duas armadilhas, mesma API.
        etapa = "BindServiceNameAsync (ligar ao nome do servico)";
        listener.BindServiceNameAsync(provider.ServiceId().AsString()).get();

        etapa = "StartAdvertising (publicar o UUID no SDP)";
        provider.StartAdvertising(listener, true);
        aviso("servico RFCOMM registado: " + para_utf8(winrt::to_hstring(SERVICO)));
    } catch (winrt::hresult_error const& e) {
        char hr[16];
        snprintf(hr, sizeof hr, "0x%08X", (unsigned)e.code().value);
        evento_erro("falhou em " + std::string(etapa) + " (" + hr + "): " +
                    para_utf8(e.message()));
        return 2;
    }

    // Laco principal: le envelopes do Python. `conn > 0` escreve num telefone;
    // `conn == 0` e controlo. Um envelope sem payload e a forma de parar.
    while (!g_parar.load()) {
        uint8_t cab[8];
        if (!ler_exacto(hin, cab, sizeof cab)) {
            break;  // Python fechou o pipe: fim de vida
        }
        uint32_t tamanho, conn;
        memcpy(&tamanho, cab, 4);
        memcpy(&conn, cab + 4, 4);
        if (tamanho < 4 || tamanho > MAX_ENVELOPE) {
            aviso("envelope invalido do Python — a desligar para nao dessincronizar");
            break;
        }
        uint32_t n = tamanho - 4;
        std::vector<uint8_t> payload(n);
        if (n > 0 && !ler_exacto(hin, payload.data(), n)) {
            break;
        }
        if (conn == CONN_CONTROLE) {
            if (n == 0) {
                break;  // parar pedido
            }
            continue;  // hoje o Python so manda dados; controlo e opcional
        }
        escreve(conn, payload);
    }

    g_parar.store(true);

    // Tirar o servico do ar antes de fechar as ligacoes: senao o telefone ainda
// tenta entrar num processo que ja esta a morrer.
    try {
        provider.StopAdvertising();
    } catch (...) {
    }

    {
        std::lock_guard<std::mutex> lock(g_ligacoes);
        for (auto& par : g_sockets) {
            try {
                par.second.Close();
            } catch (...) {
            }
        }
        g_sockets.clear();
    }
    return 0;
}