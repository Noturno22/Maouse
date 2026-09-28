"""Portao de regressao do reconhecimento: a fixture tem de se comportar igual.

Este e o unico teste do projecto que fixa o **comportamento** do classificador
de gestos (e nao o de uma unidade isolada). Sem ele, uma refactorizacao de
`core/gestures.py` que mexa na cadeia de limiares passava o CI e so se
descobria no hardware.

O que o teste garante
---------------------
* o corpus e reproduzivel (mesma seed, mesmas landmarks);
* o replay do corpus commitado bate certo com o baseline commitado;
* nenhuma classe perde precisao ou recall;
* os cliques fantasma nao aumentam e os cliques nao deixam de acontecer.

O que o teste NAO garante
-------------------------
Que o sistema e bom. A fixture e parametrica (`tools/make_corpus_fixture.py`):
mede regressao, nao qualidade em maos reais. Para numero de marketing so
serve um corpus gravado no hardware.

Sobre o F1 alvo
---------------
`--gate` com min_f1=0.97 hoje **falha** (0.896), e nao por acidente: o par
PINKY/SHAKA esta 100% trocado (ver `TestKnownLimitationShakaVsPinky`). O CI
compara com o baseline para bloquear *piora*; o alvo de aceitacao e um
judgemento a parte, que se decide quando houver corpus gravado. Um CI sempre
vermelho ensina toda a gente a ignorar o CI - pior do que nao ter.
"""
import json
import math
import os
from pathlib import Path

import numpy as np

from core.corpus import (
    FORMAT_VERSION,
    LABEL_NAMES,
    SETTLE_INDEX,
    Corpus,
)
from core.gestures import Gesture
from tools.eval_recognition import evaluate
from tools.make_corpus_fixture import (
    FINGER_CURLS,
    HEIGHT,
    RUNS,
    SCALE_PX,
    SEED,
    WIDTH,
    _place,
    _skeleton,
    corpus_path,
    make_corpus,
)

FIXTURES = Path(__file__).parent / "fixtures"
CORPUS = corpus_path(str(FIXTURES))
BASELINE = FIXTURES / "corpus_regressao_v1.baseline.json"

# O replay e determinista (sem rng, sem camera, sem rato), portanto a tolerancia
# existe so para proteger contra ruido de ponto flutuante entre versoes de
# numpy. Uma mudanca real de decisao move o F1 por centimos, nao por 1e-9.
TOL = 1e-9


def _report():
    return evaluate(CORPUS, width=WIDTH, height=HEIGHT)


def _baseline() -> dict:
    return json.loads(BASELINE.read_text(encoding="utf-8"))


class TestFixtureIsWellFormed:
    """A fixture so vale se ela propria for honesta."""

    def test_corpus_is_committed(self):
        assert Path(CORPUS).is_file(), (
            f"falta a fixture {CORPUS}; gerar com "
            "`python tools/make_corpus_fixture.py`"
        )
        assert BASELINE.is_file(), (
            f"falta o baseline {BASELINE}; gerar com "
            "`python tools/make_corpus_fixture.py --force`"
        )

    def test_format_version_is_current(self):
        with np.load(CORPUS, allow_pickle=False) as z:
            assert int(z["version"]) == FORMAT_VERSION

    def test_covers_every_gesture_it_claims_to_test(self):
        counts = Corpus.load(CORPUS).label_counts()
        missing = [
            g.name for g in Gesture
            if g is not Gesture.NONE and counts.get(g.name, 0) == 0
        ]
        assert not missing, f"gestos sem evidencia na fixture: {missing}"

    def test_has_frames_without_a_hand(self):
        # Sao a evidencia de que o pipeline nao inventa gestos. Sem eles os
        # cliques fantasma nao tem onde acontecer.
        a = Corpus.load(CORPUS).arrays()
        assert (~a.mask).any(axis=1).sum() > 0

    def test_has_settling_frames(self):
        # Se a fixture deixasse de marcar a transicao, o F1 passaria a contar o
        # debounce como erro e o baseline deixaria de ser comparavel.
        a = Corpus.load(CORPUS).arrays()
        assert (a.labels == SETTLE_INDEX).any()

    def test_labels_are_gestures_or_sentinels(self):
        a = Corpus.load(CORPUS).arrays()
        for index in a.labels[a.mask].ravel():
            value = int(index)
            if value >= 0:
                assert value < len(LABEL_NAMES)
            else:
                assert value == SETTLE_INDEX

    def test_hand_is_well_above_the_absolute_pixel_gate(self):
        # min_hand_scale_px = 55 px e um limiar ABSOLUTO: se a fixture meter uma
        # mao de 20 px, o replay classifica tudo NONE e a medicao deixa de dizer
        # alguma coisa. SCALE_PX mantem a mao a ~120 px.
        assert SCALE_PX > 55 * 2

    def test_runs_are_long_enough_to_exercise_transitions(self):
        # Os runs existem para exercitar TRANSICOES entre gestos vizinhos; um
        # run de um so gesto nao mede nada.
        assert all(len(run) >= 2 for run in RUNS)
        assert len(RUNS) >= 5

    def test_baseline_path_is_relative(self):
        # O baseline e versionado: um caminho absoluto da minha maquina tornaria
        # o diff ilegivel em qualquer outro checkout.
        path = _baseline()["corpus"]["path"]
        assert not os.path.isabs(path), f"caminho absoluto no baseline: {path}"
        assert ":" not in path, f"caminho com letra de unidade: {path}"


