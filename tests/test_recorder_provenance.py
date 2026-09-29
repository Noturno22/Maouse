"""O que a sessao de recolha diz sobre si mesma.

O formato v2 grava a confiança e a origem (commit anterior). Faltava a ultima
peca: **ligar as duas ao caminho de gravação real**, que e o `--record`. Sem
isto o formato tem campos e o gravador nao os preenche — a mesma classe de
problema de um log configurado que ninguemactivate.

Tres coisas que este ficheiro fixa:

1. **A confiança do tracker chega ao corpus.** O `HandTracker.process` devolve-a
   (commit `ad0b824`); se o `observe` a descarta, a coluna fica a NaN em todas as
   mãos reais e ninguém dá por isso, porque NaN é um valor válido. Um gravador
   que aceita e deita fora um campo é indistinguível de um gravador que nunca o
   recebeu — e o corpus resultante é o mesmo.

2. **Um gravador de `--record` é sempre `source="real"`.** A câmara é uma câmara
   e as mãos são de uma pessoa. Marcá-lo como outra coisa seria falsificar a
   proveniência; deixá-lo "unknown" seria despejar a responsabilidade em quem
   recebe o ficheiro. A única excepção é o replay, que não passa por aqui.

3. **O que o gravador não sabe, ele não escreve.** O fps medido sai dos
   timestamps que ele próprio gravou, e não é gravado com um frame só, porque
   com um frame não há nada a medir e `0.0` seria uma mentira.
"""

from __future__ import annotations

import numpy as np
import pytest

from core.corpus import ABSENT_LABEL, Corpus, CorpusRecorder


def _hand(seed=0):
    return np.random.default_rng(seed).random((21, 3), dtype=np.float32)


class TestConfiancaChegaAoCorpus:
    def test_a_confianca_do_tracker_chega(self):
        rec = CorpusRecorder()
        rec.set_label("OPEN")
        assert rec.observe([_hand()], ["Right"], 0, 0, confs=[0.91])
        assert rec.corpus.arrays().conf[0][0] == pytest.approx(0.91)

    def test_sem_confianca_continua_a_valer(self):
        """Os chamadores antigos passam a mesma assinatura e obtêm NaN.

        `tools/eval_recognition.py` e os testes já existentes chamam `observe`
        com quatro argumentos; nenhum pode partir por causa de um campo novo.
        """
        rec = CorpusRecorder()
        rec.set_label("OPEN")
        assert rec.observe([_hand()], ["Right"], 0, 0)
        assert np.isnan(rec.corpus.arrays().conf[0][0])

    def test_a_confianca_da_mao_certo(self):
        """`confs` é paralelo a `hands`, e o `index` escolhe a mão do cursor.

        Gravar a confiança da mão errada seria pior do que não gravar nenhuma:
        mediria a classificação de uma mão enquanto se avalia a pose de outra.
        """
        rec = CorpusRecorder()
        rec.set_label("OPEN")
        rec.observe([_hand(1), _hand(2)], ["Left", "Right"], 1, 0, confs=[0.3, 0.8])
        assert rec.corpus.arrays().conf[0][0] == pytest.approx(0.8)

    def test_confs_do_tamanho_errado_nao_mata_a_sessao(self):
        """O gravador está no caminho quente, a meio de uma recolha de 20 min.

        Levantar aqui seria deitar fora a sessão por um descasamento de lista,
        e o operador teria de recomeçar do zero. Grava NaN e continua — que é
        registável, ao contrário de um crash.
        """
        rec = CorpusRecorder()
        rec.set_label("OPEN")
        assert rec.observe([_hand()], ["Right"], 0, 0, confs=[]) is True
        assert rec.observe([_hand()], ["Right"], 0, 33, confs=[0.9, 0.9, 0.9])
        assert np.isnan(rec.corpus.arrays().conf[0][0])
        assert rec.corpus.arrays().conf[1][0] == pytest.approx(0.9)

    def test_uma_confianca_ilegivel_vira_nan(self):
        rec = CorpusRecorder()
        rec.set_label("OPEN")
        rec.observe([_hand()], ["Right"], 0, 0, confs=["alta"])
        assert np.isnan(rec.corpus.arrays().conf[0][0])

    def test_nan_no_tracker_passa_nan_no_corpus(self):
        """O tracker grava NaN quando não há score. Isso tem de chegar intacto,
        para se poder distinguir "não medido" de "mediu zero" na análise."""
        rec = CorpusRecorder()
        rec.set_label("OPEN")
        rec.observe([_hand()], ["Right"], 0, 0, confs=[float("nan")])
        assert np.isnan(rec.corpus.arrays().conf[0][0])


