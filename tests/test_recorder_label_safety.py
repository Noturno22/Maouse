"""`set_label` nao pode transformar um sentinela num gesto.

`CorpusRecorder.set_label` fazia `LABEL_NAMES[label_index(label)]`. Os
sentinelas `ABSENT` (-1) e `SETTLE` (-2) sao indices negativos validos para
`label_index` mas nao para `LABEL_NAMES`: indexar a ceu aberto devolvia o
penultimo e o antepenultimo gesto. Com `SETTLE_LABEL` obtinha-se 'SHAKA' em
silencio — e SHAKA e Ctrl+V, ou seja, nao se via.

O `label_name()` foi escrito exactamente para isto, do lado da leitura. Estes
testes trancam o lado da escrita, antes que a tecla que faz SETTLE existir.
"""
import pytest

from core.corpus import (
    ABSENT_LABEL,
    LABEL_NAMES,
    SETTLE_LABEL,
    CorpusRecorder,
    label_index,
    label_name,
)


class TestSetLabelSentinels:
    def test_settle_does_not_become_a_gesture(self):
        # A regressão literal: -2 em LABEL_NAMES é 'SHAKA'.
        assert LABEL_NAMES[-2] == "SHAKA"

        r = CorpusRecorder()
        r.set_label(SETTLE_LABEL)
        assert r.label == SETTLE_LABEL
        assert r.label != "SHAKA"

    def test_absent_does_not_become_a_gesture(self):
        # -1 devolve 'ROCK' (indicador + mindelho) — um comando real, disparado
        # a partir de um frame em que nao havia mao nenhuma.
        assert LABEL_NAMES[-1] == "ROCK"

        r = CorpusRecorder()
        r.set_label(SETTLE_LABEL)
        r.set_label(ABSENT_LABEL)
        assert r.label == ABSENT_LABEL
        assert r.label != "ROCK"

    @pytest.mark.parametrize("name", LABEL_NAMES)
    def test_every_real_gesture_survives_unchanged(self, name):
        r = CorpusRecorder()
        r.set_label(name)
        assert r.label == name

    def test_settle_is_idempotent(self):
        r = CorpusRecorder()
        r.set_label(SETTLE_LABEL)
        first = r.label
        r.set_label(SETTLE_LABEL)
        assert r.label == first == SETTLE_LABEL

    def test_survives_a_round_trip_through_a_gesture(self):
        # O caminho real: NONE -> gesto -> SETTLE -> gesto. O sentinela nao pode
        # deixar o recorder num gesto que o operador nunca escolheu.
        r = CorpusRecorder()
        r.set_label("ROCK")
        r.set_label(SETTLE_LABEL)
        r.set_label("PEACE")
        assert r.label == "PEACE"


class TestConsistencyWithTheReader:
    def test_write_and_read_agree(self):
        # A mesma tabela tem de valer nos dois sentidos, senao o ficheiro
        # gravado e o relatorio=lido discordam do que foi pedido.
        for name in (SETTLE_LABEL, ABSENT_LABEL, *LABEL_NAMES):
            r = CorpusRecorder()
            r.set_label(name)
            assert label_name(label_index(r.label)) == r.label

    def test_unknown_label_still_raises(self):
        r = CorpusRecorder()
        with pytest.raises(KeyError):
            r.set_label("GESTO_QUE_NAO_EXISTE")
