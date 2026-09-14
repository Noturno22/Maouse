#!/usr/bin/env bash
# Arranca o Mãouse no Linux.
cd "$(dirname "$0")"
if [ ! -f .venv/bin/python ]; then
    echo "Ambiente nao configurado. Executa ./setup.sh primeiro."
    exit 1
fi

# Em sessao GNOME/Wayland, o Qt por defeito usa XWayland (xcb) e o Mutter
# nao compoe a janela -> "o Mãouse abriu mas nao aparece". Forcamos o
# backend Wayland nativo do Qt para a janela ficar visivel.
# Nota: em Wayland o rato via pynput (Xorg) nao mexe o cursor virtual; para
# controlo total usa a sessao "GNOME on Xorg" (login: engrenagem -> Xorg).
if [ -n "$WAYLAND_DISPLAY" ] && [ -z "${QT_QPA_PLATFORM:-}" ]; then
    echo "[Mãouse] Sessao Wayland detetada: Qt via 'wayland' (janela visivel)."
    echo "         Para rato/gestos 100% funcionais, usa a sessao GNOME on Xorg."
    export QT_QPA_PLATFORM=wayland
fi

exec .venv/bin/python main.py "$@"