"""Testes do controlo remoto por telemóvel (core.remote)."""
import asyncio
import json

import pytest

from config import Config
from core.remote import (
    RemoteArbiter,
    RemoteServer,
    generate_code,
    lan_ips,
    valid_code,
)


class FakePointer:
    def __init__(self):
        self.position = (0, 0)
        self.scrolls = []
        self.clicks = []
        self.presses = []
        self.releases = []

    def scroll(self, dx, dy):
        self.scrolls.append((dx, dy))

    def click(self, button):
        self.clicks.append(button)

    def press(self, button):
        self.presses.append(button)

    def release(self, button):
        self.releases.append(button)


class FakeMouse:
    def __init__(self):
        self.screen_w = 1920
        self.screen_h = 1080
        self.mouse = FakePointer()
        self.moves = []
        self.clicks = []
        self.pressed = []
        self.released = []
        self.scrolled = []
        # Onde o cursor estava no momento EXACTO de cada clique. Sem isto não
        # se pode provar que o clique caiu no ponto tocado: o `move_to` e o
        # `left_click` acontecem no mesmo comando e a posição final é a mesma
        # nos dois casos.
        self.click_at = []

    def move_by(self, dx, dy):
        self.moves.append((dx, dy))
        x, y = self.mouse.position
        self.mouse.position = (
            min(max(x + dx, 0), self.screen_w - 1),
            min(max(y + dy, 0), self.screen_h - 1),
        )

    def left_click(self):
        self.clicks.append("left")
        self.click_at.append(("left", self.mouse.position))

    def right_click(self):
        self.clicks.append("right")
        self.click_at.append(("right", self.mouse.position))

    def press_left(self):
        self.pressed.append("left")

    def release_left(self):
        self.released.append("left")

    def scroll(self, dy):
        self.scrolled.append(dy)


class _FakeConnection:
    """Ligação WebSocket mínima: entrega uma lista de mensagens já prontas."""

    def __init__(self, messages):
        self._messages = [json.dumps(m) for m in messages]
        self.remote_address = ("192.168.0.189", 51234)
        self.sent = []

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._messages:
            raise StopAsyncIteration
        return self._messages.pop(0)

    async def send(self, payload):
        self.sent.append(payload)


def test_generate_code_is_unique_e_de_seis_digitos():
    a = generate_code()
    b = generate_code()
    assert valid_code(a)
    assert valid_code(b)
    assert len(a) == 6
    assert a.isdigit()
    assert a != b


def test_lan_ips_returns_list():
    ips = lan_ips()
    assert isinstance(ips, list)
    assert all(":" not in ip for ip in ips)


def test_usable_ip_filters_non_routable():
    from core.remote import _usable_ip

    assert _usable_ip("192.168.1.50") is True
    assert _usable_ip("10.0.0.7") is True
    assert _usable_ip("127.0.0.1") is False
    assert _usable_ip("169.254.10.1") is False
    assert _usable_ip("0.0.0.0") is False
    assert _usable_ip("::1") is False
    assert _usable_ip("") is False


def test_key_aliases_arrow_keys():
    from pynput.keyboard import Key

    from core.remote import RemoteServer

    srv = RemoteServer(Config(), FakeMouse())
    assert srv._resolve_key("arrow_left") is Key.left
    assert srv._resolve_key("arrow_up") is Key.up
    assert srv._resolve_key("arrow_down") is Key.down
    assert srv._resolve_key("arrow_right") is Key.right
    assert srv._resolve_key("left") is Key.left


def test_dispatch_move_click_scroll_press():
    cfg = Config()
    cfg.remote_code = "123456"
    cfg.remote_move_gain = 1.0
    mouse = FakeMouse()
    srv = RemoteServer(cfg, mouse)

    srv._handle("move", {"dx": 12, "dy": -4})
    assert mouse.moves == [(12, -4)]

    srv._handle("click", {"button": "left", "count": 1})
    assert mouse.clicks == ["left"]

    srv._handle("click", {"button": "left", "count": 2})
    assert mouse.clicks == ["left", "left", "left"]

    srv._handle("scroll", {"dx": 0, "dy": 3})
    assert mouse.scrolled == [3]

    srv._handle("press", {"button": "left"})
    srv._handle("release", {"button": "left"})
    assert mouse.pressed == ["left"]
    assert mouse.released == ["left"]


def test_dispatch_move_to_clamps():
    cfg = Config()
    cfg.remote_code = "123456"
    mouse = FakeMouse()
    srv = RemoteServer(cfg, mouse)

    srv._handle("move_to", {"x": 0.5, "y": 0.25})
    assert mouse.mouse.position == (959, 269)

    srv._handle("move_to", {"x": 5.0, "y": -1.0})
    assert mouse.mouse.position == (1919, 0)


