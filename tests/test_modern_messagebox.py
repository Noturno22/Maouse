"""Testes do componente que substitui o QMessageBox nativo.

Este componente entrou no repo sem um unico teste e com tres defeitos
medidos. A suite existe para que nenhum deles volte, e para que a proxima
alteracao o encontre. Duas regras do repo valem aqui:

* um guard que nao pode falhar nao e um guard — cada teste abaixo tem uma
  mutacao que o mata, e as mutacoes estao escritas em
  ``test_a_opacidade_chega_a_um`` e ``test_so_ha_uma_animacao``.
* nao se escreve a mao uma copia de um valor que o codigo ja define: as
  cores vem de ``ui.theme``, e os tipos de ``msg_type`` de uma tabela que
  o proprio componente expoe.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEvent, QEventLoop, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QPushButton

from ui import modern_messagebox as mmb
from ui.modern_messagebox import ModernMessageBox
from ui.theme import ACCENT, ERROR, SUCCESS, WARNING

MSG_TYPES = ("info", "warning", "error", "success")


@pytest.fixture(scope="session", autouse=True)
def _qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def spin(ms=400):
    """Deixa o event loop correr o tempo suficiente para a animacao."""
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def spin_ate_terminar(anim, limite_ms=10000):
    """Espera pelo FIM da animacao, nao por um tempo fixo.

    `spin(400)` parecia correcta — a animacao dura 250 ms — e o teste passava
    sozinho. Na suite completa, com o event loop atrasado, os 400 ms de
    relogio nem chegavam: opacidade 0.83 e FAILED. Um teste-guarda nao pode
    depender de o CPU estar livre, por isso espera-se o sinal. O tecto de 10 s
    existe para nao travar o CI se a animacao nunca comecar.
    """
    loop = QEventLoop()
    anim.finished.connect(loop.quit)
    QTimer.singleShot(limite_ms, loop.quit)
    loop.exec()


@pytest.fixture
def box():
    d = ModernMessageBox(None, "Titulo", "Mensagem de teste", "info")
    yield d
    d.close()
    d.deleteLater()


# ── Visibilidade ────────────────────────────────────────────────────────────
# O defeito 1 eran 269 linhas de componente a substituir o QMessageBox em todo
# o dialogo de licenca, e a caixa ficava a opacidade 0.0: invisivel. Nao dava
# erro, nao dava log — so faltava aparecer. A causa era um QParallelAnimationGroup
# com DUAS animacoes na mesma property, que deixava o valor no startValue.
# Medido: animacao solitaria 1.0 · grupo com duas 0.0 · grupo com uma 1.0.


def test_a_opacidade_chega_a_um(box):
    """A janela tem de ficar visivel depois de shown.

    Mutacao que mata: voltar a meter duas animacoes de ``windowOpacity`` no
    mesmo grupo. Este foi o bug original.
    """
    box.show()
    spin_ate_terminar(box._fade_in)
    assert box.windowOpacity() == pytest.approx(1.0)


def test_so_ha_uma_animacao(box):
    """Uma property, uma animacao.

    Este e o teste que diz *porquê*: o defeito nao foi um limiar mal afinado,
    foi codigo morto. Duas `QPropertyAnimation` na mesma property dentro de um
    grupo em paralelo nao se conseguemabulhar, e o grupo deixa a opacidade no
    startValue. Escrever a segunda animacao aqui mata este teste.
    """
    opacity_anims = [
        a for a in box.findChildren(QPropertyAnimation)
        if bytes(a.propertyName()) == b"windowOpacity"
    ]
    assert len(opacity_anims) == 1, (
        f"ha {len(opacity_anims)} animacoes em windowOpacity; duas em "
        "paralelo fazem a janela ficar invisivel"
    )


def test_a_visibilidade_nao_depende_da_animacao(box):
    """A janela tem de ser visivel mesmo se a animacao for interrompida.

    Sem esta rede, uma animacao interrompida a meio (o utilizador mexe na
    janela enquanto ela entra) deixa o componente a meio da transparecia para
    sempre. `finished` reforca o valor final; aqui forcamos esse worst case.
    """
    box.show()
    box._fade_in.stop()
    box.setWindowOpacity(0.0)
    box._settle_visible()
    assert box.windowOpacity() == pytest.approx(1.0)


# ── Fechar ──────────────────────────────────────────────────────────────────
# O defeito 2 era um `TypeError` ao fechar: `_fade_out.finished.connect(self.done)`
# passa 0 argumentos e `done(self, result)` nao tinha default.
# O defeito 3 era `event.ignore()` sem event loop: `close()` deixava a janela
# visivel para sempre.


def test_close_fecha_a_janela(box):
    """`close()` tem de fechar. Antes deixava `isVisible()` em True."""
    box.show()
    spin(100)
    box.close()
    assert not box.isVisible()


def test_fechar_sem_ok_reporta_rejected(box):
    """Fechar sem carregar em OK e recusar, nunca aceitar.

    Se isto pasar a devolver Accepted, quem chama `show_*` comecaria a tratar
    um cancelamento como uma confirmacao.
    """
    box.show()
    box.close()
    assert box.result() == QDialog.Rejected


def test_esc_fecha(box):
    """A janela e frameless: nao ha X, o teclado e a saida de emergencia."""
    box.show()
    box.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier))
    assert not box.isVisible()


def test_ok_fecha_e_aceita(box):
    box.show()
    ok = next(b for b in box.findChildren(QPushButton)
              if b.objectName() == "MsgBoxOkButton")
    ok.click()
    assert not box.isVisible()
    assert box.result() == QDialog.Accepted


def test_done_nao_e_uma_override(box):
    """`done` e o do QDialog.

    A classe chegou a sobrescrever `done` sem valor por omissao, e o `finished`
    de uma animacao chama o slot sem argumentos. Se alguem voltar a sobrescrever,
    este teste apanha o override antes de ele rebentar em producao.
    """
    assert ModernMessageBox.done is QDialog.done


# ── Conteudo ────────────────────────────────────────────────────────────────


def test_a_mensagem_esta_visivel_e_quebra():
    """O texto tem de estar la e a partir, senao e um popup sem texto."""
    d = ModernMessageBox(None, "Titulo", "uma mensagem comprida " * 6, "info")
    try:
        label = next(rot for rot in d.findChildren(QLabel)
                     if rot.objectName() == "MsgBoxMessage")
        assert "uma mensagem comprida" in label.text()
        assert label.wordWrap() is True
    finally:
        d.close()


def test_a_cor_de_cada_tipo():
    """Cada `msg_type` tem a cor do tema, lida do tema — nao escrita aqui.

    A mutacao que mata: trocar um dos quatro tokens por um literal, ou fazer
    `_get_msg_color` devolver sempre ACCENT.
    """
    esperado = {"info": ACCENT, "warning": WARNING,
                "error": ERROR, "success": SUCCESS}
    d = ModernMessageBox(None, "T", "M", "info")
    try:
        for tipo, cor in esperado.items():
            assert d._get_msg_color(tipo) == cor, f"cor errada para {tipo!r}"
    finally:
        d.close()


def test_tipo_desconhecido_cai_no_accent():
    """Um `msg_type` que nao existe nao pode levantar; cai no tom neutro."""
    d = ModernMessageBox(None, "T", "M", "info")
    try:
        assert d._get_msg_color("tipo-que-nao-existe") == ACCENT
    finally:
        d.close()


# ── As tres funcoes que o dialogo de licenca usa ─────────────────────────────


@pytest.mark.parametrize("funcao,tipo", [
    (mmb.show_information, "info"),
    (mmb.show_warning, "warning"),
    (mmb.show_error, "error"),
])
def test_as_funcoes_delegam_ao_tipo_certo(monkeypatch, funcao, tipo):
    """`show_*` tem de chegar ao `msg_type` certo, e abrir uma modal.

    `exec()` e um event loop modal: sem este spy o teste bloqueava para
    sempre. E o spy e o que torna o teste verificavel — verificar apenas que
    nao rebentou passaria mesmo com `show_error` a desenhar um "informacao".

    A mutacao que mata: `show_error` a delegar em "warning" (ou as tres a
    delegarem em "info").
    """
    boxes = []
    monkeypatch.setattr(ModernMessageBox, "exec", lambda self: boxes.append(self))

    funcao(None, "Titulo", "Mensagem")

    assert len(boxes) == 1, "a funcao tem de abrir exactamente uma caixa"
    assert boxes[0]._msg_type == tipo
    assert boxes[0].windowTitle() == "Titulo"


def test_a_caixa_mostrada_tem_a_cor_do_tipo():
    """A cor que o utilizador ve vem do `msg_type`, nao de uma constante solta.

    Fecha o ciclo entre `show_*` e o que e desenhado: `show_error` tem de
    levar a um botao na cor de erro.
    """
    d = ModernMessageBox(None, "T", "M", "error")
    try:
        ok = next(b for b in d.findChildren(QPushButton)
                  if b.objectName() == "MsgBoxOkButton")
        folha = ok.styleSheet()
        for token in (ERROR, WARNING, SUCCESS, ACCENT):
            if token == ERROR:
                assert token.name() in folha, "o botao de erro nao usa a cor de erro"
            else:
                assert token.name() not in folha, (
                    f"o botao de erro carrega a cor de {token.name()}"
                )
    finally:
        d.close()
