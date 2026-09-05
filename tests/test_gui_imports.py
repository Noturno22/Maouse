import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from ui import main_window, menu_panel
from ui.theme import MAIN_STYLESHEET


def test_gui_stack_imports():
    assert hasattr(main_window, "MainWindow")
    assert hasattr(menu_panel, "MenuPanel")
    assert hasattr(menu_panel, "MenuButton")


def test_menu_panel_widgets_import_from_correct_modules():
    assert hasattr(menu_panel, "QMenu")
    assert hasattr(menu_panel, "QLabel")


def test_main_stylesheet_keeps_bundled_fonts_and_no_placeholders():
    assert isinstance(MAIN_STYLESHEET, str) and len(MAIN_STYLESHEET) > 1000
    for family in ("Inter", "Space Grotesk", "JetBrains Mono"):
        assert family in MAIN_STYLESHEET
    assert "\x00" not in MAIN_STYLESHEET
    assert "Segoe UI" in MAIN_STYLESHEET