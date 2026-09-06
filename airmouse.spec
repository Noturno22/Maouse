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
for pkg in ("mediapipe", "vosk"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

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
    name="AirMouse",
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
    name="AirMouse",
)
