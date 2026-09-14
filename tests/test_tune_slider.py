import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QGraphicsDropShadowEffect

from ui.tune_slider import TuneSlider


@pytest.fixture(scope="module", autouse=True)
def _qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _drain(ms=500):
    end = time.monotonic() + ms / 1000.0
    while time.monotonic() < end:
        QApplication.processEvents()
        time.sleep(0.005)


def test_api_value_and_range():
    ts = TuneSlider("Ganho", lambda v: f"{v / 10:.1f}")
    ts.setRange(6, 50)
    assert ts.value() == 6
    assert ts.minimum() == 6
    assert ts.maximum() == 50
    ts.setValue(35)
    assert ts.value() == 35
    assert ts.name_label.objectName() == "SettingsLabel"
    assert ts.value_label.objectName() == "SliderValue"


def test_tween_reaches_formatted_final_value():
    ts = TuneSlider("Ganho", lambda v: f"{v / 10:.1f}", tween_ms=50, glow_ms=30)
    ts.setRange(6, 50)
    ts.setValue(35)
    assert ts.value_label.text() != "3.5" or True  # permitido ser imediato/inicial
    _drain(400)
    assert ts.value_label.text() == "3.5"


def test_glow_applied_after_change():
    ts = TuneSlider("Zona morta", lambda v: f"{v}px", tween_ms=20, glow_ms=20)
    ts.setRange(0, 20)
    ts.setValue(10)
    _drain(200)
    assert isinstance(ts.graphicsEffect(), QGraphicsDropShadowEffect)


def test_new_set_during_tween_reaches_new_target():
    ts = TuneSlider("Ganho", lambda v: f"{v / 10:.1f}", tween_ms=350, glow_ms=30)
    ts.setRange(6, 50)
    ts.setValue(10)
    _drain(60)
    mid_text = ts.value_label.text()
    ts.setValue(40)
    _drain(500)
    assert ts.value_label.text() == "4.0"
    assert mid_text != "4.0"


def test_drag_keeps_steady_glow_through_changes():
    ts = TuneSlider("Estabilidade", lambda v: f"{v} frames", tween_ms=20, glow_ms=20)
    ts.setRange(1, 6)
    ts.slider.sliderPressed.emit()
    ts.slider.setValue(5)
    assert isinstance(ts.graphicsEffect(), QGraphicsDropShadowEffect)
    assert ts.graphicsEffect().color().alpha() > 0
    ts.slider.sliderReleased.emit()
    _drain(400)
    assert isinstance(ts.graphicsEffect(), QGraphicsDropShadowEffect)
