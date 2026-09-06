import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from i18n import tr
from ui.voice_bar import VoiceBar


@pytest.fixture(scope="module")
def _qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_error_status_text_tooltip_no_backend_suffix(_qapp):
    vb = VoiceBar()
    vb.update_state("error", backend="local", mic_error="Microfone 'x' nao encontrado")
    assert tr("voice.mic_error_status") in vb.text()
    assert "stt:local" not in vb.text()
    assert vb.toolTip() == "Microfone 'x' nao encontrado"


def test_off_hides_bar(_qapp):
    vb = VoiceBar()
    vb.update_state("off")
    assert vb.isHidden()


def test_ready_shows_backend(_qapp):
    vb = VoiceBar()
    vb.update_state("ready", wake_word="jarvis", backend="cloud")
    assert tr("voice.backend.cloud") in vb.text()