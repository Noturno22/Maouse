import queue
import time
import types

import numpy as np
import pytest

import config as config_mod
from core.voice import VoiceEngine, _NoiseFloor, _strip_accents


def make_cfg(**kw):
    base = dict(
        voice_enabled=True,
        voice_always_on=True,
        voice_wake_word="jarvis",
        vosk_model_path="models/vosk-model-small-pt",
        whisper_model="small",
        llm_enabled=False,
    )
    base.update(kw)
    return types.SimpleNamespace(**base)


class FakeSTT:
    def __init__(self, text=""):
        self.text = text
        self.backend = "local"

    def prepare(self):
        return self.backend

    def transcribe(self, pcm_int16):
        return self.text


class FakeSpeaker:
    def __init__(self):
        self.spoken = []

    def say(self, text, interrupt=False):
        self.spoken.append(text)


def make_ve(**kw):
    cfg = make_cfg(**kw)
    ve = VoiceEngine(cfg, queue.Queue())
    ve._stt = FakeSTT(kw.get("stt_text", "pausa"))
    ve.speaker = FakeSpeaker()
    return ve, cfg


def test_strip_accents():
    assert _strip_accents("Não") == "Nao"


def test_noise_floor_trip_bounds():
    nf = _NoiseFloor(start=420.0, min_trip=300.0, factor=1.6, window=16)
    assert nf.trip_level() == pytest.approx(672.0)
    assert nf.trip_level() >= nf.trip_level()


def test_noise_floor_recalibrates_down():
    nf = _NoiseFloor(start=420.0, min_trip=300.0, factor=1.6, window=4)
    for _ in range(4):
        nf.update(260.0, speech=False)
    assert nf.baseline() < 420.0
    assert nf.trip_level() < 672.0


def test_always_on_dispatches_direct_command(monkeypatch):
    ve, _ = make_ve(stt_text="clica uma vez")
    pcm = np.full(16000, 800, dtype=np.int16)

    def fake_capture():
        return pcm.tobytes()

    ve._capture_utterance = fake_capture
    ve.status = "ready"
    ve._handle_vosk_result("qualquer fala")
    q = []
    while not ve.cmd_queue.empty():
        q.append(ve.cmd_queue.get_nowait())
    assert len(q) == 1 and q[0]["action"] == "left_click"


def test_wake_word_mode_still_works():
    ve, _ = make_ve(voice_always_on=False)
    calls = {"n": 0}

    def fake_capture():
        calls["n"] += 1
        return b""

    ve._capture_utterance = fake_capture
    ve.status = "wake"
    ve._handle_vosk_result("jarvis")
    assert calls["n"] == 1
    assert ve.speaker.spoken == ["Sim?"]


def test_always_on_empty_capture_is_quiet():
    ve, _ = make_ve()
    ve._capture_utterance = lambda: b""
    ve.status = "ready"
    ve._handle_vosk_result("ruido")
    assert ve.speaker.spoken == []
    assert ve.status == "ready"


def test_voice_always_on_default_true():
    assert config_mod.Config().voice_always_on is True


def test_toggle_off_then_on_resumes():
    ve, _ = make_ve()
    ve._running = True
    ve.status = "off"
    ve._warmup_stt = lambda: setattr(ve, "status", "ready")
    assert ve.start() is True
    for _ in range(50):
        if ve.status == "ready":
            break
        time.sleep(0.01)
    assert ve.status == "ready"


def test_deaf_while_speaker_talks_ignores_results():
    ve, _ = make_ve()
    spk = FakeSpeaker()
    spk.is_speaking = True
    ve.speaker = spk
    ve.status = "ready"
    ve._handle_vosk_result("qualquer fala")
    assert ve.cmd_queue.empty()
    assert ve.status == "ready"


def test_deaf_window_after_speak_blocks_capture():
    ve, _ = make_ve()
    ve.status = "ready"
    ve._say("olá")
    assert ve.speaker.spoken == ["olá"]
    ve._handle_vosk_result("eco")
    assert ve.cmd_queue.empty()
    assert ve.status == "ready"
