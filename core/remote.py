"""Controlo remoto por telemóvel (WebSocket).

Servidor WebSocket que permite ao app mobile Mãouse controlar o rato e o
teclado do PC via WiFi (rede local) ou Internet (IP público + porta).

Protocolo (JSON por mensagem):

-> {"cmd": "auth", "code": "123456", "lease": "..."}  # 1ª msg obrigatória
  <- {"cmd": "auth", "ok": true, "w": 1920, "h": 1080}
  <- {"cmd": "auth", "ok": false, "error": "auth_required"}   # código errado
  <- {"cmd": "auth", "ok": false, "error": "auth_locked"}     # muitas tentativas
  <- {"cmd": "auth", "ok": false, "error": "pro_required"}    # sem lease Pro válida

  O `code` é o segredo de emparelhamento definido no PC (6 dígitos); o nome
  antigo `token` ainda é aceite. O `lease` é o JWT ES256 que o license-server
  emite para o telemóvel (tier `mobile_pro`). O gate exige os dois, e pela ordem
  certa: código errado ou muitas tentativas dão `auth_required`/`auth_locked`;
  só depois de o código passar é a lease verificada, e lease ausente, expirada ou
  de tier não pago dá `pro_required`. Em qualquer caso a ligação é fechada. Ver
  `core.licensing.verify_remote_entitlement`.
  -> {"cmd": "ping"}
  <- {"ok": true, "pong": true}
  -> {"cmd": "move", "dx": 12, "dy": -4}          # relativo, com remote_move_gain
  -> {"cmd": "move_to", "x": 0.5, "y": 0.3}       # absoluto normalizado [0..1]
  -> {"cmd": "click", "button": "left", "count": 2}
  -> {"cmd": "press", "button": "left"}           # arrastar: press + move + release
  -> {"cmd": "release", "button": "left"}
  -> {"cmd": "scroll", "dx": 0, "dy": 3}
  -> {"cmd": "key", "key": "enter"}
  -> {"cmd": "combo", "mods": ["ctrl"], "key": "c"}
  -> {"cmd": "text", "text": "ola mundo"}
  -> {"cmd": "media", "action": "volume_up"}
  -> {"cmd": "gesture", "event": "tap", "x": .5, "y": .5}  # salto absoluto + clique

O touchpad do app é HÍBRIDO, e é o cliente que decide: o arrasto de um dedo é
relativo (``move``, com o ganho em ``remote_move_gain``) e o toque é ABSOLUTO
(``gesture tap`` com ``x``/``y``, que faz ``move_to`` e clica no mesmo comando).
O toque tem de ser absoluto porque é a única forma de o clique não depender de
uma mira: com o toque relativo, acertar o ponto passa a depender de acertar o
ganho, e qualquer erro ai aparece ao utilizador como "o clique salta".
``x``/``y`` num ``gesture`` são opcionais; sem eles o gesto clica onde o cursor
está, que é o que os clientes que enviam só o evento preferem.

A credencial é um **código de 6 dígitos** que o utilizador lê nas definições do
PC e escreve no telemóvel, em vez dos 16 caracteres hexadecimais que eram
copiados. Trocar 64 bits por 6 dígitos é trocar força por memória de escrever à
mão, e traz três obrigações que o token longo não tinha — porque um segredo curto
que se pode adivinhar é um segredo curto a adivinhar:

* comparar em **tempo constante** (:func:`hmac.compare_digest`), não com ``==``;
* **contar tentativas** por origem e bloquear quem insiste (:class:`AuthLimiter`),
  porque 10^6 tentativas sem limite são um número, não uma barreira;
* e **não escrever dígitos no log** — o arranque já registava os primeiros 4
  caracteres do token, que num código de 6 são dois terços do segredo.

Toda a execução corre numa thread própria com o seu event loop asyncio, de
forma a funcionar com a janela PySide6 (modo GUI) e com o preview OpenCV.
"""
import asyncio
import hmac
import json
import re
import secrets
import socket
import threading
import time

try:
    from pynput.mouse import Button
except Exception:
    Button = None

from config import Config
from core.licensing import verify_remote_entitlement
from core.log import get_logger, trace
from core.mouse_ctl import MouseCtl

