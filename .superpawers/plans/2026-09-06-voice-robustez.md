# Voz Robusta (STT/voice) — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpawers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tornar a voz profissional eliminando falsos disparos por ruído (gate de qualidade antes do STT), dando gestão de microfone com erro visível, e melhorando o fallback local offline.

**Architecture:** Um gate pure-numpy (`CaptureQualityGate`) inserido entre a captura e o STTRouter rejeita clips sem fala (energia + vozeamento ZCR) em ambos os backends; um módulo `core/audio_devices.py` centraliza query/seleção de mic e o `VoiceEngine` expõe `mic_error` + estado `"error"` consumido pela UI (voice bar + toast); `LocalSTT` passa a usar VAD/beam/idioma configuráveis via `Config`.

**Tech Stack:** Python 3.10+, numpy, sounddevice, faster-whisper (lazy), Vosk, PySide6 (UI), pytest (TDD).

**Spec:** `.superpawers/specs/2026-09-06-voice-robustez-design.md`
**Branch:** `feature/license-dialog-modernize` (WIP de outros sub-sistemas NÃO pertence a estes tasks — commits sempre cirúrgicos com `git add <ficheiros do próprio task>`).
**Venv sempre:** `.venv\Scripts\python.exe` (nunca `python`/`pytest` nus).
**Ambiente:** falha pré-existente a ignorar em TODA a suite: `tests/test_licensing.py::test_active_license_defaults_to_free` (máquina dev tem licença PRO). LSP false-alarms (PySide6/numpy/sounddevice/vosk/faster_whisper) ignorar.

---

## ESTRADO DE EXECUÇÃO — COMPLETO (verificado a 2026-09-06) ✅

> Banner criado a pedido do utilizador ("parar para documentar e continuar depois"). O plano todo (Tasks 1–9) foi executado com TDD estrito + 2 rondas de review; tudo verde com exceções documentadas abaixo. **Retomar aqui = avançar para o "plano maior da app"** (todo `pending` na session).

**Commits (ordem cronológica):**

| Commit | Conteúdo |
|---|---|
| `e4e62d7` | Spec aprovada (design) |
| `2b68731` | **T1** core/voice_quality.py + 6 tests |
| `a55f864` | **T2** gate no core/voice.py (helpers speech_pcm/SpyTranscriber); 12 tests |
| `b59fcd4` | **T3** config.py mic_device/whisper_* + roundtrip; 12 tests |
| `04d1d4c` | **T4** core/audio_devices.py (DeviceError/list_input_devices/select_device); 6 tests |
| `db652c8` | **T5** LocalSTT lê cfg (pt/VAD/beam); 11 tests |
| `9a875e7` | **T6** mic_error + estado "error" em VoiceEngine; 13+6 tests |
| `f447410` | Fixes da 1ª review (I-1..I-3, M-1..M-4); 31+54 verdes; **re-review APROVADO** |
| `6053179` | **T7** i18n 5 chaves ×7 línguas após `settings.voice.groq_key`; 9 tests |
| `3cebb23` | **T8** UI: voice_bar estado error+tooltip, main_window toast+retry, settings_dlg combo mic; tests/test_voice_bar.py. ⚠️ incluiu WIP pré-existente de main_window.py (splash/`_flash_locked`) — acordo da branch colaborativa, não revertido |
| `dbce9b0` | Fix 2ª review: `_sync_toolbar` não re-checka VOZ em "error" + +3 testes voice_bar + 4 testes settings_ui (test_voice_settings_ui.py); **re-review APROVADO** |
| `a79d7b5` | lint próprio (ruff --fix): 7 violações nossas (newlines EOF, import não usado em core/voice.py:165, ordenação imports test_voice_bar.py) |

**Verificação final (Task 9):**
- Suíte completa: **211 coletados → 210 PASS / 1 FAIL** (única = `test_licensing.py::test_active_license_defaults_to_free`, ambiental PRO).
- `py_compile` dos 9 ficheiros: exit 0.
- Ruff nos ficheiros do plano: **7 fixados por nós**; restam **21 E501 pré-existentes** em `i18n.py` (linhas 166–172, 1184–1190, 1292–1298 — anteriores ao plano, fora do scope; ticket no "plano maior").
- `tools/test_voice_llm.py`: 4/5, aborta em `test_classify_cmd_ollama_fallback` — **bug pré-existente do tool** (`.env` com a chave GROQ real vaza: o tool só faz `os.environ.pop` mas `core/llm._load_api_key` lê `.env` → preenche `self._key` real → classificador vai à cloud primeiro → sem URL "11434" em calls). `core/llm.py` + o tool estão limpos no git (não tocados por este plano).