def test_dispatch_unknown_command_raises():
    cfg = Config()
    cfg.remote_code = "123456"
    srv = RemoteServer(cfg, FakeMouse())
    with pytest.raises(ValueError):
        srv._handle("coiso", {})


class TestTouchpadRelativo:
    """O arrasto de um dedo é RELATIVO: o dedo move o cursor a partir de onde
    ele está, com o ganho de ``remote_move_gain``.

    O TOQUE é que é absoluto (ver ``TestToqueAbsoluto``): é a única forma de o
    clique não depender de uma mira. Estas duas coisas juntas — arrasto
    relativo, toque absoluto — são o design escolhido, e é a combinação que
    elimina o "o clique salta" que o utilizador reportou três vezes."""

    def test_toque_clica_onde_o_cursor_esta_sem_o_saltar(self):
        """Um ``gesture tap`` sem coordenadas é um clique trackpad: não pode
        teletransportar o rato. O app do telemóvel já não usa este caminho (manda
        sempre x/y), mas o servidor continua a aceitá-lo para clientes que
        queiram o rato como alvo."""
        cfg = Config()
        cfg.remote_code = "123456"
        mouse = FakeMouse()
        srv = RemoteServer(cfg, mouse)

        # O utilizador arrastou o cursor até aqui...
        mouse.mouse.position = (1000, 130)
        srv._handle("gesture", {"event": "tap"})

        assert mouse.mouse.position == (1000, 130), (
            "o toque moveu o rato: o cursor tem de carregar onde já está, "
            "não saltar para o ponto tocado"
        )
        assert mouse.clicks == ["left"]

    def test_toque_com_coordenadas_mantem_o_salto_explicito(self):
        """Clientes que mandem x/y continuam a poder saltar antes de clicar."""
        cfg = Config()
        cfg.remote_code = "123456"
        mouse = FakeMouse()
        srv = RemoteServer(cfg, mouse)

        srv._handle("gesture", {"event": "tap", "x": 0.5, "y": 0.5})
        assert mouse.mouse.position == (959, 539)
        assert mouse.clicks == ["left"]

    def test_ganho_default_torna_o_ecra_alcancavel(self):
        """O touchpad tem ~330 px e o ecrã 1366.

        A 1:1 (o bug) uma varredura do dedo cobria 330 dos 1366 px: o cursor
        ficava a um quarto do caminho e o toque seguinte — absoluto — atirava-o
        para o outro lado. Com o ganho por omissão, uma varredura tem de chegar
        a pelo menos dois terços do ecrã, e o canto oposto tem de ficar
        alcançável sem dificuldade.
        """
        cfg = Config()
        mouse = FakeMouse()
        mouse.screen_w, mouse.screen_h = 1366, 768
        srv = RemoteServer(cfg, mouse)
        pad_w = 330

        for _ in range(pad_w):
            srv._handle("move", {"dx": 1, "dy": 0})
        uma_varredura = mouse.mouse.position[0]

        assert uma_varredura >= 2 * mouse.screen_w // 3, (
            f"uma varredura do pad cobriu só {uma_varredura} de "
            f"{mouse.screen_w} px: o ganho não está a compensar o touchpad"
        )
        # Continuar a varrer tem de levar ao canto oposto.
        for _ in range(pad_w):
            srv._handle("move", {"dx": 1, "dy": 0})
        assert mouse.mouse.position[0] == mouse.screen_w - 1

    def test_ganho_nao_perde_pixels_fracionarios(self):
        """Ganho fraccionário tem de acumular: arredondar por evento perde
        meio píxel de cada vez e, com centenas de eventos, o cursor ficava
        progressivamente atrasado."""
        cfg = Config()
        cfg.remote_move_gain = 2.5
        mouse = FakeMouse()
        srv = RemoteServer(cfg, mouse)

        for _ in range(100):
            srv._handle("move", {"dx": 1, "dy": 0})

        assert mouse.mouse.position[0] == 250

    def test_ganho_fora_de_raio_e_limitado(self):
        for bruto, esperado in ((0.1, 1.0), (99.0, 8.0), (-5.0, 1.0)):
            cfg = Config()
            cfg.remote_code = "123456"
            cfg.remote_move_gain = bruto
            mouse = FakeMouse()
            srv = RemoteServer(cfg, mouse)
            srv._handle("move", {"dx": 1, "dy": 0})
            assert mouse.moves == [(esperado, 0)]

    def test_salto_absolvo_zera_o_resto_fraccionario(self):
        """Depois de um salto absoluto, o resto fraccionário do movimento
        relativo já não tem sentido: sem o reset, o primeiro `move` following
        arrancava um deslocamento fantasma."""
        cfg = Config()
        cfg.remote_code = "123456"
        cfg.remote_move_gain = 2.5
        mouse = FakeMouse()
        srv = RemoteServer(cfg, mouse)

        srv._handle("move", {"dx": 1, "dy": 0})  # deixa 0.5 px de resto
        srv._handle("move_to", {"x": 0.5, "y": 0.5})
        mouse.moves.clear()
        srv._handle("move", {"dx": 1, "dy": 0})

        assert mouse.moves == [(2, 0)]

    def test_ganho_esta_guardado_nas_definicoes(self, monkeypatch, tmp_path):
        import config as config_mod

        monkeypatch.setattr(
            config_mod, "SETTINGS_FILE", str(tmp_path / "settings.json")
        )
        cfg = Config()
        cfg.remote_code = "123456"
        cfg.remote_move_gain = 4.5
        config_mod.save_settings(cfg, "NORMAL")

        lido = Config()
        config_mod.load_settings(lido)
        assert lido.remote_move_gain == 4.5

    def test_ganho_aplicado_so_pelo_pc(self):
        """O ganho vive num sítio só: o PC.

        Havia `MOVE_GAIN = 1.8` no telefone E `remote_move_gain = 3.0` aqui, e
        os dois multiplicavam. Uma varredura do dedo na largura do touchpad
        levava o cursor a 1780 px num ecrã de 1366 — ou seja, batia sempre no
        limite, e o toque clicava onde o cursor tinha ficado em vez de onde o
        dedo parou. Este teste fixa o rácio pad/ecrã para esse tipo de regressão
        voltar a ser óbvio: o cliente envia o delta do dedo a 1:1 e o ganho é
        aplicado uma vez.
        """
        cfg = Config()
        mouse = FakeMouse()
        mouse.screen_w, mouse.screen_h = 1366, 768
        cfg.remote_move_gain = 3.0
        srv = RemoteServer(cfg, mouse)
        pad_w = 330

        for _ in range(pad_w):
            srv._handle("move", {"dx": 1, "dy": 0})

        # 1 varredura = pad_w x ganho. Com o ganho duplicado dava 1780.
        assert mouse.mouse.position[0] == pad_w * 3
        assert mouse.mouse.position[0] < mouse.screen_w, (
            "uma varredura do pad já atravessa o ecrã: o ganho está a ser "
            "aplicado mais do que uma vez"
        )


