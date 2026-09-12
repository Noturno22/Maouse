# Voz Profissional: cloud-first STT com fallback local — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpawers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fazer a voz do Mãouse (recurso PRO) funcionar de forma fiável — comandos diretos sem "jarvis", STT cloud (Groq Whisper large-v3-turbo) com fallback local, arranque com feedback imediato e sem períodos de silêncio de 20-70s.

**Architecture:** Camada `core/stt.py` (CloudSTT + LocalSTT + STTRouter) reutiliza o padrão de chave/base URL de `core/llm.py`. `core/voice.py` passa a usar o router, deteta fala com VAD adaptativo (piso de ruído), pré-aquece o STT em background (estado `preparing` → `ready`) e, com `voice_always_on=True` (novo default), trata qualquer fala detetada como comando direto. Feedback e TTS localizados via `i18n`.

**Tech Stack:** Python 3.14, PySide6 (UI), faster-whisper/vosk (local, lazy), urllib (cloud), numpy. Venv: `.venv\Scripts\python.exe`.

---

## Decisões de contexto (ler primeiro)

- Branch isolada: `feature/license-dialog-modernize` (não é main; o skill `using-git-branches` já validou). Há WIP descomitado de sessões anteriores — **cada commit só faz `git add` dos ficheiros do próprio task**.
- `settings.json` não é reescrito por este plano; os defaults novos aplicam-se quando os campos faltam (o utilizador grava quando quiser via config).
- Spec: `.superpawers/specs/2026-09-05-voice-professional-design.md`.
- Falha ambiental conhecida (ignorar): `tests/test_licensing.py::test_active_license_defaults_to_free` (máquina dev tem licença PRO).
- O LSP continua sem resolver `PySide6`/`numpy`/`sounddevice`/`vosk`/`faster_whisper` — são falsos alarmes de ambiente; o venv tem tudo instalado (validado nesta sessão). Ignorar diagnostics desses imports.
- `core/voice.py` importa `i18n` (e `i18n` importa PySide6.QtCore) — **seguro headless**: `tests/test_i18n.py` já corre sem QApplication.

---

## Estrutura de ficheiros

- **Criar:** `core/stt.py`; `tests/test_stt.py`; `tests/test_voice_direct.py`.
- **Modificar:** `config.py` (campos + load/save); `core/voice.py` (router, warmup, sempre-ligado, VAD adaptativo, i18n); `i18n.py` (chaves novas ×6 línguas); `ui/voice_bar.py`; `ui/main_window.py` (`_toggle_voice`, `_tick`); `ui/settings_dlg.py` (grupo Voz); `tests/test_config.py`; `tools/test_voice_llm.py` (strings TTS novas); `tools/test_voice_runtime.py` (backend+latência); `.env.example` (comentário GROQ → STT).

---

### Task 1: Config — campos STT + sempre-ligado (TDD)

**Files:**
- Modify: `config.py:142-149` (campos), `config.py:204-207` (load), `config.py:254-255` (save)
- Test: `tests/test_config.py`

- [ ] **Step 1: Escrever os testes que falham**

Anexar a `tests/test_config.py`:

```python
def test_voice_always_on_default_true():
    assert config.Config().voice_always_on is True


def test_stt_provider_default_auto():
    assert config.Config().stt_provider == "auto"
    assert config.Config().stt_model == "whisper-large-v3-turbo"
    assert config.Config().stt_base_url == "https://api.groq.com/openai/v1"
    assert config.Config().stt_api_key_env == "GROQ_API_KEY"


def test_save_load_voice_settings(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "SETTINGS_FILE", str(tmp_path / "settings.json"))
    cfg = config.Config()
    cfg.voice_always_on = False
    cfg.stt_provider = "local"
    config.save_settings(cfg, "NORMAL")
    cfg2 = config.Config()
    config.load_settings(cfg2)
    assert cfg2.voice_always_on is False
    assert cfg2.stt_provider == "local"
```

- [ ] **Step 2: Correr e ver falhar**

Run: `.venv\Scripts\python.exe -m pytest tests/test_config.py -q`
Expected: FAIL (AttributeError / values diferem dos defaults).

- [ ] **Step 3: Implementar**

Em `config.py`, na zona da voz (linhas 142-149), inserir os campos novos:

```python
    voice_enabled: bool = True
    voice_wake_word: str = "jarvis"
    voice_window_s: float = 8.0
    voice_always_on: bool = True
    vosk_model_url: str = (
        "https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip"
    )
    vosk_model_path: str = "models/vosk-model-small-pt"

    stt_provider: str = "auto"  # auto | cloud | local
    stt_model: str = "whisper-large-v3-turbo"
    stt_base_url: str = "https://api.groq.com/openai/v1"
    stt_api_key_env: str = "GROQ_API_KEY"
```

No `load_settings`, junto do bloco `voice_enabled`/`tts_enabled` (linhas 204-207):