**Counts finais por ficheiro (todos VERDES):** voice_quality 8 · audio_devices 8 · voice_direct 15 · stt 11 · config 12 · i18n 9 · voice_bar 6 · voice_settings_ui 4 · gui_imports 3.

**Pendente MANUAL (não automatizável):** Step 3 da Task 9 — `.venv\Scripts\python.exe tools\test_voice_runtime.py` (precisa de mic real + `.env` com chave; esperado backend `stt:groq`).

**Decisões pós-revisão a respeitar (desvios do plano):**
- Gate: energy floor `max(0.5*trip, rms_min)`; speech `rms_f >= trip` (1.0×); "short" = `<1 frame` **ou** `len(pcm) < 3200` (0.2 s). Valores: `rms_min=200, voicing_coverage=0.15, frame_ms=30, zcr_std_min=0.04`.
- Contrato error-state: `toggle()` em `"error"` → `start()` (retry); pausa limpa `mic_error`; UI mostra toast danger SEM wedge; check-state do botão = `status not in ("off","error")` (unificado em `_toggle_voice` e `_sync_toolbar`).
- Combo mic: `mic_device` é nome-string persistido em cfg; `""` = sistema; `select_device("")` → `None` → default.

---

### Task 1: `core/voice_quality.py` — `CaptureQualityGate`

**Files:**
- Create: `core/voice_quality.py`
- Test: `tests/test_voice_quality.py`

- [ ] **Step 1: Escrever o teste falhado**

Create `tests/test_voice_quality.py`:

```python
import numpy as np

from core.voice_quality import CaptureQualityGate


def sine(rms_target, sr=16000):
    t = np.arange(sr) / sr
    return (np.sin(2 * np.pi * 440 * t) * rms_target * np.sqrt(2)).astype(np.int16)


def speech_like():
    sr = 16000
    frame = int(sr * 0.03)
    rng = np.random.default_rng(7)
    out = np.empty(sr, dtype=np.int16)
    for start in range(0, sr - frame + 1, frame):
        seg = out[start:start + frame]
        if (start // frame) % 2 == 0:
            tt = np.arange(seg.size) / sr
            seg[:] = (np.sin(2 * np.pi * 200 * tt) * 7000).astype(np.int16)
        else:
            seg[:] = rng.integers(-2500, 2500, size=seg.size, dtype=np.int16)
    return out


def test_rejects_empty():
    g = CaptureQualityGate()
    assert g.evaluate(np.zeros(16000, dtype=np.int16), 300.0) is False
    assert g.reject_reason() in ("energy", "short")


def test_rejects_very_short():
    g = CaptureQualityGate()
    assert g.evaluate(np.zeros(240, dtype=np.int16), 300.0) is False
    assert g.reject_reason() == "short"


def test_accepts_speech_like():
    g = CaptureQualityGate()
    assert g.evaluate(speech_like(), 300.0) is True
    assert g.reject_reason() is None


def test_rejects_tonal_noise():
    g = CaptureQualityGate()
    assert g.evaluate(sine(5000), 300.0) is False
    assert g.reject_reason() == "voicing"


def test_high_trip_level_rejects_by_energy():
    g = CaptureQualityGate()
    assert g.evaluate(sine(5000), 10000.0) is False
    assert g.reject_reason() == "energy"


def test_rms_min_parameter():
    g = CaptureQualityGate(rms_min=6000.0)
    assert g.evaluate(sine(4200), 300.0) is False
    assert g.reject_reason() == "energy"
```

- [ ] **Step 2: Correr para ver falhar**

Run: `.venv\Scripts\python.exe -m pytest tests/test_voice_quality.py -q`
Expected: `ModuleNotFoundError: No module named 'core.voice_quality'` (6 falhas).

- [ ] **Step 3: Implementação mínima**

Create `core/voice_quality.py`:

