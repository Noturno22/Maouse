"""Controlo remoto por telemóvel (WebSocket).

Servidor WebSocket que permite ao app mobile Mãouse controlar o rato e o
teclado do PC via WiFi (rede local) ou Internet (IP público + porta).

Protocolo (JSON por mensagem):

  -> {"cmd": "auth", "token": "..."}              # primeira mensagem obrigatória
  <- {"ok": true, "w": 1920, "h": 1080}
  -> {"cmd": "ping"}
  <- {"ok": true, "pong": true}
  -> {"cmd": "move", "dx": 12, "dy": -4}          # movimento relativo (px)
  -> {"cmd": "move_to", "x": 0.5, "y": 0.3}       # absoluto normalizado [0..1]
  -> {"cmd": "click", "button": "left", "count": 2}
  -> {"cmd": "press", "button": "left"}           # arrastar: press + move + release
  -> {"cmd": "release", "button": "left"}
  -> {"cmd": "scroll", "dx": 0, "dy": 3}
  -> {"cmd": "key", "key": "enter"}
  -> {"cmd": "combo", "mods": ["ctrl"], "key": "c"}
  -> {"cmd": "text", "text": "ola mundo"}
  -> {"cmd": "media", "action": "volume_up"}
  -> {"cmd": "gesture", "event": "tap", "x": 0.5, "y": 0.5}   # gestos da câmara

Toda a execução corre numa thread própria com o seu event loop asyncio, de
forma a funcionar com a janela PySide6 (modo GUI) e com o preview OpenCV.
"""
import asyncio
import json
import secrets
import socket
import threading

from pynput.mouse import Button

from config import Config
from core.log import get_logger
from core.mouse_ctl import MouseCtl

log = get_logger("remote")

MAX_MSG_BYTES = 2**20


def generate_token(nbytes=8):
    """Token de autenticação aleatório (seguro)."""
    return secrets.token_hex(nbytes)


def lan_ips():
    """Endereços IPv4 desta máquina na rede local (exclui loopback)."""
    try:
        _, _, addrs = socket.gethostbyname_ex(socket.gethostname())
    except Exception:
        addrs = []
    out = []
    for addr in addrs:
        addr = str(addr)
        if not addr.startswith("127.") and ":" not in addr:
            out.append(addr)
    for addr in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
        ip = str(addr[4][0])
        if not ip.startswith("127.") and ip not in out:
            out.append(ip)
    return out


