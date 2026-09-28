"""Testes do harness de avaliacao de reconhecimento (tools/eval_recognition.py).

Este e o coracao da Onda 0: sem mediicao objectiva nao ha forma de provar que
uma mudanca no classificador melhorou (ou piorou) o sistema.

Duas niveis de metrica:
  * frame  -> precisao/recall/F1 por gesto + confusion matrix
  * evento -> cliques fantasma/hora + latencia de reacao (ms)

O harness tem de correr SEM camera, SEM rato e SEM modelo de IA.
"""
import numpy as np
import pytest

from core.corpus import ACTIVE_NONE, Corpus
from core.gestures import Gesture
from tools.eval_recognition import (
    CLICK_GESTURES,
    EventStats,
    Prediction,
    _click_latencies,
    acceptance_report,
    click_episodes,
    confusion_matrix,
    evaluate,
    macro_f1,
    ordered_labels,
    per_class_prf,
    score_predictions,
)


def _skeleton(seed=0, span=0.3):
    """Esqueleto de mao plausivel e ESTAVEL (mesma pose em todos os frames).

    ``span`` e a distancia normalizada pulso->lambida 9. Por omissao 0.3, que
    a 240px de altura da 72px: acima de ``min_hand_scale_px`` (55), logo o
    gesto e classificado normalmente.
    """
    r = np.random.default_rng(seed)
    pts = r.uniform(0.0, 0.3, (21, 3)).astype(np.float32)
    pts[0] = [0.5, 0.5, 0.0]
    pts[9] = [0.5, 0.5 + span, 0.0]
    return pts


def _corpus_from(labels, active=0, step_ms=33, hand=None):
    """Corpus de uma mao, com ground truth = `labels` (um por frame)."""
    hand = _skeleton() if hand is None else hand
    c = Corpus()
    for i, name in enumerate(labels):
        c.add_frame(i * step_ms, [hand.copy()], ["Right"], [name], active)
    return c


class TestClickGestureSet:
    def test_click_gestures_is_pinch(self):
        # Alvo do documento: o clique esquerdo so pode nascer de PINCH.
        assert CLICK_GESTURES == frozenset({Gesture.PINCH})


class TestConfusionMatrix:
    """Os eixos seguem sempre a ordem canonica ``sorted(base | observados)``.

    Assim a mesma evidencia produz a mesma matriz qualquer que seja a ordem
    em que o caller liste as classes.
    """

    def test_diagonal_when_all_correct(self):
        pairs = [("OPEN", "OPEN")] * 3 + [("FIST", "FIST")] * 2
        base = ("OPEN", "FIST")
        m = confusion_matrix(pairs, base)
        order = ordered_labels(base, pairs)
        ix = {n: i for i, n in enumerate(order)}
        assert m.shape == (2, 2)
        assert m[ix["OPEN"], ix["OPEN"]] == 3
        assert m[ix["FIST"], ix["FIST"]] == 2
        assert m.sum() == 5

    def test_off_diagonal_counts_misclassification(self):
        pairs = [("OPEN", "ONE")]
        base = ("OPEN", "FIST")
        m = confusion_matrix(pairs, base)
        order = ordered_labels(base, pairs)
        ix = {n: i for i, n in enumerate(order)}
        assert m[ix["OPEN"], ix["ONE"]] == 1
        assert m[ix["OPEN"], ix["OPEN"]] == 0

    def test_empty_is_all_zero(self):
        m = confusion_matrix([], ("OPEN", "FIST"))
        assert m.sum() == 0
        assert m.shape == (2, 2)

    def test_unseen_label_in_prediction_becomes_an_extra_axis(self):
        pairs = [("OPEN", "THREE")]
        base = ("OPEN", "FIST")
        order = ordered_labels(base, pairs)
        m = confusion_matrix(pairs, base)
        assert m.shape == (len(order), len(order))
        assert order == sorted(set(base) | {"THREE"})

    def test_order_is_canonical_regardless_of_base_order(self):
        pairs = [("FIST", "FIST")]
        a = confusion_matrix(pairs, ("FIST", "OPEN"))
        b = confusion_matrix(pairs, ("OPEN", "FIST"))
        assert a.tolist() == b.tolist()

    def test_explicit_label_order_is_respected(self):
        m = confusion_matrix([("PINCH", "PINCH")], ("PINCH", "FIST"),
                             label_order=("FIST", "PINCH"))
        assert m[1][1] == 1

    def test_label_order_must_cover_the_data(self):
        with pytest.raises(KeyError):
            confusion_matrix([("OPEN", "THREE")], ("OPEN", "FIST"),
                             label_order=("OPEN", "FIST"))


