"""Onda 1 §1.2: o motor abstém-se, e "nao medido" nao e "medido e mau".

`min_class_conf` so pode guardar uma coisa sem mentir: que existe um limiar.
O limiar em si **nao esta afinado** — o corpus versionado e sintetico e nao tem
confianca de classificacao (`test_tracker_confidence.py` grava `NaN` por
desenho), portanto nao ha numero com que o afinar. O que fica fixado aqui e a
*semantica*, que e a parte que rebenta em silencio:

- `NaN` e `None` sao "nao medido". O corpus inteiro esta a `NaN`. Se o motor os
  lesse como confianca zero, a §1.2 calava a IA em todas as maos do gate de
  regressao e o gate passava a verde por estar **mudo** — o pior estado
  possivel para um teste de regressao: um teste que parece protege-te e nao
  mede nada.
- Confianca medida e abaixo do limiar abste-se, e a IA nao e consultada.
  Consultar um classificador cujas entradas ninguem sabe de que lado estao
  produz uma confirmacao com falsa autoridade: parece medida, nao esta.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from config import Config
from core.gestures import Gesture, GestureEngine
from core.overlay import draw_overlay
from tools.train_gesture_ai import synthesize

W, H = 640, 480


def _lm(gesture=Gesture.OPEN, seed=11):
    skel = synthesize(gesture, np.random.default_rng(seed)).astype(float)
    pts = skel[:, :2] * 150 + np.array([320.0, 240.0])
    return [
        (p[0] / W, p[1] / H, z) for p, z in zip(pts, skel[:, 2], strict=True)
    ]


def _feed(eng, lm, conf=None, frames=6):
    last = None
    for i in range(frames):
        last = eng.update(lm, W, H, conf=conf, t=i / 30.0)
    return last[0]


def _engine(gesture_ai=None, min_class_conf=0.5):
    cfg = Config()
    cfg.min_class_conf = min_class_conf
    return GestureEngine(cfg, gesture_ai=gesture_ai)


class _SpyAI:
    def __init__(self):
        self.calls = 0

    def classify(self, pts):
        self.calls += 1
        return Gesture.OPEN, 0.9


class TestAbstencaoPorConfianca:
    def test_confianca_baixa_abste(self):
        frame = _feed(_engine(), _lm(), conf=0.2)
        assert frame.raw_gesture == Gesture.NONE

    def test_confianca_alta_nao_abste(self):
        frame = _feed(_engine(), _lm(), conf=0.95)
        assert frame.raw_gesture != Gesture.NONE

    def test_nan_nao_abste(self):
        """O teste que carrega o peso: e o estado de todo o corpus v1."""
        frame = _feed(_engine(), _lm(), conf=float("nan"))
        assert frame.raw_gesture != Gesture.NONE

    def test_none_nao_abste(self):
        frame = _feed(_engine(), _lm(), conf=None)
        assert frame.raw_gesture != Gesture.NONE

    def test_limiar_zero_desliga(self):
        frame = _feed(_engine(min_class_conf=0.0), _lm(), conf=0.01)
        assert frame.raw_gesture != Gesture.NONE

    def test_confianca_medida_viaja_para_o_frame(self):
        frame = _feed(_engine(), _lm(), conf=0.31)
        assert frame.class_conf == pytest.approx(0.31)

    def test_nao_medido_viaja_como_nan_e_nao_como_zero(self):
        """`0.0` seria pior que nada: o limiar descartaria todas as maoas de quem
        nao tem handedness, sem que ninguem soubesse porque."""
        assert math.isnan(_feed(_engine(), _lm(), conf=None).class_conf)

    def test_abstencao_ignora_a_ia_mesmo_com_ia_ligada(self):
        """A geometria e a unica coisa que decide a abstencao; a IA nunca ressuscita
        um gesto que o motor ja recusou por nao saber de que mao se trata."""
        ai = _SpyAI()
        frame = _feed(_engine(gesture_ai=ai), _lm(), conf=0.1)
        assert frame.raw_gesture == Gesture.NONE


class TestGateDaIA:
    def test_ia_nao_e_consultada_quando_abste(self):
        ai = _SpyAI()
        _feed(_engine(gesture_ai=ai), _lm(), conf=0.1)
        assert ai.calls == 0

    def test_ia_e_consultada_quando_nao_mediu(self):
        ai = _SpyAI()
        _feed(_engine(gesture_ai=ai), _lm(), conf=float("nan"))
        assert ai.calls > 0

    def test_ia_e_consultada_com_confianca_alta(self):
        ai = _SpyAI()
        _feed(_engine(gesture_ai=ai), _lm(), conf=0.9)
        assert ai.calls > 0

    def test_confianca_da_ia_nao_vaza_para_a_classificacao(self):
        """Duas confiancas com o mesmo nome e significados diferentes: `ml_conf` e
        a do classificador, `class_conf` e a da mao. Aqui a IA reporta 0.9 e a mao
        foi medida a 0.6 — se `class_conf` reflectisse a IA, o motor declararia
        confiante numa mao que ele proprio nao sabe de que lado esta."""
        cfg = Config()
        cfg.min_class_conf = 0.5
        cfg.ai_confidence_min = 0.0
        eng = GestureEngine(cfg, gesture_ai=_SpyAI())
        frame = _feed(eng, _lm(), conf=0.6)
        assert frame.ai_conf == pytest.approx(0.9)
        assert frame.class_conf == pytest.approx(0.6)


def _ui(**over):
    """O dicionario completo que `core/engine.py:234` monta. Falta uma chave e o
    overlay levanta `KeyError` — que e o que aconteceu na primeira versao."""
    ui = {
        "ai_on": False,
        "ai_conf": 0.0,
        "class_conf": math.nan,
        "voice": "off",
        "toast": "",
        "toast_until": 0.0,
        "autotune": False,
        "magnify": "",
        "hands": 1,
        "light": False,
        "tts": "",
        "ui_show": False,
    }
    ui.update(over)
    return ui


class TestBadgeHonesto:
    """Compara-se o PIXEL, nao o texto: interessa e que o aviso apareca quando
    deve, e NUNCA apareca quando nao ha nada medido para avisar.

    `hands=0` e obrigatorio. Sem ele o badge "N MAOS" desenha-se em
    (522, 10)-(628, 40) — exactamente o rect onde o badge novo vive, porque o
    `x_right` so e empurrado se o badge novo existir. A primeira versao deste
    teste passava por estar a medir o "N MAOS": um teste que verde por razao
    errada e pior do que um teste que falha.
    """

    def _render(self, class_conf):
        frame = _feed(_engine(), _lm(), conf=class_conf)
        img = np.zeros((H, W, 3), dtype=np.uint8)
        draw_overlay(img, {"Left": frame}, "Left", None, 30, Config(),
                     "NORMAL", False, False, 0.0,
                     _ui(class_conf=class_conf, hands=0))
        return img[10:40, 522:628]

    def test_badge_aparece_com_confianca_mediada_baixa(self):
        assert self._render(0.1).any()

    def test_sem_badge_quando_a_confianca_nao_foi_medida(self):
        """O aviso sobre "o tracker nao disse" seria um aviso sobre uma coisa que
        o utilizador nao pode ver nem corrigir."""
        assert not self._render(float("nan")).any()

    def test_sem_badge_quando_a_confianca_e_alta(self):
        assert not self._render(0.95).any()

    def test_sem_badge_quando_a_mao_desapareceu(self):
        img = np.zeros((H, W, 3), dtype=np.uint8)
        draw_overlay(img, {}, "Left", None, 30, Config(),
                     "NORMAL", False, False, 0.0, _ui(class_conf=0.1, hands=0))
        assert not img[10:40, 522:628].any()
