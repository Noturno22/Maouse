#pragma once

#include <windows.h>

#include <winrt/base.h>

#include <array>
#include <cstdint>

// Converte "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX" nos campos que o construtor de
// `winrt::guid` espera. Nao ha endianness a baralhar: os bytes sao lidos na ordem
// em que aparecem na cadeia, e e o `operator GUID const&` da propria struct que
// reconverte para o formato do Win32. Evita `UuidFromString`, cuja assinatura muda
// entre SDKs e que arrastava uma lib extra de link.
//
// Vive num header partilhado, e nao repetido em cada ferramenta, porque e um
// parser de byte-order: duas copias divergem em silencio no primeiro edit.
inline winrt::guid guid_de(wchar_t const* texto) {
    unsigned char cru[16] = {};
    int nibbles = 0;
    for (int i = 0; texto[i] != 0 && nibbles < 32; ++i) {
        wchar_t c = texto[i];
        if (c == L'-') {
            continue;
        }
        int v = 0;
        if (c >= L'0' && c <= L'9') {
            v = c - L'0';
        } else if (c >= L'a' && c <= L'f') {
            v = c - L'a' + 10;
        } else if (c >= L'A' && c <= L'F') {
            v = c - L'A' + 10;
        } else {
            throw winrt::hresult_error(E_INVALIDARG, L"UUID invalido: " + winrt::to_hstring(texto));
        }
        cru[nibbles / 2] =
            static_cast<unsigned char>(cru[nibbles / 2] | (v << (nibbles % 2 ? 0 : 4)));
        ++nibbles;
    }
    if (nibbles != 32) {
        throw winrt::hresult_error(E_INVALIDARG, L"UUID invalido: " + winrt::to_hstring(texto));
    }
    return winrt::guid(
        (uint32_t(cru[0]) << 24) | (uint32_t(cru[1]) << 16) | (uint32_t(cru[2]) << 8) | cru[3],
        uint16_t((uint16_t(cru[4]) << 8) | cru[5]),
        uint16_t((uint16_t(cru[6]) << 8) | cru[7]),
        std::array<uint8_t, 8>{cru[8], cru[9], cru[10], cru[11], cru[12], cru[13], cru[14], cru[15]});
}