class TestPerClassPrf:
    def test_perfect_classification(self):
        m = confusion_matrix(
            [("PINCH", "PINCH")] * 10, ("PINCH", "FIST"), label_order=("FIST", "PINCH")
        )
        prf = per_class_prf(m, ("FIST", "PINCH"))
        assert prf["PINCH"].precision == 1.0
        assert prf["PINCH"].recall == 1.0
        assert prf["PINCH"].f1 == 1.0

    def test_zero_division_is_zero_not_nan(self):
        m = np.array([[0, 0], [0, 5]], dtype=np.int64)
        prf = per_class_prf(m, ("A", "B"))
        assert prf["A"].precision == 0.0
        assert prf["A"].recall == 0.0
        assert prf["A"].f1 == 0.0
        assert prf["B"].recall == 1.0

    def test_precision_penalises_false_positives(self):
        # Verdadeiros: 1 PINCH. Previstos: 1 PINCH correcto + 9 falsos (linha
        # FIST, coluna PINCH) -> 10 previstos para 1 verdadeiro.
        m = np.array([[1, 0], [9, 0]], dtype=np.int64)
        prf = per_class_prf(m, ("PINCH", "OUTRO"))
        assert prf["PINCH"].precision == pytest.approx(0.1)
        assert prf["PINCH"].recall == 1.0

    def test_macro_f1_averages_present_classes(self):
        m = np.array([[5, 0], [0, 5]], dtype=np.int64)
        assert macro_f1(m, ("A", "B")) == pytest.approx(1.0)

    def test_macro_f1_ignores_classes_without_support(self):
        # Classe B nunca aparece: nao pode arrastar a media para baixo.
        m = np.array([[10, 0], [0, 0]], dtype=np.int64)
        assert macro_f1(m, ("A", "B")) == pytest.approx(1.0)


class TestClickEpisodes:
    """Um 'episodio de clique' e uma sequencia continua de left_down.

    Medir por episodio (e nao por frame) e o que torna a metrica honesta: o
    debounce do engine atrasa o clique alguns frames, e esse atraso NAO e um
    erro. Um clique que cai dentro de um segmento PINCH e correcto mesmo
    chegando tarde.
    """
    def test_single_episode(self):
        # 3 frames com left_down seguidos.
        events = [None, "left_down", "left_down", "left_down", None]
        labels = [None, "PINCH", "PINCH", "PINCH", None]
        eps = click_episodes(events, labels)
        assert len(eps) == 1
        assert eps[0].start_frame == 1
        assert eps[0].length == 3

    def test_two_separate_episodes(self):
        events = ["left_down", "left_down", None, None, "left_down", None]
        labels = ["PINCH", "PINCH", "PINCH", "PINCH", "PINCH", "PINCH"]
        eps = click_episodes(events, labels)
        assert len(eps) == 2

    def test_episode_within_intent_is_true(self):
        events = ["left_down", "left_down"]
        labels = ["PINCH", "PINCH"]
        eps = click_episodes(events, labels)
        assert eps[0].is_phantom is False

    def test_episode_outside_intent_is_phantom(self):
        events = ["left_down", "left_down"]
        labels = ["OPEN", "OPEN"]
        eps = click_episodes(events, labels)
        assert eps[0].is_phantom is True

    def test_late_click_inside_pinch_segment_is_not_phantom(self):
        # O debounce atrasa 2 frames: o clique dispara em t+2, ainda no PINCH.
        labels = ["PINCH"] * 5
        events = [None, None, "left_down", "left_down", None]
        eps = click_episodes(events, labels)
        assert eps[0].is_phantom is False

    def test_no_events_gives_no_episodes(self):
        assert click_episodes([None] * 5, ["OPEN"] * 5) == []


