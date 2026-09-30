import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from _dialog_spies import install
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

import ui.license_dlg as ld
from core.licensing import Tier
from i18n import tr


@pytest.fixture(scope="session", autouse=True)
def _qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class ProLicense:
    @property
    def is_pro(self):
        return True

    def deactivate(self):
        pass


class Cfg:
    license_tier = "pro"


@pytest.fixture(autouse=True)
def _spy(monkeypatch):
    return install(monkeypatch, ld)


@pytest.fixture
def dialog():
    dlg = ld.LicenseDialog(Cfg(), ProLicense())
    yield dlg
    dlg.close()


def test_pro_dialog_uses_minimal_layout(dialog):
    assert dialog.width() == 560
    assert dialog.height() == 340
    chips = [w for w in dialog.findChildren(QLabel) if w.objectName() == "HeroChip"]
    assert chips, "falta HeroChip na UI PRO"


def test_pro_dialog_remove_button_uses_secondary_style(dialog):
    btns = [b for b in dialog.findChildren(QPushButton)
            if b.objectName() == "SettingsButtonSecondary"]
    assert len(btns) == 1
    assert btns[0].text() == tr("license.remove")


def test_pro_dialog_deactivates_and_accepts(dialog):
    dialog._deactivate()
    assert dialog._cfg.license_tier == Tier.FREE.value
    assert dialog.result() == 1


def test_desativar_avisa_o_utilizador(dialog, _spy):
    """Desactivar uma licença é uma acção destrutiva: tem de ser confirmada.

    O `_cfg.license_tier` já é posto a FREE e o diálogo já fecha — o que
    desaparece em silêncio é a confirmação. Com o substituto mudo antigo,
    este teste passava sem uma única mensagem ser mostrada.
    """
    dialog._deactivate()
    assert _spy.count == 1, "desactivar mostra exactamente uma mensagem"
    assert _spy.of_kind("information"), "a confirmação é informação, não aviso nem erro"
