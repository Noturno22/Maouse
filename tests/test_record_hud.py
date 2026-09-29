"""O painel de gravacao tem de ser verdadeiro, e tem de caber.

Nao sao testes de "a janela abre". Sao testes de duas promessas que o operador
faz ao gravar: a etiqueta que o preview mostra e a etiqueta que esta no ficheiro,
e a tabela de teclas que ele le no rodape e a que o codigo mapeia. As duas
falham em silencio - um texto trocado no rodape custa uma sessao inteira de
maos reais, e nao ha segunda tentativa.
"""
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from core import overlay
from core.corpus import (
    LABEL_KEY_CHOICES,
    CorpusRecorder,
    label_index,
    label_name,
)
from core.engine import _REC_HISTORY_MAX, _record_hud
from core.overlay import (
    _fps_txt,
    _wrap_pairs,
    draw_overlay,
    draw_record_panel,
    record_keymap_lines,
)


def _fake_rec(label="NONE", frames=0, fps=None):
    """Um gravador com a mesma leitura que o `CorpusRecorder` usa no HUD.

    Stub, e nao um gravador a serio, porque o painel so precisa de `label`,
    `frames`, `key_char` e `measured_fps` - e um gravador a serio exigiria
    landmarks frames a frames para testar uma frase. O que muda de facto
    (a etiqueta) vem do `CorpusRecorder` verdadeiro nos testes abaixo.
    """
    return SimpleNamespace(
        label=label, frames=frames,
        key_char=lambda: next(
            (k for k, v in LABEL_KEY_CHOICES.items() if v == label), "?"),
        measured_fps=lambda: fps,
    )


def _fake_E(ui=None):
    return SimpleNamespace(
        ui=ui if ui is not None else {"hands": 1},
        rec_label=None, rec_seg_start=0, rec_history=[],
    )


def _session(steps, ui=None):
    """Corre `_record_hud` como `process_frame` faria.

    `steps` e `[(etiqueta, frames_com_essa_etiqueta)]` e o contador de frames
    SOBE, que e o que o gravador faz. Escrever os numeros a mao dava contagens
    erradas nos testes: o segmento fecha no momento em que a etiqueta muda,
    com o total de frames *daquele* instante, e nao com o que se julgava ter
    escrito antes.
    """
    E = _fake_E(ui)
    total = 0
    for label, count in steps:
        # A tecla e lida num frame, e esse frame ja conta como "muda de
        # etiqueta" sem acrescentar nada ao corpus. E por isso que um
        # segmento pode ficar a 0 frames sem que nada tenha corrido mal: a
        # etiqueta foi posta e a mao nao estava a vista.
        _record_hud(E, _fake_rec(label, frames=total))
        for _ in range(count):
            total += 1
            _record_hud(E, _fake_rec(label, frames=total))
    return E

# ------------------------------------------------------------------ etiqueta


def test_key_char_diz_a_tecla_de_cada_gesto():
    """Toda a etiqueta tem de conseguir dizer a sua tecla, incluindo as tres
    que nao sao digitos. `d`/`c`/`g` sao as que ninguem adivinha, e sao
    precisamente as que o rodape do preview tem de mostrar."""
    for key, name in LABEL_KEY_CHOICES.items():
        rec = CorpusRecorder()
        rec.set_label(name)
        assert rec.key_char() == key, name


def test_key_char_diz_que_nao_ha_tecla_quando_nao_ha():
    """`SETTLE` e um indice negativo e nao tem tecla. `?` e nao `""`: um HUD
    que mostra `PINCH []` le-se como um bug de desenho."""
    rec = CorpusRecorder()
    rec.set_label("SETTLE")
    assert rec.key_char() == "?"


def test_a_tecla_que_o_rodape_mostra_e_a_que_o_codigo_mapeia():
    """O round-trip completo: carregar a tecla poe a etiqueta que o rodape
    diz. E o que impede o texto do rodape de divergir de `LABEL_KEY_CHOICES`."""
    for key, name in LABEL_KEY_CHOICES.items():
        rec = CorpusRecorder()
        # Comeca em `SETTLE` para que a mudanca seja sempre real: comecando em
        # NONE, a tecla "0" devolveria False (ja era NONE) e o teste estaria a
        # medir `set_label_by_key` e nao o mapeamento.
        rec.set_label("SETTLE")
        assert rec.set_label_by_key(ord(key)) is True
        assert rec.label == name
        assert rec.key_char() == key


