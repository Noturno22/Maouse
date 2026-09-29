"""A janela de transicao que um corpus de maos reais nao pode escrever.

Um corpus gravado com `--record` tem como ground truth a etiqueta que o
operador escolheu com uma tecla. O `LABEL_KEY_CHOICES` nao tem SETTLE, e nao
tem porqueria: SETTLE nao e um gesto, e o operador nao tem quando o aplicar.
O que resta e que a etiqueta muda no instante da tecla e a mao so chega a pose
uns centimos de segundo depois. Sem uma janela, TODO inicio de segmento conta
como erro e o F1 mede a velocidade da mao humana em vez da qualidade do
classificador.

`settle_frames` deriva essa janela da **mudanca de etiqueta** — a unica coisa
que um corpus real tem para dizer "aqui comecou um segmento".

Duas propriedades que estes testes trancam, porque sao as que fazem o numero
confiavel:

1. A janela e um intervalo de **tempo**, nao uma contagem de frames. O mesmo
   corpus lido a 14,6 fps (HP i3-5005U) e a 30 fps tem de dar a mesma resposta
   ao mesmo intervalo em ms.
2. A janela e um **diagnostico ao lado** do F1, nunca a sua substituta. O gate
   avalia sempre o numero estrito; se nao, a janela passava a ser uma forma de
   tornar o alvo de 0.97 mais facil.
"""
import pytest

from tools.eval_recognition import (
    Prediction,
    evaluate,
    score_predictions,
    settle_frames,
)

MS = 33  # ~30 fps


def _seq(labels, step_ms=MS, start=0):
    """(predictions, events, truth, t_ms) para uma sequencia de ground truth."""
    t_ms = [start + i * step_ms for i in range(len(labels))]
    pairs = [
        Prediction(frame=i, hand=0, truth=name, pred=name)
        for i, name in enumerate(labels)
    ]
    return pairs, [None] * len(labels), list(labels), t_ms


class TestSettleFrames:
    def test_no_change_no_window(self):
        _, _, truth, t_ms = _seq(["OPEN"] * 10)
        assert settle_frames(truth, t_ms, 300) == set()

    def test_window_covers_the_frames_after_the_change(self):
        # 10 frames de OPEN, depois PINCH a partir do frame 10.
        truth = ["OPEN"] * 10 + ["PINCH"] * 10
        t_ms = [i * MS for i in range(20)]
        got = settle_frames(truth, t_ms, 300)
        # A janela e [t_mudanca, t_mudanca + 300). A mudanca e no t=330 ms, o
        # limite 630 ms, e o ultimo frame antes disso e o 19 (t=627).
        assert got == set(range(10, 20))
        assert t_ms[max(got)] - t_ms[10] < 300

    def test_window_is_time_based_not_frame_based(self):
        """O ponto 1. Mesma ground truth, dois rhythms, mesma janela em ms."""
        truth = ["OPEN"] * 10 + ["PINCH"] * 20
        slow = [i * 69 for i in range(30)]   # ~14,6 fps (HP i3-5005U)
        fast = [i * 33 for i in range(30)]   # ~30 fps
        a = settle_frames(truth, slow, 300)
        b = settle_frames(truth, fast, 300)
        # A fronteira e a mesma nos dois: o ultimo frame dentro da janela esta
        # a menos de 300 ms da mudanca, e o seguinte ja esta a 300 ms ou mais.
        for ts, got in ((slow, a), (fast, b)):
            change_t = ts[10]
            assert ts[max(got)] - change_t < 300
            nxt = max(got) + 1
            assert nxt >= len(ts) or ts[nxt] - change_t >= 300
        # E a mesma janela abrange menos frames na maquina lenta. Se a guarda
        # fosse "N frames", os dois corpora nao seriam comparaveis.
        assert len(a) < len(b)

    def test_no_timestamps_means_no_window(self):
        # Sem `t_ms` nao ha como saber quanto tempo passou. Devolver a janela
        # toda seria inventar; devolver nada e dizer porquê.
        _, _, truth, _ = _seq(["OPEN"] * 5 + ["PINCH"] * 5)
        assert settle_frames(truth, None, 300) == set()

    def test_zero_guard_is_a_no_op(self):
        truth = ["OPEN"] * 5 + ["PINCH"] * 5
        t_ms = [i * MS for i in range(10)]
        assert settle_frames(truth, t_ms, 0) == set()

    def test_transition_to_no_hand_is_also_a_transition(self):
        # A mao aparece: o pool precisa dos seus frames para fechar o debounce.
        truth = [None, None, None, "PINCH", "PINCH", "PINCH"]
        t_ms = [i * MS for i in range(6)]
        assert 3 in settle_frames(truth, t_ms, 150)

    def test_every_change_gets_its_own_window(self):
        truth = ["OPEN", "PINCH", "OPEN", "PINCH"] * 3
        t_ms = [i * MS for i in range(12)]
        got = settle_frames(truth, t_ms, 99)
        # Mudancas em 1, 2, 3 (e o ciclo repete) — cada uma abre a sua janela.
        assert {1, 2, 3, 5, 6, 7, 9, 10, 11} <= got


