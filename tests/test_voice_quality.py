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
    assert g.evaluate(sine(4500), 10000.0) is False
    assert g.reject_reason() == "energy"


def test_accepts_quiet_speech_near_trip():
    g = CaptureQualityGate()
    sr = 16000
    frame = int(sr * 0.03)
    rng = np.random.default_rng(11)
    out = np.empty(sr, dtype=np.int16)
    for start in range(0, sr - frame + 1, frame):
        seg = out[start:start + frame]
        if (start // frame) % 2 == 0:
            tt = np.arange(seg.size) / sr
            seg[:] = (np.sin(2 * np.pi * 200 * tt) * 481).astype(np.int16)
        else:
            seg[:] = rng.integers(-589, 589, size=seg.size, dtype=np.int16)
    assert g.evaluate(out, 300.0) is True
    assert g.reject_reason() is None


def test_rejects_short_under_200ms():
    g = CaptureQualityGate()
    assert g.evaluate(np.zeros(1600, dtype=np.int16), 300.0) is False
    assert g.reject_reason() == "short"


def test_rms_min_parameter():
    g = CaptureQualityGate(rms_min=6000.0)
    assert g.evaluate(sine(4200), 300.0) is False
    assert g.reject_reason() == "energy"