log = get_logger("remote")

MAX_MSG_BYTES = 2**20

# O código de emparelhamento: 6 dígitos, sempre, com zeros à esquerda. São
# 10^6 ≈ 19,9 bits — de propósito, porque é o que cabe em seis teclas e num
# ecrã que o utilizador lê de relance. O que segura a troca está em
# `AuthLimiter`, não na entropia.
CODE_LEN = 6
CODE_RE = re.compile(rf"\d{{{CODE_LEN}}}")

# Tentativas de `auth` erradas por origem, e o que acontece a quem passa
# disto. A janela conta as tentativas que se acercam: um atacante que espaça
# as tentativas não ganha nada, porque a janela é contígua.
AUTH_MAX_FAILURES = 5
AUTH_WINDOW_S = 60.0
AUTH_LOCK_S = 300.0
# Tecto de origens lembradas. Sem isto, um scanner a abrir ligações de
# milhares de IPs deixava o dicionário crescer sem limite — e um dicionário
# que cresce é uma porta aberta, não uma proteção.
AUTH_MAX_SOURCES = 256


def generate_code() -> str:
    """Código de emparelhamento de 6 dígitos (aleatório e seguro)."""
    return f"{secrets.randbelow(10 ** CODE_LEN):0{CODE_LEN}d}"


def normalise_code(value) -> str:
    """O código como o utilizador o escreve, já normalizado.

    Tira espaços e traços, porque o código é lido de um ecrã e copiado com o
    dedo para o teclado — e `"123 456"` tem de ser o mesmo código que
    `"123456"`. Tudo o resto fica como está: um código com uma letra dentro é
    inválido, e limpá-lo para o transformar em válido seria aceitar um valor
    que o utilizador não introduziu.
    """
    text = str(value if value is not None else "").strip()
    return "".join(ch for ch in text if ch not in " -")


def valid_code(value) -> bool:
    """True se ``value`` é um código de emparelhamento bem formado."""
    return bool(CODE_RE.fullmatch(normalise_code(value)))


def _source_of(connection) -> str:
    """A chave de contagem de tentativas de uma ligação.

    Só o **IP**, nunca o par ``(ip, porta)``: a porta de origem muda a cada
    ligação, e um limitador com a porta na chave contaria cada tentativa como
    se fosse a primeira — que é exactamente o que um script que abre uma
    ligação por tentativa precisa.
    """
    addr = getattr(connection, "remote_address", None)
    if isinstance(addr, (tuple, list)) and addr:
        return str(addr[0])
    return str(addr or "?")