```python
        if "voice_enabled" in data:
            cfg.voice_enabled = bool(data["voice_enabled"])
        if "voice_always_on" in data:
            cfg.voice_always_on = bool(data["voice_always_on"])
        if "stt_provider" in data:
            cfg.stt_provider = str(data["stt_provider"])
        if "tts_enabled" in data:
            cfg.tts_enabled = bool(data["tts_enabled"])
```

No `save_settings` (junto das chaves `voice_enabled`/`tts_enabled`):

```python
                    "voice_enabled": bool(cfg.voice_enabled),
                    "voice_always_on": bool(cfg.voice_always_on),
                    "stt_provider": str(cfg.stt_provider),
                    "tts_enabled": bool(cfg.tts_enabled),
```

- [ ] **Step 4: Correr e ver passar**

Run: `.venv\Scripts\python.exe -m pytest tests/test_config.py -q`
Expected: PASS (todos; 9 testes).

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat(config): campos STT (cloud/local/auto) e voice_always_on default true"
```

---

### Task 2: `core/stt.py` — CloudSTT, LocalSTT, STTRouter (TDD)

**Files:**
- Create: `core/stt.py`
- Test: `tests/test_stt.py`

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/test_stt.py`:

```python
import json
import os
import types

import numpy as np
import pytest

from core import stt


def make_cfg(**kw):
    base = dict(
        stt_provider="auto",
        stt_model="whisper-large-v3-turbo",
        stt_base_url="https://api.groq.com/openai/v1",
        stt_api_key_env="GROQ_API_KEY",
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
    monkeypatch.setenv("GROQ_API_KEY", "gsk_x")
    net = FakeNet({"text": "clica uma vez"})
    cs = stt.CloudSTT(make_cfg(), transport=net)
    assert cs.transcribe(pcm()) == "clica uma vez"
    url, body, headers, _t = net.calls[0]
    assert url.endswith("/audio/transcriptions")
    assert "multipart/form-data; boundary=" in headers["Content-Type"]
    assert b"whisper-large-v3-turbo" in body
    assert body.startswith(b"RIFF")


def test_cloud_returns_empty_without_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    net = FakeNet({"text": "x"})
    cs = stt.CloudSTT(make_cfg(), transport=net)
    assert cs.transcribe(pcm()) == ""
    assert net.calls == []


def test_cloud_ping_false_without_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    cs = stt.CloudSTT(make_cfg())
    assert cs.ping() is False


def test_cloud_ping_true_with_200():
    net = FakeNet({"text": ""})
    cs = stt.CloudSTT(make_cfg(), transport=net)
    assert cs.ping() is True


def test_router_prepare_auto_picks_cloud(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_x")
    net = FakeNet({"text": ""})
    r = stt.STTRouter(make_cfg(), transport=net)
    assert r.prepare() == "cloud"
    assert r.backend == "cloud"


def test_router_prepare_auto_falls_local(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    r = stt.STTRouter(make_cfg())
    assert r.prepare() == "local"
    assert r.backend == "local"


def test_router_forced_local_never_calls_cloud(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_x")
    net = FakeNet({"text": "x"})
    r = stt.STTRouter(make_cfg(stt_provider="local"), transport=net)
    r.local.transcribe = lambda pcm_bytes: "pausa"
    assert r.prepare() == "local"
    assert r.transcribe(pcm()) == "pausa"
    assert net.calls == []


def test_router_transcribe_falls_back_to_local(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_x")
    net = FakeNet({"text": ""})
    r = stt.STTRouter(make_cfg(stt_provider="cloud"), transport=net)
    r.local.transcribe = lambda pcm_bytes: "pausa"
    assert r.transcribe(pcm()) == "pausa"
    assert r.backend == "local"
```

- [ ] **Step 2: Correr e ver falhar**

Run: `.venv\Scripts\python.exe -m pytest tests/test_stt.py -q`
Expected: FAIL (ModuleNotFoundError: core.stt).

- [ ] **Step 3: Implementar `core/stt.py`**