class TestProvenienciaDaSessao:
    def test_um_gravador_de_record_e_real(self):
        """Câmara a sério, mãos a sério. Não há caminho em que isto seja
        sintético, e dizer "unknown" transferia para quem recebe o ficheiro uma
        dúvida que o gravador tem a informação para resolver."""
        assert CorpusRecorder().corpus.source == "real"

    def test_o_fps_medido_sai_dos_timestamps_gravados(self):
        rec = CorpusRecorder()
        rec.set_label("OPEN")
        for i in range(11):  # 10 intervalos de 50 ms = 10/0.5 s = 20 fps
            rec.observe([_hand()], ["Right"], 0, i * 50)
        assert rec.measured_fps() == pytest.approx(20.0)

    def test_com_um_frame_so_nao_ha_o_que_medir(self):
        rec = CorpusRecorder()
        rec.set_label("OPEN")
        rec.observe([_hand()], ["Right"], 0, 0)
        assert rec.measured_fps() is None
        rec.corpus.set_meta(fps=rec.measured_fps())
        assert "fps" not in rec.corpus.meta, (
            "0.0 fps seria uma medida que ninguém fez; None é o honesto"
        )

    def test_flush_grava_o_fps_e_o_tamanho(self, tmp_path):
        rec = CorpusRecorder(path=tmp_path / "s.npz")
        rec.set_label("OPEN")
        for i in range(21):
            rec.observe([_hand()], ["Right"], 0, i * 40)
        assert rec.flush()
        m = Corpus.load(tmp_path / "s.npz").meta
        assert m["fps"] == pytest.approx(25.0)
        assert m["frames"] == 21
        assert m["source"] == "real"

    def test_a_proveniencia_diz_real(self, tmp_path):
        rec = CorpusRecorder(path=tmp_path / "s.npz")
        rec.set_label("OPEN")
        rec.observe([_hand()], ["Right"], 0, 0)
        rec.flush()
        assert "REAL" in Corpus.load(tmp_path / "s.npz").provenance()

    def test_o_dispositivo_pode_ser_declarado(self):
        """O `main.py` diz qual é a máquina. Sem isso, `provenance()` diz
        "dispositivo desconhecido" — honesto, mas inútil para comparar corpus
        entre máquinas, que é metade do que se quer de um corpus de mãos reais."""
        rec = CorpusRecorder(meta={"device": "HP i3-5005U"})
        assert "HP i3-5005U" in rec.corpus.provenance()

    def test_o_dispositivo_por_omissao_diz_que_nao_sabe(self):
        assert "desconhecido" in CorpusRecorder().corpus.provenance()

    def test_reset_tambem_repete_a_fps_medida(self):
        """`reset()` limpa os frames; o que sobrou no `meta` seria de uma sessão
        que já não existe, e o `flush` reescreve o fps de qualquer forma."""
        rec = CorpusRecorder()
        rec.set_label("OPEN")
        rec.observe([_hand()], ["Right"], 0, 0)
        rec.reset()
        assert rec.measured_fps() is None
        assert rec.corpus.source == "real"


