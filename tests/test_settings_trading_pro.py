import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QCheckBox, QPushButton

from config import Config
from core.licensing import Tier
from ui.license_dlg import PADDLE_VENDOR_ID
from ui.settings_dlg import SettingsDialog


@pytest.fixture(scope="module", autouse=True)
def _qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class FakeLM:
    def __init__(self, tier):
        self.tier = tier
        self.called = None

    def open_checkout(self, product, vendor_id):
        self.called = (product, vendor_id)
        return True


def _tv_checkbox(dlg):
    found = [w for w in dlg.findChildren(QCheckBox)
             if "Modo Trading Master" in w.text()]
    assert found, "falta o checkbox do Modo Trading Master"
    return found[0]


def _buy_buttons(dlg):
    return [w for w in dlg.findChildren(QPushButton)
            if "SUBSCREVER TRADING MASTER" in w.text()]


def test_free_locks_trading_master():
    lm = FakeLM(Tier.FREE)
    dlg = SettingsDialog(Config(), "NORMAL", license_mgr=lm)
    try:
        cb = _tv_checkbox(dlg)
        assert not cb.isEnabled()
        assert "[PRO]" in cb.text()
        assert not dlg._tv_combos_edit.isEnabled()
        btn = _buy_buttons(dlg)
        assert len(btn) == 1
        btn[0].click()
        assert lm.called == ("trading_master", PADDLE_VENDOR_ID)
    finally:
        dlg.close()


def test_pro_unlocks_trading_master():
    lm = FakeLM(Tier.PRO)
    dlg = SettingsDialog(Config(), "NORMAL", license_mgr=lm)
    try:
        cb = _tv_checkbox(dlg)
        assert cb.isEnabled()
        assert "[PRO]" not in cb.text()
        assert dlg._tv_combos_edit.isEnabled()
        assert _buy_buttons(dlg) == []
    finally:
        dlg.close()