class TestGeneratorIsReproducible:
    def test_same_seed_gives_identical_landmarks(self):
        a = make_corpus(seed=SEED).arrays()
        b = make_corpus(seed=SEED).arrays()
        assert a.landmarks.tobytes() == b.landmarks.tobytes()
        assert a.labels.tolist() == b.labels.tolist()

    def test_different_seed_changes_noise_but_not_structure(self):
        a = make_corpus(seed=SEED).arrays()
        b = make_corpus(seed=SEED + 1).arrays()
        assert a.landmarks.tobytes() != b.landmarks.tobytes()
        assert a.labels.tolist() == b.labels.tolist()

    def test_regenerated_corpus_equals_the_committed_one(self):
        # Liga o ficheiro commitado ao gerador: mexer no gerador sem
        # re-baselinear tem de aparecer aqui, nao no hardware de um utilizador.
        a = make_corpus(seed=SEED).arrays()
        b = Corpus.load(CORPUS).arrays()
        assert a.landmarks.shape == b.landmarks.shape
        assert a.landmarks.tobytes() == b.landmarks.tobytes()


class TestReplayMatchesBaseline:
    """O portao propriamente dito."""

    def test_macro_f1_has_not_regressed(self):
        assert _report().score.macro_f1 >= _baseline()["macro_f1"] - TOL

    def test_accuracy_has_not_regressed(self):
        assert _report().score.accuracy >= _baseline()["accuracy"] - TOL

    def test_no_class_lost_recall(self):
        now = _report().score.per_class
        for name, before in _baseline()["per_class"].items():
            assert name in now, f"a classe {name} desapareceu do replay"
            assert now[name].recall >= before["recall"] - TOL, (
                f"recall de {name} desceu de {before['recall']} "
                f"para {now[name].recall}"
            )

    def test_no_class_lost_precision(self):
        now = _report().score.per_class
        for name, before in _baseline()["per_class"].items():
            assert name in now, f"a classe {name} desapareceu do replay"
            assert now[name].precision >= before["precision"] - TOL, (
                f"precisao de {name} desceu de {before['precision']} "
                f"para {now[name].precision}"
            )

    def test_no_new_phantom_clicks(self):
        assert (_report().score.events.phantom_clicks
                <= _baseline()["events"]["phantom_clicks"])

    def test_clicks_still_happen(self):
        # Uma queda de cliques e uma regressao silenciosa: o utilizador deixa
        # de poder clicar e o F1 continua a dar 1.0.
        assert (_report().score.events.total_clicks
                >= _baseline()["events"]["total_clicks"])

    def test_click_latency_did_not_grow(self):
        now = _report().score.events.latency_p95_ms
        before = _baseline()["events"]["latency_p95_ms"]
        if now is not None and before is not None:
            assert now <= before + TOL


