import queue
import sys
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


def speech_pcm(dur_s=1.0):
    sr = 16000
    frame = int(sr * 0.03)
    n = int(sr * dur_s)
    rng = np.random.default_rng(42)
    out = np.empty(n, dtype=np.int16)
    for start in range(0, n - frame + 1, frame):
        seg = out[start:start + frame]
        if (start // frame) % 2 == 0:
            tt = np.arange(seg.size) / sr
            seg[:] = (np.sin(2 * np.pi * 220 * tt) * 6000).astype(np.int16)
        else:
            seg[:] = rng.integers(-3000, 3000, size=seg.size, dtype=np.int16)
    return out


class SpyTranscriber:
    def __init__(self, inner):
        self.inner = inner
        self.calls = []

    def prepare(self):
        return "local"

    def transcribe(self, pcm_int16):
        self.calls.append(pcm_int16)
        return self.inner.transcribe(pcm_int16)


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
    pcm = speech_pcm()

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


def test_noise_capture_rejected_before_stt():
    ve, _ = make_ve(stt_text="clica")
    sr = 16000
    t = np.arange(sr) / sr
    sine = (np.sin(2 * np.pi * 440 * t) * 8000).astype(np.int16)
    ve._capture_utterance = lambda: sine.tobytes()
    spy = SpyTranscriber(ve._stt)
    ve._stt = spy
    ve.status = "ready"
    ve._handle_vosk_result("ruido")
    assert spy.calls == []
    assert ve.speaker.spoken == []
    assert ve.status == "ready"
    assert ve._gate.reject_reason() == "voicing"


def test_speech_capture_passes_gate_to_stt():
    ve, _ = make_ve(stt_text="clica uma vez")
    ve._capture_utterance = lambda: speech_pcm().tobytes()
    spy = SpyTranscriber(ve._stt)
    ve._stt = spy
    ve.status = "ready"
    ve._handle_vosk_result("fala")
    assert len(spy.calls) == 1
    q = []
    while not ve.cmd_queue.empty():
        q.append(ve.cmd_queue.get_nowait())
    assert q and q[0]["action"] == "left_click"


def _stub_audio_deps(monkeypatch):
    """Põe `sounddevice` e `vosk` no `sys.modules` como módulos vazios.

    O `VoiceEngine.start()` abre por `import sounddevice` e `from vosk import
    ...`, e num clone a serio os dois precisam de coisas que nem sempre existem
    na maquina: o `sounddevice` levanta `OSError` sem a lib de PortAudio
    instalada no sistema, e o `vosk` precisa do `srt`. Sem este stub, o teste
    do erro do microfone nunca chegava ao `select_device` — falhava no import,
    a medir outra coisa.

    O que se testa aqui e' o que acontece **depois** dos imports: e' o
    `select_device` que esta sob teste (e vem logo a seguir), nao o
    `sounddevice`. Por isso um modulo vazio chega, e e' melhor que depends de
    haver hardware de audio na maquina.
    """
    for nome in ("sounddevice", "vosk"):
        monkeypatch.setitem(sys.modules, nome, types.ModuleType(nome))
    vosk = sys.modules["vosk"]
    for attr in ("KaldiRecognizer", "Model", "SetLogLevel"):
        setattr(vosk, attr, object())


class _PortAudioAusente:
    """Finder que faz `import sounddevice` levantar `OSError`.

    E' o que acontece numa maquina com o `pip install sounddevice` feito e a
    biblioteca de PortAudio do sistema em falta — o `sounddevice` e' importado
    com sucesso e explode ao procurar o `libportaudio`, com `OSError` e nao com
    `ImportError`. Um stub no `sys.modules` nao reproduz isso (um modulo
    posto la importa-se sem erro nenhum), por isso a falha tem de vir do
    proprio mecanismo de import.
    """

    def find_spec(self, name, path=None, target=None):
        if name == "sounddevice":
            raise OSError("PortAudio library not found")
        return None


def test_start_mic_error_sets_status_error(monkeypatch):
    import core.audio_devices as ad
    _stub_audio_deps(monkeypatch)
    ve, _ = make_ve()

    def boom(pref):
        raise ad.DeviceError("Microfone 'x' nao encontrado")

    monkeypatch.setattr(ad, "select_device", boom)
    assert ve.start() is False
    assert ve.status == "error"
    assert "x" in (ve.mic_error or "")


def test_start_sem_portaudio_desactiva_a_voz_em_vez_de_rebentar(monkeypatch, capsys):
    """O bug: `OSError` do PortAudio nao era apanhado e subia ao chamador.

    O `start()` so apanhava `ImportError`, que e' o que da quando o *pacote*
    falta. Com o pacote instalado e a lib do sistema em falta, o `sounddevice`
    levanta `OSError` — que passava a serio, e a aplicacao rebentava a
    tentar ligar a voz em vez de a desactivar. Os outros tres sitios que
    importam `sounddevice` ja apanham largo; este era o unico que nao.
    """
    monkeypatch.setattr(sys, "meta_path", [_PortAudioAusente()] + list(sys.meta_path))
    # `sys.meta_path` so e' consultado em cache miss, e o `sounddevice` ja esta
    # em `sys.modules` porque `core/audio_devices.py` o importa ao nivel do
    # modulo. O finder nunca era chamado: o `start()` ia direito a interrogar o
    # microfone a serio, e o teste media a maquina em vez do tratamento do
    # `OSError`. Nos dois sentidos em que falhava -- com microfone o `start()`
    # devolvia `True`, sem microfone dava "Error querying device -1" -- nenhuma
    # das falhas tinha a ver com o que o teste diz testar.
    monkeypatch.delitem(sys.modules, "sounddevice", raising=False)
    ve, _ = make_ve()

    assert ve.start() is False
    assert ve.status == "error"
    assert "PortAudio" in (ve.mic_error or "")
    # E' preciso dizer o que fazer, e nao so que falhou: a biblioteca do
    # sistema instala-se com apt/dnf, nao com pip.
    saida = capsys.readouterr().out
    assert "apt install" in saida or "dnf install" in saida


def test_toggle_from_error_retries_start(monkeypatch):
    ve, _ = make_ve()
    ve.status = "error"
    ve.mic_error = "Microfone 'x' nao encontrado"
    calls = {"n": 0}

    def fail_start():
        calls["n"] += 1
        return False

    monkeypatch.setattr(ve, "start", fail_start)
    assert ve.toggle() is False
    assert calls["n"] == 1
    assert ve.status == "error"
    assert ve.mic_error == "Microfone 'x' nao encontrado"


def test_toggle_pause_clears_mic_error():
    ve, _ = make_ve()
    ve.status = "listening"
    ve.mic_error = "Falha ao abrir o microfone (x)"
    assert ve.toggle() is True
    assert ve.status == "off"
    assert ve.mic_error is None
