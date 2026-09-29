"""Toast temporizado, com as cores da identidade visual.

Duas coisas que a versão anterior a este redesign acertava e que o redesign
perdeu, ambas com consequência real e não só com os testes a dizer:

**O `objectName` alterna entre `Toast` e `ToastLocked`.** `ui/theme.py` tem uma
regra `QLabel#ToastLocked` a sério, e o nome é o que a distingue. O redesign
trocou o estilo do tema por um `setStyleSheet` inline, cujo selector era
`QLabel#Toast` — que não casa com o nome de perigo e que, por ser inline, anula
o tema na mesma. Passou a ser `QLabel#{objectName}`.

**O widget fica na posição final, não na deslocada.** O `show_toast` anima de
`pos + 20` para `pos` e, à saída, de volta a `pos + 20`. Como o alvo é lido de
`self.pos()` no *início* do `show_toast` seguinte, cada toast aparecia 20 px mais
baixo que o anterior, e a deriva acumulava. A posição de destino é agora
guardada e reposta no fim da animação de saída.
"""

from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    Qt,
    QTimer,
)
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QLabel

from ui.theme import ACCENT, ERROR, FONT_MONO_BOLD, SUCCESS, WARNING

#: O nome do objectName distingue o toast normal do de perigo, e é o que a
#: regra `QLabel#ToastLocked` de `ui/theme.py` aponta.
NAME_NORMAL = "Toast"
NAME_LOCKED = "ToastLocked"

#: Acento por tipo. `danger=True` é o atalho para `"error"`; o `toast_type`
#: fica disponível para quem queira os outros dois sem mudar o call site.
ACCENTS = {
    "info": ACCENT,      # Neon azul
    "success": SUCCESS,  # Verde
    "warning": WARNING,  # Laranja
    "error": ERROR,      # Vermelho
}


class Toast(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName(NAME_NORMAL)
        self.setFont(FONT_MONO_BOLD)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(48)
        self.setMinimumWidth(200)
        self.hide()

        # Onde o toast deve ficar quando está visível. Reposto no fim da
        # animação de saída, senão cada `show_toast` derivava 20 px para baixo.
        self._anchor = QPoint(0, 50)
        self._slide_offset = 20

        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(20)
        self._shadow.setColor(QColor(0, 0, 0, 160))
        self._shadow.setOffset(0, 4)
        self.setGraphicsEffect(self._shadow)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._start_exit_animation)

        self._fade_in = QPropertyAnimation(self, b"windowOpacity")
        self._fade_in.setDuration(250)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.OutCubic)

        self._fade_out = QPropertyAnimation(self, b"windowOpacity")
        self._fade_out.setDuration(200)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.setEasingCurve(QEasingCurve.InCubic)

        self._slide_in = QPropertyAnimation(self, b"pos")
        self._slide_in.setDuration(250)
        self._slide_in.setEasingCurve(QEasingCurve.OutCubic)

        self._slide_out = QPropertyAnimation(self, b"pos")
        self._slide_out.setDuration(200)
        self._slide_out.setEasingCurve(QEasingCurve.InCubic)

        # Fade + slide em conjunto: um sem o outro lê-se como um salto.
        self._show_anim = QParallelAnimationGroup()
        self._show_anim.addAnimation(self._fade_in)
        self._show_anim.addAnimation(self._slide_in)

        self._hide_anim = QParallelAnimationGroup()
        self._hide_anim.addAnimation(self._fade_out)
        self._hide_anim.addAnimation(self._slide_out)
        self._hide_anim.finished.connect(self._settle)

    def show_toast(self, text, danger=False, duration_ms=2000, toast_type=None):
        """Mostra um toast.

        Args:
            text: a mensagem.
            danger: atalho para o estilo de perigo. É o que os ~20 call sites
                existentes usam, e o que os testes fixam.
            duration_ms: quanto tempo fica no ecrã antes de sair.
            toast_type: `"info"`, `"success"`, `"warning"` ou `"error"`, para
                quem quiser um tom sem passar por `danger`. Tem precedência
                sobre `danger`.
        """
        tipo = (toast_type or ("error" if danger else "info")).lower()
        if tipo not in ACCENTS:
            tipo = "info"

        nome = NAME_LOCKED if tipo == "error" else NAME_NORMAL
        if self.objectName() != nome:
            self.setObjectName(nome)
            # Sem isto, o Qt usa o estilo antigo até algo invalidar o widget —
            # e um toast de perigo que fica com a cor do normal não dá erro.
            self.style().unpolish(self)
            self.style().polish(self)

        self.setText(text)
        if self.parent():
            pw = self.parent().width()
            text_width = len(text) * 14 + 40
            self.setFixedWidth(min(max(text_width, 200), pw - 40))

        self._apply_toast_style(tipo)

        # A posição de destino é a de agora: se o pai a mudou desde o último
        # toast, é essa a nova posição; se não mudou, é a âncora reposta por
        # `_settle`, e não a posição deslocada de onde a animação saiu.
        self._anchor = QPoint(self.pos())
        start = QPoint(self._anchor.x(), self._anchor.y() + self._slide_offset)
        self._slide_in.setStartValue(start)
        self._slide_in.setEndValue(self._anchor)
        self._slide_out.setStartValue(self._anchor)
        self._slide_out.setEndValue(start)

        self.move(start)
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        self._show_anim.start()
        self._timer.start(duration_ms)

    def _apply_toast_style(self, tipo):
        accent = ACCENTS.get(tipo, ACCENT).name().upper()
        # O selector tem de ser o objectName actual: com `QLabel#Toast` fixo, o
        # toast de perigo não casava com a regra e ficava com o estilo do
        # normal — e o `setStyleSheet` inline anulava a regra do tema na mesma.
        self.setStyleSheet(f"""
            QLabel#{self.objectName()} {{
                background-color: rgba(10, 10, 18, 0.9);
                border: 2px solid {accent};
                border-radius: 12px;
                color: #F0F4F8;
                font-family: 'JetBrains Mono';
                font-size: 13px;
                font-weight: 500;
                padding: 12px 24px;
            }}
        """)

    def _start_exit_animation(self):
        self._hide_anim.start()

    def _settle(self):
        """Fim da animação de saída: esconder e voltar à posição de destino.

        Sem o `move`, o widget ficava 20 px abaixo da âncora e o `show_toast`
        seguinte animava a partir dali — a deriva acumulava a cada aviso.
        """
        self.hide()
        self.move(self._anchor)

    def enterEvent(self, event):
        # O rato em cima do aviso segura-o: sair de baixo dos olhos e o timer
        # ficar a contar o resto do tempo seria o pior dos dois.
        self._timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._timer.start()
        super().leaveEvent(event)