class TestToqueAbsoluto:
    """O toque é ABSOLUTO: carrega no ponto tocado, não onde o cursor estiver.

    Esta é a regressão do sintoma que o utilizador reportou ("o clique no
    telefone continua a saltar"). Com o toque relativo, o clique dependia de o
    cursor já estar no sítio certo — e o cursor só lá chega se o ganho estiver
    certo. Com o toque absoluto não há mira: o ponto tocado é o ponto do
    clique."""

    def _srv(self, cfg=None, mouse=None):
        cfg = cfg or Config()
        cfg.remote_code = "123456"
        mouse = mouse or FakeMouse()
        return RemoteServer(cfg, mouse), mouse

    def test_toque_cai_no_ponto_tocado(self):
        srv, mouse = self._srv()
        mouse.mouse.position = (1000, 130)

        srv._handle("gesture", {"event": "tap", "x": 0.25, "y": 0.4})

        esperado = (int(0.25 * (mouse.screen_w - 1)), int(0.4 * (mouse.screen_h - 1)))
        assert mouse.click_at == [("left", esperado)], (
            f"o clique carregou em {mouse.click_at}, esperava {esperado}"
        )

    def test_toque_cai_no_ponto_tocado_mesmo_com_movimento_relativo_pendente(
        self,
    ):
        """O caso que falha na vida real: o utilizador anda a arrastar o
        cursor e carrega. Todo o movimento relativo anterior tem de estar
        aplicado ANTES do clique — o clique assenta no ponto tocado e o cursor
        não fica a andar depois dele.

        Do lado do telefone isto é o `flushMoves` antes de cada comando
        discreto; do lado do PC é a ordem de chegada. O teste fixa o
        resultado, que é o que o utilizador vê."""
        cfg = Config()
        cfg.remote_move_gain = 3.0
        srv, mouse = self._srv(cfg)
        mouse.mouse.position = (100, 100)

        for _ in range(20):
            srv._handle("move", {"dx": 1, "dy": 0})
        antes_do_toque = mouse.mouse.position
        srv._handle("gesture", {"event": "tap", "x": 0.75, "y": 0.75})

        esperado = (int(0.75 * (mouse.screen_w - 1)), int(0.75 * (mouse.screen_h - 1)))
        assert mouse.click_at == [("left", esperado)]
        # O cursor não pode ter ficado a meia caminho: ou está no ponto do
        # clique, ou no fim do movimento. Nunca nos dois.
        assert mouse.mouse.position == esperado
        assert antes_do_toque == (100 + 20 * 3, 100)

    def test_toque_nos_quatro_cantos(self):
        """Precisão nas pontas: o clamp a [0..1] e a conversão para píxeis têm
        de acertar também em (0,0) e (1,1), que é onde o dedo vai quando o
        alvo é um botão no canto."""
        srv, mouse = self._srv()
        for x, y in ((0.0, 0.0), (1.0, 1.0), (0.0, 1.0), (1.0, 0.0)):
            mouse.click_at.clear()
            srv._handle("gesture", {"event": "tap", "x": x, "y": y})
            assert mouse.click_at == [
                ("left", (int(x * (mouse.screen_w - 1)), int(y * (mouse.screen_h - 1))))
            ]

    def test_toque_com_pedrao_no_ganho_continua_exacto(self):
        """O ganho é o que fazia o cursor passar do ponto; o clique absoluto
        não pode depender dele. Com o ganho no extremo, o ponto tocado tem de
        dar a mesma coordenada."""
        for ganho in (1.0, 3.0, 8.0):
            cfg = Config()
            cfg.remote_move_gain = ganho
            srv, mouse = self._srv(cfg)
            for _ in range(50):
                srv._handle("move", {"dx": 7, "dy": -3})
            mouse.click_at.clear()
            srv._handle("gesture", {"event": "tap", "x": 0.3, "y": 0.6})
            assert mouse.click_at == [
                ("left", (int(0.3 * (mouse.screen_w - 1)), int(0.6 * (mouse.screen_h - 1))))
            ], f"ganho {ganho} deslocou o clique"