# ------------------------------------------------------------------ o painel


def test_um_segmento_com_0_frames_diz_no_painel():
    """O contador de frames por segmento e a unica forma de o operador ver que
    pos a etiqueta sem mao a vista - e `seg_frames` em 0 e o unico sinal que
    o diferencia de "ainda nao ha frames para este segmento"."""
    E = _session([("NONE", 4), ("PINCH", 0)])
    assert E.ui["record"]["label"] == "PINCH"
    assert E.ui["record"]["seg_frames"] == 0
    assert E.ui["record"]["frames"] == 4


def test_mudar_de_etiqueta_fecha_o_segmento_anterior():
    E = _session([("OPEN", 10), ("FIST", 5)])
    assert E.ui["record"]["history"] == [("OPEN", 10)]
    assert E.ui["record"]["seg_frames"] == 5
    assert E.ui["record"]["frames"] == 15


def test_o_historico_nao_cresce_sem_limite():
    """O historico e para o operador ver a ultima volta de gestos. Se cresce
    sem limite, o `list()` que o HUD faz por frame comeca a pesar - e o que
    tem de caber e o rodape, nao o ficheiro."""
    steps = []
    for _ in range(_REC_HISTORY_MAX * 4):
        steps += [("OPEN", 3), ("FIST", 2)]
    E = _session(steps)
    assert len(E.ui["record"]["history"]) == _REC_HISTORY_MAX


def test_a_primeira_etiqueta_nao_inventa_um_segmento_vazio():
    """Um segmento de 0 frames no inicio seria mentira: a sessao ainda nao
    comecou. So a partir da segunda etiqueta ha historico."""
    E = _session([("NONE", 3)])
    assert E.ui["record"]["history"] == []


def test_o_painel_avisa_com_duas_maos_no_ecra():
    """So a mao do cursor e gravada. Com duas maos a vista, uma so tecla
    nao descreve as duas - e o aviso e o que diz isso antes de o ficheiro
    ficar mal etiquetado."""
    E = _session([("PEACE", 3)], ui={"hands": 2})
    assert E.ui["record"]["hands"] == 2


def test_o_historico_passado_e_copia():
    """`ui["record"]` e reescrito por frame. Se o HUD entregasse um `list`
    vivo, o `history` do frame anterior mudaria sozinho - e `process_frame` e
    o unico consumidor, nao ha razao para isso estar errado."""
    E = _session([("OPEN", 4)])
    primeiro = E.ui["record"]["history"]
    _record_hud(E, _fake_rec("FIST", frames=4))
    assert primeiro == []
    assert E.ui["record"]["history"] == [("OPEN", 4)]


def test_um_gravador_incompleto_nao_mata_a_recolha():
    """O painel e apresentacao; nao pode ser o motivo de uma recolha acabar a
    meio. Um gravador com etiqueta e frames mas sem `key_char` nem
    `measured_fps` - o spy de `test_recorder_provenance.py` e assim que fica -
    nao rebenta: o que falta vira `?` e `--`, nunca um numero inventado."""
    class _SoObserve:
        label = "PINCH"
        frames = 12

        def observe(self, hands, sides, index, t_ms, confs=None):
            return True

    E = _fake_E()
    _record_hud(E, _SoObserve())
    assert E.ui["record"]["key"] == "?"
    assert E.ui["record"]["fps"] is None
    assert E.ui["record"]["frames"] == 12


def test_um_gravador_sem_etiqueta_nao_inventa_uma_faixa():
    """Sem `label` nao ha nada verdadeiramente a mostrar. Pôr `None` no
    painel faria o rodape mentir sobre o que se esta a gravar."""
    E = _fake_E()
    _record_hud(E, SimpleNamespace(frames=12))
    assert "record" not in E.ui


# ------------------------------------------------------------------- desenho


#: O par mais longo da tabela. Abaixo disto a quebra ja nao tem grao: partir
#: "THUMB_DOWN" ao meio produz "THUMB_D", que e pior do que uma linha
#: ligeiramente comprida demais.
_PAR_MAIS_LONGO = max(len(f"{k} {n}") for k, n in LABEL_KEY_CHOICES.items())