```python
"""Reconhecimento de fala (STT): cloud (Groq Whisper) com fallback local.

Sem novas dependencias obrigatorias: urllib para a cloud, faster-whisper
(lazy) para o local. O router decide o backend em prepare() e cai para local
a qualquer erro de rede/chave.
"""
import io
import json
import os
import threading
import time
import urllib.request
import wave

import numpy as np

from core.llm import _load_api_key
from core.log import get_logger

log = get_logger("stt")


def _pcm_to_wav(pcm_int16, sr=16000):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm_int16.tobytes())
    return buf.getvalue()


def _multipart(fields, file_bytes, filename="comando.wav", file_field="file"):
    boundary = "----MaouiseSTT"
    crlf = b"\r\n"
    body = bytearray()
    for k, v in fields.items():
        body += b"--" + boundary.encode() + crlf
        body += f'Content-Disposition: form-data; name="{k}"'.encode() + crlf + crlf
        body += str(v).encode() + crlf
    body += b"--" + boundary.encode() + crlf
    body += (
        f'Content-Disposition: form-data; name="{file_field}"; '
        f'filename="{filename}"'
    ).encode() + crlf
    body += b"Content-Type: audio/wav" + crlf + crlf
    body += file_bytes + crlf
    body += b"--" + boundary.encode() + b"--" + crlf
    return bytes(body), f"multipart/form-data; boundary={boundary}"


def _default_transport(url, body, headers, timeout):
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


class CloudSTT:
    """Transcricao via API OpenAI-compativel (Groq /audio/transcriptions)."""

    def __init__(self, cfg, transport=None):
        self.cfg = cfg
        self._transport = transport or _default_transport
        self._base = (
            (getattr(cfg, "stt_base_url", None)
                or "https://api.groq.com/openai/v1").rstrip("/")
        )
        self._model = getattr(cfg, "stt_model", None) or "whisper-large-v3-turbo"
        self._key = _load_api_key(
            getattr(cfg, "stt_api_key_env", None) or "GROQ_API_KEY"
        )

    def available(self):
        return bool(self._key)

    def ping(self, timeout=2.0):
        if not self._key:
            return False
        try:
            self._transcribe(np.zeros(4000, dtype=np.int16), timeout=timeout)
            return True
        except Exception:
            return False

    def transcribe(self, pcm_int16, timeout=15.0):
        if not self._key:
            return ""
        try:
            obj = self._transcribe(pcm_int16, timeout=timeout)
        except Exception as exc:
            log.debug("STT cloud erro: %s", exc)
            return ""
        return str((obj or {}).get("text", "") or "").strip()

    def _transcribe(self, pcm_int16, timeout):
        headers = {
            "Authorization": f"Bearer {self._key}",
            "Content-Type": None,  # preenche-se abaixo
        }
        body, ctype = _multipart(
            {"model": self._model, "temperature": "0"},
            _pcm_to_wav(pcm_int16),
        )
        headers["Content-Type"] = ctype
        return self._transport(self._base + "/audio/transcriptions", body, headers, timeout)


class LocalSTT:
    """Whisper local via faster-whisper (lazy + thread-safe)."""

    def __init__(self, cfg):
        self.cfg = cfg
        self._whisper = None
        self._lock = threading.Lock()

    def _get_whisper(self):
        if self._whisper is not None:
            return self._whisper
        with self._lock:
            if self._whisper is not None:
                return self._whisper
            name = getattr(self.cfg, "whisper_model", "small")
            log.info("A carregar Whisper local '%s'...", name)
            from faster_whisper import WhisperModel

            self._whisper = WhisperModel(
                name, device="cpu", compute_type="int8", cpu_threads=4
            )
            log.info("Whisper local pronto.")
            return self._whisper

    def preload(self):
        try:
            self._get_whisper()
        except Exception as exc:
            log.info("STT local indisponivel (cai para cloud): %s", exc)

    def transcribe(self, pcm_int16):
        try:
            model = self._get_whisper()
        except Exception as exc:
            log.debug("STT local indisponivel: %s", exc)
            return ""
        audio = pcm_int16.astype(np.float32) / 32768.0
        try:
            segments, _info = model.transcribe(
                audio, language="pt", beam_size=5, vad_filter=False
            )
            return " ".join(seg.text.strip() for seg in segments).strip()
        except Exception as exc:
            log.debug("STT local erro: %s", exc)
            return ""


class STTRouter:
    """Escolhe cloud/local. Configure: stt_provider = auto | cloud | local."""

    CLOUD_TTL = 60.0

    def __init__(self, cfg, transport=None):
        self.cfg = cfg
        self.cloud = CloudSTT(cfg, transport=transport)
        self.local = LocalSTT(cfg)
        self._backend = None  # "cloud" | "local"
        self._checked_at = 0.0

    @property
    def backend(self):
        if self._backend:
            return self._backend
        return "cloud" if self.cloud.available() else "local"

    def _provider(self):
        return (getattr(self.cfg, "stt_provider", None) or "auto").lower()

    def prepare(self):
        provider = self._provider()
        if provider == "local":
            self._backend, self._checked_at = "local", time.monotonic()
            self.local.preload()
            return self._backend
        if (provider == "cloud" and not self.cloud.available()) or not self.cloud.ping():
            self._backend, self._checked_at = "local", time.monotonic()
            self.local.preload()
            return self._backend
        self._backend, self._checked_at = "cloud", time.monotonic()
        return self._backend

    def transcribe(self, pcm_int16):
        provider = self._provider()
        if provider == "local":
            self._backend = "local"
            return self.local.transcribe(pcm_int16)
        try_cloud = provider == "cloud" or (
            provider == "auto"
            and (
                self._backend == "cloud"
                or self._backend is None
                or time.monotonic() - self._checked_at > self.CLOUD_TTL
            )
        )
        if try_cloud and self.cloud.available():
            text = self.cloud.transcribe(pcm_int16)
            if text:
                self._backend, self._checked_at = "cloud", time.monotonic()
                return text
            if provider == "cloud":
                self._backend, self._checked_at = "local", time.monotonic()
        self._backend = "local"
        return self.local.transcribe(pcm_int16)
```

- [ ] **Step 4: Correr e ver passar**

