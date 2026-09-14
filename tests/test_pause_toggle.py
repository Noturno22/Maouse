import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QGraphicsDropShadowEffect

from ui.pause_toggle import PauseToggle


@pytest.fixture(scope="module", autouse=True)
def _qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _drain(ms=500):
    end = time.monotonic() + ms / 1000.0
    while time.monotonic() < end:
        QApplication.processEvents()
        time.sleep(0.005)


def test_default_state_is_on_with_glow():
    pt = PauseToggle()
    assert pt.is_paused() is False
    assert "ON" in pt.text().upper()
    eff = pt.graphicsEffect()
    assert isinstance(eff, QGraphicsDropShadowEffect)
    assert eff.color().alpha() > 0


def test_set_paused_true_shows_off_no_glow():
    pt = PauseToggle(glow_ms=30)
    pt.set_paused(True)
    _drain(400)
    assert pt.is_paused() is True
    assert "OFF" in pt.text().upper()
    eff = pt.graphicsEffect()
    assert isinstance(eff, QGraphicsDropShadowEffect)
    assert eff.color().alpha() == 0


def test_set_paused_false_restores_on():
    pt = PauseToggle(glow_ms=30)
    pt.set_paused(True)
    _drain(400)
    pt.set_paused(False)
    _drain(400)
    assert pt.is_paused() is False
    assert "ON" in pt.text().upper()
    assert pt.graphicsEffect().color().alpha() > 0


def test_click_toggles_state():
    pt = PauseToggle(glow_ms=30)
    pt.click()
    _drain(400)
    assert pt.is_paused() is True
    assert "OFF" in pt.text().upper()