class TestFramesSemMao:
    def test_o_frame_de_repouso_tambem_leva_meta(self, tmp_path):
        rec = CorpusRecorder(path=tmp_path / "r.npz")
        rec.set_label(ABSENT_LABEL)
        rec.observe([], [], -1, 0)
        assert rec.flush()
        c = Corpus.load(tmp_path / "r.npz")
        assert c.frames == 1
        assert c.source == "real"


# ----------------------------------------------------------------- ligacao


class _SpyRecorder:
    """Apanha o que o engine passa, sem gravar.

    Testa-se a ligação, não o gravador (esse está testado em
    `test_corpus_recorder.py`). O que interessa aqui é que o terceiro valor do
    `tracker.process` chegue ao `observe` — e isso só se vê de fora.
    """

    def __init__(self):
        self.calls = []

    def observe(self, hands, sides, index, t_ms, confs=None):
        self.calls.append((hands, sides, index, t_ms, confs))
        return True


class _FakeTracker:
    def __init__(self, confs):
        self._confs = confs
        self._hand = _hand(3)

    def process(self, rgb, ts_ms):
        return [self._hand.copy()], ["Right"], list(self._confs)


class _Cam:
    def __init__(self):
        self._f = np.zeros((240, 320, 3), dtype=np.uint8)

    def read(self):
        return self._f, 0

    def try_boost_exposure(self):
        pass


class _Mouse:
    def __getattr__(self, _name):
        return lambda *a, **k: None

    class mouse:
        position = (100.0, 100.0)


class _Emitter:
    """O `process_frame` fala com o TTS nos ramos de transição de mão. Um duplo
    mudo chega: o que se quer exercitar aqui é a ligação tracker -> recorder,
    e um `toast` que fala em voz alta em cada teste seria pior."""

    def push(self, *a, **k):
        pass

    def clear(self):
        pass

    def start(self):
        pass

    def stop(self):
        pass


class TestOEnginePassaAConfianca:
    def _correr(self, monkeypatch, confs):
        import types

        import core.licensing as lic
        from config import Config
        from core import engine
        from core.autotune import AutoTuner

        monkeypatch.setattr(
            engine,
            "active_license",
            lambda: lic.LicenseManager(store_path=":memory:", trial_seconds=60),
        )
        cfg = Config()
        cfg.mirror = False
        ctx = types.SimpleNamespace(
            assistant=None, speaker=None, snap=None, magnifier=None,
            exit_requested=False,
        )
        E = engine.make_engine_ctx(cfg, -1, None, AutoTuner(cfg), ctx)
        # O warmup é um early-return antes do tracker: deixá-lo ativo faria o
        # teste passar sem nunca exercitar a ligação que quer testar.
        E.warmup_left = 0
        E.emitter = _Emitter()
        spy = _SpyRecorder()
        E.recorder = spy
        state = {
            "license_blocked": False, "_license_warned": False, "paused": False,
            "freeze_until": 0.0, "button_down": False, "flash": 0,
            "smooth_name": "NORMAL", "dbg_until": 0.0,
        }
        engine.process_frame(
            cfg, _Cam(), _FakeTracker(confs), _Mouse(), None, None,
            AutoTuner(cfg), ctx, state, E,
        )
        return spy

    def test_a_confianca_do_tracker_chega_ao_recorder(self, monkeypatch):
        spy = self._correr(monkeypatch, [0.83])
        assert spy.calls, "o recorder nao foi chamado: o teste nao mede nada"
        _hands, _sides, _idx, _t, confs = spy.calls[-1]
        assert confs == [0.83]

    def test_a_confianca_por_mao_mantem_a_ordem(self, monkeypatch):
        spy = self._correr(monkeypatch, [0.11, 0.99])
        _hands, _sides, _idx, _t, confs = spy.calls[-1]
        assert confs == [0.11, 0.99]

    def test_nan_do_tracker_chega_nan(self, monkeypatch):
        spy = self._correr(monkeypatch, [float("nan")])
        _hands, _sides, _idx, _t, confs = spy.calls[-1]
        assert np.isnan(confs[0])
