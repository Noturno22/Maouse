import types

import numpy as np

from core import stt


def make_cfg(**kw):
    base = dict(
        stt_provider="auto",
        stt_model="whisper-large-v3-turbo",
        stt_base_url="https://api.groq.com/openai/v1",
        stt_api_key_env="MAOUSE_STT_TEST_KEY",
        whisper_model="small",
    )
    base.update(kw)
    return types.SimpleNamespace(**base)


def pcm(n=16000, rms=800.0):
    return np.full(n, int(rms), dtype=np.int16)


class FakeNet:
    def __init__(self, result=None, error=None):
        self.result = result  # dict devolvido (JSON)
        self.error = error
        self.calls = []

    def __call__(self, url, body, headers, timeout):
        self.calls.append((url, body, headers, timeout))
        if self.error:
            raise self.error
        return self.result


def test_cloud_transcribe_sends_multipart(monkeypatch):
    monkeypatch.setenv("MAOUSE_STT_TEST_KEY", "gsk_x")
    net = FakeNet({"text": "clica uma vez"})
    cs = stt.CloudSTT(make_cfg(), transport=net)
    assert cs.transcribe(pcm()) == "clica uma vez"
    url, body, headers, _t = net.calls[0]
    assert url.endswith("/audio/transcriptions")
    assert "multipart/form-data; boundary=" in headers["Content-Type"]
    assert b"whisper-large-v3-turbo" in body
    assert b'filename="comando.wav"\r\nContent-Type: audio/wav\r\n\r\nRIFF' in body


def test_cloud_returns_empty_without_key(monkeypatch):
    monkeypatch.delenv("MAOUSE_STT_TEST_KEY", raising=False)
    net = FakeNet({"text": "x"})
    cs = stt.CloudSTT(make_cfg(), transport=net)
    assert cs.transcribe(pcm()) == ""
    assert net.calls == []


def test_cloud_ping_false_without_key(monkeypatch):
    monkeypatch.delenv("MAOUSE_STT_TEST_KEY", raising=False)
    cs = stt.CloudSTT(make_cfg())
    assert cs.ping() is False


def test_cloud_ping_true_with_200(monkeypatch):
    monkeypatch.setenv("MAOUSE_STT_TEST_KEY", "gsk_ping")
    net = FakeNet({"text": ""})
    cs = stt.CloudSTT(make_cfg(), transport=net)
    assert cs.ping() is True


def test_router_prepare_auto_picks_cloud(monkeypatch):
    monkeypatch.setenv("MAOUSE_STT_TEST_KEY", "gsk_x")
    net = FakeNet({"text": ""})
    r = stt.STTRouter(make_cfg(), transport=net)
    assert r.prepare() == "cloud"
    assert r.backend == "cloud"


def test_router_prepare_auto_falls_local(monkeypatch):
    monkeypatch.delenv("MAOUSE_STT_TEST_KEY", raising=False)
    r = stt.STTRouter(make_cfg())
    r.local.preload = lambda: None
    assert r.prepare() == "local"
    assert r.backend == "local"


def test_router_forced_local_never_calls_cloud(monkeypatch):
    monkeypatch.setenv("MAOUSE_STT_TEST_KEY", "gsk_x")
    net = FakeNet({"text": "x"})
    r = stt.STTRouter(make_cfg(stt_provider="local"), transport=net)
    r.local.transcribe = lambda pcm_bytes: "pausa"
    r.local.preload = lambda: None
    assert r.prepare() == "local"
    assert r.transcribe(pcm()) == "pausa"
    assert net.calls == []


def test_router_transcribe_falls_back_to_local(monkeypatch):
    monkeypatch.setenv("MAOUSE_STT_TEST_KEY", "gsk_x")
    net = FakeNet({"text": ""})
    r = stt.STTRouter(make_cfg(stt_provider="cloud"), transport=net)
    r.local.transcribe = lambda pcm_bytes: "pausa"
    assert r.transcribe(pcm()) == "pausa"
    assert r.backend == "local"
