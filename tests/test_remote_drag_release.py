"""Botões que ficam premidos quando a ligação morre a meio de um arrasto.

O comando `press` sem `release` correspondente, ou o gesto `left_down` sem
`left_up`, deixavam o botão do rato fisicamente premido no PC. Sem isso, quem
perde a rede durante um arrasto fica com o rato «cola» até carregar em algo e
ver que aquilo fica a ser arrastado. O `_combo` já fazia a limpeza das teclas
nos dois caminhos; os botões é que não tinham estado.
"""
import pytest

from core.remote import Button
from tests.lease_test_keys import VALID_LEASE
from tests.test_remote_protocol_contract import _run, _server

pytestmark = pytest.mark.usefixtures("patched_public_key")

AUTH = {"cmd": "auth", "token": "segredo123", "lease": VALID_LEASE}


def _held_calls(mouse):
    return [c for c in mouse.calls if c[0] in ("press_left", "release_left", "press", "release")]


# ── O comando `press` ─────────────────────────────────────────────────────

def test_press_sem_release_solta_o_botao_quando_a_ligacao_morre():
    """O bug: a rede cai entre o `press` e o `release`."""
    srv, mouse = _server()
    _run(srv, [AUTH, {"cmd": "press", "button": "left"}])
    assert ("release_left",) in mouse.calls, "o botao esquerdo ficou premido"


def test_press_e_release_completos_nao_soltam_duas_vezes():
    srv, mouse = _server()
    _run(srv, [
        AUTH,
        {"cmd": "press", "button": "left"},
        {"cmd": "release", "button": "left"},
    ])
    assert mouse.calls.count(("release_left",)) == 1, "o release explicito ja bastava"


def test_press_direito_sem_release_solta_o_direito():
    srv, mouse = _server()
    _run(srv, [AUTH, {"cmd": "press", "button": "right"}])
    assert ("release", Button.right) in mouse.calls


def test_press_do_meio_sem_release_solta_o_meio():
    srv, mouse = _server()
    _run(srv, [AUTH, {"cmd": "press", "button": "middle"}])
    assert ("release", Button.middle) in mouse.calls


def test_lmb_e_left_sao_o_mesmo_botao():
    """`lmb` e `left` têm de colapsar no mesmo botão held.

    Sem canonicalizar, `press lmb` seguido de nada limpava duas vezes, e um
    `press lmb` + `release left` deixava o botão premido para sempre.
    """
    srv, mouse = _server()
    _run(srv, [
        AUTH,
        {"cmd": "press", "button": "lmb"},
        {"cmd": "release", "button": "left"},
    ])
    assert mouse.calls.count(("release_left",)) == 1, "lmb e left sao o mesmo botao"
    assert srv._held == set()


def test_alias_desconhecido_nao_poe_o_botao_em_held():
    srv, _ = _server()
    try:
        srv._handle("press", {"button": "lmb"})
        srv._handle("release", {"button": "botao-que-nao-existe"})
    except ValueError:
        pass
    assert "botao-que-nao-existe" not in srv._held


def test_dois_botoes_ao_mesmo_tempo_sao_soltos_os_dois():
    srv, mouse = _server()
    _run(srv, [
        AUTH,
        {"cmd": "press", "button": "left"},
        {"cmd": "press", "button": "right"},
    ])
    assert ("release_left",) in mouse.calls
    assert ("release", Button.right) in mouse.calls


# ── O gesto `left_down` ───────────────────────────────────────────────────

def test_left_down_sem_left_up_solta_o_arrasto():
    """O caminho do gesto tinha o mesmo furo: `_drag` ficava a True e o botão
    premido, e nada voltava a zero."""
    srv, mouse = _server()
    _run(srv, [AUTH, {"cmd": "gesture", "event": "left_down"}])
    assert ("release_left",) in mouse.calls, "o arrasto ficou premido"
    assert srv._drag is False, "_drag tem de voltar a False"


def test_left_down_e_left_up_completos_nao_soltam_duas_vezes():
    srv, mouse = _server()
    _run(srv, [
        AUTH,
        {"cmd": "gesture", "event": "left_down"},
        {"cmd": "gesture", "event": "left_up"},
    ])
    assert mouse.calls.count(("release_left",)) == 1
    assert srv._drag is False


def test_gesto_left_down_depois_de_press_solta_uma_vez_cada():
    """`press left` + `left_down` são o mesmo botão. Se a ligação morresse, só
    pode haver um `release` — dois deixariam o estado incoerente."""
    srv, mouse = _server()
    _run(srv, [
        AUTH,
        {"cmd": "press", "button": "left"},
        {"cmd": "gesture", "event": "left_down"},
    ])
    assert mouse.calls.count(("release_left",)) == 1, "o botao esquerdo e um so"
    assert srv._drag is False


# ── O que não pode ser afectado ──────────────────────────────────────────

def test_ligacao_limpa_nao_solta_nada():
    """Uma sessão que nunca premiu nada não pode gerar um `release` espúrio —
    senão cada reconexão largava um botão que o utilizador não estava a
    carregar."""
    srv, mouse = _server()
    _run(srv, [AUTH, {"cmd": "move_rel", "dx": 5, "dy": 5}])
    assert ("release_left",) not in mouse.calls


def test_clique_completo_nao_e_misturado_com_arrasto():
    srv, mouse = _server()
    _run(srv, [AUTH, {"cmd": "click", "button": "left"}])
    assert ("left_click",) in mouse.calls
    assert ("release_left",) not in mouse.calls


def test_clique_durante_o_arrasto_solta_o_arrasto():
    """Um `click` (que faz down+up) no meio de um arrasto tem de ser
    neutralizado: senão o `release` do clique desfaz o `press` do arrasto."""
    srv, mouse = _server()
    _run(srv, [
        AUTH,
        {"cmd": "gesture", "event": "left_down"},
        {"cmd": "click", "button": "left"},
    ])
    assert srv._drag is False, "o clique anulou o arrasto; o estado tem de saber"


def test_o_estado_fica_limpo_para_a_proxima_ligacao():
    srv, mouse = _server()
    _run(srv, [AUTH, {"cmd": "press", "button": "left"}])
    assert srv._held == set() and srv._drag is False
    # Segunda ligacao: nao pode herd nada da primeira.
    _run(srv, [AUTH, {"cmd": "move_rel", "dx": 1, "dy": 1}])
    assert ("release_left",) not in mouse.calls[2:], "a segunda sessao herdou estado"
