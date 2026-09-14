"""Interruptor circular ON/OFF (pausa) com animacao de estado.

Substitui o botao de lista do menu lateral: um circulo moderno e simples,
posicionado no centro-inferior por baixo do logo, que respira ao alternar
ON -> OFF e acende (glow) enquanto esta ON.
"""
from PySide6.QtCore import QEasingCurve, Qt, QVariantAnimation
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QPushButton,
)

from i18n import tr
from ui.theme import ACCENT, ACCENT_GLOW, breathe_glow


class PauseToggle(QPushButton):
    """Circulo ON/OFF. ON = preenchido com accent + glow a respirar;
    OFF = contorno escuro sem glow. ``clicked`` e emitido (como qualquer
    QPushButton); a janela liga-o a ``_toggle_pause``.
    """

    def __init__(self, parent=None, size=52, glow_ms=450):
        super().__init__(parent)
        self._paused = False
        self._glow_ms = glow_ms
        self._size = size
        self._breath = None
        self.setObjectName("PauseToggle")
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self._configure_glow()
        self._refresh()
        self.clicked.connect(self._on_clicked)

    def _on_clicked(self):
        self.set_paused(not self._paused)
        self._pulse()

    def is_paused(self) -> bool:
        return self._paused

    def set_paused(self, paused: bool):
        paused = bool(paused)
        if paused == self._paused:
            return
        self._paused = paused
        self._refresh()

    def _refresh(self):
        if self._breath is not None:
            self._breath.stop()
            self._breath = None
        if not self._paused:
            self.setText(tr("btn.on"))
            self.setProperty("on", True)
            self.setStyleSheet(self._on_style())
            self._breath = breathe_glow(
                self, ACCENT_GLOW, min_alpha=90, max_alpha=200,
                min_blur=8, max_blur=20, ms=self._glow_ms,
            )
        else:
            self.setText(tr("btn.off"))
            self.setProperty("on", False)
            self.setStyleSheet(self._off_style())
            self._fade_glow()
        self.style().unpolish(self)
        self.style().polish(self)

    def _on_style(self) -> str:
        return (
            f"QPushButton#PauseToggle {{ border: none;"
            f" border-radius: {self._size // 2}px; background: {ACCENT.name()};"
            f" color: #0c1016; font-family: 'Segoe UI Semibold'; font-size: 13px; }}"
        )

    def _off_style(self) -> str:
        return (
            f"QPushButton#PauseToggle {{ border: 2px solid {QColor('#8b96a5').name()};"
            f" border-radius: {self._size // 2}px; background: {QColor('#1d2530').name()};"
            f" color: {QColor('#aab4c2').name()}; font-family: 'Segoe UI Semibold';"
            f" font-size: 13px; }}"
        )

    def _configure_glow(self):
        eff = QGraphicsDropShadowEffect(self)
        eff.setOffset(0, 0)
        eff.setColor(QColor(0, 0, 0, 0))
        eff.setBlurRadius(0)
        self.setGraphicsEffect(eff)

    def _fade_glow(self):
        if self._breath is not None:
            self._breath.stop()
            self._breath = None
        eff = self.graphicsEffect()
        if eff is None:
            self._configure_glow()
            eff = self.graphicsEffect()
        eff.setColor(QColor(0, 0, 0, 0))
        eff.setBlurRadius(0)

    def _pulse(self):
        anim = QVariantAnimation(self)
        anim.setStartValue(1.0)
        anim.setEndValue(1.12)
        anim.setDuration(140)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.valueChanged.connect(self._scale_to)
        anim.finished.connect(self._reset_size)
        anim.start()

    def _scale_to(self, t):
        self.setFixedSize(int(self._size * t), int(self._size * t))

    def _reset_size(self):
        self.setFixedSize(self._size, self._size)
