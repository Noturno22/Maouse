"""Testes do CorpusRecorder: a ponte entre a sessao ao vivo e o corpus.

O recorder grava **a mao do cursor** de cada frame, com a etiqueta que o
operador escolheu. So a mao activa e gravada, de proposito: com duas maos nao
ha forma honesta de saber, a partir de uma unica tecla, o que cada mao faz.
"""
import numpy as np
import pytest

from core.corpus import (
    LABEL_KEY_CHOICES,
    LABEL_KEYS,
    Corpus,
    CorpusRecorder,
)


def _hand(seed=0):
    r = np.random.default_rng(seed)
    pts = r.uniform(0.0, 0.3, (21, 3)).astype(np.float32)
    pts[0] = [0.5, 0.5, 0.0]
    pts[9] = [0.5, 0.8, 0.0]
    return pts


class TestLabelKeys:
    def test_every_gesture_has_a_key(self):
        # todas as classes do enum tem de ser alcancaveis pelo operador
        from core.gestures import Gesture

        assert set(LABEL_KEY_CHOICES.values()) == {g.name for g in Gesture}

    def test_no_duplicate_keys(self):
        assert len(LABEL_KEY_CHOICES) == len(set(LABEL_KEY_CHOICES))

    def test_keys_are_the_ord_of_the_choices(self):
        # A tabela de teclas tem de ser derivada da legivel, nunca paralela:
        # duas tabelas paralelas divergem em silencio.
        assert LABEL_KEYS == {ord(ch): n for ch, n in LABEL_KEY_CHOICES.items()}

    def test_rest_is_key_zero(self):
        # 0 tem de ser "sem mao": e o repouso, o estado mais importante para
        # medir alucinacao.
        assert LABEL_KEYS[ord("0")] == "NONE"

    def test_letters_are_lowercase_for_the_operator(self):
        # As letras tem de ser minusculas: cv2.waitKey devolve o ASCII cru, e
        # o operador nao deve depender de Shift. c/d/g porque q/s/a/b/m/v/h
        # sao controlo do preview.
        for ch in "cdg":
            assert ch in LABEL_KEY_CHOICES


class TestCorpusRecorder:
    def test_starts_on_rest(self):
        rec = CorpusRecorder()
        assert rec.label == "NONE"

    def test_set_label_accepts_name(self):
        rec = CorpusRecorder()
        rec.set_label("PINCH")
        assert rec.label == "PINCH"

    def test_set_label_accepts_gesture_enum(self):
        from core.gestures import Gesture

        rec = CorpusRecorder()
        rec.set_label(Gesture.FIST)
        assert rec.label == "FIST"

    def test_set_label_rejects_unknown(self):
        rec = CorpusRecorder()
        with pytest.raises(KeyError):
            rec.set_label("DANCA")

    def test_set_label_by_key(self):
        rec = CorpusRecorder()
        rec.set_label_by_key(ord("3"))
        assert rec.label == "PINCH"

    def test_set_label_by_unknown_key_is_ignored(self):
        rec = CorpusRecorder()
        rec.set_label("OPEN")
        rec.set_label_by_key(ord("z"))
        assert rec.label == "OPEN"

    def test_observe_records_one_hand(self):
        rec = CorpusRecorder()
        rec.set_label("OPEN")
        rec.observe([_hand()], ["Right"], 0, 30)
        assert rec.frames == 1
        assert rec.corpus.total == 1

    def test_observe_selects_the_given_hand(self):
        rec = CorpusRecorder()
        rec.set_label("PINCH")
        a, b = _hand(0), _hand(1)
        rec.observe([a, b], ["Left", "Right"], 1, 30)
        lm = rec.corpus.arrays().landmarks
        # a mao activa (indice 1) e a que fica na ranhura 0 do corpus
        assert np.allclose(lm[0][0], b)

    def test_observe_marks_active_slot_zero(self):
        rec = CorpusRecorder()
        rec.observe([_hand()], ["Right"], 0, 30)
        assert rec.corpus.arrays().active[0] == 0

    def test_observe_keeps_the_side(self):
        rec = CorpusRecorder()
        rec.observe([_hand()], ["Left"], 0, 30)
        _t, hands, sides, _l, _a = next(iter(rec.corpus.replay()))
        assert sides == ["Left"]

    def test_observe_ignores_missing_index(self):
        rec = CorpusRecorder()
        rec.observe([_hand()], ["Right"], 3, 30)
        assert rec.frames == 0

    def test_observe_ignores_hands_without_landmarks(self):
        rec = CorpusRecorder()
        rec.observe([], [], 0, 30)
        assert rec.corpus.total == 0

    def test_rest_label_records_absent_hand(self):
        # Em repouso (etiqueta NONE) um frame sem mao e informacao valiosa:
        # e a evidencia de que o pipeline nao inventou nada.
        rec = CorpusRecorder()
        rec.set_label("NONE")
        rec.observe([], [], -1, 30)
        assert rec.frames == 1
        assert rec.corpus.total == 0

    def test_rest_label_with_hand_present_is_kept(self):
        rec = CorpusRecorder()
        rec.set_label("NONE")
        rec.observe([_hand()], ["Right"], 0, 30)
        assert rec.corpus.total == 1

    def test_active_label_ignores_frames_without_hand(self):
        # Se o ground truth e um gesto e nao ha mao no frame, o frame nao serve
        # para nada: descartar e melhor que guardar falsidade.
        rec = CorpusRecorder()
        rec.set_label("PINCH")
        rec.observe([], [], -1, 30)
        assert rec.frames == 0

    def test_counters_follow_corpus(self):
        rec = CorpusRecorder()
        for i in range(5):
            rec.observe([_hand()], ["Right"], 0, i * 30)
        assert rec.frames == 5
        assert rec.total == 5

    def test_max_frames_stops_recording(self):
        rec = CorpusRecorder(max_frames=3)
        for i in range(10):
            rec.observe([_hand()], ["Right"], 0, i * 30)
        assert rec.frames == 3
        assert rec.full is True

    def test_full_is_false_while_recording(self):
        rec = CorpusRecorder()
        assert rec.full is False

    def test_flush_writes_the_file(self, tmp_path):
        path = tmp_path / "s.npz"
        rec = CorpusRecorder(path=path)
        rec.observe([_hand()], ["Right"], 0, 0)
        assert rec.flush() is True
        assert Corpus.load(path).frames == 1

    def test_flush_without_path_returns_false(self):
        rec = CorpusRecorder()
        rec.observe([_hand()], ["Right"], 0, 0)
        assert rec.flush() is False

    def test_flush_empty_returns_false(self, tmp_path):
        rec = CorpusRecorder(path=tmp_path / "s.npz")
        assert rec.flush() is False

    def test_flush_twice_overwrites(self, tmp_path):
        path = tmp_path / "s.npz"
        rec = CorpusRecorder(path=path)
        rec.observe([_hand()], ["Right"], 0, 0)
        rec.flush()
        rec.observe([_hand(2)], ["Right"], 0, 30)
        rec.flush()
        assert Corpus.load(path).frames == 2

    def test_reset_clears_but_keeps_label(self):
        rec = CorpusRecorder()
        rec.set_label("FIST")
        rec.observe([_hand()], ["Right"], 0, 0)
        rec.reset()
        assert rec.frames == 0
        assert rec.label == "FIST"