class TestEventStats:
    def test_phantom_rate_per_hour(self):
        s = EventStats(total_clicks=5, phantom_clicks=5, duration_s=3600.0)
        assert s.phantom_per_hour == pytest.approx(5.0)

    def test_phantom_rate_scales_with_duration(self):
        s = EventStats(total_clicks=5, phantom_clicks=5, duration_s=1800.0)
        assert s.phantom_per_hour == pytest.approx(10.0)

    def test_zero_duration_is_zero_rate(self):
        s = EventStats(total_clicks=0, phantom_clicks=0, duration_s=0.0)
        assert s.phantom_per_hour == 0.0

    def test_latency_percentiles(self):
        s = EventStats(latencies_ms=[10.0, 20.0, 30.0, 40.0])
        p50, p95 = s.latency_p50_ms, s.latency_p95_ms
        assert p50 is not None and p95 is not None
        assert p50 == pytest.approx(25.0, abs=6.0)
        assert p95 >= p50

    def test_no_latency_is_none(self):
        s = EventStats()
        assert s.latency_p50_ms is None
        assert s.latency_p95_ms is None

    def test_latency_percentile_p95_ge_p50_on_ugly_values(self):
        s = EventStats(latencies_ms=[3.0, 3.0, 4.0, 900.0])
        p50, p95 = s.latency_p50_ms, s.latency_p95_ms
        assert p50 is not None and p95 is not None
        assert p95 >= p50


class TestClickLatency:
    """Latencia = instante do primeiro frame do segmento ate ao clique.

    Regressao: as amostras de latencia 0 ms eram descartadas, e o relatorio
    passava a dizer "sem latencia" exactamente quando o classificador estava
    melhor — commit na primeira frame. Um numero que desaparece no melhor caso
    e pior do que um numero feio.
    """
    def test_zero_latency_is_kept(self):
        # Clique no primeiro frame do segmento: latencia 0, e mesmo assim e
        # uma medicao.
        labels = ["SETTLE", "PINCH", "PINCH"]
        events = ["left_down", None, None]
        eps = click_episodes(events, labels)
        assert _click_latencies(eps, labels, [0, 33, 66]) == [0.0]

    def test_latency_counts_from_the_start_of_the_settle_window(self):
        # A janela de transicao pertence ao gesto destino: o clique no frame 2
        # do PINCH deve ser medido a partir do frame 0, nao do frame 2.
        labels = ["SETTLE", "PINCH", "PINCH", "PINCH"]
        events = [None, None, "left_down", None]
        eps = click_episodes(events, labels)
        assert _click_latencies(eps, labels, [0, 33, 66, 99]) == [66.0]

    def test_no_timestamps_gives_no_latency(self):
        labels = ["SETTLE", "PINCH"]
        events = ["left_down", None]
        eps = click_episodes(events, labels)
        assert _click_latencies(eps, labels, []) == []

    def test_phantom_click_still_contributes_latency(self):
        # A latencia descreve o atraso; a fantasia e outra metrica. Nao se
        # excluem cliques fantasma da distribuicao de latencia.
        labels = ["SETTLE", "OPEN", "OPEN"]
        events = ["left_down", None, None]
        eps = click_episodes(events, labels)
        assert eps[0].is_phantom is True
        assert _click_latencies(eps, labels, [0, 33, 66]) == [0.0]