@pytest.mark.websocket
def test_auth_and_commands_over_websocket():
    cfg = Config()
    cfg.remote_bind = "127.0.0.1"
    cfg.remote_port = 0
    cfg.remote_code = "123456"
    # Ganho a 1: este teste é sobre o protocolo e o auth, não sobre a
    # velocidade do touchpad (ver TestTouchpadRelativo).
    cfg.remote_move_gain = 1.0
    mouse = FakeMouse()
    srv = RemoteServer(cfg, mouse)
    assert srv.start() is True
    try:
        port = srv.bound_port
        assert port, "servidor sem porta"

        async def bad_auth():
            from websockets.asyncio.client import connect

            try:
                async with connect(f"ws://127.0.0.1:{port}") as ws:
                    await ws.send(json.dumps({"cmd": "auth", "code": "000000"}))
                    reply = json.loads(await asyncio.wait_for(ws.recv(), 3))
                    assert reply.get("ok") is False
            except Exception:
                # a ligação é fechada após auth falhada
                pass

        asyncio.run(bad_auth())

        async def good_flow():
            from websockets.asyncio.client import connect

            async with connect(f"ws://127.0.0.1:{port}") as ws:
                await ws.send(json.dumps({"cmd": "auth", "code": "123456"}))
                reply = json.loads(await asyncio.wait_for(ws.recv(), 3))
                assert reply.get("ok") is True
                assert reply.get("w") == 1920

                await ws.send(json.dumps({"cmd": "move", "dx": 5, "dy": 6}))
                assert json.loads(await asyncio.wait_for(ws.recv(), 3)).get("ok") is True

                await ws.send(json.dumps({"cmd": "ping"}))
                reply = json.loads(await asyncio.wait_for(ws.recv(), 3))
                assert reply.get("pong") is True

        asyncio.run(good_flow())
        assert mouse.moves == [(5, 6)]
    finally:
        srv.stop()


# ── Arbitro remoto vs. motor da câmara ──────────────────────────────────

