"""Robustez do Alt+F4 por punho (fechar janela com a mao de comandos).

O bug corrigido: bastava 1 frame de FIST (gesto commitado) para fechar a
janela - um punho transitorio (pinca de clique, dedos a curvarem-se) ou a
mao do cursor a atravessar a metade esquerda do ecra fechava janelas a toa.

Agora o disparo exige um HOLD continuo (left_hand_fist_close_hold_s) e um
cooldown, tal como as outras acoes da mao esquerda (PEACE/alternador).
"""
from core.twohand import FistHoldDetector

HOLD = 0.8
COOLDOWN = 2.5


def _events(actions, dt=0.05, hold=HOLD, cooldown=COOLDOWN):
    """`actions` e uma lista de bools (punho ativo) frame a frame com passo dt.

    Devolve os instantes em que o detector disparou.
    """
    det = FistHoldDetector(hold_s=hold, cooldown_s=cooldown)
    fired = []
    for i, active in enumerate(actions):
        if det.update(active, i * dt):
            fired.append(i * dt)
    return fired


def test_short_fist_does_not_fire():
    fired = _events([True] * int(HOLD / 0.05 - 1), hold=HOLD)
    assert fired == []


def test_fist_after_hold_fires_exactly_once():
    fired = _events([True] * int(HOLD / 0.05 + 1), hold=HOLD)
    assert len(fired) == 1
    # dispara apenas depois do hold completo
    assert fired[0] >= HOLD - 0.001


def test_held_forever_fires_once_not_in_bursts():
    # segurar durante 6s (muito alem do hold + cooldown) nao fecha em rajada
    fired = _events([True] * int(6.0 / 0.05), hold=HOLD, cooldown=COOLDOWN)
    assert len(fired) == 1


def test_interruption_resets_hold():
    # 0.5s de punho + pausa de 0.1s + 0.5s de punho => total 1.0s, mas nunca
    # continuo => nao dispara
    actions = [True] * 10 + [False] * 2 + [True] * 10
    fired = _events(actions, hold=HOLD)
    assert fired == []


def test_refire_after_cooldown():
    # dispara, larga o punho, espera o cooldown e segura de novo
    fire_t = HOLD
    actions = [True] * (int(fire_t / 0.05) + 1)
    actions += [False] * int(0.2 / 0.05)
    actions += [True] * int((COOLDOWN + HOLD) / 0.05)
    fired = _events(actions, hold=HOLD, cooldown=COOLDOWN)
    assert len(fired) == 2
    assert fired[1] - fired[0] >= COOLDOWN - 0.001