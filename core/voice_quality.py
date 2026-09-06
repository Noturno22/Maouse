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
        if n_frames < 1 or len(pcm) < int(16000 * 0.2):
            self._reason = "short"
            return False
        if _rms(pcm) < max(float(trip_level) * 0.5, self.rms_min):
            self._reason = "energy"
            return False
        frames = pcm[: n_frames * frame_sz].reshape(n_frames, frame_sz)
        rms_f = np.sqrt(np.mean(np.square(frames.astype(np.float64)), axis=1))
        speech = rms_f >= float(trip_level)
        n_speech = int(np.count_nonzero(speech))
        if n_speech < max(3, self.voicing_coverage * n_frames):
            self._reason = "voicing"
            return False
        zcr = np.array([_zcr(f.ravel()) for f in frames[speech]], dtype=np.float64)
        if zcr.size < 2 or float(np.std(zcr)) < self.zcr_std_min:
            self._reason = "voicing"
            return False
        return True