class TestKnownLimitationShakaVsPinky:
    """A confusao que a fixture encontrou, e porque nao e um bug da fixture.

    `core/gestures.py:188-194` decide PINKY vs SHAKA por `thumb_out`: o
    deslocamento da ponta do polegar **relacionado com o landmark 3** tem de
    passar 0.30 (dx) ou 0.25 (dy) vezes a escala (pulso -> landmark 9).

    O modelo cinematico do projecto tem uma falange distal de 0.28 unidades
    para uma escala de 1.10, ou seja 0.2545. Nao existe pose com dx > 0.30. Para
    dy > 0.25 so resta uma janela de ~20 graus em torno da vertical. Numa mao
    real o racio e o mesmo (~30 mm de falange distal para ~95 mm de palma), pelo
    que o limiar mede anatomia e nao intencao — e o resultado varia de pessoa
    para pessoa.

    Consequencia medida na fixture: 100% das SHAKA sao lidas como PINKY, ou
    seja o Ctrl+V nunca acontece com o gesto "hang loose".
    """

    def test_thumb_phalanx_cannot_clear_the_horizontal_threshold(self):
        rng = np.random.default_rng(SEED)
        for _ in range(50):
            skel = _skeleton("SHAKA", rng)
            wrist, m9 = skel[0], skel[9]
            scale = float(np.hypot(m9[0] - wrist[0], m9[1] - wrist[1]))
            assert abs(float(skel[4][0] - skel[3][0])) < 0.30 * scale

    def test_vertical_window_is_under_twenty_degrees(self):
        # A falange distal mede 0.28 e o limiar e 0.275 (0.25 x 1.10). Para a
        # componente vertical bater, o angulo com a vertical tem de satisfazer
        # cos(t) > 0.275/0.28, ou seja t < 10.9 graus. O polegar tem de apontar
        # quase exactamente para cima (ou para baixo) para o SHAKA existir.
        assert math.degrees(math.acos(0.275 / 0.28)) < 20.0

    def test_pinky_and_shaka_are_the_same_finger_pose(self):
        # O que separa os dois gestos e o limiar anatomico acima, nao a pose.
        assert FINGER_CURLS["PINKY"] == FINGER_CURLS["SHAKA"]

    def test_shaka_is_always_read_as_pinky(self):
        # Fixa o comportamento actual para que a correcao seja visivel: quando
        # alguem a implementar, este teste falha e obriga a ler o porque.
        report = _report()
        assert report.score.per_class["SHAKA"].f1 == 0.0
        assert report.score.per_class["PINKY"].recall == 1.0


class TestPlacement:
    """A conversao modelo -> frame e o que torna a fixture valida."""

    @staticmethod
    def _px(placed: np.ndarray) -> np.ndarray:
        """Landmarks normalizadas -> o mesmo espaco que o GestureEngine usa:
        x e z multiplicados pela largura, y pela altura."""
        return placed * np.array([WIDTH, HEIGHT, WIDTH], dtype=np.float64)

    def test_pinch_closes_below_the_on_threshold(self):
        from config import Config
        from tools.make_corpus_fixture import _close_pinch

        cfg = Config()
        rng = np.random.default_rng(SEED)
        for _ in range(20):
            skel = _skeleton("PINCH", rng)
            _close_pinch(skel, 8, 7)
            px = self._px(_place(skel, rng))
            scale = float(np.linalg.norm(px[9] - px[0]))
            assert float(np.linalg.norm(px[8] - px[4])) < cfg.pinch_on_ratio * scale

    def test_placed_hand_stays_inside_the_frame(self):
        rng = np.random.default_rng(SEED)
        for label in ("OPEN", "FIST", "PEACE", "THUMB_UP", "ROCK"):
            placed = _place(_skeleton(label, rng), rng)
            assert (placed[:, :2] > -0.1).all() and (placed[:, :2] < 1.1).all()

    def test_placed_hand_is_above_the_pixel_gate(self):
        rng = np.random.default_rng(SEED)
        for _ in range(20):
            px = self._px(_place(_skeleton("OPEN", rng), rng))
            assert float(np.linalg.norm(px[9][:2] - px[0][:2])) > 55.0
