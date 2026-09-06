"""Anti-falso-positivo do alternador.

A mao do CURSOR (direita) a atravessar a metade esquerda do ecra com a palma
aberta nao deve abrir o alternador de janelas: durante o hold de ~2s a palma
nao pode derivar mais que cfg.left_hand_open_switch_max_move_px (senao nao e
um hold intencional de comando, e sim a mao do cursor a mover-se).
"""
from config import Config
from core.gestures import Gesture
from core.twohand import LeftHandDetector

cfg = Config()
HOLD = cfg.left_hand_open_switch_s
DT = 0.05


def _fired(palms):
    det = LeftHandDetector(cfg)
    fired = []
    for i, palm in enumerate(palms):
        ev, _ = det.update(palm, i * DT, Gesture.OPEN)
        if ev == "alt_switch_open":
            fired.append(i * DT)
    return fired


def test_open_parada_abre_o_alternador():
    n = int(HOLD / DT + 2)
    assert len(_fired([(200.0, 200.0)] * n)) == 1


def test_cursor_a_atravessar_nao_abre_o_alternador():
    # 3 px/frame -> move mais de 45 px no tempo do hold (mao do cursor a cruzar)
    n = int(HOLD / DT + 2)
    palms = [(220.0 + 3.0 * i, 200.0) for i in range(n)]
    assert _fired(palms) == []


def test_hold_longa_estavel_depois_de_atravessar_ainda_abre():
    # A mao cruza primeiro (move muito) e depois PARA: o hold volta a contar
    # a partir do momento em que fica estavel e acaba por abrir.
    n = int(HOLD / DT + 2)
    palms = [(220.0 + 3.0 * i, 200.0) for i in range(int(HOLD / DT))]
    palms += [(220.0 + 3.0 * int(HOLD / DT), 200.0)] * n
    assert len(_fired(palms)) == 1


def _fired_ok(det, palms, ok):
    fired = []
    for i, palm in enumerate(palms):
        ev, _ = det.update(palm, i * DT, Gesture.OPEN, commands_ok=ok)
        if ev == "alt_switch_open":
            fired.append(i * DT)
    return fired


def test_uma_mao_nao_abre_o_alternador():
    # Com as DUAS maos exigidas, uma unica mao a segurar aberta nao abre.
    det = LeftHandDetector(cfg)
    n = int(HOLD / DT + 2)
    assert _fired_ok(det, [(200.0, 200.0)] * n, ok=False) == []


def test_peace_toggle_so_com_uma_mao_continua_a_funcionar():
    # O PEACE (mostrar/ocultar interface) NAO exige as duas maos.
    det = LeftHandDetector(cfg)
    fired = []
    now = 0.0
    for i in range(int(cfg.left_hand_gesture_stable_frames + 2)):
        now += 0.1
        ev, _ = det.update((200.0, 200.0), now, Gesture.PEACE, commands_ok=False)
        if ev == "gui_toggle":
            fired.append(now)
    assert len(fired) == 1


def _fired_full(det, palms, fully_open):
    fired = []
    for i, palm in enumerate(palms):
        ev, _ = det.update(palm, i * DT, Gesture.OPEN, fully_open=fully_open)
        if ev == "alt_switch_open":
            fired.append(i * DT)
    return fired


def test_totalmente_aberta_abre_o_alternador_quase_de_imediato():
    # Mão 100% aberta (fully_open) com palma ESTAVEL abre muito antes do hold
    # normal de left_hand_open_switch_s: usa left_hand_open_fast_s.
    det = LeftHandDetector(cfg)
    n = int(HOLD / DT + 2)
    fired = _fired_full(det, [(200.0, 200.0)] * n, fully_open=True)
    assert len(fired) == 1
    fast_limit = cfg.left_hand_open_fast_s + 2 * DT
    assert fired[0] <= fast_limit


def test_aberta_normal_nao_usa_o_hold_rapido():
    # Mão aberta mas NÃO totalmente (fully_open=False) respeita o hold normal.
    det = LeftHandDetector(cfg)
    n = int(HOLD / DT + 2)
    fired = _fired_full(det, [(200.0, 200.0)] * n, fully_open=False)
    assert len(fired) == 1
    assert fired[0] >= cfg.left_hand_open_switch_s


def test_mao_a_mover_o_rato_nao_abre_mesmo_totalmente_aberta():
    # A mao do CURSOR a mover o rato (8 px/frame ~ 160 px/s) com a mao aberta
    # NAO deve abrir o alternador: durante a janela fast a palma deriva muito
    # mais que left_hand_open_fast_max_move_px (15 px).
    det = LeftHandDetector(cfg)
    n = int(HOLD / DT + 2)
    palms = [(220.0 + 8.0 * i, 200.0) for i in range(n)]
    assert _fired_full(det, palms, fully_open=True) == []