class AuthLimiter:
    """Conta ``auth`` errados por origem e bloqueia quem insiste.

    Sem isto, um código de 6 dígitos é um alvo de 10^6 tentativas e nada mais:
    a barra não é o segredo, é o número de vezes que se pode chutar. O
    bloqueio é por origem e temporário — o telemóvel do próprio utilizador que
    wrote o código três vezes seguidas fica de fora cinco minutos, que é o
    custo honesto de um limite que existe para ser sentido.

    **Uma instância é partilhada pelos dois transportes.** O `RemoteServer`
    é-o dono, e o BLE vai buscá-la: um atacante não ganha por trocar de
    caminho, e um utilizador que se enganou três vezes no WiFi não fica de
    repente com outra chance no Bluetooth. Isso obriga a um `Lock` — o
    WebSocket vive no loop asyncio e o BLE no loop do BlueZ, que são duas
    threads diferentes.

    O tempo vem de ``now``, injetável, para os testes não terem de esperar
    cinco minutos para provar que o bloqueio expira.
    """

    def __init__(
        self,
        max_failures: int = AUTH_MAX_FAILURES,
        window_s: float = AUTH_WINDOW_S,
        lock_s: float = AUTH_LOCK_S,
        now=None,
    ):
        self._max = int(max_failures)
        self._window = float(window_s)
        self._lock_s = float(lock_s)
        self._now = now or time.monotonic
        self._fails: dict[str, list[float]] = {}
        self._locked: dict[str, float] = {}
        self._guard = threading.Lock()

    def locked_for(self, source: str) -> float:
        """Segundos que faltam para esta origem desbloquear (0 se não está)."""
        with self._guard:
            self._prune()
            until = self._locked.get(source)
            if until is None:
                return 0.0
            restante = until - self._now()
            if restante <= 0:
                self._locked.pop(source, None)
                return 0.0
            return restante

    def allow(self, source: str) -> bool:
        """Esta origem pode tentar agora?"""
        return self.locked_for(source) <= 0.0

    def fail(self, source: str) -> bool:
        """Conta uma falha. Devolve True se foi esta que fechou a porta."""
        with self._guard:
            agora = self._now()
            self._prune()
            vezes = [t for t in self._fails.get(source, ()) if agora - t < self._window]
            vezes.append(agora)
            self._fails[source] = vezes
            if len(vezes) >= self._max:
                self._locked[source] = agora + self._lock_s
                self._fails.pop(source, None)
                return True
            return False

    def success(self, source: str) -> None:
        """Autenticou: as falhas desta origem deixam de contar."""
        with self._guard:
            self._fails.pop(source, None)

    def _prune(self) -> None:
        """Deita fora o que já não pode bloquear ninguém."""
        agora = self._now()
        for origem in [k for k, v in self._locked.items() if v <= agora]:
            self._locked.pop(origem, None)
        for origem in list(self._fails):
            if agora - self._fails[origem][-1] >= self._window:
                self._fails.pop(origem, None)
        # Tecto duro, para um scanner não transformar a proteção em dívida de
        # memória. Limpar tudo é preferível a manter entradas inúteis: quem
        # estava a tentar chutar recomeça a contar, que é o que a proteção já
        # não conseguia travar.
        if len(self._fails) + len(self._locked) > AUTH_MAX_SOURCES:
            log.warning(
                "Limite de tentativas: mais de %d origens em memória, "
                "contadores esquecidos.", AUTH_MAX_SOURCES,
            )
            self._fails.clear()
            self._locked.clear()


def _usable_ip(ip):
    ip = str(ip or "")
    return bool(
        ip
        and not ip.startswith("127.")
        and not ip.startswith("169.254.")
        and not ip.startswith("0.")
        and ":" not in ip
    )


def lan_ips():
    """Endereços IPv4 desta máquina na rede local (exclui loopback)."""
    out = []
    try:
        _, _, addrs = socket.gethostbyname_ex(socket.gethostname())
        for addr in addrs:
            if _usable_ip(addr) and addr not in out:
                out.append(addr)
    except Exception:
        pass
    try:
        for addr in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = str(addr[4][0])
            if _usable_ip(ip) and ip not in out:
                out.append(ip)
    except Exception:
        pass
    # Linux/macOS: interfaces reais (ignora docker/veth/br-/pontes virtuais),
    # para o utilizador só ver o IP da rede local.
    try:
        import subprocess

        proc = subprocess.run(
            ["ip", "-o", "-4", "addr", "show"],
            capture_output=True, text=True, timeout=3,
        )
        for line in proc.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 4:
                iface = parts[1]
                ip = parts[3].split("/", 1)[0]
                if iface.startswith(
                    ("docker", "br-", "veth", "virbr", "vboxnet", "podman", "lo")
                ):
                    continue
                if _usable_ip(ip) and ip not in out:
                    out.append(ip)
    except Exception:
        pass
    # Fallback: IP da rota por omissão (funciona mesmo sem hostname resolvível).
    if not out:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                if _usable_ip(ip) and ip not in out:
                    out.append(ip)
            finally:
                s.close()
        except Exception:
            pass
    return out


