"""Fontes embebidas do Mãouse (Inter / Space Grotesk / JetBrains Mono).

Registadas via ``QFontDatabase`` a partir de ``assets/fonts`` (licenças OFL
incluídas) para tipografia consistente em qualquer máquina. Chamar
``ensure_fonts()`` depois de criar o ``QApplication`` e antes de mostrar UI.
"""

import os
import sys

from PySide6.QtGui import QFontDatabase

EXPECTED_FONTS = {
    "Inter": "Inter-Variable.ttf",
    "Space Grotesk": "SpaceGrotesk-Variable.ttf",
    "JetBrains Mono": "JetBrainsMono-Variable.ttf",
}

_loaded = {}


def font_dir():
    """Resolve o diretório das fontes (source, exe congelado ou cwd)."""
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [os.path.join(here, "assets", "fonts")]
    if getattr(sys, "frozen", False):
        candidates.insert(0, os.path.join(os.path.dirname(sys.executable), "assets", "fonts"))
        candidates.insert(
            1, os.path.join(os.path.dirname(sys.executable), "_internal", "assets", "fonts")
        )
    candidates.append(os.path.join(os.getcwd(), "assets", "fonts"))
    for c in candidates:
        if os.path.isdir(c):
            return c
    return candidates[0]


def ensure_fonts(force=False):
    """Regista as fontes embebidas (idempotente) e devolve {family: path}."""
    if _loaded and not force:
        return dict(_loaded)
    base = font_dir()
    for family, fname in EXPECTED_FONTS.items():
        path = os.path.join(base, fname)
        if not os.path.isfile(path):
            continue
        fid = QFontDatabase.addApplicationFont(path)
        if fid >= 0:
            _loaded[family] = path
    return dict(_loaded)


def is_loaded():
    return bool(_loaded)
