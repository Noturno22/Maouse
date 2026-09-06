"""Reconhecimento de fala (STT): cloud (Groq Whisper) com fallback local.

Sem novas dependencias obrigatorias: urllib para a cloud, faster-whisper
(lazy) para o local. O router decide o backend em prepare() e cai para local
a qualquer erro de rede/chave.
"""
import io
import json
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
            "User-Agent": "MaoiseSTT/1.0",
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
