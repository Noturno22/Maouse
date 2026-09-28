"""Testes do formato de corpus de landmarks (core/corpus.py).

O corpus e o artefacto central da Onda 0: guarda as landmarks JA TRACKED
(normalizadas) + a etiqueta humana, para que o pipeline geometrico possa ser
re-executado de forma deterministica, sem camera e sem rato.

Formato (npz):
    landmarks : (F, 2, 21, 3) float32  - posicoes normalizadas 0..1
    mask      : (F, 2)      bool        - True = esta mao existe neste frame
    sides     : (F, 2)      int8        - 0=Left, 1=Right
    labels    : (F, 2)      int8        - indice em LABEL_NAMES, -1 = sem mao
    active    : (F,)        int8        - indice da mao do cursor, -1 = nenhuma
    t_ms      : (F,)        int64       - timestamp do frame
"""
import numpy as np
import pytest

from core.corpus import (
    ACTIVE_NONE,
    FORMAT_VERSION,
    LABEL_NAMES,
    MAX_HANDS,
    N_LABELS,
    SETTLE_INDEX,
    SETTLE_LABEL,
    SIDE_LEFT,
    SIDE_RIGHT,
    Corpus,
    label_index,
    label_name,
    side_name,
)
from core.gestures import Gesture


class TestLabelVocabulary:
    def test_covers_every_gesture(self):
        # O corpus tem de conseguir descrever TUDO o que o engine pode emitir,
        # senao um "gesto desconhecido" fica sem ground truth.
        assert set(LABEL_NAMES) == {g.name for g in Gesture}

    def test_none_is_first_and_is_the_absent_label(self):
        assert LABEL_NAMES[0] == "NONE"
        assert LABEL_NAMES[ACTIVE_NONE + 1] == "NONE"

    def test_label_count_matches_constant(self):
        assert N_LABELS == len(LABEL_NAMES)

    def test_label_index_roundtrip(self):
        for i, name in enumerate(LABEL_NAMES):
            assert label_index(name) == i
            assert label_name(i) == name

    def test_label_index_accepts_gesture_enum(self):
        assert label_index(Gesture.PINCH) == LABEL_NAMES.index("PINCH")

    def test_label_index_rejects_unknown(self):
        with pytest.raises(KeyError):
            label_index("NAO_EXISTE")

    def test_label_index_rejects_non_string(self):
        with pytest.raises(KeyError):
            label_index(7)

    def test_side_names(self):
        assert side_name(SIDE_LEFT) == "Left"
        assert side_name(SIDE_RIGHT) == "Right"


class TestSettleLabel:
    """``SETTLE`` e um marcador de frame em transicao, nao um gesto.

    Vive com indice negativo para nao poder colidir com nenhum
    ``LABEL_NAMES``. O risco de o tratar como indice normal e indexar
    ``LABEL_NAMES[-2]``, que devolve um gesto real em silencio.
    """
    def test_is_not_a_gesture(self):
        assert SETTLE_LABEL not in LABEL_NAMES
        assert SETTLE_INDEX < 0

    def test_index_roundtrip(self):
        assert label_index(SETTLE_LABEL) == SETTLE_INDEX
        assert label_name(SETTLE_INDEX) == SETTLE_LABEL

    def test_label_name_rejects_out_of_range(self):
        with pytest.raises(ValueError):
            label_name(len(LABEL_NAMES))
        with pytest.raises(ValueError):
            label_name(-3)

    def test_survives_the_npz_roundtrip(self, tmp_path):
        c = Corpus()
        hand = np.zeros((21, 3), dtype=np.float32)
        hand[9][1] = 0.3
        c.add_frame(0, [hand], ["Right"], [SETTLE_LABEL], 0)
        p = tmp_path / "c.npz"
        assert c.save(p) is True
        back = Corpus.load(p)
        _t, hands, _sides, labels, _active = next(iter(back.replay()))
        assert len(hands) == 1
        assert labels == [SETTLE_LABEL]
        assert back.label_counts()[SETTLE_LABEL] == 1

    def test_settle_is_counted_separately_from_gestures(self, tmp_path):
        c = Corpus()
        hand = np.zeros((21, 3), dtype=np.float32)
        hand[9][1] = 0.3
        c.add_frame(0, [hand], ["Right"], [SETTLE_LABEL], 0)
        c.add_frame(33, [hand], ["Right"], ["OPEN"], 0)
        counts = c.label_counts()
        assert counts[SETTLE_LABEL] == 1
        assert counts["OPEN"] == 1
        assert c.total == 2