```python
"""Gate de qualidade de captura: rejeita audio sem fala antes do STT.

Filtros pure-numpy, sem dependencias novas:
1. Energia global — clip quase vazio rejeitado ("energy").
2. Vozeamento — frames de fala (RMS acima do limiar) com cobertura minima e
   variacao de Zero-Crossing Rate; ruido tonal/estacionario cai aqui ("voicing").
Devolve False para clips com menos de um frame ("short"). Nunca lanca excecoes.
"""
import numpy as np


def _rms(x):
    if x.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(x, dtype=np.float64))))


def _zcr(x):
    if x.size < 2:
        return 0.0
    return float(0.5 * np.mean(np.abs(np.diff(np.sign(x))), dtype=np.float64))


class CaptureQualityGate:
    def __init__(
        self,
        rms_min=200.0,
        voicing_coverage=0.15,
        frame_ms=30,
        zcr_std_min=0.04,
    ):
        self.rms_min = float(rms_min)
        self.voicing_coverage = float(voicing_coverage)
        self.frame_ms = int(frame_ms)
        self.zcr_std_min = float(zcr_std_min)
        self._reason = None

    def reject_reason(self):
        return self._reason

    def evaluate(self, pcm_int16, trip_level):
        """True se o clip tem fala real; False caso contrario."""
        self._reason = None
        pcm = np.asarray(pcm_int16)
        frame_sz = int(16000 * self.frame_ms / 1000.0)
        n_frames = len(pcm) // frame_sz
        if n_frames < 1:
            self._reason = "short"
            return False
        if _rms(pcm) < max(float(trip_level) * 0.75, self.rms_min):
            self._reason = "energy"
            return False
        frames = pcm[: n_frames * frame_sz].reshape(n_frames, frame_sz)
        rms_f = np.sqrt(np.mean(np.square(frames.astype(np.float64)), axis=1))
        speech = rms_f >= float(trip_level) * 1.2
        n_speech = int(np.count_nonzero(speech))
        if n_speech < max(3, self.voicing_coverage * n_frames):
            self._reason = "voicing"
            return False
        zcr = np.array([_zcr(f.ravel()) for f in frames[speech]], dtype=np.float64)
        if zcr.size < 2 or float(np.std(zcr)) < self.zcr_std_min:
            self._reason = "voicing"
            return False
        return True
```

- [ ] **Step 4: Correr para ver passar**

Run: `.venv\Scripts\python.exe -m pytest tests/test_voice_quality.py -q`
Expected: `6 passed`.

- [ ] **Step 5: Commit**

```bash
git add core/voice_quality.py tests/test_voice_quality.py
git commit -m "feat(voice): gate de qualidade de captura (energia + vozeamento ZCR)"
```

---

### Task 2: Ligar o gate em `core/voice.py` (before STT)

**Files:**
- Modify: `core/voice.py`
- Test: `tests/test_voice_direct.py` (modify + extend)

- [ ] **Step 1: Escrever os testes (fragmentar o teste existente + 2 novos)**

In `tests/test_voice_direct.py`:

1. Add these helpers after the `FakeSpeaker` class (before `make_ve`):

```python
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
```

2. Change `test_always_on_dispatches_direct_command` so the capture is speech-like (the old constant `800` DC now fails the gate):

```python
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
```

3. Add two new tests at the end of the file:

```python
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
```

- [ ] **Step 2: Correr para ver falhar**

Run: `.venv\Scripts\python.exe -m pytest tests/test_voice_direct.py -q`
Expected: 3 falhas — `AttributeError: 'VoiceEngine' object has no attribute '_gate'` em `test_noise_capture_rejected_before_stt`, `test_speech_capture_passes_gate_to_stt` e `test_always_on_dispatches_direct_command`.

- [ ] **Step 3: Implementação mínima**

In `core/voice.py`:

1. Add import after `from core.stt import STTRouter`:

```python
from core.voice_quality import CaptureQualityGate
```

2. In `__init__` (after `self._noise = _NoiseFloor()`):

```python
        self._gate = CaptureQualityGate()
```

3. In `_listen_and_dispatch`, replace:

```python
        raw = np.frombuffer(pcm, dtype=np.int16)
        said = self._transcribe(raw)
        if not said:
```

with:

```python
        raw = np.frombuffer(pcm, dtype=np.int16)
        if not self._gate.evaluate(raw, self._noise.trip_level()):
            log.debug("Captura rejeitada (%s)", self._gate.reject_reason())
            self.status = "ready"
            return
        said = self._transcribe(raw)
        if not said:
```

- [ ] **Step 4: Correr para ver passar**

Run: `.venv\Scripts\python.exe -m pytest tests/test_voice_direct.py -q`
Expected: `12 passed`.

- [ ] **Step 5: Commit**

```bash
git add core/voice.py tests/test_voice_direct.py
git commit -m "feat(voice): gate de qualidade filtra ruído antes de qualquer STT"
```

---

### Task 3: `config.py` — campos mic + whisper (defaults e settings.json)

