"""Testes da ligacao do recorder ao engine (core/engine.py).

O ponto de risco nao e o recorder (ja testado em test_corpus_recorder.py), e
sim descobrir **qual** das maos detectadas e a mao do cursor, porque o
``HandPool`` pode descartar duplicados e trocar os labels. Errar aqui grava a
mao errada com a etiqueta errada, e o corpus passa a medir fiction.
"""
import numpy as np

from core.corpus import CorpusRecorder
from core.engine import _active_hand_index


def _hand(cx, cy, seed=0):
    r = np.random.default_rng(seed)
    pts = r.uniform(0.0, 0.3, (21, 3)).astype(np.float32)
    pts[0] = [cx, cy, 0.0]
    pts[9] = [cx, cy + 0.2, 0.0]
    return pts


class TestActiveHandIndex:
    def test_single_hand_is_index_zero(self):
        hands = [_hand(0.5, 0.5)]
        # palma = media de pulso (0.5) e lambida 9 (0.7) -> 0.6, tal como o
        # HandPool calcula
        assert _active_hand_index(hands, 640, 480, (0.5 * 640, 0.6 * 480)) == 0

    def test_picks_the_left_hand(self):
        hands = [_hand(0.2, 0.5, 1), _hand(0.8, 0.5, 2)]
        # palma da mao da esquerda, em px
        palm = ((0.2 + 0.2) / 2 * 640, (0.5 + 0.7) / 2 * 480)
        assert _active_hand_index(hands, 640, 480, palm) == 0

    def test_picks_the_right_hand(self):
        hands = [_hand(0.2, 0.5, 1), _hand(0.8, 0.5, 2)]
        palm = ((0.8 + 0.8) / 2 * 640, (0.5 + 0.7) / 2 * 480)
        assert _active_hand_index(hands, 640, 480, palm) == 1

    def test_no_hands_gives_minus_one(self):
        assert _active_hand_index([], 640, 480, (0.0, 0.0)) == -1

    def test_palm_without_lands_gives_minus_one(self):
        hands = [_hand(0.2, 0.5), _hand(0.8, 0.5, 2)]
        assert _active_hand_index(hands, 640, 480, (1234.0, 5678.0)) == -1

    def test_none_palm_gives_minus_one(self):
        hands = [_hand(0.5, 0.5)]
        assert _active_hand_index(hands, 640, 480, None) == -1

    def test_matches_the_pool_palm_formula(self):
        # O centro tem de ser calculado exactamente como o HandPool, senao o
        # casamento falha sempre.
        hands = [_hand(0.3, 0.4, 5)]
        h = hands[0]
        expected_x = (h[0][0] + h[9][0]) / 2.0 * 640
        expected_y = (h[0][1] + h[9][1]) / 2.0 * 480
        assert _active_hand_index(hands, 640, 480, (expected_x, expected_y)) == 0

    def test_2d_landmarks_are_accepted(self):
        pts = np.asarray([(0.5, 0.5)] * 21, dtype=np.float32)
        pts[9] = (0.5, 0.7)
        assert _active_hand_index([pts], 640, 480, (0.5 * 640, 0.6 * 480)) == 0


class TestRecorderThroughEngineIndex:
    def test_recorder_receives_the_chosen_hand(self):
        rec = CorpusRecorder()
        rec.set_label("OPEN")
        hands = [_hand(0.2, 0.5, 1), _hand(0.8, 0.5, 2)]
        palm = ((0.8 + 0.8) / 2 * 640, (0.5 + 0.7) / 2 * 480)
        i = _active_hand_index(hands, 640, 480, palm)
        rec.observe(hands, ["Left", "Right"], i, 0)
        assert rec.frames == 1
        # a mao do cursor (indice 1) foi a gravada
        assert np.allclose(rec.corpus.arrays().landmarks[0][0], hands[1])

    def test_unmatched_palm_records_nothing(self):
        rec = CorpusRecorder()
        rec.set_label("PINCH")
        hands = [_hand(0.2, 0.5)]
        rec.observe(hands, ["Right"], _active_hand_index(hands, 640, 480, None), 0)
        assert rec.frames == 0


class TestEngineWiring:
    def test_engine_ctx_exposes_a_recorder_slot(self):
        # A ligacao tem de ser opcional: sem --record, E.recorder e None e o
        # engine corre exactamente como antes.
        from config import Config
        from core.autotune import AutoTuner
        from core.commands import AppCtl
        from core.engine import make_engine_ctx

        ctx = AppCtl()
        ctx.snap = None
        E = make_engine_ctx(Config(), 1, None, AutoTuner(Config()), ctx)
        assert E.recorder is None

    def test_preview_keys_do_not_collide_with_label_keys(self):
        # Uma colisao faria o operador sair/guardar/voz ao tentar etiquetar.
        # Ver core.corpus: q/s/a/b/m/v/h sao controlo; por isso as classes
        # restantes usam c/d/g.
        from core.corpus import LABEL_KEYS
        from core.engine import PREVIEW_KEYS

        assert not (set(LABEL_KEYS) & PREVIEW_KEYS)

    def test_label_keys_cover_every_corpus_label(self):
        from core.corpus import ABSENT_LABEL, LABEL_KEYS, LABEL_NAMES

        assert set(LABEL_KEYS.values()) == set(LABEL_NAMES)
        assert ABSENT_LABEL in LABEL_KEYS.values()
