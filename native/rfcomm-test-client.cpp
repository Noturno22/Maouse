// Cliente RFCOMM de teste do Maouse.
//
// Serve para duas coisas:
//   1. Provar o caminho completo (telefone -> PC) sem esperar pelo cliente Android.
//   2. Ser a referencia de que o Fortune pode ler para confirmar que o cliente dele
//      fala a mesma lingua que o do PC.
//
// Nao faz parte do produto: e ferramenta. Compila para o mesmo toolchain do
// servidor (`native\build-host.bat` serviu de modelo).
//
// Uso (o PC tem de ter o `maouse-bluetooth-host.exe` a correr, e o servico
// registado no Windows):
//
//     native\rfcomm-test-client.exe --code 123456
//
// ── A armadilha do endianness ────────────────────────────────────────────────
// Este ficheiro tem DOIS endianness diferentes e nao se pode misturar:
//
//   telefone -> PC (stream RFCOMM)  tamanho em 4 bytes BIG-endian
//   PC -> host (envelope no pipe)   tamanho em 4 bytes LITTLE-endian
//
// O primeiro e o que o Fortune tem de escrever. O segundo e interno do PC e
// nunca aparece na ligacao. Ver docs/PROTOCOLO_REMOTE.md.

#include <windows.h>

#include <winrt/Windows.Devices.Bluetooth.h>
#include <winrt/Windows.Devices.Bluetooth.Rfcomm.h>
#include <winrt/Windows.Devices.Enumeration.h>
#include <winrt/Windows.Foundation.Collections.h>
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Networking.Sockets.h>
#include <winrt/Windows.Storage.Streams.h>

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "guid_texto.h"

using namespace winrt::Windows::Devices::Bluetooth;
using namespace winrt::Windows::Devices::Bluetooth::Rfcomm;
using namespace winrt::Windows::Devices::Enumeration;
using namespace winrt::Windows::Foundation;
using namespace winrt::Windows::Networking::Sockets;
using namespace winrt::Windows::Storage::Streams;

namespace {

constexpr wchar_t SERVICO[] = L"D9905F51-F497-49A4-88DF-784D82249EFD";
constexpr size_t TAM_FRAME = 4;

void aviso(const std::string& t) {
    fprintf(stderr, "%s\n", t.c_str());
    fflush(stderr);
}

std::string para_utf8(const winrt::hstring& s) {
    int n = WideCharToMultiByte(CP_UTF8, 0, s.c_str(), -1, nullptr, 0, nullptr, nullptr);
    std::string buf(n > 0 ? n : 1, '\0');
    if (n > 0) {
        WideCharToMultiByte(CP_UTF8, 0, s.c_str(), -1, buf.data(), n, nullptr, nullptr);
        buf.resize(n - 1);
    }
    return buf;
}

// O prefixo de 4 bytes, big-endian. E o que o Fortune tem de escrever.
std::vector<uint8_t> frame(const std::string& msg) {
    uint32_t n = (uint32_t)msg.size();
    std::vector<uint8_t> out(TAM_FRAME + msg.size());
    out[0] = (uint8_t)(n >> 24);
    out[1] = (uint8_t)(n >> 16);
    out[2] = (uint8_t)(n >> 8);
    out[3] = (uint8_t)n;
    memcpy(out.data() + TAM_FRAME, msg.data(), msg.size());
    return out;
}

// Acumula o stream e devolve as mensagens completas. O SO pode partir uma
// mensagem em varios `LoadAsync`, e podem chegar varias numa so leitura.
class Frames {
public:
    void feed(const uint8_t* d, size_t n) { buf_.insert(buf_.end(), d, d + n); }

    std::vector<std::string> take() {
        std::vector<std::string> out;
        while (true) {
            if (buf_.size() < TAM_FRAME) break;
            uint32_t total = ((uint32_t)buf_[0] << 24) | ((uint32_t)buf_[1] << 16) |
                             ((uint32_t)buf_[2] << 8) | (uint32_t)buf_[3];
            if (total == 0 || total > 64u * 1024u) {
                aviso("tamanho invalido do PC (" + std::to_string(total) + ") - a largar");
                buf_.clear();
                break;
            }
            if (buf_.size() < TAM_FRAME + total) break;
            out.emplace_back((char*)buf_.data() + TAM_FRAME, total);
            buf_.erase(buf_.begin(), buf_.begin() + TAM_FRAME + total);
        }
        return out;
    }

private:
    std::vector<uint8_t> buf_;
};

void enviar(StreamSocket& socket, DataWriter& writer, const std::string& msg) {
    std::vector<uint8_t> b = frame(msg);
    writer.WriteBytes(b);
    writer.StoreAsync().get();
    printf("  -> %s\n", msg.c_str());
    fflush(stdout);
}

}  // namespace