**Files:**
- Modify: `config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Escrever os testes falhados**

Add to `tests/test_config.py`:

```python
def test_voice_robustez_config_defaults():
    cfg = config.Config()
    assert cfg.mic_device == ""
    assert cfg.whisper_vad_filter is True
    assert cfg.whisper_beam_size == 3
    assert cfg.whisper_language == "pt"


def test_mic_device_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "SETTINGS_FILE", str(tmp_path / "settings.json"))
    cfg = config.Config()
    cfg.mic_device = "Microfone Realtek"
    config.save_settings(cfg, "NORMAL")
    cfg2 = config.Config()
    config.load_settings(cfg2)
    assert cfg2.mic_device == "Microfone Realtek"
```

- [ ] **Step 2: Correr para ver falhar**

Run: `.venv\Scripts\python.exe -m pytest tests/test_config.py::test_voice_robustez_config_defaults tests/test_config.py::test_mic_device_roundtrip -q`
Expected: `AttributeError: 'Config' object has no attribute 'mic_device'`.

- [ ] **Step 3: Implementação mínima**

In `config.py`, after `stt_api_key_env: str = "GROQ_API_KEY"` add:

```python
    mic_device: str = ""
    whisper_vad_filter: bool = True
    whisper_beam_size: int = 3
    whisper_language: str = "pt"
```

In `load_settings`, after the `stt_provider` block add:

```python
        if "mic_device" in data:
            cfg.mic_device = str(data["mic_device"])
```

In `save_settings`, after `"stt_provider": str(cfg.stt_provider),` add:

```python
                    "mic_device": str(cfg.mic_device),
```

- [ ] **Step 4: Correr para ver passar**

Run: `.venv\Scripts\python.exe -m pytest tests/test_config.py -q`
Expected: `12 passed`.

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat(config): campo mic_device persistido + parâmetros whisper locais"
```

---

### Task 4: `core/audio_devices.py` — query e seleção de mic

**Files:**
- Create: `core/audio_devices.py`
- Test: `tests/test_audio_devices.py`

- [ ] **Step 1: Escrever o teste falhado**

Create `tests/test_audio_devices.py`:

```python
import pytest

from core import audio_devices as ad


def fake_query():
    return [
        {"name": "Microfone Realtek HD", "max_input_channels": 2},
        {"name": "Alto-falantes", "max_input_channels": 0},
    ]


def test_list_only_inputs():
    assert ad.list_input_devices(query=fake_query) == [(0, "Microfone Realtek HD")]


def test_list_empty_on_query_failure():
    def boom():
        raise Exception("no audio api")

    assert ad.list_input_devices(query=boom) == []


def test_select_by_name_substring():
    assert ad.select_device("realtek", query=fake_query) == 0
    assert ad.select_device("MICROFONE", query=fake_query) == 0


def test_select_by_index():
    assert ad.select_device("0", query=fake_query) == 0


def test_select_empty_means_default():
    assert ad.select_device("", query=fake_query) is None
    assert ad.select_device(None, query=fake_query) is None


def test_select_unknown_raises():
    with pytest.raises(ad.DeviceError):
        ad.select_device("webcam x", query=fake_query)

    with pytest.raises(ad.DeviceError):
        ad.select_device("9", query=fake_query)
```

- [ ] **Step 2: Correr para ver falhar**

Run: `.venv\Scripts\python.exe -m pytest tests/test_audio_devices.py -q`
Expected: `ModuleNotFoundError: No module named 'core.audio_devices'` (6 falhas).

- [ ] **Step 3: Implementação mínima**

Create `core/audio_devices.py`:

```python
"""Query e selecao de microfones (sounddevice).

Sem dependencias pesadas: as funcoes aceitam um callable de query injetavel
para testes (os testes nao tocam em audio real).
"""
class DeviceError(Exception):
    pass


def list_input_devices(query=None):
    """Lista de (indice, nome) dos dispositivos com canais de entrada."""
    if query is None:
        import sounddevice as sd

        query = sd.query_devices
    try:
        devices = query()
    except Exception:
        return []
    return [
        (i, (d.get("name", "") or f"Dispositivo {i}"))
        for i, d in enumerate(devices)
        if d.get("max_input_channels", 0) > 0
    ]


def select_device(pref, query=None):
    """Devolve o indice audio para pref, ou None para default do sistema.

    pref vazio/None -> None (default). Match por substring do nome
    (case-insensitive); senao interpreta o pref como indice numerico.
    Falha -> DeviceError com a lista dos microfones disponiveis.
    """
    if not pref:
        return None
    if query is None:
        import sounddevice as sd

        query = sd.query_devices
    try:
        devices = query()
    except Exception as exc:
        raise DeviceError(f"Sem microfones: {exc}") from exc
    inputs = [
        (i, d.get("name", "") or f"Dispositivo {i}")
        for i, d in enumerate(devices)
        if d.get("max_input_channels", 0) > 0
    ]
    low = str(pref).lower()
    for idx, name in inputs:
        if low in name.lower():
            return idx
    if str(pref).strip().isdigit() and int(pref) in [i for i, _ in inputs]:
        return int(pref)
    available = ", ".join(name for _, name in inputs) or "nenhum"
    raise DeviceError(f"Microfone '{pref}' nao encontrado. Disponiveis: {available}")
```

