"""O tool que recolhe mãos reais nunca foi corrido, e isso moldou-o mal.

`tools/collect_gestures.py` faz `hands = tracker.process(...)` e depois
`hands[0]`, o que levanta `ValueError` — o `process()` devolve uma tupla desde o
primeiro commit (`3a5c67b`) e o tool nunca a descompactou. O ficheiro foi
submetido sem nunca ser executado.

Este ficheiro não volta a deixá-lo assim. Testa-se a **única coisa que faz o
tool valer**: o contrato entre o que ele grava e o que `tools/train_gesture_ai.py`
consegue ler. Esse contrato nunca teve teste, e é exactamente onde um tool
inutilizado erro — as duas pontassey modificadas em separado, cada uma
consistente consigo própria.

O que este ficheiro NÃO faz é decidir que a IA passa a ter 13 classes.
`core/gesture_ai.py::CLASSES` tem 9, e os pesos que o produto distribui são um
modelo de 9 classes de um org de terceiros. Alargar `N_CLASSES` sem retreinar
faz o modelo distribuído mentir — e a decisão de retreinar é do dono do
produto, não daqui. O que este ficheiro garante é que a decisão, quando for
tomada, não pode acontecer por acidente: o tool e o treinador passam a ler a
mesma lista, e um ficheiro com uma classe fora do modelo falha com uma frase
legível em vez de um erro de `zip`.
"""

from __future__ import annotations

import numpy as np
import pytest

from core.gesture_ai import CLASSES, N_CLASSES
from tools import collect_gestures as cg
from tools.train_gesture_ai import load_real


def _pts(seed=0):
    return np.random.default_rng(seed).random((21, 3), dtype=np.float32)


class TestUmaSoFonteDeVerdade:
    """O tool declarava a sua própria lista de classes.

    Duplicar a lista é como as duas já divergiram uma vez: `CLASS_NAMES` aqui e
    `CLASSES` em `core/gesture_ai.py` são a mesma coisa escrita duas vezes, e
    basta alguém acrescentar uma classe a uma para o tool passar a oferecer 9 de
    10 sem dar por isso. O padrão do repo (`LABEL_KEYS` derivada de
    `LABEL_KEY_CHOICES`) existe para isto.
    """

    def test_as_classes_do_modelo_estao_nas_recolhiveis(self):
        """Toda a classe que o modelo sabe prever tem de ser recolhivel.

        Se o modelo treinasse uma classe que este tool nao consegue recolher, o
        ciclo recolher->treinar->avaliar estava cortado sem ninguem dar por isso:
        o treino só via o sintetico dessa classe, e o modelo nunca a via numa mao
        real. E o inverso — recolher uma classe que o modelo nao tem — pelo menos
        falha alto, e com nome.
        """
        assert cg.AI_NAMES == tuple(g.name for g in CLASSES)
        faltam = [n for n in cg.AI_NAMES if n not in cg.COLLECTABLE_NAMES]
        assert not faltam, f"o modelo treina classes que nao se recolhem: {faltam}"

    def test_recolhiveis_sao_mais_que_as_do_modelo(self):
        assert len(cg.COLLECTABLE_NAMES) > len(cg.AI_NAMES)
        assert cg.OUT_OF_MODEL, (
            "esperado: enquanto a IA tiver 9 classes, ha gestos que se recolhem "
            "e nao se treinam (PINKY, ONE, THUMB_DOWN)"
        )

    def test_o_tool_nao_declara_a_lista_a_si(self):
        """Guarda contra alguém voltar a escrever a lista à mão aqui."""
        import inspect

        src = inspect.getsource(cg)
        # Uma tupla literal de nomes de gestos é a tabela duplicada.
        assert '("OPEN", "PINCH"' not in src, (
            "a lista de classes tem de ser derivada de core.gesture_ai.CLASSES, "
            "não escrita à mão: são a mesma tabela e já divergiram uma vez"
        )

    def test_cada_classe_tem_a_sua_tecla(self):
        names = [n for n, _cid in cg.CLASS_KEYS.values()]
        assert sorted(names) == sorted(cg.COLLECTABLE_NAMES)
        assert len(set(names)) == len(names), "duas teclas para a mesma classe"

    def test_as_teclas_sao_as_do_record(self):
        """Um operador que recolhe com as duas ferramentas não pode ter de
        decorar dois teclados para a mesma tarefa.

        Este tool tinha 1-9 pela ordem de `AI_CLASSES` e `c` para limpar; o
        `--record` tem 0-9 pela ordem de `Gesture` e `x` para limpar. Errar a
        tecla não dá erro — grava o gesto errado, que é a forma mais cara de errar
        sobre mãos reais.
        """
        from core.corpus import LABEL_KEY_CHOICES

        for ch, nome in LABEL_KEY_CHOICES.items():
            if nome not in cg.COLLECTABLE_NAMES:
                continue
            assert ch in cg.CLASS_KEY_CHOICES, f"{nome} perdeu a tecla {ch!r}"
            assert cg.CLASS_KEY_CHOICES[ch] == nome

    def test_nenhuma_tecla_de_comando_e_uma_tecla_de_classe(self):
        """`c` era "limpa gesto" aqui e SHAKA no `--record`. Duas coisas
        diferentes na mesma tecla, e a que perde depende da ordem do `if`."""
        comandos = {cg.KEY_UNDO, cg.KEY_CLEAR, cg.KEY_SAVE, "q"}
        assert not comandos & set(cg.CLASS_KEY_CHOICES), (
            f"colisao de teclas: {comandos & set(cg.CLASS_KEY_CHOICES)}"
        )

    def test_limpar_usa_a_tecla_do_record(self):
        from core.corpus import LABEL_KEY_CHOICES

        assert cg.KEY_CLEAR not in LABEL_KEY_CHOICES, (
            "a tecla de limpar tem de estar livre no --record tambem"
        )