class RemoteArbiter:
    """Arbitra entre o controlo remoto e o motor de rastreamento da mão.

    Os dois mexem no mesmo rato. Sem coordenação, o motor da câmara continua a
    mover o cursor enquanto o telemóvel clica, e o clique parece saltar: o rato
    vai para o ponto certo, carrega, e é logo arrastado para outro sítio — ou
    para o lado errado, se a câmara ganhar a corrida.

    Cada comando de um telemóvel autenticado silencia a câmara durante
    ``hold_s``; passado esse tempo sem comandos, o rato volta para a câmara.
    Se o utilizador tinha pausado o motor por si (barra de espaço), o árbitro
    não toca nesse estado.
    """

    def __init__(self, state: dict, hold_s: float = 1.5):
        self._state = state
        self._hold = float(hold_s)
        self._deadline = 0.0
        self._holding = False
        self._in_flight = 0

    def begin_command(self) -> None:
        """Marca o início da execução de um comando.

        A inferência da câmara segura a GIL, por isso um comando pode ficar
        bloqueado mais tempo do que ``hold_s`` — em aparelho sobrecarregado
        chega a passar de um segundo. Sem esta marca, a janela de silêncio
        expirava a meio da execução, a câmara reabria o rato e o clique
        aterrava onde ela tivesse deixado o cursor, e não onde o dedo tocou.
        """
        self._in_flight += 1
        if self._in_flight == 1:
            self.note()

    def end_command(self) -> None:
        """O comando terminou de executar; volta a contar ``hold_s`` a partir
        de agora, que é quando o clique já aconteceu."""
        if self._in_flight > 0:
            self._in_flight -= 1
        self.note()

    def note(self) -> None:
        """Um comando chegou do telemóvel: cede o rato à câmara por ``hold_s``."""
        now = time.monotonic()
        if self._holding:
            self._deadline = now + self._hold
            trace("ARBITER prolonga por mais %.2fs", self._hold)
            return
        if self._state.get("paused"):
            trace("ARBITER ignora: ja pausado pelo utilizador")
            # Pausado pelo utilizador — não tomar conta do estado.
            return
        self._state["paused"] = True
        self._holding = True
        self._deadline = now + self._hold
        trace("ARBITER toma o rato por %.2fs (pausa a camara)", self._hold)
        self._drain_backlog()

    def _drain_backlog(self) -> None:
        """Esvazia o movimento que a câmara já tinha enfileirado.

        Pausar a câmara só impede que ela decida mais movimentos: o emissor
        continua a despejar, a ~180 Hz, o que já estava na fila (até
        ``max_pending_px``). Sem esvaziar, o rato continua a andar durante o
        silêncio do telemóvel e volta a arrastar o clique.
        """
        emitter = self._state.get("emitter")
        if emitter is None:
            return
        try:
            emitter.clear()
        except Exception as e:
            log.debug("Esvaziar a fila do emissor falhou: %s", e)

    def tick(self) -> None:
        """Devolve o rato à câmara quando o telemóvel fica em silêncio.

        Só repõe se ``paused`` continuar a ser o valor que o árbitro pôs: se o
        utilizador mexer no estado entretanto, deixa-o em paz.
        """
        if self._in_flight > 0:
            # Comando ainda a executar: a câmara fica calada até ele terminar,
            # por mais tempo que a GIL segura o comando.
            return
        if self._holding and time.monotonic() >= self._deadline:
            if self._state.get("paused"):
                self._state["paused"] = False
            self._holding = False
            trace("ARBITER devolve o rato a camara")

    @property
    def holding(self) -> bool:
        return self._holding