class TestCorpusBuilder:
    def _hand(self, x=0.5, y=0.5, seed=0):
        r = np.random.default_rng(seed)
        pts = r.uniform(0.0, 0.4, (21, 3)).astype(np.float32)
        pts[0] = [x, y, 0.0]
        pts[9] = [x, y + 0.2, 0.0]
        return pts

    def test_starts_empty(self):
        c = Corpus()
        assert c.frames == 0
        assert c.total == 0

    def test_add_frame_stores_one_hand(self):
        c = Corpus()
        c.add_frame(
            t_ms=100,
            hands=[self._hand()],
            sides=["Right"],
            labels=["PINCH"],
            active=0,
        )
        assert c.frames == 1
        assert c.total == 1

    def test_frame_without_hands_is_kept(self):
        # Frames vazios sao VALIOSOS: sao os que revelam alucinacao (o pipeline
        # nao deve inventar gestos quando nao ha mao nenhuma).
        c = Corpus()
        c.add_frame(t_ms=1, hands=[], sides=[], labels=[], active=ACTIVE_NONE)
        assert c.frames == 1
        assert c.total == 0

    def test_total_counts_hands_not_frames(self):
        c = Corpus()
        c.add_frame(1, [self._hand(seed=0), self._hand(seed=1)], ["Left", "Right"],
                    ["OPEN", "FIST"], 0)
        c.add_frame(2, [self._hand(seed=2)], ["Right"], ["PEACE"], 0)
        assert c.frames == 2
        assert c.total == 3

    def test_active_index_selects_cursor_hand(self):
        c = Corpus()
        c.add_frame(1, [self._hand(seed=0), self._hand(seed=1)], ["Left", "Right"],
                    ["OPEN", "PINCH"], 1)
        a = c.arrays()
        assert a.mask[0].tolist() == [True, True]
        assert a.active[0] == 1

    def test_missing_hand_is_masked(self):
        c = Corpus()
        c.add_frame(1, [self._hand()], ["Right"], ["OPEN"], 0)
        a = c.arrays()
        assert a.mask[0].tolist() == [True, False]

    def test_too_many_hands_raises(self):
        c = Corpus()
        with pytest.raises(ValueError, match="2"):
            c.add_frame(1, [self._hand()] * 3, ["Right"] * 3, ["OPEN"] * 3, 0)

    def test_side_of_absent_slot_is_stored_as_left(self):
        c = Corpus()
        c.add_frame(1, [self._hand()], ["Right"], ["OPEN"], 0)
        a = c.arrays()
        assert not a.mask[0][1]
        assert a.sides[0][1] == SIDE_LEFT

    def test_none_label_marks_absent_hand(self):
        c = Corpus()
        c.add_frame(1, [self._hand()], ["Right"], ["NONE"], 0)
        a = c.arrays()
        assert a.mask[0][0]
        assert a.labels[0][0] == 0

    def test_unknown_side_rejected(self):
        c = Corpus()
        with pytest.raises(ValueError):
            c.add_frame(1, [self._hand()], ["Middle"], ["OPEN"], 0)

    def test_unknown_label_rejected(self):
        c = Corpus()
        with pytest.raises(KeyError):
            c.add_frame(1, [self._hand()], ["Right"], ["DANCA"], 0)

    def test_mismatched_lengths_rejected(self):
        c = Corpus()
        with pytest.raises(ValueError):
            c.add_frame(1, [self._hand()], ["Right", "Left"], ["OPEN"], 0)

    def test_active_out_of_range_rejected(self):
        c = Corpus()
        with pytest.raises(ValueError, match="active"):
            c.add_frame(1, [self._hand()], ["Right"], ["OPEN"], 5)

    def test_active_on_empty_frame_rejected(self):
        c = Corpus()
        with pytest.raises(ValueError, match="active"):
            c.add_frame(1, [], [], [], 0)

    def test_non_finite_landmarks_rejected(self):
        c = Corpus()
        bad = self._hand()
        bad[4] = [np.nan, 0.1, 0.0]
        with pytest.raises(ValueError, match="finit"):
            c.add_frame(1, [bad], ["Right"], ["OPEN"], 0)

    def test_clear_empties(self):
        c = Corpus()
        c.add_frame(1, [self._hand()], ["Right"], ["OPEN"], 0)
        c.clear()
        assert c.frames == 0
        assert c.total == 0


