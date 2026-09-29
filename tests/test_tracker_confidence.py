"""A confiança que o tracker deitava fora, e o nome certo para ela.

`core/tracker.py:89-99` lia `handed[0].category_name` e deitava fora
`handed[0].score`. `RECONHECIMENTO_MAOS.md` §1.2 quer essa confiança para a
abstenção (`IsHighConfidence` à Meta). While o corpus de mãos reais não a
guardar, os dados ficam sem ela **para sempre** — e mãos reais não se
recolhem duas vezes. Por isso isto entra antes de gravar seja o que for.

O nome é deliberado e não é "confidence":

`handedness[0].score` é a confiança da **classificação** (isto é uma mão
esquerda ou direita). **Não** é a confiança de ter detectado uma mão. O
`HandLandmarker` do MediaPipe não expõe a confiança de detecção na API Python
— só os limiares `min_hand_detection_confidence` / `min_hand_presence_confidence`,
que são dezoito, não uma medida. Chamar-lhe "detection confidence" seria
exatamente a KIND de over-claim que este projecto já se pegou a pagar duas
vezes; por isso o campo chama-se `conf` mas o docstring diz o que é, e o
corpus grava `NaN` quando não há valor em vez de inventar um.

Consequência para a §1.2, que fica registada aqui para não ser redescoberta
depois: a abstinação **não** pode assentar só nesta nota. O sinal mais forte
disponível é derivado (margem da histerese da pinça, escala da mão, concordância
geométrica) — e é por isso que o corpus guarda as landmarks, não só o rótulo.
"""

from __future__ import annotations

import math

import pytest

from core.tracker import parse_landmarks_result


class _Category:
    def __init__(self, name, score):
        self.category_name = name
        self.score = score


class _Handedness(list):
    """O MediaPipe devolve uma lista de listas de `Category`."""


class _Result:
    def __init__(self, landmarks, handedness):
        self.hand_landmarks = landmarks
        self.handedness = handedness


class _Lm:
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z


def _lm21():
    return [_Lm(i / 21.0, 0.5, 0.0) for i in range(21)]


class TestConfiancaDaClassificacao:
    def test_devolve_um_score_por_mao(self):
        r = _Result(
            [_lm21(), _lm21()],
            [_Handedness([_Category("Right", 0.97)]), _Handedness([_Category("Left", 0.81)])],
        )
        hands, sides, confs = parse_landmarks_result(r)
        assert len(confs) == len(hands) == len(sides) == 2
        assert confs == pytest.approx([0.97, 0.81])

    def test_hands_e_sides_continuam_igual(self):
        """A mudanca e aditiva: quem descompactava 2 valores tem de ler os mesmos."""
        r = _Result(
            [_lm21()], [_Handedness([_Category("Left", 0.9)])]
        )
        hands, sides, confs = parse_landmarks_result(r)
        assert sides == ["Left"]
        assert len(hands[0]) == 21
        assert all(len(p) == 3 for p in hands[0])

    def test_sem_handedness_da_nan_e_nao_zero(self):
        """A distincao que importa: `NaN` e "nao medido", 0.0 e "mediu zero".

        Guardar 0.0 seria pior que guardar nada: um limiar de abstencao
        descartaria todas as mãos de quem nao tem handedness, sem que ninguem
        saiba porque.
        """
        r = _Result([_lm21()], [_Handedness()])
        _hands, _sides, confs = parse_landmarks_result(r)
        assert math.isnan(confs[0])

    def test_handedness_ausente_por_completo(self):
        r = _Result([_lm21()], None)
        hands, sides, confs = parse_landmarks_result(r)
        assert sides == ["Right"]  # o fallback antigo
        assert math.isnan(confs[0])

    def test_lado_desconhecido_cai_para_right(self):
        """O MediaPipe pode devolver um category_name fora de Left/Right; o
        tracker historicamente caia para 'Right' e isso nao se altera."""
        r = _Result([_lm21()], [_Handedness([_Category("Middle", 0.6)])])
        _hands, sides, confs = parse_landmarks_result(r)
        assert sides == ["Right"]
        # mesmo com lado invalido, a confianca que veio continua a ser a real
        assert confs == pytest.approx([0.6])

    def test_sem_maos_devolve_listas_vazias(self):
        r = _Result([], [])
        assert parse_landmarks_result(r) == ([], [], [])

    def test_score_ausente_no_categoria_da_nan(self):
        class _SemScore:
            category_name = "Right"

        r = _Result([_lm21()], [_Handedness([_SemScore()])])
        _hands, _sides, confs = parse_landmarks_result(r)
        assert math.isnan(confs[0])
