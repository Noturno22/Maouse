"""Botão circular 'Modo Trading Master' com a imagem tv.png.

Liga/desliga o modo trading master a partir do dashboard (janela principal).
O modo ativa o controlo remoto por telemóvel para comandar o PC de trading.
"""
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import QPushButton

from ui.theme import breathe_glow


class TvMasterButton(QPushButton):
    """Botão pequeno circular (28 px) com a tv.png como ícone."""

    SIZE = 28

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active = None
        self._pulse = None
        self.setObjectName("TvMasterBtn")
        self.setCheckable(True)
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Modo Trading Master — controlo remoto do PC de trading")
        self._load_icon()
        self.toggled.connect(self._on_active_changed)

    def _load_icon(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pm = QPixmap(os.path.join(root, "assets", "brand", "tv.png"))
        if pm.isNull():
            return
        pm = pm.scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setIcon(QIcon(pm))
        self.setIconSize(pm.size())

    def set_on(self, on: bool):
        """Reflete o estado do modo SEM disparar o sinal `toggled`."""
        on = bool(on)
        if on == self._active:
            return
        self._active = on
        self.blockSignals(True)
        self.setChecked(on)
        self.blockSignals(False)
        self._on_active_changed()

    def _on_active_changed(self):
        self._active = self.isChecked()
        if self._pulse is not None:
            self._pulse.stop()
            self.setGraphicsEffect(None)
            self._pulse = None
        if self.isChecked():
            self._pulse = breathe_glow(
                self, QColor(80, 200, 255),
                min_alpha=70, max_alpha=190, min_blur=6, max_blur=26, ms=900,
            )