class TestPinkyEDaConfusaoQueNaoSePodeRecolher:
    """`PINKY` é metade da confusão PINKY/SHAKA, e `SHAKA` é o gesto que o
    `RECONHECIMENTO_MAOS.md` marca como "por confirmar em mãos reais".

    `PINKY` não é classe do modelo actual, portanto **o tool não a consegue
    recolher**: não há tecla para ela. Isto é a confusão que não se resolve a
    recolher mais dados, porque os dados de um dos lados não se podem recolher.
    Fica registado num teste para que a lacuna seja visível quando se decidir
    retreinar, e não descoberta depois.
    """

    def test_pinky_e_recolhivel_mesmo_sem_ser_classe_do_modelo(self):
        assert "PINKY" in cg.COLLECTABLE_NAMES

    def test_a_lacuna_e_visivel(self):
        faltam = [g.name for g in cg.COLLECTABLE if g.name not in
                  {c.name for c in CLASSES}]
        assert faltam, (
            "esperado: enquanto a IA tiver 9 classes, recolher PINKY/ONE/"
            "THUMB_DOWN/NONE produz ficheiro que o treinador recusa"
        )


class TestOQueOToolGrava:
    def _um_exemplo(self):
        c = cg.Collector()
        c.add(0, _pts(1), conf=0.93)
        c.add(0, _pts(2), conf=0.88)
        c.add(1, _pts(3), conf=float("nan"))
        return c

    def test_grava_a_confianca(self, tmp_path):
        p = tmp_path / "r.npz"
        assert cg.save(p, self._um_exemplo(), meta={"source": "real"})
        with np.load(p, allow_pickle=False) as z:
            assert "conf" in z.files
            assert z["conf"][0] == pytest.approx(0.93)
            assert np.isnan(z["conf"][2])

    def test_grava_a_proveniencia(self, tmp_path):
        """O `Corpus` passou a ter `meta`; o ficheiro do trainer nao tinha nada.
        Um `.npz` de mãos reais sem origem é um ficheiro que não se pode
        citar — nem para debugging, quanto mais para um commit."""
        import json

        p = tmp_path / "r.npz"
        cg.save(p, self._um_exemplo(), meta={"source": "real", "device": "HP"})
        with np.load(p, allow_pickle=False) as z:
            meta = json.loads(str(z["meta"]))
        assert meta["source"] == "real"
        assert meta["device"] == "HP"

    def test_a_proveniencia_e_json_e_nao_pickle(self, tmp_path):
        p = tmp_path / "r.npz"
        cg.save(p, self._um_exemplo(), meta={"source": "real"})
        # `allow_pickle=False`: se `meta` fosse pickle, o np.load levantava aqui
        # e o ficheiro seria codigo a correr na maquina de quem o abre.
        with np.load(p, allow_pickle=False):
            pass

    def test_um_ficheiro_vazio_nao_e_gravado(self, tmp_path):
        assert not cg.save(tmp_path / "vazio.npz", cg.Collector())


class TestOQueOTreinadorLe:
    """O contrato, ponta a ponta. Foi isto que não existia."""

    def test_o_que_o_tool_grava_o_treinador_le(self, tmp_path):
        p = tmp_path / "r.npz"
        c = cg.Collector()
        for cls_id in range(N_CLASSES):
            for k in range(30):  # o minimo do load_real
                c.add(cls_id, _pts(cls_id * 100 + k), conf=0.9)
        assert cg.save(p, c, meta={"source": "real"})
        X, y = load_real(p, min_per_class=30)
        assert X.shape == (N_CLASSES * 30, 21, 3)
        assert y.tolist() == sorted(y.tolist())
        for cls_id, g in enumerate(CLASSES):
            assert (y == cls_id).sum() == 30, f"classe errada para {g.name}"

    def test_um_ficheiro_com_classe_desconhecida_falha_legivel(self, tmp_path):
        """Antes disto: `ValueError: zip() argument 2 is longer than argument 1`.

        Não diz o que aconteceu, não diz qual classe, e quem lê a mensagem
        pensa que o ficheiro está corrompido. A falha tem de dizer "treinaste
        uma classe que o modelo não tem" — que é uma instrução, não um
        sintoma.
        """
        p = tmp_path / "fora.npz"
        c = cg.Collector()
        for cls_id in range(N_CLASSES):
            for k in range(30):
                c.add(cls_id, _pts(cls_id * 100 + k), conf=0.9)
        c.add(_index_de("PINKY"), _pts(9), conf=0.9)
        assert cg.save(p, c, meta={"source": "real"})
        with pytest.raises(ValueError) as exc:
            load_real(p, min_per_class=30)
        msg = str(exc.value)
        assert "PINKY" in msg
        assert "9" in msg  # quantas classes o modelo tem

    def test_o_erro_diz_o_que_fazer(self, tmp_path):
        p = tmp_path / "fora.npz"
        c = cg.Collector()
        c.add(_index_de("PINKY"), _pts(1), conf=0.9)
        assert cg.save(p, c, meta={"source": "real"})
        with pytest.raises(ValueError, match="retrein"):
            load_real(p, min_per_class=1)


def _index_de(nome: str) -> int:

    return [g.name for g in cg.COLLECTABLE].index(nome)