class TestCorpusRoundTrip:
    def _rich(self):
        c = Corpus()
        r = np.random.default_rng(3)
        for f in range(5):
            h = r.uniform(0, 1, (21, 3)).astype(np.float32)
            h[0] = [0.4, 0.4, 0.0]
            h[9] = [0.4, 0.6, 0.0]
            c.add_frame(t_ms=1000 + f * 33, hands=[h], sides=["Right"],
                        labels=["FIST"], active=0)
        c.add_frame(t_ms=1200, hands=[], sides=[], labels=[], active=ACTIVE_NONE)
        return c

    def test_save_then_load_preserves_frames(self, tmp_path):
        src = self._rich()
        path = tmp_path / "c.npz"
        assert src.save(path) is True
        back = Corpus.load(path)
        assert back.frames == src.frames
        assert back.total == src.total

    def test_save_then_load_preserves_timestamps(self, tmp_path):
        src = self._rich()
        path = tmp_path / "c.npz"
        src.save(path)
        assert (Corpus.load(path).arrays().t_ms.tolist()
                == src.arrays().t_ms.tolist())

    def test_save_then_load_preserves_landmarks(self, tmp_path):
        src = self._rich()
        path = tmp_path / "c.npz"
        src.save(path)
        assert np.allclose(Corpus.load(path).arrays().landmarks,
                           src.arrays().landmarks)

    def test_save_then_load_preserves_labels(self, tmp_path):
        src = self._rich()
        path = tmp_path / "c.npz"
        src.save(path)
        lb = Corpus.load(path).arrays().labels
        assert lb[0][0] == label_index("FIST")
        assert lb[-1].tolist() == [-1, -1]

    def test_save_creates_parent_dir(self, tmp_path):
        src = self._rich()
        path = tmp_path / "sub" / "dir" / "c.npz"
        assert src.save(path) is True
        assert path.is_file()

    def test_save_empty_corpus_fails(self, tmp_path):
        assert Corpus().save(tmp_path / "c.npz") is False

    def test_loaded_corpus_can_be_extended(self, tmp_path):
        src = self._rich()
        path = tmp_path / "c.npz"
        src.save(path)
        back = Corpus.load(path)
        h = np.zeros((21, 3), dtype=np.float32)
        h[0] = [0.5, 0.5, 0.0]
        h[9] = [0.5, 0.7, 0.0]
        back.add_frame(t_ms=9999, hands=[h], sides=["Left"], labels=["OPEN"], active=0)
        assert back.frames == src.frames + 1

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            Corpus.load(tmp_path / "nao_existe.npz")

    def test_file_without_version_raises(self, tmp_path):
        p = tmp_path / "c.npz"
        np.savez_compressed(p, landmarks=np.zeros((1, 2, 21, 3), dtype=np.float32))
        with pytest.raises(ValueError, match="vers"):
            Corpus.load(p)

    def test_future_version_raises(self, tmp_path):
        p = tmp_path / "c.npz"
        np.savez_compressed(
            p,
            landmarks=np.zeros((1, 2, 21, 3), dtype=np.float32),
            version=np.array(FORMAT_VERSION + 1),
        )
        with pytest.raises(ValueError, match="vers"):
            Corpus.load(p)