class TestScoreIsNeverInflated:
    """Ponto 2: a janela é diagnóstico, o gate continua a ver o estrito."""

    def _score_with_guard(self, guard_ms):
        # PINCH comecou mas o classificador ainda diz OPEN durante 4 frames: o
        # erro tipico de um corpus real, e o que a janela existe para medir.
        truth = ["OPEN"] * 6 + ["PINCH"] * 14
        t_ms = [i * MS for i in range(20)]
        pairs = [
            Prediction(
                frame=i, hand=0, truth=name,
                pred="OPEN" if 6 <= i < 10 else name,
            )
            for i, name in enumerate(truth)
        ]
        return score_predictions(
            pairs, [None] * 20, truth, duration_s=0.66, t_ms=t_ms,
            settle_guard_ms=guard_ms,
        )

    def test_strict_score_counts_the_transition_as_error(self):
        s = self._score_with_guard(0.0)
        assert s.total == 20          # todos os frames avaliaveis
        assert s.correct == 16        # 4 erros no inicio de PINCH
        assert s.macro_f1 < 1.0

    def test_guard_is_off_by_default(self):
        s = self._score_with_guard(0.0)
        assert s.guard_ms == 0.0
        assert s.guard_frames == 0
        assert s.guarded_macro_f1 is None

    def test_headline_is_identical_with_and_without_a_guard(self):
        """O numero que o gate avalia não pode mudar. Point and click."""
        off = self._score_with_guard(0.0)
        on = self._score_with_guard(300)
        assert on.macro_f1 == off.macro_f1
        assert on.accuracy == off.accuracy
        assert on.total == off.total

    def test_guard_reports_a_separate_diagnostic(self):
        s = self._score_with_guard(300)
        assert s.guard_ms == 300
        # A janela tira 10 frames, nao so os 4 que estavam errados: e uma
        # janela de 300 ms, e o resto dos frames do segmento tambem esta dentro
        # dela. E esse excesso que torna este numero um diagnostico e nao um
        # alvo — um F1 de 1.0 alcancado assim mede a janela, nao o classificador.
        assert s.guard_frames == 10
        assert s.guarded_total == 10
        assert s.guarded_macro_f1 == 1.0
        assert s.macro_f1 < s.guarded_macro_f1
        assert s.correct == 16          # o estrito continua a contar os 4

    def test_guard_never_touches_frames_already_settled(self):
        # SETTLE escrito no ficheiro continua a ser SETTLE, e nao e contado
        # duas vezes nem re-resolvido.
        truth = ["OPEN"] * 4 + ["PINCH"] * 4
        t_ms = [i * MS for i in range(8)]
        pairs = [
            Prediction(
                frame=i, hand=0,
                truth="SETTLE" if i in (4, 5) else name,
                pred="SETTLE" if i in (4, 5) else name,
            )
            for i, name in enumerate(truth)
        ]
        s = score_predictions(
            pairs, [None] * 8, truth, t_ms=t_ms, settle_guard_ms=200
        )
        assert s.settle == 2          # so os dois que o ficheiro trazia
        assert s.total == 6