Run: `.venv\Scripts\python.exe -m pytest tests/test_stt.py -q`
Expected: PASS (9 testes).

- [ ] **Step 5: Commit**

```bash
git add core/stt.py tests/test_stt.py
git commit -m "feat(stt): cloud-first (Groq Whisper) com fallback local e router"
```

---

### Task 3: `core/voice.py` — router, warmup, sempre-ligado, VAD adaptativo, i18n (TDD)

**Files:**
- Modify: `core/voice.py`
- Test: `tests/test_voice_direct.py` (criar)
- Modify: `tools/test_voice_llm.py` (strings TTS novas)

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/test_voice_direct.py`:

```python
import queue
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
```

- [ ] **Step 2: Correr e ver falhar**

Run: `.venv\Scripts\python.exe -m pytest tests/test_voice_direct.py -q`
Expected: FAIL (falta `_NoiseFloor`, `voice_always_on` default False, fluxo sem wake).

- [ ] **Step 3: Implementar em `core/voice.py`**

3a. **Imports/topos** (substituir o topo, mantendo `SIL_END_RMS`, `WAKE_ALIASES`...):

```python
import collections
import difflib
import json
import os
import queue
import re
import threading
import time
import unicodedata
import urllib.request
import zipfile

import numpy as np

from core.log import get_logger
from core.nlu import parse_local, parse_with_llm
from core.stt import STTRouter
from i18n import tr

log = get_logger("voice")

WAKE_ALIASES = ("jarvis", "jarbas", "assistente", "computador")

