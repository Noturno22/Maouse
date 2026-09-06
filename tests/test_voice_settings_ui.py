import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QDialog, QWidget

import core.audio_devices as ad
import config
import ui.settings_dlg as sd
from core.licensing import Tier


@pytest.fixture(scope="module")
def _qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class FakeLicense:
    tier = Tier.FREE


def mic_devices():
    # list_input_devices() (core/audio_devices) já devolve apenas dispositivos
    # com canais de entrada; o mock espelha essa fronteira.
    return [
        (0, "Microfone Realtek HD"),
        (1, "Mic USB"),
    ]


def build(monkeypatch, devices):
    monkeypatch.setattr(ad, "list_input_devices", lambda: devices)
    dlg = sd.SettingsDialog(config.Config(), "SMOOTH", license_mgr=FakeLicense())
    return dlg


def test_mic_combo_lists_only_inputs(monkeypatch, _qapp):
    dlg = build(monkeypatch, mic_devices())
    try:
        assert dlg._mic_combo is not None
        names = [dlg._mic_combo.itemText(i) for i in range(1, dlg._mic_combo.count())]
        assert names == ["Microfone Realtek HD", "Mic USB"]
    finally:
        dlg.close()


def test_mic_combo_preselects_saved_device(monkeypatch, _qapp):
    cfg = config.Config()
    cfg.mic_device = "Mic USB"
    monkeypatch.setattr(ad, "list_input_devices", lambda: mic_devices())
    dlg = sd.SettingsDialog(cfg, "SMOOTH", license_mgr=FakeLicense())
    try:
        assert dlg._mic_combo.currentData() == "Mic USB"
    finally:
        dlg.close()


def test_mic_combo_save_roundtrip(monkeypatch, _qapp):
    cfg = config.Config()
    monkeypatch.setattr(ad, "list_input_devices", lambda: mic_devices())
    dlg = sd.SettingsDialog(cfg, "SMOOTH", license_mgr=FakeLicense())
    try:
        idx = dlg._mic_combo.findData("Mic USB")
        assert idx >= 0
        dlg._mic_combo.setCurrentIndex(idx)
        dlg._save()
        assert cfg.mic_device == "Mic USB"
    finally:
        dlg.close()


def test_mic_combo_none_when_no_devices(monkeypatch, _qapp):
    monkeypatch.setattr(ad, "list_input_devices", lambda: [])
    dlg = sd.SettingsDialog(config.Config(), "SMOOTH", license_mgr=FakeLicense())
    try:
        assert dlg._mic_combo is None
    finally:
        dlg.close()