class TestRemoteArbiter:
    """O motor da câmara e o telemóvel disputam o mesmo rato.

    Sem arbitragem, a câmara mexe no cursor enquanto o telemóvel clica, e o
    clique parece saltar.
    """

    def test_comando_do_telemovel_pausa_a_camara(self):
        state = {"paused": False}
        arb = RemoteArbiter(state, hold_s=1.5)
        arb.note()
        assert state["paused"] is True
        assert arb.holding is True

    def test_rato_volta_a_camara_quando_o_telemovel_cala(self, monkeypatch):
        state = {"paused": False}
        arb = RemoteArbiter(state, hold_s=1.5)
        clock = {"t": 100.0}
        monkeypatch.setattr("core.remote.time.monotonic", lambda: clock["t"])

        arb.note()
        clock["t"] += 1.0
        arb.tick()
        assert state["paused"] is True, "ainda dentro da janela, não pode devolver"

        clock["t"] += 1.0  # 2.0 s no total, acima de hold_s
        arb.tick()
        assert state["paused"] is False
        assert arb.holding is False

    def test_comandos_successivos_estendem_a_janela(self, monkeypatch):
        state = {"paused": False}
        arb = RemoteArbiter(state, hold_s=1.5)
        clock = {"t": 100.0}
        monkeypatch.setattr("core.remote.time.monotonic", lambda: clock["t"])

        arb.note()
        for _ in range(5):  # um comando por segundo durante 5 s
            clock["t"] += 1.0
            arb.note()
            arb.tick()
        assert state["paused"] is True, "uso contínuo tem de manter a câmara calada"

        clock["t"] += 2.0
        arb.tick()
        assert state["paused"] is False

    def test_nao_toca_na_pausa_do_utilizador(self):
        state = {"paused": True}
        arb = RemoteArbiter(state, hold_s=1.5)
        arb.note()
        assert state["paused"] is True
        assert arb.holding is False, "a pausa é do utilizador, não do árbitro"

    def test_nao_reverte_um_despauso_feito_durante_a_janela(self, monkeypatch):
        state = {"paused": False}
        arb = RemoteArbiter(state, hold_s=1.5)
        clock = {"t": 100.0}
        monkeypatch.setattr("core.remote.time.monotonic", lambda: clock["t"])

        arb.note()
        state["paused"] = False  # utilizador primiu espaço durante a janela
        clock["t"] += 5.0
        arb.tick()
        assert state["paused"] is False
        assert arb.holding is False

    def test_on_activity_chama_o_arbitro(self):
        state = {"paused": False}
        arb = RemoteArbiter(state, hold_s=1.5)
        srv = RemoteServer(Config(), FakeMouse())
        srv.on_activity = arb.note
        srv._note_activity()
        assert arb.holding is True
        assert state["paused"] is True, "o comando tem de calar a câmara"

    def test_on_activity_ausente_nao_parte_nada(self):
        srv = RemoteServer(Config(), FakeMouse())
        assert srv.on_activity is None
        srv._note_activity()  # não pode rebentar

    def test_callback_que_falha_nao_derruba_o_comando(self):
        srv = RemoteServer(Config(), FakeMouse())

        def boom():
            raise RuntimeError("falhou")

        srv.on_activity = boom
        srv._note_activity()  # a excepção é engolida e registada em debug

    def test_arbitro_cala_a_camara_durante_o_clique(self, monkeypatch):
        """Regressão: um comando atrasado não pode clicar com a câmara livre.

        A inferência da câmara segura a GIL e o comando pode ficar à espera
        mais tempo do que a janela de silêncio. Se o árbitro se armasse na
        recepção, expirava antes do clique, a câmara voltava a mexer no rato a
        meio do `move_to` + `left_click` e o clique aterrava noutro sítio.
        """
        clock = {"t": 0.0}
        monkeypatch.setattr("core.remote.time.monotonic", lambda: clock["t"])
        monkeypatch.setattr("core.engine.time.monotonic", lambda: clock["t"])

        state = {"paused": False}
        arb = RemoteArbiter(state, hold_s=1.5)
        srv = RemoteServer(Config(), FakeMouse())
        srv.on_activity = arb.note
        srv.on_command_begin = arb.begin_command
        srv.on_command_end = arb.end_command

        pausa_durante_o_clique = []

        def lento(cmd, data):
            # A câmara não rende a GIL: é o que a inferência em background
            # provoca num Raspberry Pi sobrecarregado.
            clock["t"] += 3.0
            for _ in range(10):
                arb.tick()  # a thread do motor vai libertando o rato
            pausa_durante_o_clique.append(state["paused"])
            return "TAP"

        srv._handle = lento

        conn = _FakeConnection(
            [
                {"cmd": "auth", "code": srv.code},
                {"cmd": "gesture", "event": "tap", "x": 0.5, "y": 0.5},
            ]
        )
        asyncio.run(srv._on_connect(conn))

        assert pausa_durante_o_clique == [True], (
            "a câmara tinha de estar calada no instante do clique, mesmo com o "
            "comando atrasado 3 s"
        )