class TestCorpusReplay:
    def test_replay_yields_tracker_style_tuples(self, tmp_path):
        c = Corpus()
        r = np.random.default_rng(1)
        for f in range(3):
            h = r.uniform(0, 1, (21, 3)).astype(np.float32)
            h[0] = [0.5, 0.5, 0.0]
            h[9] = [0.5, 0.7, 0.0]
            c.add_frame(10 * f, [h], ["Right"], ["OPEN"], 0)
        path = tmp_path / "c.npz"
        c.save(path)

        got = list(Corpus.load(path).replay())
        assert len(got) == 3
        t_ms, hands, sides, labels, active = got[0]
        assert t_ms == 0
        # Mesma forma que devolve HandTracker.process -> encaixa directo no pool.
        assert len(hands) == 1
        assert np.asarray(hands[0]).shape == (21, 3)
        assert sides == ["Right"]
        assert labels == ["OPEN"]
        assert active == 0

    def test_replay_of_empty_frame_gives_empty_lists(self, tmp_path):
        c = Corpus()
        c.add_frame(1, [], [], [], ACTIVE_NONE)
        path = tmp_path / "c.npz"
        c.save(path)
        _t, hands, sides, labels, active = next(iter(Corpus.load(path).replay()))
        assert hands == []
        assert sides == []
        assert labels == []
        assert active == ACTIVE_NONE

    def test_replay_orders_frames_by_time(self, tmp_path):
        c = Corpus()
        h = np.zeros((21, 3), dtype=np.float32)
        h[9] = [0.5, 0.7, 0.0]
        for t in (30, 10, 20):
            c.add_frame(t, [h], ["Right"], ["OPEN"], 0)
        path = tmp_path / "c.npz"
        c.save(path)
        ts = [t for t, *_ in Corpus.load(path).replay()]
        assert ts == [10, 20, 30]

    def test_landmarks_are_normalised_not_pixels(self, tmp_path):
        # Guardar em px tornaria o corpus dependente da resolucao; o replay
        # tem de rodar com qualquer width/height.
        c = Corpus()
        h = np.zeros((21, 3), dtype=np.float32)
        h[0] = [0.25, 0.25, 0.0]
        h[9] = [0.25, 0.45, 0.0]
        c.add_frame(1, [h], ["Right"], ["OPEN"], 0)
        path = tmp_path / "c.npz"
        c.save(path)
        _t, hands, _s, _l, _a = next(iter(Corpus.load(path).replay()))
        assert np.asarray(hands[0])[0][0] == pytest.approx(0.25)


class TestCorpusStats:
    def test_label_histogram_counts_occurrences(self, tmp_path):
        c = Corpus()
        h = np.zeros((21, 3), dtype=np.float32)
        h[9] = [0.5, 0.7, 0.0]
        c.add_frame(1, [h], ["Right"], ["OPEN"], 0)
        c.add_frame(2, [h], ["Right"], ["PINCH"], 0)
        c.add_frame(3, [h, h.copy()], ["Left", "Right"], ["OPEN", "FIST"], 0)
        assert c.label_counts()["OPEN"] == 2
        assert c.label_counts()["PINCH"] == 1
        assert c.label_counts()["FIST"] == 1

    def test_duration_seconds(self, tmp_path):
        c = Corpus()
        h = np.zeros((21, 3), dtype=np.float32)
        h[9] = [0.5, 0.7, 0.0]
        c.add_frame(0, [h], ["Right"], ["OPEN"], 0)
        c.add_frame(2000, [h], ["Right"], ["OPEN"], 0)
        assert c.duration_s() == pytest.approx(2.0)

    def test_duration_of_single_frame_is_zero(self):
        c = Corpus()
        h = np.zeros((21, 3), dtype=np.float32)
        h[9] = [0.5, 0.7, 0.0]
        c.add_frame(500, [h], ["Right"], ["OPEN"], 0)
        assert c.duration_s() == 0.0

    def test_two_hand_frames_counted(self):
        c = Corpus()
        h = np.zeros((21, 3), dtype=np.float32)
        h[9] = [0.5, 0.7, 0.0]
        c.add_frame(1, [h, h], ["Left", "Right"], ["OPEN", "PINCH"], 0)
        assert c.two_hand_frames == 1

    def test_max_hands_constant(self):
        assert MAX_HANDS == 2
