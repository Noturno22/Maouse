import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

import config
from config import Config
from core.licensing import Tier
from ui.settings_dlg import SettingsDialog
from ui.tune_slider import TuneSlider


@pytest.fixture(scope="module", autouse=True)
def _qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class FakeLM:
    tier = Tier.PRO


@pytest.fixture(autouse=True)
def _iso_settings(tmp_path, monkeypatch):
    monkeypatch.setattr(
        config, "SETTINGS_FILE", str(tmp_path / "settings.json")
    )


@pytest.fixture
def dlg():
    dlg = SettingsDialog(Config(), "NORMAL", license_mgr=FakeLM())
    yield dlg
    dlg.close()


def test_cursor_panel_sliders_are_tune_sliders(dlg):
    assert isinstance(dlg._gain_sl, TuneSlider)
    assert isinstance(dlg._dead_sl, TuneSlider)
    assert isinstance(dlg._stable_sl, TuneSlider)
    assert dlg._gain_sl.value() == int(Config().move_gain * 10)


def test_reset_defaults_still_reaches_sliders(dlg):
    dlg._gain_sl.setValue(12)
    dlg._dead_sl.setValue(19)
    dlg._stable_sl.setValue(5)
    dlg._reset_defaults()
    dlg._save()
    assert dlg._gain_sl.value() == int(Config().move_gain * 10)