- [ ] **Step 4: Correr para ver passar**

Run: `.venv\Scripts\python.exe -m pytest tests/test_audio_devices.py -q`
Expected: `6 passed`.

- [ ] **Step 5: Commit**

```bash
git add core/audio_devices.py tests/test_audio_devices.py
git commit -m "feat(voice): utilitarios de microfone (lista/select com erro claro)"
```

---

### Task 5: `core/stt.py` — `LocalSTT` com VAD/beam/idioma configuráveis

**Files:**
- Modify: `core/stt.py`
- Test: `tests/test_stt.py`

- [ ] **Step 1: Escrever os testes falhados**

Add to `tests/test_stt.py` (após `FakeNet`):

```python
class FakeWhisper:
    def __init__(self):
        self.kwargs = None

    def transcribe(self, audio, **kw):
        self.kwargs = kw
        return iter(()), None
```

Add at the end:

```python
def test_local_transcribe_forwards_defaults(monkeypatch):
    lc = stt.LocalSTT(make_cfg())
    fw = FakeWhisper()
    lc._whisper = fw
    assert lc.transcribe(pcm()) == ""
    assert fw.kwargs["language"] == "pt"
    assert fw.kwargs["vad_filter"] is True
    assert fw.kwargs["beam_size"] == 3
    assert fw.kwargs["condition_on_previous_text"] is False


def test_local_transcribe_honors_cfg(monkeypatch):
    lc = stt.LocalSTT(
        make_cfg(
            whisper_vad_filter=False,
            whisper_beam_size=5,
            whisper_language="en",
        )
    )
    fw = FakeWhisper()
    lc._whisper = fw
    assert lc.transcribe(pcm()) == ""
    assert fw.kwargs["language"] == "en"
    assert fw.kwargs["vad_filter"] is False
    assert fw.kwargs["beam_size"] == 5
```

- [ ] **Step 2: Correr para ver falhar**

Run: `.venv\Scripts\python.exe -m pytest tests/test_stt.py::test_local_transcribe_forwards_defaults tests/test_stt.py::test_local_transcribe_honors_cfg -q`
Expected: `KeyError: 'language'` (faltam os kwargs).

- [ ] **Step 3: Implementação mínima**

In `core/stt.py`, replace `LocalSTT.transcribe`:

```python
    def transcribe(self, pcm_int16):
        try:
            model = self._get_whisper()
        except Exception as exc:
            log.debug("STT local indisponivel: %s", exc)
            return ""
        audio = pcm_int16.astype(np.float32) / 32768.0
        language = getattr(self.cfg, "whisper_language", "pt")
        vad = bool(getattr(self.cfg, "whisper_vad_filter", True))
        beam = int(getattr(self.cfg, "whisper_beam_size", 3))
        try:
            segments, _info = model.transcribe(
                audio,
                language=language,
                beam_size=beam,
                vad_filter=vad,
                condition_on_previous_text=False,
            )
            return " ".join(seg.text.strip() for seg in segments).strip()
        except Exception as exc:
            log.debug("STT local erro: %s", exc)
            return ""
```

- [ ] **Step 4: Correr para ver passar**

Run: `.venv\Scripts\python.exe -m pytest tests/test_stt.py -q`
Expected: `11 passed`.

- [ ] **Step 5: Commit**

```bash
git add core/stt.py tests/test_stt.py
git commit -m "feat(voice): fallback local com VAD on, idioma config, beam menor e sem texto anterior"
```

---

### Task 6: `core/voice.py` — mic selecionado + `mic_error` + estado `"error"`

**Files:**
- Modify: `core/voice.py`
- Test: `tests/test_voice_direct.py`

- [ ] **Step 1: Escrever o teste falhado**

Add to `tests/test_voice_direct.py`:

```python
def test_start_mic_error_sets_status_error(monkeypatch):
    import core.audio_devices as ad
    ve, _ = make_ve()

    def boom(pref):
        raise ad.DeviceError("Microfone 'x' nao encontrado")

    monkeypatch.setattr(ad, "select_device", boom)
    assert ve.start() is False
    assert ve.status == "error"
    assert "x" in (ve.mic_error or "")
```

- [ ] **Step 2: Correr para ver falhar**

Run: `.venv\Scripts\python.exe -m pytest tests/test_voice_direct.py::test_start_mic_error_sets_status_error -q`
Expected: `AttributeError: 'VoiceEngine' object has no attribute 'mic_error'`.

- [ ] **Step 3: Implementação mínima**

In `core/voice.py`:

1. In `__init__`, after `self._deaf_until = 0.0` add:

```python
        self.mic_error = None
        self._mic_device = getattr(cfg, "mic_device", "")
```

2. In `start()`, replace the mic-probe block:

```python
        try:
            sd.default.device = (sd.default.device[0], None)
            test = sd.query_devices(device=sd.default.device[0])
            print(f"Mic: {test['name']}")
        except Exception as exc:
            print(f"Aviso: nenhum microfone encontrado ({exc}); voz desativada.")
            return False
```

with:

```python
        try:
            from core.audio_devices import DeviceError, select_device
            dev_idx = select_device(self._mic_device)
            if dev_idx is None:
                sd.default.device = (sd.default.device[0], None)
                dev_idx = sd.default.device[0]
            probe = sd.query_devices(device=dev_idx)
            print(f"Mic: {probe['name']}")
        except Exception as exc:
            self.mic_error = str(exc)
            self.status = "error"
            print(f"Aviso: nenhum microfone encontrado ({exc}); voz desativada.")
            return False
```

3. In `start()`, the stream-open `except` block:

```python
        except Exception as exc:
            print(f"Aviso: falha ao abrir o microfone ({exc}); voz desativada.")
            return False
```

becomes:

```python
        except Exception as exc:
            self.mic_error = f"Falha ao abrir o microfone ({exc})"
            self.status = "error"
            print(f"Aviso: {self.mic_error}")
            return False
```

4. In the same try, pass the selected device to the stream:

```python
            self._stream = sd.RawInputStream(
                samplerate=16000,
                blocksize=4000,
                dtype="int16",
                channels=1,
                device=dev_idx,
                callback=_callback,
            )
```

5. After `self._stream.start()` success, reset the error before `self._running`:

```python
            self._stream.start()
            self.mic_error = None
```

6. In `_loop()`, extend the off guard:

```python
            if self.status in ("off", "error"):
                continue
```

- [ ] **Step 4: Correr para ver passar**

Run: `.venv\Scripts\python.exe -m pytest tests/test_voice_direct.py tests/test_voice_quality.py -q`
Expected: `13 passed` (voice_direct) + `6 passed` (voice_quality).

- [ ] **Step 5: Commit**

```bash
git add core/voice.py tests/test_voice_direct.py
git commit -m "feat(voice): microfone selecionável + mic_error visível + estado error"
```

---

### Task 7: `i18n.py` — 5 chaves novas (mic + estado de erro)

**Files:**
- Modify: `i18n.py`
- Test: `tests/test_i18n.py`

- [ ] **Step 1: Escrever o teste falhado**

In `tests/test_i18n.py`, in `test_voice_keys_exist_in_all_langs`, extend the `keys` list:

```python
    keys = [
        "voice.prompt", "voice.not_heard", "voice.not_understood",
        "voice.status.preparing", "voice.status.ready",
        "voice.status.listening", "voice.status.thinking", "voice.status.on",
        "voice.backend.cloud", "voice.backend.local",
        "voice.mic_error_status", "voice.mic_error_tip",
        "settings.voice.stt_provider", "settings.voice.direct_commands",
        "settings.voice.groq_key",
        "settings.voice.mic_label", "settings.voice.mic_default",
        "settings.voice.mic_list_failed",
        "settings.voice.provider.auto", "settings.voice.provider.cloud",
        "settings.voice.provider.local",
    ]
```

- [ ] **Step 2: Correr para ver falhar**

Run: `.venv\Scripts\python.exe -m pytest tests/test_i18n.py::test_voice_keys_exist_in_all_langs -q`
Expected: `1 falha` (chaves `voice.mic_error_status` etc. não existem).

- [ ] **Step 3: Implementação mínima**

