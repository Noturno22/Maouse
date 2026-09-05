import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QFrame, QGraphicsEffect, QLabel

import ui.license_dlg as ld
from core.licensing import Tier
from i18n import tr


@pytest.fixture(scope="session", autouse=True)
def _qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class FakeLicense:
    @property
    def is_pro(self):
        return False

    def trial_remaining_seconds(self):
        return 0

    def open_checkout(self, product, vendor_id):
        return True

    def activate(self, key):
        return True

    def deactivate(self):
        pass


class Cfg:
    license_tier = "free"


@pytest.fixture
def dialog(monkeypatch):
    class Box:
        @staticmethod
        def information(*a, **k):
            pass

        @staticmethod
        def warning(*a, **k):
            pass
    monkeypatch.setattr(ld, "QMessageBox", Box)
    dlg = ld.LicenseDialog(Cfg(), FakeLicense())
    yield dlg
    dlg.close()


def test_free_dialog_has_status_chip_without_pulse(dialog):
    chips = [w for w in dialog.findChildren(QLabel) if w.objectName() == "StatusChip"]
    assert chips, "falta StatusChip na UI FREE"
    assert dialog.width() == 620
    assert not any(isinstance(w, QGraphicsEffect)
                   for w in dialog.findChildren(QGraphicsEffect))


def test_free_dialog_plans_render_dynamically(dialog):
    cards = [w for w in dialog.findChildren(QFrame) if w.objectName() == "PlanCard"]
    assert len(cards) == len(ld._PRODUCTS)
    assert dialog._cta.text() == f"{tr('license.cta')} · {ld._PRODUCTS[0][2]}"


def test_clicking_plan_updates_selection(dialog):
    cards = [w for w in dialog.findChildren(QFrame) if w.objectName() == "PlanCard"]
    target = next(c for c in cards if c._plan_id == ld._PRODUCTS[1][0])
    target.selected.emit(ld._PRODUCTS[1][0])
    assert target.selected
    assert f"{ld._PRODUCTS[1][2]}" in dialog._cta.text()
    for c in cards:
        if c._plan_id == ld._PRODUCTS[1][0]:
            assert c.property("selected") == "true"
        else:
            assert c.property("selected") == "false"


def test_key_activation_updates_cfg_and_accepts(dialog):
    dialog._key_edit.setText("TEST-KEY-1234")
    dialog._activate_key()
    assert dialog._cfg.license_tier == Tier.PRO.value
    assert dialog.result() == 1