class TestScorePredictions:
    def test_empty_prediction_set_scores_zero(self):
        sc = score_predictions([], [], [])
        assert sc.frames == 0
        assert sc.total == 0

    def test_perfect_scores(self):
        pairs = [("OPEN", "OPEN")] * 4
        sc = score_predictions(pairs, [None] * 4, [None] * 4)
        assert sc.accuracy == pytest.approx(1.0)
        assert sc.total == 4
        assert sc.macro_f1 == pytest.approx(1.0)

    def test_accuracy_counts_frame_agreement(self):
        pairs = [("OPEN", "OPEN"), ("FIST", "OPEN")]
        sc = score_predictions(pairs, [None] * 2, [None] * 2)
        assert sc.accuracy == pytest.approx(0.5)

    def test_worst_confusions_ranked_by_count(self):
        pairs = [("OPEN", "FIST")] * 5 + [("FIST", "OPEN")] * 1 + [("FIST", "FIST")] * 9
        sc = score_predictions(pairs, [None] * 15, [None] * 15)
        top = sc.worst_confusions[0]
        assert (top.truth, top.pred) == ("OPEN", "FIST")
        assert top.hits == 5

    def test_none_class_excluded_from_macro_f1(self):
        # "sem mao" nao e um gesto: inclui-lo no F1 distorce a leitura.
        pairs = [("OPEN", "OPEN")] * 4 + [("NONE", "NONE")] * 20
        sc = score_predictions(pairs, [None] * 24, [None] * 24)
        assert sc.macro_f1 == pytest.approx(1.0)
        assert sc.total == 4

    def test_event_stats_aggregated(self):
        events = ["left_down", "left_down", None, "left_down", None]
        labels = ["PINCH", "PINCH", "PINCH", "OPEN", "OPEN"]
        sc = score_predictions([("PINCH", "PINCH")] * 5, events, labels,
                               duration_s=3600.0)
        assert sc.events.total_clicks == 2
        assert sc.events.phantom_clicks == 1
        assert sc.events.phantom_per_hour == pytest.approx(1.0)


class TestAcceptanceReport:
    def test_passes_when_targets_met(self):
        sc = score_predictions([("PINCH", "PINCH")] * 100, [None] * 100, [None] * 100,
                               duration_s=3600.0)
        rep = acceptance_report(sc, min_f1=0.97, min_pinch_precision=0.99,
                                max_phantom_per_hour=0.0)
        assert rep.passed is True
        assert rep.failures == ()

    def test_fails_on_low_f1(self):
        sc = score_predictions([("OPEN", "FIST")] * 100, [None] * 100, [None] * 100)
        rep = acceptance_report(sc, min_f1=0.97, min_pinch_precision=0.0,
                                max_phantom_per_hour=999.0)
        assert rep.passed is False
        assert any("F1" in f for f in rep.failures)

    def test_fails_on_phantom_clicks(self):
        sc = score_predictions(
            [("OPEN", "OPEN")] * 10, ["left_down"] * 10, ["OPEN"] * 10,
            duration_s=3600.0,
        )
        rep = acceptance_report(sc, min_f1=0.0, min_pinch_precision=0.0,
                                max_phantom_per_hour=0.0)
        assert rep.passed is False
        assert any("fantasma" in f for f in rep.failures)

    def test_pinch_precision_target_enforced(self):
        m = np.zeros((2, 2), dtype=np.int64)
        m[0][0] = 90   # 90 PINCH correctos
        m[1][0] = 10   # 10 nao-PINCH classificados como PINCH
        pairs = ([("PINCH", "PINCH")] * 90 + [("FIST", "PINCH")] * 10)
        sc = score_predictions(pairs, [None] * 100, [None] * 100)
        rep = acceptance_report(sc, min_f1=0.0, min_pinch_precision=0.99,
                                max_phantom_per_hour=999.0)
        assert rep.passed is False
        assert any("PINCH" in f for f in rep.failures)

    def test_absent_pinch_class_skips_its_check(self):
        sc = score_predictions([("OPEN", "OPEN")] * 10, [None] * 10, [None] * 10)
        rep = acceptance_report(sc, min_f1=0.0, min_pinch_precision=0.99,
                                max_phantom_per_hour=999.0)
        assert rep.passed is True