SIL_START_RMS = 550.0
SIL_END_RMS = 380.0
SILENCE_END_S = 1.0
MAX_UTT_S = 7.0
PREROLL_S = 0.45
```

3b. **`_NoiseFloor`** — nova classe (pôr antes de `VoiceEngine`):

```python
class _NoiseFloor:
    """Piso de ruido adaptativo: recomecalibra com a mediana de uma janela de
    RMS capturada em silencio. trip_level() = max(base * factor, min_trip)."""

    def __init__(self, start=420.0, min_trip=300.0, factor=1.6, window=16):
        self._base = float(start)
        self._win = collections.deque(maxlen=int(window))
        self._min_trip = float(min_trip)
        self._factor = float(factor)

    def baseline(self):
        return max(self._base, self._min_trip / self._factor)

    def trip_level(self):
        return max(self._base * self._factor, self._min_trip)

    def update(self, rms, speech):
        if speech:
            return
        self._win.append(float(rms))
        if len(self._win) == self._win.maxlen:
            s = sorted(self._win)
            self._base = self._base * 0.8 + s[len(s) // 2] * 0.2
```

3c. **`VoiceEngine.__init__`** — trocar a linha de `self._stt`/noise (substituir o `__init__` atual):

```python
    def __init__(self, cfg, cmd_queue):
        self.cfg = cfg
        self.cmd_queue = cmd_queue
        self.speaker = None
        self.chat = None
        self._chat_busy = False
        self.status = "off"
        self._running = False
        self._thread = None
        self._audio_q = queue.Queue()
        self._stream = None
        self._rec = None
        self._whisper = None
        self._stt = STTRouter(cfg)
        self._noise = _NoiseFloor()
```

3d. **`start()`** — no fim (substituir o bloco `self._running = True ... return True`):

```python
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self.status = "preparing"
        threading.Thread(target=self._warmup_stt, daemon=True).start()
        mode = "sempre ativo" if self.cfg.voice_always_on else f'diga "{wake}"'
        print(f"Voz ativa ({mode})")
        return True
```

E adicionar o método:

```python
    def _warmup_stt(self):
        self._stt.prepare()
        if self.status == "preparing":
            self.status = "ready"
```

3e. **`backend` property** (adicionar a `VoiceEngine`):

```python
    @property
    def backend(self):
        return self._stt.backend
```

3f. **Remover** o método `_get_whisper` (linhas atuais ~200-215) e substituir `_transcribe`:

```python
    def _transcribe(self, pcm_int16):
        return self._stt.transcribe(pcm_int16)
```

3g. **`_capture_utterance`** — VAD adaptativo (substituir o corpo). Usar `self._noise.trip_level()` no início; fim mantém `SIL_END_RMS`:

```python
    def _capture_utterance(self):
        chunks = collections.deque()
        chunk_durs = collections.deque()
        started = None
        last_voice_t = None
        deadline = time.monotonic() + MAX_UTT_S
        while time.monotonic() < deadline:
            try:
                data = self._audio_q.get(timeout=0.15)
            except queue.Empty:
                data = None
            now = time.monotonic()
            if data is not None:
                dur = len(data) / 32000.0
                rms = _rms_i16(data)
                chunks.append(data)
                chunk_durs.append(dur)
                if started is None:
                    while chunk_durs and sum(chunk_durs) > PREROLL_S:
                        chunk_durs.popleft()
                        chunks.popleft()
                    if rms >= self._noise.trip_level():
                        started = now
                        last_voice_t = now
                else:
                    self._noise.update(rms, speech=True)
                    if rms >= SIL_END_RMS:
                        last_voice_t = now
            if started is not None:
                if last_voice_t is not None and now - last_voice_t >= SILENCE_END_S:
                    break
                if time.monotonic() - (started - PREROLL_S) > MAX_UTT_S:
                    break
        if started is None:
            return b""
        return b"".join(chunks)
```

3h. **`_handle_vosk_result`** — sempre-ligado primeiro (substituir o início do método):

```python
    def _handle_vosk_result(self, text):
        t = _strip_accents(text.lower()).strip()
        if not t:
            return

        if getattr(self.cfg, "voice_always_on", False):
            if self.status in ("ready", "wake", "on", "preparing"):
                self._listen_and_dispatch(prompt=False)
            return

        for alias in WAKE_ALIASES:
            if alias in t or difflib.get_close_matches(t, (alias,), n=1, cutoff=0.7):
                self._listen_and_dispatch(prompt=True)
                return
        ...
```

(No modo wake-word, remover as chamadas a `_listen_for_command()` das linhas 301/315 e trocá-las por `self._listen_and_dispatch(prompt=True)`.)

3i. **`_listen_for_command` → `_listen_and_dispatch(prompt=True)`** (substituir o método, agora com `prompt`):

```python
    def _listen_and_dispatch(self, prompt=True):
        self.status = "listening"
        if prompt:
            self._beep()
            if self.speaker is not None:
                self.speaker.say(tr("voice.prompt"))
        pcm = self._capture_utterance()
        if self.status == "off":
            return
        if not pcm:
            self.status = "ready"
            if prompt and self.speaker is not None:
                self.speaker.say(tr("voice.not_heard"))
            return
        raw = np.frombuffer(pcm, dtype=np.int16)
        said = self._transcribe(raw)
        if not said:
            self.status = "ready"
            if prompt and self.speaker is not None:
                self.speaker.say(tr("voice.not_heard"))
            return
        self._dispatch(_strip_accents(said.lower()))
        if self.status != "off":
            self.status = "ready"
```

3j. **Mensagens TTS via i18n** em `_dispatch` e `_reply_conversation`:

Em `_reply_conversation` (linhas ~376-381), trocar:
```python
        self._chat_busy = True
        self.status = "thinking"
```
e o bloco `speaker.say("Nao entendi.")` passa a `self.speaker.say(tr("voice.not_understood"))`.

Em `_dispatch`, o fallback `self._reply_conversation(text)` é atingido no fluxo existente — sem mudança de fluxo.

- [ ] **Step 4: Atualizar `tools/test_voice_llm.py`** (strings TTS novas)

Substituir as duas asserções (linhas ~230 e ~240) de:
```python
    check(spk.spoken == ["Nao entendi."],
```
por:
```python
    check(spk.spoken == ["Não entendi — repete, por favor."],
```
(2 ocorrências; o texto vem de `tr("voice.not_understood")` com default PT.)

- [ ] **Step 5: Correr testes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_voice_direct.py tests/test_stt.py tests/test_i18n.py -q`
Expected: PASS. O `test_i18n.py` passa porque o scan de chaves é genérico (as chaves `voice.*` ainda não existem → `tr()` devolve a chave; os testes de `_STRINGS` exigem que as chaves EXISTAM no mapa). **Nota:** como `test_all_keys_*` percorre `i18n._STRINGS` (não os usos), `test_voice_direct` não depende das chaves — mas precisa que existam para `tr()` dar texto real. As chaves são adicionadas na Task 4; enquanto isso os testes não usam `tr()` diretamente na verificação de texto (o `test_wake_word_mode_still_works` espera "Sim?" que vem de `tr("voice.prompt")` → **falhará** até a Task 4). 

Para desbloquear, correr primeiro a Task 4 (i18n) OU confirmar aqui ambos. **Ordem recomendada: completar Task 4 (chaves i18n) antes de correr este Step 5** — se implementares por ordem, corre o Step 3+4 juntos no fim da Task 4.

Run (junto, depois da Task 4): `.venv\Scripts\python.exe -m pytest tests/test_voice_direct.py tests/test_stt.py tests/test_i18n.py tests/test_config.py -q`
Expected: PASS (todos).

Também:
Run: `.venv\Scripts\python.exe -m py_compile core/voice.py core/stt.py`
Expected: `PY_COMPILE_OK` (sem output de erro).

- [ ] **Step 6: Commit**

```bash
git add core/voice.py tests/test_voice_direct.py tools/test_voice_llm.py
git commit -m "feat(voice): STT router, warmup em background, comandos diretos e VAD adaptativo"
```

---

### Task 4: i18n (chaves voz), UI (voice_bar/main_window/settings_dlg) (TDD)

**Files:**
- Modify: `i18n.py`
- Modify: `ui/voice_bar.py`
- Modify: `ui/main_window.py:293-302` (`_toggle_voice`), `ui/main_window.py:582-585` (`_tick`)
- Modify: `ui/settings_dlg.py`
- Test: `tests/test_i18n.py` (extendido — cobertura automática)

- [ ] **Step 1: Escrever o teste que falha**

Anexar a `tests/test_i18n.py`:

```python
def test_voice_keys_exist_in_all_langs():
    keys = [
        "voice.prompt", "voice.not_heard", "voice.not_understood",
        "voice.status.preparing", "voice.status.ready",
        "voice.status.listening", "voice.status.thinking", "voice.status.on",
        "voice.backend.cloud", "voice.backend.local",
        "settings.voice.stt_provider", "settings.voice.direct_commands",
        "settings.voice.groq_key",
        "settings.voice.provider.auto", "settings.voice.provider.cloud",
        "settings.voice.provider.local",
    ]
    for key in keys:
        assert key in i18n._STRINGS, key
        for lang in i18n.LANGS:
            assert i18n._STRINGS[key][lang], f"{key}/{lang}"
```

- [ ] **Step 2: Correr e ver falhar**

Run: `.venv\Scripts\python.exe -m pytest tests/test_i18n.py::test_voice_keys_exist_in_all_langs -q`
Expected: FAIL.

- [ ] **Step 3: Adicionar as chaves a `i18n.py`**

Inserir no fim do dicionário `_STRINGS` (antes do `}` final — depois da chave `access.submitted`):

```python
    "voice.prompt": {
        "pt": "Sim?",
        "en": "Yes?",
        "es": "¿Sí?",
        "fr": "Oui ?",
        "de": "Ja?",
        "it": "Sì?",
        "pt_br": "Sim?",
    },
    "voice.not_heard": {
        "pt": "Não ouvi — repete, por favor.",
        "en": "I couldn't hear you — please repeat.",
        "es": "No te he oído — repite, por favor.",
        "fr": "Je n'ai pas entendu — répète, s'il te plaît.",
        "de": "Ich habe dich nicht gehört — bitte wiederhole das.",
        "it": "Non ho sentito — ripeti, per favore.",
        "pt_br": "Não ouvi — repete, por favor.",
    },
    "voice.not_understood": {
        "pt": "Não entendi — repete, por favor.",
        "en": "I didn't understand — please repeat.",
        "es": "No te he entendido — repite, por favor.",
        "fr": "Je n'ai pas compris — répète, s'il te plaît.",
        "de": "Ich habe nicht verstanden — bitte wiederhole das.",
        "it": "Non ho capito — ripeti, per favore.",
        "pt_br": "Não entendi — repete, por favor.",
    },
    "voice.status.preparing": {
        "pt": "VOZ A PREPARAR",
        "en": "VOICE PREPARING",
        "es": "VOZ PREPARANDO",
        "fr": "VOIX : PRÉPARATION",
        "de": "STIMME WIRD VORBEREITET",
        "it": "VOCE IN PREPARAZIONE",
        "pt_br": "VOZ PREPARANDO",
    },
    "voice.status.ready": {
        "pt": "VOZ PRONTA",
        "en": "VOICE READY",
        "es": "VOZ LISTA",
        "fr": "VOIX PRÊTE",
        "de": "STIMME BEREIT",
        "it": "VOCE PRONTA",
        "pt_br": "VOZ PRONTA",
    },
    "voice.status.listening": {
        "pt": "A OUVIR",
        "en": "LISTENING",
        "es": "ESCUCHANDO",
        "fr": "À L'ÉCOUTE",
        "de": "HÖRT ZU",
        "it": "IN ASCOLTO",
        "pt_br": "OUVINDO",
    },
    "voice.status.thinking": {
        "pt": "A PENSAR",
        "en": "THINKING",
        "es": "PENSANDO",
        "fr": "RÉFLÉCHIT",
        "de": "DENKT NACH",
        "it": "PENSA",
        "pt_br": "PENSANDO",
    },
    "voice.status.on": {
        "pt": "VOZ ON",
        "en": "VOICE ON",
        "es": "VOZ ON",
        "fr": "VOIX ON",
        "de": "STIMME AN",
        "it": "VOCE ON",
        "pt_br": "VOZ ON",
    },
    "voice.backend.cloud": {
        "pt": "stt:groq",
        "en": "stt:groq",
        "es": "stt:groq",
        "fr": "stt:groq",
        "de": "stt:groq",
        "it": "stt:groq",
        "pt_br": "stt:groq",
    },
    "voice.backend.local": {
        "pt": "stt:local",
        "en": "stt:local",
        "es": "stt:local",
        "fr": "stt:local",
        "de": "stt:local",
        "it": "stt:local",
        "pt_br": "stt:local",
    },
    "settings.voice.stt_provider": {
        "pt": "Reconhecimento de voz",
        "en": "Voice recognition",
        "es": "Reconocimiento de voz",
        "fr": "Reconnaissance vocale",
        "de": "Spracherkennung",
        "it": "Riconoscimento vocale",
        "pt_br": "Reconhecimento de voz",
    },
    "settings.voice.provider.auto": {
        "pt": "Automático (cloud ou local)",
        "en": "Automatic (cloud or local)",
        "es": "Automático (cloud o local)",
        "fr": "Automatique (cloud ou local)",
        "de": "Automatisch (Cloud oder lokal)",
        "it": "Automatico (cloud o locale)",
        "pt_br": "Automático (cloud ou local)",
    },
    "settings.voice.provider.cloud": {
        "pt": "Cloud (chave Groq)",
        "en": "Cloud (Groq key)",
        "es": "Cloud (clave Groq)",
        "fr": "Cloud (clé Groq)",
        "de": "Cloud (Groq-Schlüssel)",
        "it": "Cloud (chiave Groq)",
        "pt_br": "Cloud (chave Groq)",
    },
    "settings.voice.provider.local": {
        "pt": "Local (Whisper)",
        "en": "Local (Whisper)",
        "es": "Local (Whisper)",
        "fr": "Local (Whisper)",
        "de": "Lokal (Whisper)",
        "it": "Locale (Whisper)",
        "pt_br": "Local (Whisper)",
    },
    "settings.voice.direct_commands": {
        "pt": "Comandos diretos (sem dizer “jarvis”)",
        "en": "Direct commands (no “jarvis”)",
        "es": "Comandos directos (sin decir «jarvis»)",
        "fr": "Commandes directes (sans dire « jarvis »)",
        "de": "Direkte Befehle (ohne „jarvis“)",
        "it": "Comandi diretti (senza «jarvis»)",
        "pt_br": "Comandos diretos (sem dizer “jarvis”)",
    },
    "settings.voice.groq_key": {
        "pt": "Chave Groq (GROQ_API_KEY) para o reconhecimento em cloud — coloca no ficheiro .env",
        "en": "Groq key (GROQ_API_KEY) for cloud recognition — put it in the .env file",
        "es": "Clave Groq (GROQ_API_KEY) para el reconocimiento en la nube — ponla en el fichero .env",
        "fr": "Clé Groq (GROQ_API_KEY) pour la reconnaissance cloud — placez-la dans le fichier .env",
        "de": "Groq-Schlüssel (GROQ_API_KEY) für Cloud-Erkennung — leg ihn in die .env-Datei",
        "it": "Chiave Groq (GROQ_API_KEY) per il riconoscimento cloud — mettila nel file .env",
        "pt_br": "Chave Groq (GROQ_API_KEY) para o reconhecimento na nuvem — coloque no arquivo .env",
    },
```

- [ ] **Step 4: `ui/voice_bar.py` — reescrever (linha 1 à 50)**

```python
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
        self._last = ("", "", "")
        self.hide()

    def update_state(self, voice_status, wake_word="jarvis", backend=None):
        if voice_status == "off":
            self.hide()
            return
        self.show()
        if voice_status == "preparing":
            txt = tr("voice.status.preparing")
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
        if txt != tr("voice.status.on"):
            btxt = tr("voice.backend.cloud") if backend == "cloud" else tr("voice.backend.local")
            txt = f"{txt} · {btxt}"
        colors = {
            "preparing": QColor(255, 170, 0),
            "on": QColor(255, 80, 200),
            "listening": QColor(255, 80, 200),
            "thinking": QColor(80, 200, 255),
        }
        color = colors.get(voice_status, TEXT_SECONDARY)
        color_name = color.name()
        if (txt, color_name, voice_status) == self._last:
            return
        self._last = (txt, color_name, voice_status)
        self.setText(txt)
        self.setStyleSheet(
            f"background-color: rgba(0,0,0,204);"
            f"border: 1px solid {color_name}; border-radius: 4px;"
            f"color: {color_name}; padding: 4px 10px;"
        )
```

- [ ] **Step 5: `ui/main_window.py` — `_toggle_voice` + `_tick`**

Substituir o corpo de `_toggle_voice` (linhas 293-302):

```python
    def _toggle_voice(self, checked):
        if self._view_license_locked("voice"):
            self._toast.show_toast(tr("license.pro_only", "") or "VOZ disponível no PRO — UPGRADE PRO")
            self._toast.show_toast("VOZ disponível no PRO — UPGRADE PRO")
            self._menu_checkable(self._menu.btn_voice, False)
            return
        if self._voice:
            self._voice.toggle()
            on = self._voice.status != "off"
            self._menu_checkable(self._menu.btn_voice, on)
            if on and self._voice.status == "preparing":
                self._toast.show_toast(tr("voice.status.preparing"))
            else:
                self._toast.show_toast(tr("toast.voice_on" if on else "toast.voice_off"))
```

Em `_tick` (linhas 582-585), trocar:
```python
        if self._voice:
            self._voice_bar.update_state(self._voice.status, self._cfg.voice_wake_word)
        else:
            self._voice_bar.update_state("off")
```
por:
```python
        if self._voice:
            self._voice_bar.update_state(
                self._voice.status, self._cfg.voice_wake_word, self._voice.backend
            )
        else:
            self._voice_bar.update_state("off")
```

- [ ] **Step 6: `ui/settings_dlg.py` — grupo "Voz"**

Adicionar `from i18n import tr` ao topo (junto dos imports). No `_build`, **depois** do grupo "Funcionalidades" (após `lay.addWidget(t)` ~linha 94), inserir:

```python
        # Voz / reconhecimento
        v = QGroupBox(tr("settings.voice.stt_provider"))
        v.setFont(FONT_PRIMARY)
        vl = QVBoxLayout()
        self._stt_combo = QComboBox()
        self._stt_combo.addItem(tr("settings.voice.provider.auto"), "auto")
        self._stt_combo.addItem(tr("settings.voice.provider.cloud"), "cloud")
        self._stt_combo.addItem(tr("settings.voice.provider.local"), "local")
        try:
            idx = ("auto", "cloud", "local").index(self._cfg.stt_provider)
        except ValueError:
            idx = 0
        self._stt_combo.setCurrentIndex(idx)
        vl.addWidget(self._stt_combo)
        self._direct_ch = QCheckBox(tr("settings.voice.direct_commands"))
        self._direct_ch.setChecked(self._cfg.voice_always_on)
        vl.addWidget(self._direct_ch)
        hint = QLabel(tr("settings.voice.groq_key"))
        hint.setWordWrap(True)
        vl.addWidget(hint)
        v.setLayout(vl)
        lay.addWidget(v)
```

No `_save` (após a linha `self._cfg.tts_enabled = ...`), adicionar:

```python
        self._cfg.stt_provider = self._stt_combo.currentData()
        self._cfg.voice_always_on = self._direct_ch.isChecked()
```

- [ ] **Step 7: Correr testes**

Run (com tudo): `.venv\Scripts\python.exe -m pytest tests/test_i18n.py tests/test_voice_direct.py tests/test_stt.py tests/test_config.py tests/test_gui_imports.py -q`
Expected: PASS (todos).

Run: `.venv\Scripts\python.exe -m py_compile i18n.py ui/voice_bar.py ui/main_window.py ui/settings_dlg.py`
Expected: sem erros de sintaxe.

- [ ] **Step 8: Commit**

```bash
git add i18n.py ui/voice_bar.py ui/main_window.py ui/settings_dlg.py tests/test_i18n.py
git commit -m "feat(voice): estados e TTS localizados + grupo reconhecimento nas definições"
```

---

### Task 5: Tool runtime + verificação final + docs

**Files:**
- Modify: `tools/test_voice_runtime.py`
- Modify: `.env.example`

- [ ] **Step 1: Alargar `tools/test_voice_runtime.py`**

Substituir o bloco da secção Whisper do `main()` (as linhas com `t0 = time.monotonic()` … `eng._transcribe` …) por:

```python
    t0 = time.monotonic()
    backend = eng._stt.prepare()
    said = eng._stt.transcribe(raws)
    dt = time.monotonic() - t0
    print(f"Backend STT: {backend}  (latência {dt:.1f}s)")
    print(f"Transcrição: {said!r}")
```

E a seguir, trocar a linha do veredicto:

```python
    ok = bool(said and action is not None)
    print("\n" + ("PASS: voz fim-a-fim a funcionar" if ok else "WARN: sem acao reconhecida"))
    return 0 if ok else 2
```

por:

```python
    ok = bool(said and action is not None)
    extra = "" if backend != "local" else " (backend local — sem chave/cloud)"
    print("\n" + ("PASS: voz fim-a-fim a funcionar" if ok else "WARN: sem acao reconhecida") + extra)
    return 0 if ok else 2
```

- [ ] **Step 2: `.env.example`** — documentar STT

Adicionar ao bloco existente (junto da chave `GROQ_API_KEY=...`) uma linha de comentário:

```
# A mesma chave GROQ_API_KEY é usada pelo reconhecimento de voz em cloud (STT).
```

- [ ] **Step 3: Verificação completa**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: 124 testes, 1 falha ambiental pré-existente (`test_active_license_defaults_to_free`).

Run: `.venv\Scripts\python.exe tools/test_voice_llm.py`
Expected: "TODOS OS TESTES DE IA DE CONVERSA PASSARAM" (23 PASS).

Run: `.venv\Scripts\python.exe -m py_compile core/stt.py core/voice.py config.py i18n.py ui/voice_bar.py ui/main_window.py ui/settings_dlg.py tools/test_voice_runtime.py`

- [ ] **Step 4: Commit**

```bash
git add tools/test_voice_runtime.py .env.example
git commit -m "chore(voice): ferramenta de validação runtime com backend/latência e doc de chave STT"
```

---

## Notas finais para o implementador

- Depois do plano, segue o `subagent-driven-development` task-a-task. O spec está em `.superpawers/specs/2026-09-05-voice-professional-design.md`.
- Não mexer em `settings.json` nem noutros ficheiros fora da lista de cada task (há WIP de outras sessões na branch — os commits são cirúrgicos por ficheiro).
- A validação fim-a-fim real com microfone é manual (`tools/test_voice_runtime.py`): o utilizador tem de falar; o passar dos testes unitários + do tool de dispatch é o critério de 'feito'.