def test_a_quebra_nao_perde_nenhum_par():
    """O rodape desenha as linhas que a quebra devolveu. Se a quebra perder um
    par, esse gesto fica sem tecla nenhuma no ecra - e o operador descobriria
    isso no meio da sessao, com a mao ja a tremer."""
    pares = [f"{k} {n}" for k, n in LABEL_KEY_CHOICES.items()]
    for max_chars in range(_PAR_MAIS_LONGO, 90, 7):
        linhas = _wrap_pairs(pares, max_chars)
        # O separador " | " so existe DENTRO de uma linha. A cada quebra um par
        # de separadores deixa de existir, dai a conta com `len(pares)`.
        esperado = sum(len(p) for p in pares) + 3 * (len(pares) - len(linhas))
        assert sum(len(x) for x in linhas) == esperado, max_chars


def test_nenhuma_linha_passa_do_maximo():
    for max_chars in range(_PAR_MAIS_LONGO, 90, 7):
        for line in _wrap_pairs(
                [f"{k} {n}" for k, n in LABEL_KEY_CHOICES.items()], max_chars):
            assert len(line) <= max_chars, (max_chars, line)


def test_um_par_maior_que_a_linha_nao_e_partido():
    """Cortado a meio, o nome do gesto deixa de se ler. Uma linha 3
    caracteres mais comprida ainda se le; `THUMB_D` ja nao e THUMB_DOWN, e
    falta THUMB_DOWN ao rodape inteiro."""
    linhas = _wrap_pairs(["9 THUMB_DOWN", "0 NONE"], 8)
    assert linhas[0] == "9 THUMB_DOWN"


def test_a_quebra_mantem_a_ordem_das_teclas():
    """A ordem e a de `LABEL_KEY_CHOICES`, que e a ordem em que os gestos
    fazem sentido (repouso, mao aberta, ...). Uma quebra que reordenasse
    transformava a tabela numa lotaria."""
    pairs = [f"{k} {n}" for k, n in LABEL_KEY_CHOICES.items()]
    flat = " ".join(_wrap_pairs(pairs, 24))
    pos = -1
    for p in pairs:
        nxt = flat.index(p, pos + 1)
        assert nxt > pos, p
        pos = nxt


def test_fps_sem_medicao_diz_que_nao_sabe():
    assert _fps_txt(None) == "fps: --"
    assert _fps_txt(0) == "fps: --"
    assert _fps_txt(14.6) == "15 fps"
    assert _fps_txt(29.97) == "30 fps"


@pytest.mark.parametrize("w", [640, 1280, 800, 480])
def test_nenhuma_linha_do_rodape_sai_do_ecra(w):
    """A quebra decide por numero de caracteres, mas o que tem de caber e
    PIXEL. Um `len()` que dá 87 caracteres numa linha de 404 px cabe; o mesmo
    `len()` com uma camara mais estreita pode nao caber, e o texto cortado no
    fim da linha e um gesto sem tecla - que e pior do que nao mostrar nada.
    """
    for line in record_keymap_lines(w, LABEL_KEY_CHOICES):
        (tw, _), _ = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
        assert 12 + tw <= w, (w, line, tw)


