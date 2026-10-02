import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from _dialog_spies import install
from PySide6.QtWidgets import QApplication, QFrame, QGraphicsEffect, QLabel

import ui.license_dlg as ld
from core.licensing import Tier
from i18n import tr


@pytest.fixture(scope="session", autouse=True)
def _qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class FakeLicense:
    _trial_remaining = 0
    activate_calls = 0

    @property
    def is_pro(self):
        return False

    def trial_remaining_seconds(self):
        return self._trial_remaining

    def open_checkout(self, product, vendor_id):
        return True

    def activate(self, key):
        FakeLicense.activate_calls += 1
        return True

    def deactivate(self):
        pass


class Cfg:
    license_tier = "free"


@pytest.fixture(autouse=True)
def _spy(monkeypatch):
    spy = install(monkeypatch, ld)
    FakeLicense.activate_calls = 0
    return spy


@pytest.fixture
def dialog():
    dlg = ld.LicenseDialog(Cfg(), FakeLicense())
    yield dlg
    dlg.close()


def test_free_dialog_has_status_chip_without_pulse(dialog):
    chips = [w for w in dialog.findChildren(QLabel) if w.objectName() == "StatusChip"]
    assert chips, "falta StatusChip na UI FREE"
    assert dialog.width() == 620
    assert not any(isinstance(w, QGraphicsEffect)
                   for w in dialog.findChildren(QGraphicsEffect))


def test_free_dialog_shows_trial_remaining_only_while_trial_active():
    class TrialLicense(FakeLicense):
        _trial_remaining = 170

    dlg = ld.LicenseDialog(Cfg(), TrialLicense())
    try:
        chips = [w for w in dlg.findChildren(QLabel) if w.objectName() == "StatusChip"]
        texts = [w.text() for w in chips]
        assert any(tr("license.trial_remaining").format(m=3) in t for t in texts), \
            "trial ativo deve mostrar o tempo restante (arredondado p/ cima)"
    finally:
        dlg.close()


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


def test_activar_chave_com_sucesso_avisa_o_utilizador(dialog, _spy):
    """Uma chave aceite tem de dizer isso — e o spy é o que o comprova.

    Antes da migração para o `ModernMessageBox` o substituto era um `pass`
    mudo, e este teste passava sem que uma única mensagem fosse mostrada.
    Apagar a chamada a `show_information` em `_activate_key` mata este teste.
    """
    dialog._key_edit.setText("TEST-KEY-1234")
    dialog._activate_key()
    assert _spy.count == 1, "activar uma chave válida mostra exactamente uma mensagem"
    assert _spy.of_kind("information"), "o sucesso é informação, não aviso nem erro"


def test_activar_chave_vazia_avisa_e_nao_toca_no_sistema(monkeypatch):
    """O caminho da chave vazia: avisa, não activa, não muda o tier.

    Este caminho não tinha teste. Sem ele, um `activate("")` que devolvesse
    True por engano deixava o utilizador com o tier PRO sem chave nenhuma.
    """
    spy = install(monkeypatch, ld)
    licence = FakeLicense()
    dlg = ld.LicenseDialog(Cfg(), licence)
    try:
        dlg._activate_key()
        assert len(spy.of_kind("warning")) == 1, "tem de avisar que falta a chave"
        assert licence.activate_calls == 0, "não pode tentar activar uma chave vazia"
        assert dlg._cfg.license_tier == Tier.FREE.value
        assert dlg.result() != 1, "uma falha não pode fechar o diálogo como se fosse sucesso"
    finally:
        dlg.close()


def test_activar_chave_invalida_avisa_e_deixa_o_tier_where_estava(monkeypatch):
    """Uma chave recusada tem de dizer que foi recusada.

    Este é o caminho que o utilizador encontra quando paga e a chave não
    cola. Sem aviso ele carrega outra vez e outra vez sem perceber porque é
    que nada muda — e o tier tem de continuar FREE, senão o diálogo
    announces uma licença que não existe.
    """
    spy = install(monkeypatch, ld)

    class RecusaLicense(FakeLicense):
        def activate(self, key):
            FakeLicense.activate_calls += 1
            return False

    cfg = Cfg()
    dlg = ld.LicenseDialog(cfg, RecusaLicense())
    try:
        dlg._key_edit.setText("CHAVE-QUE-NAO-EXISTE")
        dlg._activate_key()
        assert len(spy.of_kind("warning")) == 1, "tem de avisar que a chave é inválida"
        assert len(spy.of_kind("information")) == 0, \
            "não pode anunciar sucesso quando a activação falhou"
        assert cfg.license_tier == Tier.FREE.value
        assert dlg.result() != 1, "uma falha não pode fechar o diálogo como se fosse sucesso"
    finally:
        dlg.close()


def test_checkout_recusado_avisa_em_vez_de_silenciar(monkeypatch):
    """`open_checkout` a False tem de produzir aviso, não silêncio.

    O caminho do erro é o que o utilizador encontra quando o browser não
    abre; sem aviso ele fica a olhar para o diálogo sem perceber.
    """
    spy = install(monkeypatch, ld)

    class SemBrowser(FakeLicense):
        def open_checkout(self, product, vendor_id):
            return False

    dlg = ld.LicenseDialog(Cfg(), SemBrowser())
    try:
        dlg._open_checkout(ld._PRODUCTS[0][0])
        assert len(spy.of_kind("warning")) == 1
        assert len(spy.of_kind("information")) == 0, \
            "não pode dizer que o checkout abriu quando não abriu"
    finally:
        dlg.close()
