# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []

# Assets do produto empacotados junto do .exe (paridade com o build.bat).
# Só os diretórios que existem; `.ttf`/`.png` são lidos em runtime pelo Qt.
for src, dst in (
    ("assets/brand", "assets/brand"),
    ("assets/fonts", "assets/fonts"),
    ("assets/models", "assets/models"),
):
    if os.path.isdir(src):
        datas.append((src, dst))
# Modelos críticos de arranque vêm DENTRO do instalador (offline, sem download
# na primeira execução). Vosk e Piper mantêm-se como download por-utilizador
# (escrevível em %LOCALAPPDATA%\Maouse\models) para não inflar o instalador.
for src, dst in (
    ("models/hand_landmarker.task", "models"),
    ("models/gesture_mlp.npz", "models"),
):
    if os.path.isfile(src):
        datas.append((src, dst))
for pkg in ("mediapipe", "vosk"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# `core/licensing.py` importa este módulo DENTRO de uma função, por isso a
# análise estática do PyInstaller não o vê. Sem esta linha, o .exe distribuído
# fica sem o endpoint do license-server e a ativação de chaves Pro não
# funciona — ver docs/DESKTOP_LICENSE_URL.md. Gerado por
# tools/gen_license_endpoint.py antes do bake (build.bat, passo 4/7).
if os.path.isfile("core/_license_endpoint.py"):
    hiddenimports.append("core._license_endpoint")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["IPython"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Maouse",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon="assets/brand/maouse.ico",
    version="version_info.txt",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Maouse",
)
