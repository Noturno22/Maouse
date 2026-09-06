"""Robustez do gesto MOVER (cursor).

Cobre as invariantes nucleares do fluxo de movimento sem depender de câmara:
  1. GestureEngine classifica OPEN e ONE como gestos de movimento;
  2. SmoothEmitter conserva pixeis (nem perde nem duplica) ao distribuir por
     micro-passos fracionários a 180 Hz;
  3. MouseCtl.move_by conserva as frações acumuladas e respeita os limites
     do ecrã virtual.
"""
import time

import numpy as np
import pytest

from config import Config
from core.gestures import Gesture, GestureEngine
from core.motion import SmoothEmitter
from core.mouse_ctl import MouseCtl
from tools.train_gesture_ai import (
    FINGER_CHAINS,
    FINGER_LEN,
    MAX_ANGLES,
    OPEN_SKELETON,
    THUMB_MAX,
    _chain,
    _thumb,
    synthesize,
)


def _skeleton_one(rng):
    """ONE = index esticado + médio/anelar/mindinho dobrados."""
    skel = [None] * 21
    skel[0] = np.array([0.0, 0.0, 0.0])
    skel[1] = np.array([OPEN_SKELETON[1][0], OPEN_SKELETON[1][1], 0.0])

    def finger(name, base_id, curl_base, spread=0.0):
        ids, ang0 = FINGER_CHAINS[name]
        base = np.array([OPEN_SKELETON[base_id][0], OPEN_SKELETON[base_id][1], 0.0])
        pts = _chain(base, ang0 + spread, FINGER_LEN[name], curl_base, MAX_ANGLES)
        for k, i in enumerate(ids):
            skel[i] = pts[k]

    finger("index", 5, (0.05, 0.04, 0.03))       # esticado
    finger("middle", 9, (0.94, 0.97, 0.92))      # dobrado
    finger("ring", 13, (0.94, 0.95, 0.9))        # dobrado
    finger("pinky", 17, (0.95, 0.96, 0.9))       # dobrado
    th = _thumb((0.15, 0.15, 0.10))
    skel[2], skel[3], skel[4] = th[1], th[2], th[3]
    return np.stack([np.asarray(p, dtype=np.float64) for p in skel])


# ── helpers ────────────────────────────────────────────────────────────
def _lm_from(skel, width=640, height=480):
    """Converte um esqueleto normalizado (21,N) em landmarks pixel (x, y[, z])."""
    pts2 = skel[:, :2] * 150 + np.array([320.0, 240.0])
    if skel.shape[1] >= 3:
        return [
            (p[0] / width, p[1] / height, z)
            for (p, z) in zip(pts2, skel[:, 2], strict=True)
        ]
    return [(p[0] / width, p[1] / height) for p in pts2]


def _engine(gesture, seed=0, frames=8):
    cfg = Config()
    cfg.gesture_stable_frames = 2
    eng = GestureEngine(cfg, gesture_ai=None)
    if gesture == Gesture.ONE:
        skel = _skeleton_one(np.random.default_rng(seed))
    else:
        skel = synthesize(gesture, np.random.default_rng(seed))
    lm = _lm_from(skel)
    last = None
    for _ in range(frames):
        last = eng.update(lm, 640, 480)
    return eng, last


# ── 1. classificação OPEN / ONE = mover ────────────────────────────────
class TestMoveClassification:
    def test_open_commits_to_open(self):
        eng, _ = _engine(Gesture.OPEN, seed=1)
        assert eng._committed == Gesture.OPEN

    def test_one_commits_to_one(self):
        eng, _ = _engine(Gesture.ONE, seed=2)
        assert eng._committed == Gesture.ONE

    def test_open_is_move_gesture(self):
        # MOVE_GESTURES em engine.py inclui OPEN
        from core.engine import MOVE_GESTURES
        assert Gesture.OPEN in MOVE_GESTURES
        assert Gesture.ONE in MOVE_GESTURES

    def test_none_is_not_move_gesture(self):
        from core.engine import MOVE_GESTURES
        assert Gesture.NONE not in MOVE_GESTURES
        assert Gesture.PINCH_MID not in MOVE_GESTURES

    def test_open_palm_center_is_detected(self):
        _, (frame, _ev, _val) = _engine(Gesture.OPEN, seed=3)
        assert frame.gesture == Gesture.OPEN
        assert frame.palm_center is not None
        assert frame.hand_scale_px > 0


