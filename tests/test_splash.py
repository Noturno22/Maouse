import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from ui import splash


@pytest.fixture(scope="module", autouse=True)
def _qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_splash_path_resolves_logo():
    path = splash.splash_path()
    assert path is not None
    assert path.endswith("logo.png")


def test_render_splash_returns_pixmap():
    pix = splash.render_splash(size=256)
    assert pix is not None
    assert not pix.isNull()
    assert pix.width() == 256
    assert pix.height() == 256


def test_render_splash_missing_file_returns_none(monkeypatch):
    monkeypatch.setattr(splash, "splash_path", lambda: None)
    assert splash.render_splash() is None


def test_show_splash_returns_widget_and_closes():
    s = splash.show_splash(ms=10, force=True)
    assert s is not None
    assert s.isVisible()
    s.close()
    assert not s.isVisible()


def test_show_splash_disabled_on_windows(monkeypatch):
    monkeypatch.setattr(splash, "splash_enabled", lambda: False)
    assert splash.show_splash(ms=5) is None


def test_show_splash_enabled_off_windows(monkeypatch):
    monkeypatch.setattr(splash, "splash_enabled", lambda: True)
    s = splash.show_splash(ms=5)
    assert s is not None
    s.close()