@pytest.mark.parametrize("size", [(640, 480), (1280, 720), (320, 240)])
def test_as_faixas_nao_se_sobrepoem(size):
    """A faixa de cima (etiqueta) e o rodape (tabela) sao as duas coisas que
    o operador nao pode perder de vista. Se a camara for baixa a ponto de as
    faixas se tocarem, uma delas tapada e o rodape que perde - e o rodape e a
    unica copia do mapeamento que o operador tem a mao."""
    w, h = size
    (pw, _), _ = cv2.getTextSize("0" * 20, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
    linhas = record_keymap_lines(w, LABEL_KEY_CHOICES)
    y1 = h - 16 * len(linhas) - 6
    y0 = 70 - 4
    for n_rows in (2, 3):          # com e sem o aviso de duas maos
        fim_cima = 70 + 20 * n_rows
        assert y1 > fim_cima or y1 < y0, (size, n_rows, y1)


@pytest.mark.parametrize("size", [(640, 480), (1280, 720), (320, 240)])
def test_o_painel_desenha_em_qualquer_resolucao(size):
    """A camara pode nao ser a do `Config`. O painel nao pode assumir 640x480
    nem rebentar - um `cv2.rectangle` com coordenadas fora do ecra e uma
    excepcao, e uma sessao de recolha morre no ultimo minuto."""
    w, h = size
    frame = np.zeros((h, w, 3), np.uint8)
    rec = CorpusRecorder()
    rec.set_label("THUMB_UP")
    draw_record_panel(frame, {
        "label": rec.label, "key": rec.key_char(), "frames": 123,
        "seg_frames": 45, "history": [("OPEN", 30)], "hands": 2,
        "keys": LABEL_KEY_CHOICES, "fps": 28.0,
    })
    assert frame.any(), "o painel nao desenhou nada"


def test_o_preview_normal_nao_mostra_a_faixa_de_gravacao():
    """`ui["record"]` so existe com `--record`. Sem isso o preview tem de ser
    exactamente o que era - senao uma correccao de recolha passa a atingir o
    uso normal."""
    frame = np.zeros((480, 640, 3), np.uint8)
    ui = {"ai_on": False, "ai_conf": 0.0, "voice": "off", "toast": "",
          "toast_until": 0.0, "autotune": False, "magnify": "", "hands": 0,
          "light": False, "tts": "", "ui_show": False}
    cfg = SimpleNamespace(move_gain=1.0, ai_confidence_min=0.5,
                          license_tier="pro")
    out = draw_overlay(frame, {}, None, None, 30.0, cfg, "NORMAL", False,
                       False, 0, ui)
    assert "record" not in ui
    assert out is not None


def test_o_preview_com_gravacao_desenha_de_fundo():
    """O caminho completo, com a ajuda aberta, que e o pior caso: as tres
    camadas (faixa, rodape, painel de ajuda) ao mesmo tempo. E o que o
    operador vai ver quando carrega `h` no meio da sessao a perguntar-se se a
    tecla esta certa."""
    frame = np.zeros((480, 640, 3), np.uint8)
    ui = {"ai_on": False, "ai_conf": 0.0, "voice": "off", "toast": "",
          "toast_until": 0.0, "autotune": False, "magnify": "", "hands": 2,
          "light": False, "tts": "", "ui_show": False,
          "record": {"label": "PEACE", "key": "6", "frames": 90,
                     "seg_frames": 12, "history": [("OPEN", 30)],
                     "hands": 2, "keys": LABEL_KEY_CHOICES, "fps": 29.9}}
    cfg = SimpleNamespace(move_gain=1.0, ai_confidence_min=0.5,
                          license_tier="pro")
    out = draw_overlay(frame, {}, None, None, 30.0, cfg, "NORMAL", False,
                       True, 0, ui)
    assert out is not None and out.any()


def test_a_ajuda_desce_quando_ha_faixa_de_gravacao():
    """A ajuda e o unico sitio onde estao as tres regras, e so aparece quando o
    operador a abre. Se ficar debaixo da faixa, ele carrega `h` no meio da
    sessao e continua sem a ver - e e a duvida que a ajuda existe para tirar.

    Medido em pixels, nao lido no codigo: a borda cinzenta da ajuda tem de
    aparecer em y=140 e nao em y=120, porque a faixa de gravacao ocupa ate
    y=130 quando ha o aviso das duas maos.
    """
    frame = np.zeros((480, 640, 3), np.uint8)
    ui = {"ai_on": False, "ai_conf": 0.0, "voice": "off", "toast": "",
          "toast_until": 0.0, "autotune": False, "magnify": "", "hands": 2,
          "light": False, "tts": "", "ui_show": False,
          "record": {"label": "PEACE", "key": "6", "frames": 90,
                     "seg_frames": 12, "history": [("OPEN", 30)], "hands": 2,
                     "keys": LABEL_KEY_CHOICES, "fps": 29.9}}
    cfg = SimpleNamespace(move_gain=1.0, ai_confidence_min=0.5,
                          license_tier="pro")
    draw_overlay(frame, {}, None, None, 30.0, cfg, "NORMAL", False, True, 0, ui)

    cinza = overlay.COLOR_GRAY
    assert tuple(frame[140, 12]) == cinza, "a ajuda nao desceu abaixo da faixa"
    # Em y=120 pode ja estar pixel de texto (a faixa escreve ate la), por isso
    # a prova e "aqui nao ha borda da ajuda" e nao "aquilo e escuro".
    assert tuple(frame[120, 12]) != cinza, "a ajuda ficou por baixo da faixa"


def test_label_index_e_label_name_aceitam_o_que_o_hud_manda():
    """Sanidade do par que o painel mostra: o `key_char` so faz sentido se
    `label_name(label_index(x)) == x` para tudo o que o HUD recebe."""
    for _key, name in LABEL_KEY_CHOICES.items():
        assert label_name(label_index(name)) == name