# ── 2. SmoothEmitter conservação ───────────────────────────────────────
class _FakeMouse:
    def __init__(self):
        self.events = []

    def move_by(self, dx, dy):
        self.events.append((dx, dy))


class TestSmoothEmitterConservation:
    def _drain(self, em, mouse, deadline=3.0):
        """Espera ate o emissor drenar e devolve os totais emitidos."""
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < deadline:
            if em.pending == 0:
                break
            time.sleep(0.003)
        # settle: garante que o flush final (idle) ja escreveu move_by
        time.sleep(0.06)
        total_x = sum(e[0] for e in mouse.events)
        total_y = sum(e[1] for e in mouse.events)
        return total_x, total_y

    def test_push_dispatches_exact_delta(self):
        mouse = _FakeMouse()
        em = SmoothEmitter(mouse, rate_hz=180.0)
        em.start()
        try:
            em.push(100.0, -50.0, seconds=0.033)
            total_x, total_y = self._drain(em, mouse)
            # conservacao: emitido + residuo acumulado = empurrado (nunca duplica)
            assert abs(total_x + em._accx - 100.0) < 1e-6
            assert abs(total_y + em._accy - (-50.0)) < 1e-6
            # nunca emite mais do que o empurrado
            assert total_x <= 100 and total_y >= -50
            assert em.pending == 0
        finally:
            em.stop()

    def test_conservation_no_duplicate_or_loss(self):
        # soma fracionaria de 99.7 px tem de emitir no maximo 100 e nunca em
        # excesso; o residuo fica no acumulador para o proximo push
        mouse = _FakeMouse()
        em = SmoothEmitter(mouse, rate_hz=180.0)
        em.start()
        try:
            em.push(99.7, 0.0, seconds=0.033)
            total_x, _ = self._drain(em, mouse)
            assert total_x <= 100
            assert abs(total_x + em._accx - 99.7) < 1e-6
            assert em.pending == 0
            # nenhum movimento retrogrado (sem perda de sinal)
            assert all(e[0] >= 0 for e in mouse.events)
        finally:
            em.stop()

    def test_clear_discards_pending(self):
        mouse = _FakeMouse()
        em = SmoothEmitter(mouse, rate_hz=180.0)
        em.start()
        try:
            em.push(50.0, 50.0, 0.033)
            em.clear()
            time.sleep(0.05)
            assert not mouse.events
            assert em.pending == 0
        finally:
            em.stop()


# ── 3. MouseCtl.move_by conservação e limites ──────────────────────────
class TestMouseCtlMoveBy:
    def _ctl(self):
        ctl = MouseCtl()
        ctl.mouse = _FakeMouse()  # injeta rato determinístico
        ctl.mouse.position = (100, 100)
        ctl.screen_w, ctl.screen_h = 2000, 1200
        ctl._frac_x = 0.0
        ctl._frac_y = 0.0
        return ctl

    def test_move_by_conserves_fractional_motion(self):
        ctl = self._ctl()
        start = ctl.mouse.position
        ctl.move_by(0.25, 0.0)
        ctl.move_by(0.25, 0.0)
        ctl.move_by(0.25, 0.0)
        ctl.move_by(0.25, 0.0)
        assert ctl.mouse.position[0] - start[0] == 1
        assert ctl.mouse.position[1] - start[1] == 0

    def test_move_by_clamps_to_screen(self):
        ctl = self._ctl()
        ctl.move_by(1_000_000, 1_000_000)
        assert ctl.mouse.position[0] == ctl.screen_w - 1
        assert ctl.mouse.position[1] == ctl.screen_h - 1
