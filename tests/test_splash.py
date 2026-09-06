import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from ui import splash


@pytest.fixture(scope="module", autouse=True)
def _qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_splash_path_resolves_svg():
    path = splash.splash_path()
    assert path is not None
    assert path.endswith("splash.svg")


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
    s = splash.show_splash(ms=10)
    assert s is not None
    assert s.isVisible()
    s.close()
    assert not s.isVisible()
