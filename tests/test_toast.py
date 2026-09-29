import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from ui import toast
from ui.theme import MAIN_STYLESHEET


@pytest.fixture(scope="module", autouse=True)
def _qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_toast_normal_uses_toast_object_name():
    t = toast.Toast()
    t.show_toast("ok")
    assert t.objectName() == "Toast"


def test_toast_danger_uses_lock_object_name():
    t = toast.Toast()
    t.show_toast("PRO", danger=True)
    assert t.objectName() == "ToastLocked"


def test_toast_returns_to_normal_object_name():
    t = toast.Toast()
    t.show_toast("PRO", danger=True)
    t.show_toast("ok")
    assert t.objectName() == "Toast"


class TestOEstiloSegueONome:
    """O `objectName` não é um detalhe: `ui/theme.py` tem uma regra
    `QLabel#ToastLocked` a sério, e o `setStyleSheet` inline com selector
    `QLabel#Toast` anulava a do tema na mesma. Um toast de perigo com a cor do
    normal não dá erro nenhum — dá de menos."""

    def test_o_selector_usa_o_objectName_do_perigo(self):
        t = toast.Toast()
        t.show_toast("PRO", danger=True)
        assert "#ToastLocked" in t.styleSheet()

    def test_o_selector_volta_ao_normal(self):
        t = toast.Toast()
        t.show_toast("PRO", danger=True)
        t.show_toast("ok")
        assert "#Toast " in t.styleSheet()
        assert "#ToastLocked" not in t.styleSheet()

    def test_o_perigo_leva_o_acento_de_erro(self):
        t = toast.Toast()
        t.show_toast("PRO", danger=True)
        from ui.theme import ERROR

        assert ERROR.name().upper() in t.styleSheet()


class TestOTomPorParametro:
    def test_toast_type_aceita_success(self):
        t = toast.Toast()
        t.show_toast("guardado", toast_type="success")
        from ui.theme import SUCCESS

        assert SUCCESS.name().upper() in t.styleSheet()

    def test_um_tom_desconhecido_cai_para_info(self):
        # `toast_type` vem de strings; um valor errado tem de dar um toast
        # normal, não uma KeyError a meio de um aviso.
        t = toast.Toast()
        t.show_toast("oi", toast_type="banana")
        assert t.objectName() == "Toast"

    def test_o_tom_tem_precedencia_sobre_danger(self):
        t = toast.Toast()
        t.show_toast("x", danger=True, toast_type="warning")
        assert t.objectName() == "Toast"


class TestADerivaDaPosicao:
    """O alvo da animação de entrada era lido de `self.pos()` no início de cada
    `show_toast`, e a animação de saída deixava o widget 20 px abaixo. Cada aviso
    aparecia 20 px mais baixo que o anterior, e a deriva acumulava."""

    def test_a_ancora_nao_deriva(self):
        t = toast.Toast()
        t.move(100, 50)
        for _ in range(4):
            t.show_toast("oi")
            t._settle()  # o que a animação de saída faz no fim
        assert (t.pos().x(), t.pos().y()) == (100, 50)

    def test_o_parent_move_a_ancora(self):
        # Se o pai reposicionar o toast, é essa a nova posição de destino — e não
        # um ponto intermédio da animação de quem já saiu.
        t = toast.Toast()
        t.move(100, 50)
        t.show_toast("oi")
        t._settle()
        t.move(300, 80)
        t.show_toast("oi")
        t._settle()
        assert (t.pos().x(), t.pos().y()) == (300, 80)


def test_stylesheet_has_locked_window_border():
    assert 'MainWindow[locked="true"]' in MAIN_STYLESHEET


def test_look_logo_exists_for_flash():
    root = os.path.dirname(os.path.dirname(os.path.abspath(toast.__file__)))
    assert os.path.isfile(os.path.join(root, "assets", "brand", "logo-look.png"))