class TestEvaluate:
    def test_evaluate_runs_without_camera_or_mouse(self, tmp_path):
        c = _corpus_from(["OPEN"] * 6 + ["PINCH"] * 6)
        p = tmp_path / "c.npz"
        c.save(p)
        rep = evaluate(p, width=640, height=480)
        assert rep.score.total == 12
        assert rep.corpus_frames == 12

    def test_evaluate_is_deterministic(self, tmp_path):
        c = _corpus_from(["FIST"] * 8)
        p = tmp_path / "c.npz"
        c.save(p)
        a = evaluate(p, width=640, height=480)
        b = evaluate(p, width=640, height=480)
        assert a.score.total == b.score.total
        assert a.score.accuracy == b.score.accuracy

    def test_evaluate_resolution_does_not_change_labels(self, tmp_path):
        # Acima do limiar de tamanho, o corpus normalizado tem de dar a mesma
        # taxa de acerto a 320x240 e a 1920x1080.
        c = _corpus_from(["OPEN"] * 5)
        p = tmp_path / "c.npz"
        c.save(p)
        a = evaluate(p, width=320, height=240)
        b = evaluate(p, width=1920, height=1080)
        assert a.score.accuracy == b.score.accuracy

    def test_small_hand_falls_below_absolute_pixel_gate(self, tmp_path):
        # ``min_hand_scale_px`` e um limiar em pixels ABSOLUTOS, nao em fracao
        # do frame: a mesma mao e "pequena demais" a 240px de altura e valida a
        # 1080px. Este teste fixa esse comportamento (que e uma fragilidade
        # real, registada em docs/RECONHECIMENTO_MAOS.md) para que uma
        # correcao futura seja visivel.
        small = _skeleton(span=0.1)   # 24px a 240px de altura, 108px a 1080px
        c = _corpus_from(["OPEN"] * 4, hand=small)
        p = tmp_path / "c.npz"
        c.save(p)
        low = evaluate(p, width=640, height=240)
        high = evaluate(p, width=1920, height=1080)
        assert low.score.per_class.get("OPEN") is None or \
            low.score.per_class["OPEN"].recall < high.score.per_class["OPEN"].recall

    def test_evaluate_reports_unseen_labels(self, tmp_path):
        # Corpus so com NONE: nao ha ground truth de gesto nenhum.
        c = Corpus()
        c.add_frame(0, [], [], [], ACTIVE_NONE)
        p = tmp_path / "c.npz"
        c.save(p)
        rep = evaluate(p)
        assert rep.score.total == 0

    def test_evaluate_emits_phantom_clicks_for_rogue_corpus(self, tmp_path):
        # Ground truth e sempre OPEN, mas o pipeline pode disparar cliques.
        c = _corpus_from(["OPEN"] * 20)
        p = tmp_path / "c.npz"
        c.save(p)
        rep = evaluate(p)
        # Nao exigimos que falhe (depende do esqueleto), so que a metrica existe.
        assert rep.score.events.total_clicks >= 0
        assert rep.score.events.phantom_clicks >= 0
        assert rep.score.events.phantom_clicks <= rep.score.events.total_clicks

    def test_report_has_human_readable_lines(self, tmp_path):
        c = _corpus_from(["OPEN"] * 4)
        p = tmp_path / "c.npz"
        c.save(p)
        rep = evaluate(p)
        text = rep.render()
        assert "acerto" in text.lower() or "accuracy" in text.lower()
        assert "F1" in text

    def test_report_json_is_serialisable(self, tmp_path):
        import json

        c = _corpus_from(["OPEN"] * 4)
        p = tmp_path / "c.npz"
        c.save(p)
        payload = json.loads(evaluate(p).to_json())
        assert "accuracy" in payload
        assert "per_class" in payload
        assert "events" in payload
        assert "acceptance" in payload


