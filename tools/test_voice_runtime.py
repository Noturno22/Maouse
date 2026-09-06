"""Validacao runtime fim-a-fim da voz: micro -> Vosk -> STT router -> comando.

Grava um comando falado do microfone real, passa o PCM pelos mesmos caminhos
que o VoiceEngine usa em producao (VAD adaptativo + core.stt) e imprime o que
o Vosk (hipotese) e o STT (cloud Groq com fallback local) entendem.

Corre:  .venv\\Scripts\\python.exe tools\\test_voice_runtime.py
        (fala para o microfone dentro de ~7 s quando pedir)
"""

import os
import queue
import sys
import time
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402

from core.voice import (  # noqa: E402
    VoiceEngine,
    _rms_i16,
    ensure_vosk_model,
)


def make_cfg(**kw):
    cfg = types.SimpleNamespace(
        voice_enabled=True,
        voice_always_on=False,
        voice_wake_word="jarvis",
        vosk_model_url="https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip",
        vosk_model_path="models/vosk-model-small-pt",
        whisper_model="small",
        stt_provider="auto",  # auto | cloud | local (mesmos defaults do config.py)
        stt_model="whisper-large-v3-turbo",
        stt_base_url="https://api.groq.com/openai/v1",
        stt_api_key_env="GROQ_API_KEY",
        llm_enabled=False,
    )
    for k, v in kw.items():
        setattr(cfg, k, v)
    return cfg


def main():
    import sounddevice as sd

    cfg = make_cfg()

    model_dir = ensure_vosk_model(cfg)
    print(f"Vosk model: {model_dir}")

    eng = VoiceEngine(cfg, queue.Queue())

    def cb(indata, frames, t, status_flag):
        eng._audio_q.put(bytes(indata))

    stream = sd.RawInputStream(
        samplerate=16000, blocksize=4000, dtype="int16", channels=1, callback=cb
    )
    stream.start()
    mic = sd.query_devices(device=sd.default.device[0])
    print(f"Mic: {mic['name']}")
    print("FALA AGORA (max ~7 s): ex. \"clica uma vez\" ou \"jarvis pausa\"")

    pcm = eng._capture_utterance()
    stream.stop()
    if not pcm:
        print("FAIL: nao se detetou voz no microfone")
        return 1

    raws = np.frombuffer(pcm, dtype=np.int16)
    rms = _rms_i16(pcm)
    print(f"Audio capturado: {len(pcm)} bytes, rms={rms:.1f}")

    from vosk import KaldiRecognizer, Model, SetLogLevel

    SetLogLevel(-3)
    model = Model(model_dir)
    rec = KaldiRecognizer(model, 16000)
    acc = rec.AcceptWaveform(pcm)
    vosk_text = ""
    if acc:
        import json

        vosk_text = json.loads(rec.Result()).get("text", "")
    else:
        vosk_text = rec.PartialResult()
    print(f"Vosk  (hipotese): {vosk_text!r}")

    t0 = time.monotonic()
    backend = eng._stt.prepare()
    said = eng._stt.transcribe(raws)
    dt = time.monotonic() - t0
    print(f"Backend STT: {backend}  (latência {dt:.1f}s)")
    print(f"Transcrição: {said!r}")

    from core.nlu import parse_local

    action, value = parse_local(said)
    print(f"Comando parseado: action={action!r} value={value!r}")
    ok = bool(said and action is not None)
    extra = "" if backend != "local" else " (backend local — sem chave/cloud)"
    status = "PASS: voz fim-a-fim a funcionar" if ok else "WARN: sem acao reconhecida"
    print("\n" + status + extra)
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
