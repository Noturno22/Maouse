"""Voice status indicator."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QLabel

from i18n import tr
from ui.theme import FONT_MONO, TEXT_SECONDARY


class VoiceBar(QLabel):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("VoiceIndicator")
        self.setFont(FONT_MONO)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(28)
        self.setMinimumWidth(140)
        self._last = ("", "", "", "")
        self.hide()

    def update_state(self, voice_status, wake_word="jarvis", backend=None, mic_error=None):
        if voice_status == "off":
            self.hide()
            return
        self.show()
        tooltip = ""
        if voice_status == "preparing":
            txt = tr("voice.status.preparing")
        elif voice_status == "error":
            txt = tr("voice.mic_error_status")
            tooltip = mic_error or tr("voice.mic_error_tip")
        elif voice_status in ("ready", "wake"):
            if wake_word:
                wake = wake_word.upper()
                txt = f"{tr('voice.status.ready')} [{wake}]"
            else:
                txt = tr("voice.status.ready")
        elif voice_status == "listening":
            txt = tr("voice.status.listening")
        elif voice_status == "thinking":
            txt = tr("voice.status.thinking")
        else:
            txt = tr("voice.status.on")
        if voice_status not in ("error", "on"):
            btxt = tr("voice.backend.cloud") if backend == "cloud" else tr("voice.backend.local")
            txt = f"{txt} · {btxt}"
        colors = {
            "preparing": QColor(255, 170, 0),
            "error": QColor(255, 60, 60),
            "on": QColor(255, 80, 200),
            "listening": QColor(255, 80, 200),
            "thinking": QColor(80, 200, 255),
        }
        color = colors.get(voice_status, TEXT_SECONDARY)
        color_name = color.name()
        if (txt, color_name, voice_status, tooltip) == self._last:
            return
        self._last = (txt, color_name, voice_status, tooltip)
        self.setToolTip(tooltip)
        self.setText(txt)
        self.setStyleSheet(
            f"background-color: rgba(0,0,0,204);"
            f"border: 1px solid {color_name}; border-radius: 4px;"
            f"color: {color_name}; padding: 4px 10px;"
        )
