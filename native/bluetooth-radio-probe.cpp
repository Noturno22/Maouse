// Sonda de diagnostico: estado do radio Bluetooth e ciclo off/on.
//
// O ciclo pelo PnP (Disable/Enable-PnpDevice) NAO e o mesmo que desligar o
// radio: oPnP reinicia o dispositivo, o radio desliga a antenna. Quando o
// registo SDP devolve 0x800710DF (device not ready) e oPnP ja foi cyclado, o
// radio e a ultima Hypothesis antes de reiniciar o Windows.
//
// Ferramenta de diagnostico, nao faz parte do produto.

#include <windows.h>

#include <winrt/Windows.Devices.Radios.h>
#include <winrt/Windows.Foundation.Collections.h>
#include <winrt/Windows.Foundation.h>

#include <cstdio>

using namespace winrt::Windows::Devices::Radios;
using namespace winrt::Windows::Foundation;

static const char* nome(RadioKind k) {
    switch (k) {
        case RadioKind::Bluetooth: return "Bluetooth";
        case RadioKind::WiFi:      return "WiFi";
        default:                    return "outro";
    }
}

static const char* estado(RadioState s) {
    switch (s) {
        case RadioState::On:     return "ON";
        case RadioState::Off:    return "OFF";
        case RadioState::Disabled: return "DISABLED";
        default:                 return "?";
    }
}

int wmain(int argc, wchar_t** argv) {
    winrt::init_apartment(winrt::apartment_type::multi_threaded);

    try {
        auto radios = Radio::GetRadiosAsync().get();
        printf("radios: %zu\n", radios.Size());

        Radio bt{nullptr};
        for (auto&& r : radios) {
            printf("  %-9s %s\n", nome(r.Kind()), estado(r.State()));
            if (r.Kind() == RadioKind::Bluetooth) bt = r;
        }

        if (!bt) {
            printf("sem radio Bluetooth visivel\n");
            return 1;
        }

        // So cicla se pedirem explicitamente.
        if (argc < 2 || wcscmp(argv[1], L"--toggle") != 0) {
            printf("\n(nada feito; usar --toggle ou --off)\n");
            return 0;
        }

        // `--off` deixa o radio desligado, para testar o caminho de erro do
        // host sem ter de o religar a mao. E o que produz 0x800710DF.
        if (wcscmp(argv[1], L"--off") == 0) {
            printf("\na desligar...\n");
            bt.SetStateAsync(RadioState::Off).get();
            Sleep(3000);
            printf("  agora: %s\n", estado(bt.State()));
            return 0;
        }

        printf("\na desligar...\n");
        bt.SetStateAsync(RadioState::Off).get();
        Sleep(3000);
        printf("  agora: %s\n", estado(bt.State()));

        printf("a ligar...\n");
        bt.SetStateAsync(RadioState::On).get();
        Sleep(5000);
        printf("  agora: %s\n", estado(bt.State()));
        printf("\nciclo completo\n");
        return 0;
    } catch (winrt::hresult_error const& e) {
        char hr[16];
        snprintf(hr, sizeof hr, "0x%08X", (unsigned)e.code().value);
        printf("falhou: %s\n", hr);
        return 2;
    }
}