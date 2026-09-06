import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from ui import toast
from ui.theme import MAIN_STYLESHEET


@pytest.fixture(scope="module", autouse=True)
def _qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_toast_normal_uses_toast_object_name():
    t = toast.Toast()
    t.show_toast("ok")
    assert t.objectName() == "Toast"


def test_toast_danger_uses_lock_object_name():
    t = toast.Toast()
    t.show_toast("PRO", danger=True)
    assert t.objectName() == "ToastLocked"


def test_toast_returns_to_normal_object_name():
    t = toast.Toast()
    t.show_toast("PRO", danger=True)
    t.show_toast("ok")
    assert t.objectName() == "Toast"


def test_stylesheet_has_locked_window_border():
    assert 'MainWindow[locked="true"]' in MAIN_STYLESHEET


def test_look_logo_exists_for_flash():
    root = os.path.dirname(os.path.dirname(os.path.abspath(toast.__file__)))
    assert os.path.isfile(os.path.join(root, "assets", "brand", "logo-look.png"))