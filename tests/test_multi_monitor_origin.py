"""Origem do ecrã virtual e clamp do rato em máquinas com 2+ monitores.

O Windows põe a origem do desktop virtual em coordenada **negativa** quando há um
ecrã à esquerda ou acima do monitor principal. O `pynput` trabalha nessas
coordenadas absolutas, mas `_screen_size` só devolvia largura e altura — e o clamp
assumia que o ecrã começava em 0. Metade do desktop ficava fora do clamp e o rato
preso no monitor principal.
"""
from core.mouse_ctl import MouseCtl
from tests.test_remote_protocol_contract import _server


class _FakeMouse:
    """Rato que regista o `position` que lhe mandam, sem sistema operativo."""

    def __init__(self, position=(0, 0)):
        self.position = position


def _ctl(screen_w, screen_h, screen_x=0, screen_y=0, position=(0, 0)):
    """Monta um `MouseCtl` sem constructor nem pynput."""
    ctl = MouseCtl.__new__(MouseCtl)
    ctl.mouse = _FakeMouse(position)
    ctl.screen_w = screen_w
    ctl.screen_h = screen_h
    ctl.screen_x = screen_x
    ctl.screen_y = screen_y
    ctl._scroll_acc = 0.0
    ctl._frac_x = 0.0
    ctl._frac_y = 0.0
    return ctl


# ── A origem ──────────────────────────────────────────────────────────────

def test_bounds_com_ecra_a_esquerda_incluem_a_origem_negativa():
    """Monitor de 1920 à esquerda do principal: o desktop vai de -1920 a +1919."""
    ctl = _ctl(3840, 1080, screen_x=-1920, screen_y=0)
    assert ctl.screen_bounds() == (-1920, 0, 1919, 1079)


def test_bounds_com_ecra_acima_incluem_a_origem_negativa():
    ctl = _ctl(1920, 2160, screen_x=0, screen_y=-1080)
    assert ctl.screen_bounds() == (0, -1080, 1919, 1079)


def test_bounds_de_ecra_unico_comecam_em_zero():
    ctl = _ctl(1920, 1080)
    assert ctl.screen_bounds() == (0, 0, 1919, 1079)


def test_ecra_com_origem_negativa_em_cima_e_a_esquerda():
    """Monitor diagonal: as duas origens negativas ao mesmo tempo."""
    ctl = _ctl(5760, 3240, screen_x=-1920, screen_y=-1080)
    assert ctl.screen_bounds() == (-1920, -1080, 3839, 2159)


# ── O clamp ───────────────────────────────────────────────────────────────

def test_rato_nao_e_atirado_para_zero_a_partir_de_x_negativo():
    """O bug: com um ecrã à esquerda, o rato estava em x negativo e o clamp
    atirava-o para 0 — o ecrã principal."""
    ctl = _ctl(3840, 1080, screen_x=-1920, position=(-1000, 500))
    ctl.move_by(50, 0)
    assert ctl.mouse.position == (-950, 500)


def test_rato_pode_sair_do_monitor_principal_para_o_da_esquerda():
    ctl = _ctl(3840, 1080, screen_x=-1920, position=(100, 500))
    ctl.move_by(-300, 0)
    assert ctl.mouse.position == (-200, 500)


def test_rato_para_na_borda_esquerda_do_ecra_virtual():
    ctl = _ctl(3840, 1080, screen_x=-1920, position=(-1900, 500))
    ctl.move_by(-500, 0)
    assert ctl.mouse.position == (-1920, 500), "tem de parar na borda, nao saltar"


def test_rato_para_na_borda_direita_do_ecra_virtual():
    ctl = _ctl(3840, 1080, screen_x=-1920, position=(1900, 500))
    ctl.move_by(500, 0)
    assert ctl.mouse.position == (1919, 500)


def test_rato_sobe_para_o_ecra_de_cima():
    ctl = _ctl(1920, 2160, screen_x=0, screen_y=-1080, position=(500, -200))
    ctl.move_by(0, -300)
    assert ctl.mouse.position == (500, -500)


def test_rato_para_na_borda_de_cima():
    ctl = _ctl(1920, 2160, screen_x=0, screen_y=-1080, position=(500, -1000))
    ctl.move_by(0, -500)
    assert ctl.mouse.position == (500, -1080)


def test_ecra_unico_continua_a_comportar_se_como_antes():
    """Sem ecrã nenhum ao lado, o comportamento tem de ser o de sempre."""
    ctl = _ctl(1920, 1080, position=(500, 500))
    ctl.move_by(100, 100)
    assert ctl.mouse.position == (600, 600)


def test_acumulador_fraccionario_sobrevive_ao_clamp_com_origem_negativa():
    """O resto fraccionário não pode perder-se nem ganhar-se no clamp.

    Cada `move_by` que não chega a 1 px guarda o resto. Se o clamp mastigasse o
    resto, o toque lento andava mais depressa do que o rápido.
    """
    ctl = _ctl(3840, 1080, screen_x=-1920, position=(-1000, 500))
    for _ in range(3):
        ctl.move_by(0.4, 0)
    assert ctl.mouse.position == (-999, 500), "1.2 px no total: passa so 1 px"


def test_move_by_nao_escreve_a_posicao_sem_delta_inteiro():
    ctl = _ctl(3840, 1080, screen_x=-1920, position=(-1000, 500))
    ctl.move_by(0, 0)
    assert ctl.mouse.position == (-1000, 500)


# ── `move_to` no PC: normalizado -> píxeis absolutos ───────────────────────

def test_move_to_aplica_a_origem_do_ecra_virtual():
    """Sem `ox`, `int(x * w)` dava uma coordenada que existe no monitor
    principal — e não no ecrã onde o utilizador tocou."""
    srv, mouse = _server()
    mouse.screen_w, mouse.screen_h = 3840, 1080
    mouse.screen_x, mouse.screen_y = -1920, 0

    srv._handle("move_to", {"x": 0.5, "y": 0.5})
    # 0.5 do desktop virtual: -1920 + int(0.5 * 3839) = -1
    assert mouse.position == (-1, 539)


def test_move_to_no_canto_do_ecra_com_origem_negativa():
    srv, mouse = _server()
    mouse.screen_w, mouse.screen_h = 3840, 1080
    mouse.screen_x, mouse.screen_y = -1920, 0

    srv._handle("move_to", {"x": 0.0, "y": 0.0})
    assert mouse.position == (-1920, 0), "o canto do desktop virtual nao e (0,0)"


def test_gesture_tambem_move_para_a_origem_certa():
    srv, mouse = _server()
    mouse.screen_w, mouse.screen_h = 3840, 1080
    mouse.screen_x, mouse.screen_y = -1920, 0

    srv._handle("gesture", {"event": "tap", "x": 0.0, "y": 0.0})
    assert mouse.position == (-1920, 0)


def test_move_to_sem_atributos_de_origem_comporta_se_como_antes():
    """Um rato de teste sem `screen_x` tem de dar 0, para o `getattr` continuar a
    ser o caminho de recurso."""
    srv, mouse = _server()
    mouse.screen_w, mouse.screen_h = 1920, 1080

    srv._handle("move_to", {"x": 0.5, "y": 0.5})
    assert mouse.position == (959, 539)
