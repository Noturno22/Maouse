"""Testes do controlo remoto por telemóvel (core.remote)."""
import asyncio
import json

import pytest

from config import Config
from core.remote import RemoteServer, generate_token, lan_ips


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

    def move_by(self, dx, dy):
        self.moves.append((dx, dy))

    def left_click(self):
        self.clicks.append("left")

    def right_click(self):
        self.clicks.append("right")

    def press_left(self):
        self.pressed.append("left")

    def release_left(self):
        self.released.append("left")

    def scroll(self, dy):
        self.scrolled.append(dy)


def test_generate_token_is_unique():
    a = generate_token()
    b = generate_token()
    assert a and b
    assert len(a) >= 8
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
    cfg.remote_token = "tok"
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
    cfg.remote_token = "tok"
    mouse = FakeMouse()
    srv = RemoteServer(cfg, mouse)

    srv._handle("move_to", {"x": 0.5, "y": 0.25})
    assert mouse.mouse.position == (959, 269)

    srv._handle("move_to", {"x": 5.0, "y": -1.0})
    assert mouse.mouse.position == (1919, 0)


def test_dispatch_unknown_command_raises():
    cfg = Config()
    cfg.remote_token = "tok"
    srv = RemoteServer(cfg, FakeMouse())
    with pytest.raises(ValueError):
        srv._handle("coiso", {})


@pytest.mark.websocket
def test_auth_and_commands_over_websocket():
    cfg = Config()
    cfg.remote_bind = "127.0.0.1"
    cfg.remote_port = 0
    cfg.remote_token = "segredo123"
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
                    await ws.send(json.dumps({"cmd": "auth", "token": "errado"}))
                    reply = json.loads(await asyncio.wait_for(ws.recv(), 3))
                    assert reply.get("ok") is False
            except Exception:
                # a ligação é fechada após auth falhada
                pass

        asyncio.run(bad_auth())

        async def good_flow():
            from websockets.asyncio.client import connect

            async with connect(f"ws://127.0.0.1:{port}") as ws:
                await ws.send(json.dumps({"cmd": "auth", "token": "segredo123"}))
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
