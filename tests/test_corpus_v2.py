"""Corpus v2: a confiança e os metadados que faltavam, antes de gravar mãos reais.

O `FORMAT_VERSION` é 1 desde o primeiro commit e o formato não tinha confiança
nem sayanything sobre de onde veio o corpus. Duas consequências, e as duas são
caras:

**A confiança não se recupera.** `RECONHECIMENTO_MAOS.md` §1.2 quer abstração por
confiança, e a confiança que existe é o `handedness[0].score` (confiança da
*classificação*, não da detecção — ver `tests/test_tracker_confidence.py`). Um
corpus gravado sem ela fica sem ela para sempre, e mãos reais não se recolhem
duas vezes. Por isso o campo entra agora e não quando "fizer sentido".

**"Sintético" versus "real" era uma nota em vez de um dado.** O
`--replay-gate` dá F1 macro 1.0000 e toda a gente le "1.0000" — e o
`PROGRESSO.md` tem de repetir, em três sítios, que é sobre corpus sintético. Com
`meta["source"]` isso passa a ser verificável por máquina: o gate passa a dizer
de que dados está a falar, e um corpus cuja origem é desconhecida não pode
ser usado para anunciar qualidade.

O `FORMAT_VERSION` sobe a 2. O loader continua a ler a v1 — a fixture
`corpus_regressao_v1.npz` é o portão de regressão do CI e não pode deixar de
carregar — mas carrega-a com a confiança a `NaN` e `source="unknown"`, que é o
honesto: ninguém sabe de onde veio, e o gate não deve fingir que sabe.

O `replay()` continua a devolver 5 valores. Há ~20 sítios que o descompactam
assim (`tools/eval_recognition.py` e quase todos os testes); mudar a forma
desses seria churn num contrato que não precisa de mudar. Quem precisar da
confiança usa `replay_with_conf()`.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from core.corpus import (
    ACTIVE_NONE,
    FORMAT_VERSION,
    Corpus,
)

V1_FIXTURE = "tests/fixtures/corpus_regressao_v1.npz"


def _hand(seed=0):
    rng = np.random.default_rng(seed)
    return rng.random((21, 3), dtype=np.float32)


class TestFormatoV2:
    def test_a_versao_subiu_para_2(self):
        assert FORMAT_VERSION == 2, (
            "o formato tem de declarar a v2; se isto mudou, os metadados e a "
            "confianca nao estao a ser gravados"
        )

    def test_a_confianca_sobe_e_desce(self, tmp_path):
        c = Corpus()
        c.add_frame(0, [_hand()], ["Right"], ["OPEN"], 0, [0.93])
        c.add_frame(33, [_hand(1)], ["Left"], ["PINCH"], 0, [0.71])
        p = tmp_path / "v2.npz"
        assert c.save(p)
        a = Corpus.load(p).arrays()
        assert a.conf[0][0] == pytest.approx(0.93)
        assert a.conf[1][0] == pytest.approx(0.71)

    def test_mao_ausente_fica_nan_e_nao_zero(self, tmp_path):
        """A distinção que decide se um limiar de abstenção funciona.

        `0.0` significa "mediu zero confiança" e faria o limiar descartar todas
        as mãos. `NaN` significa "não medido", que é o que um slot vazio é.
        """
        c = Corpus()
        c.add_frame(0, [], [], [], ACTIVE_NONE)
        assert c.save(tmp_path / "v.npz")
        got = Corpus.load(tmp_path / "v.npz").arrays()
        assert np.isnan(got.conf[0][0])
        assert np.isnan(got.conf[0][1])

    def test_add_frame_sem_confianca_continua_a_valer(self, tmp_path):
        """Os chamadores antigos passam a mesma signature e obtêm NaN.

        A confiança é um campo novo; não pode ser obrigatório, senão
        `make_corpus_fixture.py` e os testes que já gravam têm de mudar todos.
        """
        c = Corpus()
        c.add_frame(0, [_hand()], ["Right"], ["OPEN"], 0)
        assert c.save(tmp_path / "semconf.npz")
        assert np.isnan(Corpus.load(tmp_path / "semconf.npz").arrays().conf[0][0])

    def test_save_escreve_a_versao_2(self, tmp_path):
        c = Corpus()
        c.add_frame(0, [_hand()], ["Right"], ["OPEN"], 0, [0.5])
        c.save(p := tmp_path / "v.npz")
        with np.load(p) as z:
            assert int(z["version"]) == 2
            assert "conf" in z.files
            assert "meta" in z.files


class TestMetadadosDeSessao:
    def test_a_origem_sobe_e_desce(self, tmp_path):
        c = Corpus()
        c.add_frame(0, [_hand()], ["Right"], ["OPEN"], 0, [0.9])
        c.set_meta(source="real", device="HP i3-5005U", fps=14.6, side="Right")
        c.save(tmp_path / "m.npz")
        m = Corpus.load(tmp_path / "m.npz").meta
        assert m["source"] == "real"
        assert m["device"] == "HP i3-5005U"
        assert m["fps"] == pytest.approx(14.6)
        assert m["side"] == "Right"

    def test_a_origem_por_omissao_e_unknow(self, tmp_path):
        """Sem origem declarada, o corpus diz que não sabe. Não assume."""
        c = Corpus()
        c.add_frame(0, [_hand()], ["Right"], ["OPEN"], 0, [0.9])
        c.save(tmp_path / "n.npz")
        assert Corpus.load(tmp_path / "n.npz").meta["source"] == "unknown"

    def test_o_meta_guarda_um_json_e_nao_um_pickle(self, tmp_path):
        """`allow_pickle=False` na leitura. Um corpus não pode meter código a
        correr na máquina de quem o abre."""
        c = Corpus()
        c.add_frame(0, [_hand()], ["Right"], ["OPEN"], 0, [0.9])
        c.set_meta(source="real")
        c.save(p := tmp_path / "j.npz")
        with np.load(p, allow_pickle=False) as z:
            assert isinstance(json.loads(str(z["meta"])), dict)

    def test_um_meta_nao_serializavel_e_erro_tem_pouco(self):
        c = Corpus()
        with pytest.raises((TypeError, ValueError)):
            c.set_meta(device=object())


class TestAOrigemChegaAoRelatorio:
    """Um campo que ninguém lê não corrige nada.

    A `meta["source"]` só serve se o número de métrica sair acompanhado dela.
    Sem isto, o `--replay-gate` volta a dizer F1 1.0000 e a primeira pessoa a
    lê lê "o reconhecedor está perfeito" — que é a leitura errada, e é a que o
    `PROGRESSO.md` tem de desmentir à mão em três sítios.
    """

    def _report(self, tmp_path, **meta):
        from tools.eval_recognition import evaluate

        c = Corpus()
        c.add_frame(0, [_hand()], ["Right"], ["PINCH"], 0, [0.9])
        c.add_frame(33, [_hand(1)], ["Right"], ["PINCH"], 0, [0.9])
        c.set_meta(**meta)
        p = tmp_path / "e.npz"
        assert c.save(p)
        return evaluate(p)

    def test_um_corpus_sintetico_diz_sintetico(self, tmp_path):
        r = self._report(tmp_path, source="synthetic")
        assert r.provenance == "synthetic"
        assert "SINTETICO" in r.render()

    def test_um_corpus_real_diz_o_dispositivo(self, tmp_path):
        r = self._report(tmp_path, source="real", device="HP i3-5005U")
        assert r.provenance == "real"
        assert "REAL" in r.render()
        assert "HP i3-5005U" in r.render()

    def test_um_corpus_desconhecido_avisa_que_nao_prova_nada(self, tmp_path):
        """A v1 e este o caso: ninguém sabe de onde veio, e o relatório tem de
        dizer isso em vez de ficar em silêncio ao lado do F1."""
        r = self._report(tmp_path)
        assert r.provenance == "unknown"
        assert "DESCONHECIDA" in r.render()

    def test_a_origem_tambem_vai_no_json(self, tmp_path):
        d = self._report(tmp_path, source="synthetic").to_dict()
        assert d["corpus"]["source"] == "synthetic"


def _write_v1(path, frames=4):
    """Escreve um `.npz` no formato v1: sem `conf`, sem `meta`, version 1.

    Feito à mão de propósito. A fixture do CI passou a v2, e um teste de
    compatibilidade que só corre contra a fixture commitada deixaria de testar
    a compatibilidade assim que a fixture fosse regenerada — que é exactamente
    o que aconteceu na primeira versão deste teste.
    """
    rng = np.random.default_rng(7)
    n = frames
    np.savez_compressed(
        path,
        landmarks=rng.random((n, 2, 21, 3), dtype=np.float32),
        mask=np.ones((n, 2), dtype=bool),
        labels=np.zeros((n, 2), dtype=np.int8),
        sides=np.zeros((n, 2), dtype=np.int8),
        active=np.zeros(n, dtype=np.int8),
        t_ms=np.arange(n, dtype=np.int64) * 33,
        version=np.array(1, dtype=np.int64),
    )
    return path


class TestLeituraDaV1:
    """A v1 não tem `conf` nem `meta`, e corpora v1 já existem em disco.

    O que este loader tem de garantir não é só não-crash: é não mentir. Uma v1
    carregada com confiança a zero e origem a "synthetic" seria um corpus que
    aparenta ter evidência que não tem, e essa é a forma de erro que a
    instrumentação inteira existe para evitar.
    """

    def test_um_v1_real_carrega(self, tmp_path):
        c = Corpus.load(_write_v1(tmp_path / "v1.npz"))
        assert c.frames == 4
        assert c.total == 8

    def test_um_v1_carrega_sem_confianca(self, tmp_path):
        assert np.isnan(Corpus.load(_write_v1(tmp_path / "v1.npz")).arrays().conf).all()

    def test_um_v1_diz_que_nao_sabe_a_origem(self, tmp_path):
        assert Corpus.load(_write_v1(tmp_path / "v1.npz")).meta["source"] == "unknown"

    def test_um_v1_diz_que_nao_prova_nada(self, tmp_path):
        """`provenance()` é o que vai para o relatório: tem de dizer que os
        números ao lado não provam qualidade em mãos reais."""
        note = Corpus.load(_write_v1(tmp_path / "v1.npz")).provenance()
        assert "DESCONHECIDA" in note
        assert "nao usar para anunciar qualidade" in note

    def test_um_v1_guarda_os_lados_e_as_etiquetas(self, tmp_path):
        """Backwards-compatible de verdade: os mesmos dados, não só não-crash."""
        c = Corpus.load(_write_v1(tmp_path / "v1.npz"))
        _t, hands, sides, labels, active = next(iter(c.replay()))
        assert len(hands) == len(sides) == len(labels) == 2
        assert active == 0
        assert c.duration_s() == pytest.approx(3 * 33 / 1000.0)

    def test_a_fixture_do_ci_diz_a_sua_origem(self):
        """A fixture regenerada tem de se declarar sintética. Se um dia alguém
        meter mãos reais lá dentro sem mudar a meta, este teste não o apanha —
        mas o `provenance` no relatório passa a dizer REAL, e é aí que se vê."""
        assert Corpus.load(V1_FIXTURE).source == "synthetic"

    def test_uma_versao_desconhecida_falha_alto(self):
        """Um v3 tem de ser erro, não um default silencioso: ler um formato
        desconhecido como se fosse o conhecido é como se perde um corpus inteiro
        sem ninguem dar por isso."""
        import tempfile

        c = Corpus()
        c.add_frame(0, [_hand()], ["Right"], ["OPEN"], 0, [0.9])
        with tempfile.TemporaryDirectory() as d:
            p = f"{d}/futuro.npz"
            a = c.arrays()
            np.savez_compressed(
                p,
                landmarks=a.landmarks,
                mask=a.mask,
                labels=a.labels,
                sides=a.sides,
                active=a.active,
                t_ms=a.t_ms,
                conf=a.conf,
                meta=np.array(json.dumps({"source": "real"})),
                version=np.array(3, dtype=np.int64),
            )
            with pytest.raises(ValueError, match="versao de corpus"):
                Corpus.load(p)


class TestReplay:
    def _um_frame(self, tmp_path):
        c = Corpus()
        c.add_frame(7, [_hand()], ["Right"], ["OPEN"], 0, [0.88])
        c.save(p := tmp_path / "r.npz")
        return Corpus.load(p)

    def test_replay_continua_a_devolver_cinco(self, tmp_path):
        """O contrato antigo não muda. Vinte sítios dependem dele."""
        t, hands, sides, labels, active = next(iter(self._um_frame(tmp_path).replay()))
        assert t == 7
        assert sides == ["Right"]
        assert labels == ["OPEN"]
        assert active == 0

    def test_replay_com_confianca_devolve_seis(self, tmp_path):
        _t, hands, sides, labels, active, conf = next(
            iter(self._um_frame(tmp_path).replay_with_conf())
        )
        assert conf == pytest.approx([0.88])
        assert len(hands) == len(sides) == len(labels) == len(conf)

    def test_as_duas_versoes_veem_os_mesmos_frames(self, tmp_path):
        c = self._um_frame(tmp_path)
        a = list(c.replay())
        b = list(c.replay_with_conf())
        assert [x[0] for x in a] == [x[0] for x in b]
        assert [x[2] for x in a] == [x[2] for x in b]