class TestGuardWithRealCorpus:
    @staticmethod
    def _evaluate(guard_ms):
        import os

        from config import Config

        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "tests", "fixtures", "corpus_regressao_v1.npz",
        )
        return evaluate(path, cfg=Config(), settle_guard_ms=guard_ms)

    def test_fixture_replay_is_unchanged_by_a_guard(self):
        """O baseline do CI nao pode mexer. O `--replay-gate` le `macro_f1`."""
        base = self._evaluate(0.0)
        withguard = self._evaluate(300)
        assert withguard.score.macro_f1 == base.score.macro_f1
        assert withguard.passed == base.passed
        assert base.score.macro_f1 == 1.0

    def test_report_states_the_guard_next_to_the_number(self):
        text = self._evaluate(100).render()
        assert "F1 macro      : 1.0000" in text
        # E a linha do diagnostico diz que nao e o alvo.
        assert "diagnostico, nao o alvo" in text

    def test_report_refuses_to_print_a_f1_when_nothing_is_left(self):
        """`F1 0.0000` com zero frames avaliados parece o classificador a falhar.

        Acontece a justo este corpus: os segmentos sinteticos tem 6 frames
        (~200 ms) e uma janela de 300 ms apaga-os todos. Quem lesse "F1 0.0000"
        concluiria que o classificador esta partido. Nao ha F1: nao ha nada
        avaliado, e e isso que a linha tem de dizer.
        """
        text = self._evaluate(300).render()
        assert "F1 0.0000" not in text
        assert "nao sobra nenhum para avaliar" in text
        assert "F1 macro      : 1.0000" in text   # o principal continua la


class TestGuardRefusesToGuess:
    def test_unpairable_pairs_raise_instead_of_guessing(self):
        from tools.eval_recognition import _apply_settle_guard

        # Ha uma mudanca de etiqueta, mas 3 pares para 4 labels: nao ha como
        # saber a que frame cada par pertence, e errar aqui marcaria o frame
        # errado como SETTLE — o pior resultado possivel, porque um SETTLE
        # posto no sitio errado tira um frame bom da matriz.
        with pytest.raises(ValueError, match="indice de frame"):
            _apply_settle_guard(
                [("OPEN", "OPEN"), ("OPEN", "OPEN"), ("PINCH", "OPEN")],
                ["OPEN", "OPEN", "PINCH", "PINCH"],
                [0, 33, 66, 99],
                300,
            )

    def test_one_pair_per_frame_is_accepted(self):
        # Corpus de maos reais: so a mao do cursor e gravada, logo ha
        # exatamente um par por frame. Esse caso tem de funcionar.
        from tools.eval_recognition import _apply_settle_guard

        new_pairs, new_labels, frames, converted = _apply_settle_guard(
            [("OPEN", "OPEN"), ("PINCH", "OPEN"), ("PINCH", "PINCH")],
            ["OPEN", "PINCH", "PINCH"],
            [0, 33, 66],
            20,
        )
        assert frames == {1}          # t=33 entra (33<53), t=66 nao
        assert converted == 1
        assert new_labels == ["OPEN", "SETTLE", "PINCH"]
        assert new_pairs[1][0] == "SETTLE"

    def test_frames_without_a_hand_are_not_counted_as_taken(self):
        """`guard_frames` e o que saiu da avaliacao, nao o que a janela tocou.

        A janela abre sobre a sequencia por frame, que inclui frames em que nao
        havia mao nenhuma. Esses nunca entraram na matriz, e announces como
        "retirados" daria um numero maior do que o corpus inteiro.
        """
        from tools.eval_recognition import _apply_settle_guard

        truth = [None, None, "OPEN", "OPEN", "OPEN", "OPEN", "OPEN", "OPEN"]
        # Frames sem mao nao geram par nenhum — e por isso que um corpus real
        # tem menos pares do que frames. E sao `Prediction`, com o indice.
        pairs = [
            Prediction(frame=i, hand=0, truth=name, pred=name)
            for i, name in enumerate(truth) if name is not None
        ]
        t_ms = [i * 33 for i in range(8)]
        _, _, frames, converted = _apply_settle_guard(pairs, truth, t_ms, 200)
        # A mudanca e no frame 2 (t=66), a janela vai ate 266 ms: toca em 2..7,
        # e os 6 frames com mao sao todos contados.
        assert frames == {2, 3, 4, 5, 6, 7}
        assert converted == 6