int wmain(int argc, wchar_t** argv) {
    winrt::init_apartment(winrt::apartment_type::multi_threaded);

    std::string code;
    for (int i = 1; i < argc; i++) {
        if (wcscmp(argv[i], L"--code") == 0 && i + 1 < argc) {
            int n = WideCharToMultiByte(CP_UTF8, 0, argv[i + 1], -1, nullptr, 0, nullptr, nullptr);
            std::string b(n > 0 ? n : 1, '\0');
            if (n > 0) {
                WideCharToMultiByte(CP_UTF8, 0, argv[i + 1], -1, b.data(), n, nullptr, nullptr);
                b.resize(n - 1);
            }
            code = b;
            i++;  // o codigo ja foi lido
        }
    }
    if (code.empty()) {
        aviso("uso: rfcomm-test-client.exe --code 123456");
        return 2;
    }

    RfcommServiceId alvo = RfcommServiceId::FromUuid(guid_de(SERVICO));

    StreamSocket socket{nullptr};

    aviso("a procurar dispositivos emparelhados...");
    // O caminho e: selector de BluetoothDevice -> FindAllAsync -> FromIdAsync em
    // cada um -> GetRfcommServicesForIdAsync, que e quem filtra pelo UUID.
    auto dispositivos = DeviceInformation::FindAllAsync(BluetoothDevice::GetDeviceSelector()).get();

    if (dispositivos.Size() == 0) {
        aviso("nenhum dispositivo Bluetooth emparelhado. Emparelhar o telefone no");
        aviso("Windows primeiro, e ter o maouse-bluetooth-host.exe a correr.");
        return 1;
    }
    aviso("dispositivos emparelhados: " + std::to_string(dispositivos.Size()));

    for (auto&& d : dispositivos) {
        std::string nome = para_utf8(d.Name());
        try {
            BluetoothDevice bt = d.as<BluetoothDevice>();
            aviso("a ver " + nome);

            auto resultado = bt.GetRfcommServicesForIdAsync(alvo).get();
            auto servicos = resultado.Services();
            for (auto&& s : servicos) {
                aviso("  servico encontrado em " + nome);
                // `ServiceId`/`ProtectionLevel`, nao `ConnectionServiceId`/
                // `ConnectionProtectionLevel`: o prefixo so existe no GATT. E o
                // `ConnectAsync` do RFCOMM e o de (HostName, serviceName:string).
                socket.ConnectAsync(s.ConnectionHostName(),
                                    s.ServiceId().AsString())
                    .get();
                break;
            }
            if (socket) break;
        } catch (winrt::hresult_error const& e) {
            char hr[16];
            snprintf(hr, sizeof hr, "0x%08X", (unsigned)e.code().value);
            aviso("  " + nome + " sem este servico (" + hr + ")");
        }
    }

    if (!socket) {
        aviso("nao consegui ligar a nenhum servico");
        return 1;
    }
    aviso("ligado. a mandar auth...");
    printf("\n");

    DataWriter writer(socket.OutputStream());
    DataReader reader(socket.InputStream());
    Frames frames;

    enviar(socket, writer, "{\"cmd\":\"auth\",\"code\":\"" + code + "\"}");

    // O `auth` tem de ser respondido antes de qualquer comando: sem isto o PC
    // mata a sessao e o teste passa a mentir.
    std::string resposta;
    for (int i = 0; i < 50 && resposta.empty(); i++) {
        uint32_t lido = reader.LoadAsync(4096).get();
        if (lido == 0) break;
        std::vector<uint8_t> buf(lido);
        reader.ReadBytes(buf);
        for (const std::string& m : frames.take()) {
            printf("  <- %s\n", m.c_str());
            resposta = m;
        }
    }
    if (resposta.find("\"ok\":true") == std::string::npos) {
        aviso("auth falhou. O resto do teste nao correria: o PC teria matado a sessao.");
        return 1;
    }

    const char* comandos[] = {
        "{\"cmd\":\"ping\"}",
        "{\"cmd\":\"move\",\"dx\":10,\"dy\":-5}",
        "{\"cmd\":\"click\",\"button\":\"left\",\"count\":1}",
        "{\"cmd\":\"scroll\",\"dx\":0,\"dy\":1}",
    };
    for (auto* c : comandos) {
        enviar(socket, writer, c);
        uint32_t lido = reader.LoadAsync(4096).get();
        if (lido == 0) break;
        std::vector<uint8_t> buf(lido);
        reader.ReadBytes(buf);
        for (const std::string& m : frames.take()) {
            printf("  <- %s\n", m.c_str());
        }
    }

    printf("\n  Chegou ao fim: o telefone ligou, autenticou e os comandos\n"
           "  chegaram ao RemoteServer do PC.\n");
    socket.Close();
    return 0;
}