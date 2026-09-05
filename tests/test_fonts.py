import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from ui import fonts
from ui.theme import MAIN_STYLESHEET


@pytest.fixture(scope="module", autouse=True)
def _qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_bundled_font_files_exist():
    d = fonts.font_dir()
    for fname in fonts.EXPECTED_FONTS.values():
        assert os.path.isfile(os.path.join(d, fname)), f"falta {fname}"


def test_ensure_fonts_registers_design_families():
    fonts.ensure_fonts()
    all_families = set(QFontDatabase.families())
    for family in ("Inter", "Space Grotesk", "JetBrains Mono"):
        assert family in all_families, f"{family} nao registada"


def test_stylesheet_leads_with_bundled_families():
    assert "'Space Grotesk'" in MAIN_STYLESHEET
    assert "'Inter'" in MAIN_STYLESHEET
    assert "'JetBrains Mono'" in MAIN_STYLESHEET
    assert "'Segoe UI'" in MAIN_STYLESHEET
    assert "'Cascadia Code'" in MAIN_STYLESHEET


def test_ensure_fonts_idempotent():
    first = fonts.ensure_fonts()
    second = fonts.ensure_fonts()
    assert first == second