class RemoteServer:
    """Servidor WebSocket que traduz comandos do telemóvel em ações de rato/teclado."""

    def __init__(self, cfg: Config, mouse: MouseCtl, on_activity=None):
        self._cfg = cfg
        self._mouse = mouse
        # Chamado a cada comando de um telemóvel autenticado, para o motor de
        # rastreamento da mão ceder o rato enquanto o telemóvel está a ser usado.
        self.on_activity = on_activity
        # Par begin/end em volta da execução de cada comando, para a câmara
        # ficar calada mesmo que o comando fique bloqueado a meio da execução.
        self.on_command_begin = None
        self.on_command_end = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._server = None
        self._thread: threading.Thread | None = None
        self._clients: set = set()
        self._key_ctl = None
        self._key_mods = None
        self._drag = False
        self._held: set[str] = set()
        # Resto fraccionário do movimento relativo (ver ``_move_rel``).
        self._mfx = 0.0
        self._mfy = 0.0
        # O código de emparelhamento e o limitador de tentativas. O limitador é
        # o mesmo objecto que o BLE vai usar (ver ``core/remote_ble.py``), e é
        # por isso que existe um atributo com nome: trocar de transporte não
        # pode dar ao utilizador mais tentativas do que as que já gastou.
        self._code = ""
        self._limiter = AuthLimiter()

    @property
    def code(self) -> str:
        """O código de 6 dígitos activo (gerado no primeiro uso, se falta)."""
        if not self._code:
            self._ensure_code()
        return self._code

    @property
    def limiter(self) -> AuthLimiter:
        """O limitador de tentativas partilhado com o BLE."""
        return self._limiter

    def _ensure_code(self) -> str:
        """Garante que há um código válido; cria um se não houver.

        Um ``settings.json`` copiado de antes do código de 6 dígitos traz um
        ``remote_token`` de 16 hex, que deixa de autenticar. Gerar um novo é a
        única coisa honesta a fazer: aceitar o antigo seria manter duas
        credenciais para o utilizador gerir, e recusar a ligação sem dizer
        nada seria o pior dos dois.
        """
        actual = normalise_code(getattr(self._cfg, "remote_code", ""))
        if valid_code(actual):
            self._code = actual
            return self._code
        self._code = generate_code()
        try:
            self._cfg.remote_code = self._code
        except Exception as e:
            log.debug("Não foi possível guardar o código novo: %s", e)
        log.info(
            "Código de emparelhamento de %d dígitos pronto "
            "(nas definições do PC, em «Controlo remoto»).",
            CODE_LEN,
        )
        return self._code

    def _code_ok(self, candidate) -> bool:
        """Compara o código em tempo constante.

        ``==`` devolve logo que os primeiros caracteres diferem, e o tempo que
        demora a responder passa a dizer quanto do segredo já acertou. Com 6
        dígitos isso é meio segredo por tentativa.
        """
        return hmac.compare_digest(normalise_code(candidate), self.code)

    def _auth_state(self, candidate, source: str) -> str:
        """``"ok"``, ``"locked"`` ou ``"bad"`` para uma tentativa de `auth`.

        O limitador é consultado **antes** da comparação, e não depois: um
        bloqueio tem de ser um bloqueio, mesmo que o código venha certo — e
        verificar primeiro o limite é o que impede um atacante de gastar
        tentativas durante os cinco minutos de bloqueio.
        """
        if not self._limiter.allow(source):
            return "locked"
        if self._code_ok(candidate):
            self._limiter.success(source)
            return "ok"
        self._limiter.fail(source)
        return "bad"

    def _note_activity(self):
        cb = self.on_activity
        if cb is None:
            return
        try:
            cb()
        except Exception as e:
            log.debug("Callback de actividade remota falhou: %s", e)

    def _begin_command(self):
        """Fecha a janela de silêncio enquanto o comando executa."""
        cb = self.on_command_begin
        if cb is None:
            self._note_activity()
            return
        try:
            cb()
        except Exception as e:
            log.debug("Callback de início de comando remoto falhou: %s", e)

    def _end_command(self):
        """O comando acabou de executar; a câmara fica calada mais ``hold_s``."""
        cb = self.on_command_end
        if cb is None:
            self._note_activity()
            return
        try:
            cb()
        except Exception as e:
            log.debug("Callback de fim de comando remoto falhou: %s", e)

    # ── Ciclo de vida ────────────────────────────────────────────────
    def start(self):
        """Arranca o servidor em background. Devolve True se ficou ativo."""
        if self._thread and self._thread.is_alive():
            log.info("Servidor remoto já está a correr.")
            return False
        self._ensure_code()
        self._thread = threading.Thread(
            target=self._thread_main, name="maouse-remote", daemon=True
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
            "Controlo remoto ativo em %s:%d (IPs de rede: %s; "
            "emparelhamento por código de %d dígitos)",
            host,
            self.bound_port,
            ", ".join(lan_ips()) or "-",
            CODE_LEN,
        )

    # ── Ligação WebSocket ─────────────────────────────────────────────
    async def _on_connect(self, connection):
        authed = False
        self._clients.add(connection)
        source = _source_of(connection)
        try:
            log.info("Telemóvel a ligar... (%s)", source)
            async for raw in connection:
                if authed is False:
                    data = self._decode(raw)