class TestSettleFramesAreNotEvaluated:
    """Frames em transicao ficam fora do F1, mas nao somem do relatorio.

    O ground truth sabe qual e o gesto destino desde o primeiro frame; o
    debounce do engine precisa de 2 frames (1 na pinca) para fechar. Contar essa
    janela como erro faria o F1 medir quantos segmentos o corpus tem, em vez da
    qualidade do classificador — e tornaria o alvo de 0.97 inalcancavel.
    """
    def test_settle_pairs_are_excluded_from_the_f1(self):
        pairs = [("OPEN", "FIST")] * 3 + [("SETTLE", "FIST")] * 2
        sc = score_predictions(pairs, [None] * 5, [None] * 5)
        assert sc.total == 3
        assert sc.settle == 2
        # So as 3 frames OPEN contam, e falharam todas.
        assert sc.accuracy == pytest.approx(0.0)
        assert "SETTLE" not in sc.per_class

    def test_settle_does_not_lower_macro_f1(self):
        clean = [("PINCH", "PINCH")] * 10
        noisy = [("SETTLE", "OPEN")] * 5 + clean
        assert score_predictions(noisy, [None] * 15, [None] * 15).macro_f1 == \
            score_predictions(clean, [None] * 10, [None] * 10).macro_f1

    def test_frames_counter_still_counts_everything(self):
        pairs = [("OPEN", "OPEN")] * 3 + [("SETTLE", "OPEN")] * 2
        sc = score_predictions(pairs, [None] * 5, [None] * 5)
        assert sc.frames == 5
        assert sc.total + sc.settle == 5

    def test_click_on_a_settling_frame_is_not_a_phantom(self):
        # A pinca fecha em 1 frame: o clique dispara no primeiro frame do
        # segmento, que e justamente o frame de transicao. Julgar esse frame
        # pelo gesto anterior contaria um clique correcto como fantasma.
        labels = ["OPEN"] * 4 + ["SETTLE", "PINCH", "PINCH", "PINCH"]
        events = [None] * 5 + ["left_down", "left_down", None, None]
        eps = click_episodes(events, labels)
        assert len(eps) == 1
        assert eps[0].is_phantom is False

    def test_click_after_a_settling_window_is_not_a_phantom(self):
        labels = ["OPEN", "SETTLE", "SETTLE", "PINCH", "PINCH"]
        events = [None, None, None, "left_down", None]
        eps = click_episodes(events, labels)
        assert eps[0].is_phantom is False

    def test_click_in_a_settling_window_that_leads_elsewhere_is_a_phantom(self):
        # A mao passou pela janela de transicao mas o clique disparou a fechar
        # PINCH -> OPEN. Nao ha intencao de clique: e fantasma.
        labels = ["PINCH", "PINCH", "SETTLE", "SETTLE", "OPEN", "OPEN"]
        events = [None, None, "left_down", "left_down", None, None]
        eps = click_episodes(events, labels)
        assert eps[0].is_phantom is True

    def test_trailing_settling_window_falls_back_to_the_previous_gesture(self):
        labels = ["PINCH", "PINCH", "SETTLE", "SETTLE"]
        events = [None, None, "left_down", None]
        eps = click_episodes(events, labels)
        assert eps[0].is_phantom is False


class TestPrediction:
    def test_fields(self):
        p = Prediction(frame=1, hand=0, truth="OPEN", pred="FIST")
        assert (p.frame, p.hand, p.truth, p.pred) == (1, 0, "OPEN", "FIST")
