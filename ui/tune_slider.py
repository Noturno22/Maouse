"""Slider com valor animado (contador) e brilho de afinação (premium).

Widget composto que substitui o padrão (nome + valor + slider) dos sliders
das Definições: o número do valor conta suavemente até ao novo valor e o
widget acende ao ajustar, mantém o brilho enquanto arrastas e esfumaça
quando largas.
"""
import math

from PySide6.QtCore import QEasingCurve, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QSlider,
    QVBoxLayout,
)

from ui.theme import ACCENT_GLOW, FONT_MONO


class TuneSlider(QFrame):
    """Nome + valor animado + slider, com brilho de afinação."""

    valueChanged = Signal(int)

    def __init__(self, name, formatter=None, parent=None,
                 tween_ms=220, glow_ms=450, accent=ACCENT_GLOW):
        super().__init__(parent)
        self._fmt = formatter or str
        self._accent = accent
        self._tween_ms = tween_ms
        self._glow_ms = glow_ms
        self._display = 0
        self._dragging = False
        self._glow = None
        self._ignite = None
        self._fade = None
        self._tween = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        row = QHBoxLayout()
        self.name_label = QLabel(name)
        self.name_label.setObjectName("SettingsLabel")
        row.addWidget(self.name_label)
        row.addStretch(1)
        self.value_label = QLabel(self._fmt(0))
        self.value_label.setObjectName("SliderValue")
        self.value_label.setFont(FONT_MONO)
        row.addWidget(self.value_label)
        lay.addLayout(row)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.sliderPressed.connect(self._on_drag_start)
        self.slider.sliderReleased.connect(self._on_drag_end)
        self.slider.valueChanged.connect(self._on_value_changed)
        lay.addWidget(self.slider)

    # ── API ───────────────────────────────────────────────────────
    def value(self) -> int:
        return self.slider.value()

    def setValue(self, value: int) -> None:
        self.slider.setValue(value)

    def setRange(self, lo: int, hi: int) -> None:
        self.slider.setRange(lo, hi)

    def minimum(self) -> int:
        return self.slider.minimum()

    def maximum(self) -> int:
        return self.slider.maximum()

    # ── Interno: tween do contador ────────────────────────────────
    def _on_value_changed(self, value: int) -> None:
        if self._tween is not None:
            self._tween.stop()
        start = self._display
        self._start_tween(start, value)
        if not self._dragging:
            self._ignite_glow()
        self.valueChanged.emit(value)

    def _start_tween(self, start: int, end: int):
        anim = QVariantAnimation(self)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setDuration(self._tween_ms)
        anim.setEasingCurve(QEasingCurve.OutCubic)

        def tick(t):
            self._display = round(start + (end - start) * t)
            self.value_label.setText(self._fmt(self._display))

        def finish():
            self._display = end
            self.value_label.setText(self._fmt(end))

        anim.valueChanged.connect(tick)
        anim.finished.connect(finish)
        tick(0.0)
        self._tween = anim
        anim.start()

    # ── Interno: brilho ───────────────────────────────────────────
    def _glow_effect(self):
        if self._glow is None:
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setOffset(0, 0)
            shadow.setBlurRadius(6)
            shadow.setColor(self._accent)
            self.setGraphicsEffect(shadow)
            self._glow = shadow
        return self._glow

    def _ignite_glow(self):
        if self._fade is not None:
            self._fade.stop()
        if self._ignite is not None:
            self._ignite.stop()
        glow = self._glow_effect()
        anim = QVariantAnimation(self)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setDuration(self._glow_ms)
        anim.setEasingCurve(QEasingCurve.InOutSine)

        def tick(t):
            peak = math.sin(math.pi * t)
            color = QColor(self._accent)
            color.setAlpha(int(150 * peak))
            glow.setColor(color)
            glow.setBlurRadius(int(6 + 22 * t))

        anim.valueChanged.connect(tick)
        self._ignite = anim
        anim.start()

    def _on_drag_start(self):
        self._dragging = True
        if self._ignite is not None:
            self._ignite.stop()
        if self._fade is not None:
            self._fade.stop()
        glow = self._glow_effect()
        color = QColor(self._accent)
        color.setAlpha(150)
        glow.setColor(color)
        glow.setBlurRadius(16)

    def _on_drag_end(self):
        self._dragging = False
        self._fade_glow()

    def _fade_glow(self, ms=350):
        if self._ignite is not None:
            self._ignite.stop()
        if self._fade is not None:
            self._fade.stop()
        glow = self._glow_effect()
        start_alpha = glow.color().alpha()
        anim = QVariantAnimation(self)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setDuration(ms)

        def tick(t):
            color = QColor(self._accent)
            color.setAlpha(int(start_alpha * t))
            glow.setColor(color)

        anim.valueChanged.connect(tick)
        self._fade = anim
        anim.start()
