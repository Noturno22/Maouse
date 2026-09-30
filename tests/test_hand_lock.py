"""A guarda do `HandLock`, feita de testes a sério.

`core/hand_lock.py` é **código morto** — o `engine.py` não o importa, e
`docs/RECONHECIMENTO_MAOS.md:1598` proíbe ligá-lo sem um corpus de mãos reais
(§1.5, Onda 3 §3.1). Isto **não** o liga. É a mesma distinção que o item 28 do
`PROGRESSO` fez com o `LicenseAgency`: o código fica, a ilusão de que está
guardado é que sai.

Porque isto importa mesmo sem ligar nada: a única guarda que o `HandLock` tinha
era `tools/test_hand_lock.py`, um **script standalone** que corre as verificações
ao nível do módulo e acaba em `sys.exit()`. `pyproject.toml` tem
`testpaths = ["tests"]`, portanto aquele ficheiro nunca correu na suite — os
"13 PASS" do `PROGRESSO` e do `re.md` vinham de o correr à mão. Pior: um dos
checks era `lock2.select([far], W, H) is None or True`, que é **sempre
verdadeiro**. Um check que não pode falhar não é um check, e era o único que
afirmava a garantia central do `HandLock`: que um intruso longe **não** rouba o
controlo durante a janela de graça.

Estes testes não ligam o `HandLock` ao produto. Têm de passar para o dia em que
alguém o ligar não herdar uma guarda que não guardava nada.
"""

from __future__ import annotations

from core.hand_lock import HandLock

W, H = 640, 480


def make_hand(cx_norm, cy_norm, scale=0.25):
    """Mao sintetica: palma em (cx,cy), escala via pulso->lm9."""
    pts = [(0.0, 0.0)] * 21
    pts[0] = (cx_norm, cy_norm + scale / 2.0)
    for i in (5, 9, 13, 17):
        pts[i] = (cx_norm, cy_norm - scale / 2.0)
    return pts


class TestUmaMaoSo:
    def test_uma_mao_controla_sempre(self):
        lock = HandLock()
        assert lock.select([make_hand(0.5, 0.5)], W, H) is not None

    def test_uma_mao_que_se_move_continua_a_controlar(self):
        lock = HandLock()
        lock.select([make_hand(0.5, 0.5)], W, H)
        assert lock.select([make_hand(0.52, 0.5)], W, H) is not None


class TestSemMaos:
    def test_sem_maos_devolve_none(self):
        assert HandLock().select([], W, H) is None

    def test_dentro_da_graca_segue_preso(self):
        lock = HandLock(lost_grace_frames=3)
        lock.select([make_hand(0.5, 0.5)], W, H)
        for _ in range(3):
            assert lock.select([], W, H) is None
        assert lock.locked

    def test_expirada_a_graca_faz_reset(self):
        lock = HandLock(lost_grace_frames=3)
        lock.select([make_hand(0.5, 0.5)], W, H)
        for _ in range(4):
            lock.select([], W, H)
        assert not lock.locked


class TestDuasMaos:
    def test_mantem_a_mao_mais_proxima_do_ponto_controlado(self):
        """A garantia de continuidade: com duas mãos, quem fica com o rato é a que
        estava mais perto de onde o rato estava, não a que apareceu primeiro."""
        lock = HandLock()
        lock.select([make_hand(0.3, 0.5)], W, H)
        owner = make_hand(0.33, 0.5)
        intruder = make_hand(0.77, 0.5)
        assert lock.select([intruder, owner], W, H) == owner

    def test_sem_historico_adquire_a_mao_maior(self):
        lock = HandLock()
        small = make_hand(0.2, 0.8, scale=0.10)
        big = make_hand(0.7, 0.3, scale=0.35)
        assert lock.select([small, big], W, H) == big


class TestIntrusoLonge:
    """A garantia central, e a que o script original nao verificava.

    Um intruso longe do ponto controlado **não** pode ficar com o rato
    imediatamente: ficaria com o rato a saltar para o outro lado do ecrã a cada
    frame em que o dono desaparecesse. Só depois de expirar a graça é que outra
    mão pode adquirir.
    """

    def test_intruso_longe_nao_rouba_durante_a_graca(self):
        lock = HandLock(lost_grace_frames=10)
        lock.select([make_hand(0.2, 0.2)], W, H)
        far = make_hand(0.85, 0.85)
        devolvidos = [lock.select([far], W, H) for _ in range(10)]
        assert devolvidos == [None] * 10

    def test_apos_a_graca_adquire_uma_mao_disponivel(self):
        lock = HandLock(lost_grace_frames=10)
        lock.select([make_hand(0.2, 0.2)], W, H)
        far = make_hand(0.85, 0.85)
        for _ in range(11):
            got = lock.select([far], W, H)
        assert got is far
        assert lock.locked


class TestTrocaLegitima:
    def test_dono_ausente_e_outro_longe_nao_troca(self):
        lock = HandLock(radius_frac=0.20)
        lock.select([make_hand(0.4, 0.4)], W, H)
        assert lock.select([make_hand(0.9, 0.9)], W, H) is None

    def test_dono_que_volta_retoma(self):
        lock = HandLock(radius_frac=0.20)
        lock.select([make_hand(0.4, 0.4)], W, H)
        lock.select([make_hand(0.9, 0.9)], W, H)
        assert lock.select([make_hand(0.41, 0.4)], W, H) is not None

    def test_mao_dentro_do_raio_ganha_a_outra(self):
        """O inverso do intruso longe: uma mão que chega perto do ponto controlado
        **deve** ficar com o rato, mesmo estando a outra mais perto em termos de
        mão maior."""
        lock = HandLock(radius_frac=0.30)
        lock.select([make_hand(0.4, 0.4)], W, H)
        perto = make_hand(0.43, 0.4)
        longe = make_hand(0.9, 0.9)
        assert lock.select([longe, perto], W, H) == perto