class RemoteServer:
    """Servidor WebSocket que traduz comandos do telemóvel em ações de rato/teclado."""

    def __init__(self, cfg: Config, mouse: MouseCtl):
        self._cfg = cfg
        self._mouse = mouse
        self._loop: asyncio.AbstractEventLoop | None = None
        self._server = None
        self._thread: threading.Thread | None = None
        self._clients: set = set()
        self._key_ctl = None
        self._key_mods = None
        self._drag = False

    # ── Ciclo de vida ────────────────────────────────────────────────
    def start(self):
        """Arranca o servidor em background. Devolve True se ficou ativo."""
        if self._thread and self._thread.is_alive():
            log.info("Servidor remoto já está a correr.")
            return False
        token = (self._cfg.remote_token or "").strip()
        if not token:
            token = generate_token()
            self._cfg.remote_token = token
            log.info("Token de controlo remoto gerado (visível nas definições).")
        self._thread = threading.Thread(
            target=self._thread_main, name="airmouse-remote", daemon=True
        )
        self._thread.start()
        # Espera (com limite) pelo arranque do servidor.
        deadline = 3.0
        step = 0.02
        waited = 0.0
        while self._server is None and waited < deadline:
            import time

            time.sleep(step)
            waited += step
        started = self._server is not None
        if not started:
            log.error("Falha ao arrancar o servidor remoto em :%s.", self._cfg.remote_port)
        return started

    def stop(self):
        """Fecha o servidor e liberta a porta."""
        server = self._server
        loop = self._loop
        if loop is not None and server is not None:

            async def _shutdown():
                server.close()
                await server.wait_closed()
                self._server = None
                loop.stop()

            future = asyncio.run_coroutine_threadsafe(_shutdown(), loop)
            try:
                future.result(timeout=2.0)
            except Exception as e:
                log.debug("Falha ao parar o servidor remoto: %s", e)
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def restart(self):
        """Reinicia com a configuração atual (usado ao gravar definições)."""
        self.stop()
        return self.start()

    @property
    def is_running(self):
        return self._server is not None

    @property
    def connected_count(self):
        return len(self._clients)

    @property
    def bound_port(self):
        if self._server is None:
            return None
        try:
            sock = self._server.sockets[0]
            return sock.getsockname()[1]
        except Exception:
            return None

    def _thread_main(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        try:
            loop.run_until_complete(self._amain())
        except Exception as e:
            log.error("Servidor remoto falhou: %s", e)
        try:
            loop.run_forever()
        finally:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            loop.close()
            self._loop = None

    async def _amain(self):
        from websockets.asyncio.server import serve

        host = self._cfg.remote_bind or "0.0.0.0"
        port = int(self._cfg.remote_port)
        self._server = await serve(
            self._on_connect,
            host,
            port,
            max_size=MAX_MSG_BYTES,
        )
        log.info(
            "Controlo remoto ativo em %s:%d (IPs de rede: %s; token: %s)",
            host,
            self.bound_port,
            ", ".join(lan_ips()) or "-",
            self._cfg.remote_token[:4] + "…",
        )

    # ── Ligação WebSocket ─────────────────────────────────────────────
    async def _on_connect(self, connection):
        authed = False
        self._clients.add(connection)
        try:
            log.info("Telemóvel a ligar... (%s)", connection.remote_address)
            async for raw in connection:
                if authed is False:
                    data = self._decode(raw)
                    if data.get("cmd") == "auth" and data.get("token") == self._cfg.remote_token:
                        authed = True
                        await self._send(
                            connection,
                            {"ok": True, "w": getattr(self._mouse, "screen_w", 1920),
                             "h": getattr(self._mouse, "screen_h", 1080)},
                        )
                        log.info("Telemóvel autenticado (%s).", connection.remote_address)
                    else:
                        await self._send(connection, {"ok": False, "error": "auth_required"})
                        await connection.close()
                        return
                    continue
                data = self._decode(raw)
                cmd = data.get("cmd")
                if cmd == "ping":
                    await self._send(connection, {"ok": True, "pong": True})
                    continue
                if cmd is None:
                    await self._send(connection, {"ok": False, "error": "bad_command"})
                    continue
                try:
                    note = self._handle(cmd, data)
                except Exception as e:
                    log.debug("Comando %s falhou: %s", cmd, e)
                    await self._send(connection, {"ok": False, "error": str(e)})
                    continue
                await self._send(connection, {"ok": True, "note": note})
        except Exception as e:
            log.debug("Ligação remota terminada: %s", e)
        finally:
            self._clients.discard(connection)

    @staticmethod
    def _decode(raw):
        if isinstance(raw, (bytes, bytearray)):
            try:
                raw = bytes(raw).decode("utf-8", errors="replace")
            except Exception:
                raw = ""
        try:
            return json.loads(raw)
        except Exception:
            return {}

    @staticmethod
    async def _send(connection, payload):
        try:
            await connection.send(json.dumps(payload))
        except Exception as e:
            log.debug("Falha ao responder ao telemóvel: %s", e)

    # ── Despacho de comandos ─────────────────────────────────────────
    def _handle(self, cmd, data):
        mouse = self._mouse
        if cmd == "move":
            mouse.move_by(self._int(data, "dx"), self._int(data, "dy"))
            return "MOVE"
        if cmd == "move_to":
            self._move_to(data)
            return "MOVE_TO"
        if cmd == "click":
            button = str(data.get("button", "left")).lower()
            count = max(1, min(self._int(data, "count", 1), 4))
            self._click(button, count)
            return f"CLICK {button.upper()} x{count}"
        if cmd == "press":
            self._press(str(data.get("button", "left")).lower(), hold=True)
            return "PRESS"
        if cmd == "release":
            self._press(str(data.get("button", "left")).lower(), hold=False)
            return "RELEASE"
        if cmd == "scroll":
            return self._scroll(data)
        if cmd == "key":
            self._tap_key(str(data.get("key", "")))
            return "KEY"
        if cmd == "combo":
            self._combo(data)
            return "COMBO"
        if cmd == "text":
            self._type_text(str(data.get("text", "")))
            return "TEXT"
        if cmd == "media":
            return self._media(str(data.get("action", "")))
        if cmd == "gesture":
            return self._gesture(data)
        raise ValueError(f"cmd_desconhecido:{cmd}")

    def _int(self, data, key, default=0):
        try:
            return int(data.get(key, default))
        except (TypeError, ValueError):
            return default

    def _float(self, data, key, default=0.0):
        try:
            return float(data.get(key, default))
        except (TypeError, ValueError):
            return default

    def _move_to(self, data):
        x = min(max(self._float(data, "x", 0.0), 0.0), 1.0)
        y = min(max(self._float(data, "y", 0.0), 0.0), 1.0)
        w = max(getattr(self._mouse, "screen_w", 1920) - 1, 1)
        h = max(getattr(self._mouse, "screen_h", 1080) - 1, 1)
        self._mouse.mouse.position = (int(x * w), int(y * h))

    def _click(self, button, count):
        mouse = self._mouse
        if button in ("left", "lmb"):
            for _ in range(count):
                mouse.left_click()
        elif button in ("right", "rmb"):
            for _ in range(count):
                mouse.right_click()
        elif button in ("middle", "mmb"):
            if count > 1:
                for _ in range(count):
                    mouse.mouse.position = mouse.mouse.position
                    mouse.mouse.click(Button.middle)
            else:
                mouse.mouse.click(Button.middle)
        else:
            raise ValueError(f"botao_desconhecido:{button}")

    def _press(self, button, hold):
        mouse = self._mouse
        if button in ("left", "lmb"):
            if hold:
                mouse.press_left()
            else:
                mouse.release_left()
        elif button in ("right", "rmb"):
            if hold:
                self._mouse.mouse.press(Button.right)
            else:
                self._mouse.mouse.release(Button.right)
        elif button in ("middle", "mmb"):
            if hold:
                self._mouse.mouse.press(Button.middle)
            else:
                self._mouse.mouse.release(Button.middle)
        else:
            raise ValueError(f"botao_desconhecido:{button}")

    def _scroll(self, data):
        dx = self._int(data, "dx")
        dy = self._int(data, "dy")
        if dy:
            self._mouse.scroll(dy)
        if dx:
            self._mouse.mouse.scroll(int(dx), 0)
        return "SCROLL"

    @property
    def keyboard(self):
        if self._key_ctl is None:
            from pynput.keyboard import Controller as KeyboardController

            self._key_ctl = KeyboardController()
        return self._key_ctl

    @property
    def pynput_keys(self):
        if self._key_mods is None:
            from pynput.keyboard import Key

            map_names = {
                "ctrl": Key.ctrl_l, "ctrl_l": Key.ctrl_l, "ctrl_r": Key.ctrl_r,
                "alt": Key.alt_l, "alt_l": Key.alt_l, "alt_r": Key.alt_r,
                "shift": Key.shift_l, "shift_l": Key.shift_l, "shift_r": Key.shift_r,
                "cmd": Key.cmd, "win": Key.cmd,
                "tab": Key.tab, "enter": Key.enter, "return": Key.enter, "esc": Key.esc,
                "escape": Key.esc, "space": Key.space, "delete": Key.delete,
                "del": Key.delete, "backspace": Key.backspace, "home": Key.home,
                "end": Key.end, "pageup": Key.page_up, "pagedown": Key.page_down,
                "pgup": Key.page_up, "pgdn": Key.page_down,
                "up": Key.up, "down": Key.down, "left": Key.left, "right": Key.right,
                "f1": Key.f1, "f2": Key.f2, "f3": Key.f3, "f4": Key.f4,
                "f5": Key.f5, "f6": Key.f6, "f7": Key.f7, "f8": Key.f8,
                "f9": Key.f9, "f10": Key.f10, "f11": Key.f11, "f12": Key.f12,
                "back": Key.backspace, "caps": Key.caps_lock, "capslock": Key.caps_lock,
            }
            self._key_mods = map_names
        return self._key_mods

    def _resolve_key(self, name):
        name = str(name or "").strip()
        if not name:
            raise ValueError("tecla_vazia")
        key = self.pynput_keys.get(name.lower())
        if key is not None:
            return key
        if len(name) == 1:
            return name
        raise ValueError(f"tecla_desconhecida:{name}")

    def _tap_key(self, name):
        key = self._resolve_key(name)
        kb = self.keyboard
        kb.press(key)
        kb.release(key)

    def _combo(self, data):
        mods = data.get("mods") or []
        if isinstance(mods, str):
            mods = [mods]
        key = self._resolve_key(data.get("key", ""))
        held = []
        for m in mods:
            r = self._resolve_key(str(m))
            self.keyboard.press(r)
            held.append(r)
        key_held = False
        try:
            self.keyboard.press(key)
            key_held = True
            import time as _t

            _t.sleep(0.04)
            self.keyboard.release(key)
            key_held = False
        finally:
            if key_held:
                self.keyboard.release(key)
            for r in reversed(held):
                self.keyboard.release(r)

    def _type_text(self, text):
        if not text:
            return
        try:
            self.keyboard.type(text)
        except Exception:
            for ch in text:
                self._tap_key(ch)

    def _media(self, action):
        from pynput.keyboard import Key

        map_actions = {
            "volume_up": Key.media_volume_up,
            "volume_down": Key.media_volume_down,
            "mute": Key.media_volume_mute,
            "play_pause": Key.media_play_pause,
            "next": Key.media_next,
            "prev": Key.media_previous,
            "stop": Key.media_stop,
        }
        key = map_actions.get(action)
        if key is None:
            raise ValueError(f"acao_media_desconhecida:{action}")
        kb = self.keyboard
        kb.press(key)
        kb.release(key)
        return f"MEDIA {action.upper()}"

    # ── Gestos da câmara do telemóvel → PC ───────────────────────────
    def _gesture(self, data):
        event = str(data.get("event", ""))
        mouse = self._mouse
        if data.get("x") is not None and data.get("y") is not None:
            self._move_to(data)
        if event == "tap":
            mouse.left_click()
            return "TAP"
        if event == "right_click":
            mouse.right_click()
            return "RIGHT"
        if event == "left_down":
            if not getattr(self, "_drag", False):
                mouse.press_left()
                self._drag = True
            return "DRAG ON"
        if event == "left_up":
            if getattr(self, "_drag", False):
                mouse.release_left()
                self._drag = False
            return "DRAG OFF"
        if event == "scroll":
            mouse.scroll(self._int(data, "value"))
            return "SCROLL"
        if event == "volume":
            val = self._int(data, "value")
            return self._media("volume_up" if val >= 0 else "volume_down")
        if event == "play_pause":
            return self._media("play_pause")
        if event == "copy":
            self._combo({"mods": ["ctrl"], "key": "c"})
            return "COPY"
        if event == "paste":
            self._combo({"mods": ["ctrl"], "key": "v"})
            return "PASTE"
        if event == "minimize":
            self._combo({"mods": ["win"], "key": "d"})
            return "MINIMIZE"
        raise ValueError(f"gesto_desconhecido:{event}")