# `code` é o nome actual; `token` é o nome de antes do
                    # código de 6 dígitos. Aceitar os dois é uma linha e
                    # poupa a reinstalar a app num telemóvel com um build de
                    # desenvolvimento já instalado — o `auth` é a única
                    # mensagem em que o nome da chave decide se o rato mexe.
                    candidate = data.get("code", data.get("token"))
                    estado = (
                        self._auth_state(candidate, source)
                        if data.get("cmd") == "auth"
                        else "bad"
                    )
                    if estado == "ok":
                        # A lease só é verificada depois de o código passar. Ao
                        # contrário, quem não tem o código consegue sondar o
                        # entitlement pela diferença entre `pro_required` e
                        # `auth_required`, sem nunca se ter autenticado.
                        ok, motivo = verify_remote_entitlement(data.get("lease"))
                        if not ok:
                            await self._send(
                                connection,
                                {"cmd": "auth", "ok": False,
                                 "error": "pro_required", "reason": motivo},
                            )
                            log.warning(
                                "Telemóvel autenticado mas sem entitlement (%s).",
                                motivo,
                            )
                            await connection.close()
                            return
                        authed = True
                        await self._send(
                            connection,
                            {"cmd": "auth", "ok": True,
                             "w": getattr(self._mouse, "screen_w", 1920),
                             "h": getattr(self._mouse, "screen_h", 1080)},
                        )
                        log.info("Telemóvel autenticado (%s).", source)
                        self._note_activity()
                    else:
                        # O que se responde diz apenas o que o telemóvel pode
                        # fazer a seguir: recuar e tentar mais tarde. Não diz
                        # quantos dígitos acertou, nem se o código existe.
                        espera = int(self._limiter.locked_for(source)) + 1
                        log.warning(
                            "Auth falhada de %s (%s).",
                            source,
                            "bloqueado" if estado == "locked" else "codigo errado",
                        )
                        await self._send(
                            connection,
                            {
                                "cmd": "auth",
                                "ok": False,
                                "error": "auth_locked" if estado == "locked"
                                else "auth_required",
                                "retry_after": espera if estado == "locked" else 0,
                            },
                        )
                        # A ligação morre com a tentativa. Uma sessão que fica
                        # à espera de uma segunda tentativa é o que faz do
                        # código curto um alvo, mesmo com o limitador.
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
                recv_at = time.monotonic()
                began = False
                try:
                    trace("REMOTE recv %s", json.dumps(data, ensure_ascii=False))
                    # Fechar a janela de silêncio durante a execução, não só na
                    # recepção: a câmara segura a GIL e o comando pode ficar
                    # bloqueado mais tempo que a janela, caso em que o rato
                    # voltava a ser da câmara a meio do `move_to` + `left_click`
                    # e o clique aterrava noutro sítio.
                    self._begin_command()
                    began = True
                    note = self._handle(cmd, data)
                except Exception as e:
                    log.debug("Comando %s falhou: %s", cmd, e)
                    await self._send(connection, {"ok": False, "error": str(e)})
                    continue
                finally:
                    if began:
                        self._end_command()
                espera = (time.monotonic() - recv_at) * 1000.0
                trace("REMOTE done  %s -> %s (espera %.0f ms)", cmd, note, espera)
                await self._send(connection, {"ok": True, "note": note})
        except Exception as e:
            log.debug("Ligação remota terminada: %s", e)
        finally:
            # Uma ligacao que morre a meio de um arrasto nao pode deixar o
            # botao premido: o utilizador so descobre quando clica e fica a
            # arrastar. `_release_held` trata do `press` e do `left_down`.
            self._release_held()
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
        if cmd == "move":
            self._move_rel(self._int(data, "dx"), self._int(data, "dy"))
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
        # O resto fraccionário é relativo à posição anterior: depois de um salto
        # absoluto não significa nada, e ficaria a arrancar um deslocamento
        # fantasma no primeiro `move` seguinte.
        self._mfx = 0.0
        self._mfy = 0.0
        x = min(max(self._float(data, "x", 0.0), 0.0), 1.0)
        y = min(max(self._float(data, "y", 0.0), 0.0), 1.0)
        w = max(getattr(self._mouse, "screen_w", 1920) - 1, 1)
        h = max(getattr(self._mouse, "screen_h", 1080) - 1, 1)
        # A origem do ecrã virtual é negativa quando há um monitor à esquerda ou
        # acima do principal. Sem ela, o telemóvel apontava para o canto superior
        # esquerdo do desktop virtual — que não existe num setup desse género —
        # e o toque caía no monitor principal em vez de cair onde se tocou.
        ox = int(getattr(self._mouse, "screen_x", 0))
        oy = int(getattr(self._mouse, "screen_y", 0))
        px, py = ox + int(x * w), oy + int(y * h)
        self._mouse.mouse.position = (px, py)
        trace("REMOTE move_to (%.4f,%.4f) -> (%d,%d)", x, y, px, py)

    def _move_rel(self, dx, dy):
        """Aplica o ganho ao movimento RELATIVO do touchpad.

        O telefone manda o deslocamento do dedo em píxeis de ecrã, 1:1. Num
        touchpad de ~330 px isso só cobre 330 dos 1366 px do ecrã: o cursor
        ficava a meio caminho e o toque seguinte — que é absoluto — levava-o
        300–400 px de repente. Era o "salto ao clicar".

        O acumulador fraccionário é indispensable: com ``remote_move_gain=3.0``
        um delta de 1 px dá 3 px inteiros, mas com ganhos como 2.5 dá 2,5 —
        arredondar para inteiro a cada evento fazia o cursor tremer e perdia
        meio píxel de cada vez, o que com centenas de eventos por segundo
        acabava num desvio visível.
        """
        gain = min(max(float(getattr(self._cfg, "remote_move_gain", 1.0)), 1.0), 8.0)
        self._mfx += dx * gain
        self._mfy += dy * gain
        ix, iy = int(self._mfx), int(self._mfy)
        if not ix and not iy:
            return
        self._mfx -= ix
        self._mfy -= iy
        self._mouse.move_by(ix, iy)

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

    # Aliases aceite no `press`. Canonicalizar evita que `lmb` e `left` fiquem
    # dois botoes Held distintos quando sao o mesmo botao.
    _BUTTONS = {
        "left": "left", "lmb": "left",
        "right": "right", "rmb": "right",
        "middle": "middle", "mmb": "middle",
    }

    def _press(self, button, hold):
        canon = self._BUTTONS.get(button)
        if canon is None:
            raise ValueError(f"botao_desconhecido:{button}")
        if hold:
            self._held.add(canon)
        else:
            self._held.discard(canon)
        mouse = self._mouse
        if canon == "left":
            if hold:
                mouse.press_left()
            else:
                mouse.release_left()
        elif canon == "right":
            if hold:
                self._mouse.mouse.press(Button.right)
            else:
                self._mouse.mouse.release(Button.right)
        else:
            if hold:
                self._mouse.mouse.press(Button.middle)
            else:
                self._mouse.mouse.release(Button.middle)

    def _release_held(self):
        """Solta o que a ligacao morreu com premido.

        Sem isto, um telefone que perde a ligacao a meio de um arrasto deixa o
        botao do rato premido no PC, e so se descobre quando se clica em algo e
        esse algo fica a arrastar. O `_combo` ja faz isto para as teclas; os
        botoes nao tinham o mesmo cuidado.
        """
        for button in sorted(self._held):
            try:
                self._press(button, hold=False)
            except Exception as e:
                log.debug("Falha ao soltar o botao %s: %s", button, e)
        self._held.clear()
        # `_drag` e um guarda de gesto, nao um segundo registo: o `left_down` ja
        # passou por `_press`, logo "left" esta em `_held` se e quando `_drag` e
        # True. So falta limpar a bandeira para o proximo `left_down` nao
        # achar que o botao ja esta premido.
        self._drag = False

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
                "arrow_up": Key.up, "arrow_down": Key.down,
                "arrow_left": Key.left, "arrow_right": Key.right,
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
            "stop": getattr(Key, "media_stop", None),
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
        # x/y são OPCIONAIS. Sem eles o gesto carrega onde o cursor já está —
        # é o que o touchpad do app envia, e é o comportamento de um touchpad.
        # Com eles, o cursor salta primeiro para o ponto normalizado indicado.
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
                self._press("left", hold=True)
                self._drag = True
            return "DRAG ON"
        if event == "left_up":
            if getattr(self, "_drag", False):
                self._press("left", hold=False)
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