In `i18n.py`, insert immediately AFTER the `"settings.voice.groq_key"` block (antes da chave final `}` em `_STRINGS`):

```python
    "settings.voice.mic_label": {
        "pt": "Microfone",
        "en": "Microphone",
        "es": "Micrófono",
        "fr": "Microphone",
        "de": "Mikrofon",
        "it": "Microfono",
        "pt_br": "Microfone",
    },
    "settings.voice.mic_default": {
        "pt": "Por omissão do sistema",
        "en": "System default",
        "es": "Por defecto del sistema",
        "fr": "Par défaut du système",
        "de": "Standard des Systems",
        "it": "Predefinito di sistema",
        "pt_br": "Padrão do sistema",
    },
    "settings.voice.mic_list_failed": {
        "pt": "Não foi possível listar microfones — verifica a ligação do dispositivo.",
        "en": "Could not list microphones — check the device connection.",
        "es": "No se pudieron listar los micrófonos — comprueba la conexión del dispositivo.",
        "fr": "Impossible de lister les microphones — vérifiez la connexion de l'appareil.",
        "de": "Mikrofone konnten nicht aufgelistet werden — Geräteverbindung prüfen.",
        "it": "Impossibile elencare i microfoni — controlla la connessione del dispositivo.",
        "pt_br": "Não foi possível listar microfones — verifique a conexão do aparelho.",
    },
    "voice.mic_error_status": {
        "pt": "MICROFONE INACESSÍVEL",
        "en": "MICROPHONE UNAVAILABLE",
        "es": "MICRÓFONO INACCESIBLE",
        "fr": "MICROPHONE INACCESSIBLE",
        "de": "MIKROFON NICHT VERFÜGBAR",
        "it": "MICROFONO NON DISPONIBILE",
        "pt_br": "MICROFONE INDISPONÍVEL",
    },
    "voice.mic_error_tip": {
        "pt": "Verifica se o microfone está ligado e sem uso por outra app.",
        "en": "Check that the microphone is connected and not in use by another app.",
        "es": "Comprueba que el micrófono esté conectado y no lo use otra app.",
        "fr": "Vérifiez que le microphone est branché et non utilisé par une autre application.",
        "de": "Prüfe, ob das Mikrofon angeschlossen und nicht von einer anderen App belegt ist.",
        "it": "Controlla che il microfono sia collegato e non in uso da un'altra app.",
        "pt_br": "Verifique se o microfone está conectado e sem uso por outro aplicativo.",
    },
```

- [ ] **Step 4: Correr para ver passar**

Run: `.venv\Scripts\python.exe -m pytest tests/test_i18n.py -q`
Expected: `9 passed`.

- [ ] **Step 5: Commit**

```bash
git add i18n.py tests/test_i18n.py
git commit -m "feat(i18n): chaves de microfone e estado de erro (7 línguas)"
```

---

### Task 8: UI — combo microfone, voice bar com erro, toast danger

**Files:**
- Modify: `ui/settings_dlg.py`, `ui/voice_bar.py`, `ui/main_window.py`
- Test: `tests/test_voice_bar.py` (novo)

- [ ] **Step 1: Escrever o teste falhado**

Create `tests/test_voice_bar.py`:

```python
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
```

- [ ] **Step 2: Correr para ver falhar**

Run: `.venv\Scripts\python.exe -m pytest tests/test_voice_bar.py -q`
Expected: `1 falha` — `AssertionError: 'MICROFONE INACESSÍVEL' not in ...` (estado `"error"` cai no else e devolve "VOZ ON").

Alternativa: se o PySide6 não arrancar offscreen na máquina, reportar e avançar mesmo assim (é Linux/driver-specific); na máquina dev com Windows o offscreen funciona (os testes de license_dialog usam o mesmo padrão).

- [ ] **Step 3: Implementação mínima**

In `ui/voice_bar.py`, replace `update_state`:

```python
    def update_state(self, voice_status, wake_word="jarvis", backend=None, mic_error=None):
        if voice_status == "off":
            self.hide()
            return
        self.show()
        if voice_status == "preparing":
            txt = tr("voice.status.preparing")
        elif voice_status == "error":
            txt = tr("voice.mic_error_status")
            self.setToolTip(mic_error or tr("voice.mic_error_tip"))
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

In `ui/main_window.py`, `_toggle_voice`, inside `if self._voice:` BEFORE the `self._voice.toggle()` call, add:

```python
            if self._voice.mic_error:
                self._toast.show_toast(
                    tr("voice.mic_error_status"), danger=True, duration_ms=2300
                )
                self._menu_checkable(self._menu.btn_voice, False)
                return
```

In `ui/main_window.py`, `_tick`, replace:

```python
            self._voice_bar.update_state(
                self._voice.status, self._cfg.voice_wake_word, self._voice.backend
            )
```

with:

```python
            self._voice_bar.update_state(
                self._voice.status,
                self._cfg.voice_wake_word,
                self._voice.backend,
                getattr(self._voice, "mic_error", None),
            )
```

In `ui/settings_dlg.py`, inside the `# Voz / reconhecimento` block, after `vl.addWidget(self._direct_ch)` add:

```python
        from core.audio_devices import list_input_devices
        devices = list_input_devices()
        vl.addWidget(QLabel(tr("settings.voice.mic_label")))
        if devices:
            self._mic_combo = QComboBox()
            self._mic_combo.addItem(tr("settings.voice.mic_default"), "")
            for _idx, name in devices:
                self._mic_combo.addItem(name, name)
            pos = self._mic_combo.findData(self._cfg.mic_device)
            self._mic_combo.setCurrentIndex(pos if pos >= 0 else 0)
            vl.addWidget(self._mic_combo)
        else:
            self._mic_combo = None
            warn = QLabel(tr("settings.voice.mic_list_failed"))
            warn.setWordWrap(True)
            vl.addWidget(warn)
```

In `ui/settings_dlg.py`, `_save`, after `self._cfg.voice_always_on = self._direct_ch.isChecked()` add:

```python
        if getattr(self, "_mic_combo", None) is not None:
            self._cfg.mic_device = self._mic_combo.currentData() or ""
```

- [ ] **Step 4: Correr para ver passar**

Run: `.venv\Scripts\python.exe -m pytest tests/test_voice_bar.py tests/test_gui_imports.py tests/test_i18n.py -q`
Expected: `4 passed` (voice_bar) + sem regressões nos outros.

- [ ] **Step 5: Commit**

```bash
git add ui/voice_bar.py ui/main_window.py ui/settings_dlg.py tests/test_voice_bar.py
git commit -m "feat(ui): combo de microfone nas definições + voice bar com estado de erro + toast"
```

---

### Task 9: Verificação final

**Files:** nenhum (verificação apenas)

- [ ] **Step 1: Suíte completa**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: tudo PASS exceto `tests/test_licensing.py::test_active_license_defaults_to_free` (falha ambiental conhecida). Registar o número total de passed (esperado ≈ 190) e a única falha.

- [ ] **Step 2: LLM tool + compilação + ruff**

```bash
.venv\Scripts\python.exe tools\test_voice_llm.py
.venv\Scripts\python.exe -m py_compile core/voice_quality.py core/audio_devices.py core/voice.py core/stt.py config.py i18n.py ui/voice_bar.py ui/main_window.py ui/settings_dlg.py
.venv\Scripts\python.exe -m ruff check core/voice_quality.py core/audio_devices.py core/voice.py core/stt.py config.py i18n.py ui/voice_bar.py ui/main_window.py ui/settings_dlg.py tests/test_voice_quality.py tests/test_audio_devices.py tests/test_voice_direct.py tests/test_stt.py tests/test_config.py tests/test_i18n.py tests/test_voice_bar.py
```

Expected: LLM tool acaba com "TODOS OS TESTES DE IA DE CONVERSA PASSARAM"; py_compile exit 0; ruff "All checks passed!".

- [ ] **Step 3: Sanity rapid (opcional, manual)** — `.venv\Scripts\python.exe tools\test_voice_runtime.py` pede para falar no mic; com mic + `.env` com chave, o backend deve aparecer como `stt:groq`.

- [ ] **Step 4: Reportar**

Reportar: Status, commits (S1..S8), contagens de testes por ficheiro, py_compile/ruff/llm, e a única falha ambiental.

---

## Referências rápidas (para quem executa)

- Venv: `.venv\Scripts\python.exe`. Nunca `python`/`pytest` nus.
- Commits cirúrgicos apenas (`git add` dos ficheiros do task; o WIP da branch — gestos, trial, locks, web/ — fica intacto).
- Falha ambiental a ignorar em qualquer corrida completa: `test_active_license_defaults_to_free`.
- Números finais esperados: `tests/test_voice_quality.py` 6; `tests/test_audio_devices.py` 6; `tests/test_stt.py` 11; `tests/test_voice_direct.py` 13; `tests/test_config.py` 12; `tests/test_voice_bar.py` 3.