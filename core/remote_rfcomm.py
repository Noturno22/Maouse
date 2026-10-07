"""Controlo remoto por Bluetooth Classic (RFCOMM/SPP) — transporte Windows.

O BLE de `core/remote_ble.py` resolve o Bluetooth em Linux, e só em Linux: fala
com o `bluetoothd` pela D-Bus de sistema, que o Windows não tem. Este módulo é o
outro lado dessa escolha — em Windows o PC **serve** uma porta RFCOMM, e o
telefone liga-se a ela como cliente.

    telefone --RFCOMM-->  Frames  -->  {cmd, ...}  -->  RemoteServer._handle

É a mesma forma do BLE e por uma razão deliberada: um rato que se repara é um rato
que não funciona. Este módulo não implementa um único comando. Recebe o mesmo
`dict`, chama o mesmo `_handle`, devolve a mesma resposta. Uma correcção ao rato
pelo WiFi aparece no Bluetooth sem tocar em nada aqui.

**Porquê RFCOMM e não BLE.** O Windows expõe BLE/GATT server por
`GattServiceProvider`, mas o peripheral role é *hardware-dependent*: a Microsoft
diz que nem todos os adaptadores o suportam e manda consultar
`BluetoothAdapter.IsPeripheralRoleSupported`. Um servidor GATT no Windows
funciona no portátil de quem Integratei-o e não funciona no desktop de um cliente
com um adaptador barato, e isso é uma promessa que a plataforma não deixa
cumprir. O RFCOMM (`RfcommServiceProvider`) é um socket e funciona em todas as
máquinas. É a diferença entre "liga nos computers dos clientes" e "liga em uns
quantos".

O iPhone não fala RFCOMM, e é por isso que o Bluetooth aqui é caminho Android. O
BLE continua a ser o caminho iOS — quando houver GATT server para Windows, ou
hardware próprio, esse reaproveita o `core/remote_ble.py` tal como está.

**O processo nativo é um tubo de bytes.** O Python não fala RFCOMM (o
`socket.AF_BLUETOOTH` é só em Linux), portanto quem o detém é um executável
WinRT. Esse executável não sabe o que é um comando, o que é um `auth`, nem o que
é o rato: recebe bytes de uma ligação e entrega-os. Toda a inteligência fica em
Python, onde já está escrita e testada — e é por isso que este módulo se prova
numa máquina sem adaptador nenhum.
"""
from __future__ import annotations

import hmac
import json
import struct
import subprocess
import sys
import threading

from core.log import get_logger, trace
from core.remote import AuthLimiter, normalise_code, valid_code

# Mesma identidade, tecnologia diferente. O namespace de UUIDs do BLE e o do SDP
# do RFCOMM não se cruzam, e usar o mesmo valor dá ao telemóvel uma só identidade
# para "isto é um Maouse" em vez de duas para aprender.
from core.remote_ble import SERVICE_UUID as SERVICE_UUID

# A **codificação** partilha-se com o BLE; o **framing** não pode. `encode_command`
# e `decode_frame` definem o que é um comando e continuam a ser os mesmos, para
# que uma correcção ao rato apareça nos dois transportes sem tocar em nada aqui: o
# corpo de uma mensagem é byte a byte igual nos dois.
#
# O framing é que diverge, e não por capricho. O do BLE põe o tamanho da mensagem
# nos dois bytes à frente de *cada* fragmento, e isso só funciona porque uma
# escrita ATT é exactamente um fragmento e o link layer nunca junta dois. Num
# stream não há essa garantia: uma leitura pode trazer meio cabeçalho, três
# mensagens, ou o fim de uma e o todo de outra. Um leitor que leia o tamanho e
# trate o resto do bloco como corpo perde-se quando o bloco traz o cabeçalho da
# mensagem seguinte a meio — e a falha aparece como "o rato não obedece", que é a
# pior forma de falhar porque parece um problema de Bluetooth.
#
# O RFCOMM leva então um prefixo de tamanho, uma vez por mensagem, e um leitor que
# só avança quando a mensagem inteira chegou. O telefone tem de escrever assim:
# `4 bytes de tamanho` + `a mensagem`, e não repetir o tamanho a cada pedaço.
from core.remote_ble import _code_de, decode_frame, encode_command

log = get_logger("remote-rfcomm")

# ── Framing das mensagens do telefone ────────────────────────────────

TAM_FRAME = 4


class _Frames:
    """Junta um stream em mensagens completas.

    Uma instância por ligação. O RFCOMM é um stream e o sistema operativo
    entrega-o aos bocados: uma leitura pode trazer meio cabeçalho, duas
    mensagens, ou o fim de uma e o todo de outra. O leitor só avança quando a
    mensagem inteira chegou, e o que sobra no buffer é o início da seguinte.
    """

    # O mesmo tecto que o BLE, e pelo mesmo motivo: sem limite, um tamanho
    # malicioso nunca permitiria ao sítio recarregar a memória.
    MAX_FRAME = 64 * 1024

    def __init__(self, max_frame=None):
        self._buf = bytearray()
        self._max = int(max_frame or self.MAX_FRAME)

    def feed(self, chunk: bytes) -> list[bytes]:
        """Acumula e devolve as mensagens que ficaram completas."""
        self._buf.extend(chunk)
        out = []
        while True:
            if len(self._buf) < TAM_FRAME + 1:
                break
            total = int.from_bytes(self._buf[:TAM_FRAME], "big")
            if total == 0 or total > self._max:
                # Tamanho que não faz sentido. Deita-se fora o acumulado, porque
                # já não se sabe onde acaba a mensagem anterior, e a partir daqui
                # é lixo — que é o que uma tentativa de inundar o buffer parece.
                log.warning("RFCOMM: tamanho de mensagem invalido (%d).", total)
                self._buf.clear()
                break
            if len(self._buf) < TAM_FRAME + total:
                break
            out.append(bytes(self._buf[TAM_FRAME:TAM_FRAME + total]))
            del self._buf[:TAM_FRAME + total]
        return out


def _frame(msg: bytes) -> bytes:
    """Prepara uma mensagem para o stream."""
    return len(msg).to_bytes(TAM_FRAME, "big") + msg

# ── O canal com o executável nativo ─────────────────────────────────
#
# stdin/stdout do filho, e não um socket em localhost. Um socket local abriria
# porta no firewall e o cliente levaria com um prompt de segurança ao arrancar uma
# app de rato — por uma ligação que só a própria máquina pode usar. O pipe de um
# filho que nós lançámos não tem superfície nenhuma: se o Python morre, o pipe
# fecha, e o executável sai com ele.
#
# Cada mensagem é um envelope com o tamanho e a ligação a que pertence, porque o
# executável serve vários telefões ao mesmo tempo e um stream só não diz de quem
# são os bytes:
#
#     +---------+---------+-----------------+
#     | tam(4) | conn(4) | payload(tam-4)  |
#     +---------+---------+-----------------+
#
# `tam` conta tudo o que vem a seguir, para o leitor saber quando a mensagem
# acaba sem esperar por mais nada. `conn` 0 é controlo (o executável a dizer que
# o adaptador não existe, que o serviço registou, que o telefone entrou); a partir
# de 1 são os bytes de um telefone.

CONN_CONTROLE = 0
_TAM_CABECALHO = 8


def _envelope(conn: int, payload: bytes) -> bytes:
    """Empacota `payload` para a ligação `conn`."""
    return struct.pack("<II", 4 + len(payload), int(conn)) + payload


def _ler_exacto(stream, n: int) -> bytes:
    """Lê `n` bytes do stream, ou menos se o pipe fechar a meio.

    Uma leitura de pipe devolve o que houver, não o que se pediu: um envelope de
    40 bytes pode chegar em três leituras. Devolver o que calhou e deixar o
    ``_envelope`` seguinte apanhar o resto é o que transforma um pipe numa coisa
    fiável.
    """
    out = bytearray()
    while len(out) < n:
        pedaco = stream.read(n - len(out))
        if not pedaco:
            return bytes(out)
        out.extend(pedaco)
    return bytes(out)


class HostNativo:
    """O que o processo nativo tem de cumprir para servir de transporte.

    Existe como classe para os testes a trocarem por um dublê. Nada aqui fala com
    Bluetooth, e é esse o ponto: a suite toda corre numa máquina sem adaptador, e
    o que está a ser provado é o framing, a autenticação e o dispatch — as três
    coisas que dão para dar errado sem nenhum Bluetooth envolvido.
    """

    def iniciar(self) -> bool:
        """Lança o processo e começa a escutar. Devolve `True` se ficou de pé."""
        raise NotImplementedError

    def parar(self) -> None:
        """Fecha a escuta e o processo. Não pode levantar."""
        raise NotImplementedError

    def enviar(self, conn: int, payload: bytes) -> None:
        """Manda bytes à ligação `conn`."""
        raise NotImplementedError

    def a_vivo(self) -> bool:
        """O processo ainda existe?"""
        raise NotImplementedError


class _HostProcesso(HostNativo):
    """Um processo filho WinRT que detém a porta RFCOMM.

    `caminho` é o executável. `on_bytes` recebe `(conn, payload)` de cada telefone
    e `on_controlo` recebe o que o executável diz de si — incluindo o endereço de
    quem se ligou, que é o que permite ao limitador de tentativas não zerar cada
    vez que o telefone volta a ligar.
    """

    def __init__(self, caminho, on_bytes, on_controlo):
        self._caminho = caminho
        self._on_bytes = on_bytes
        self._on_controlo = on_controlo
        self._proc: subprocess.Popen | None = None
        self._leitor: threading.Thread | None = None
        self._erro: threading.Event = threading.Event()

    def iniciar(self) -> bool:
        if self._proc is not None:
            return False
        self._erro.clear()
        try:
            # `bufsize=0` deixa os pipes em modo binário e sem buffer próprio: o
            # que se escreve é o que o outro lado recebe, sem uma cópia pelo meio
            # a inventar fronteiras de mensagem onde só há um stream.
            self._proc = subprocess.Popen(
                [self._caminho],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
            )
        except OSError as e:
            log.warning("RFCOMM: nao arranquei o host nativo: %s", e)
            return False
        self._leitor = threading.Thread(
            target=self._ler, args=(self._proc.stdout,),
            name="rfcomm-leitor", daemon=True,
        )
        self._leitor.start()
        threading.Thread(
            target=self._ler_erros, args=(self._proc.stderr,),
            name="rfcomm-erros", daemon=True,
        ).start()
        return True

    def _ler_erros(self, stream) -> None:
        """O `stderr` do executável vai para o log, nunca para o `stdout`.

        Uma linha de aviso doWinRT é a diferença entre "o adaptador está desligado"
        e "isto está partido", e um aviso que vai para o pipe dos dados corrompe o
        protocolo em vez de explicar a falha.
        """
        try:
            for linha in iter(stream.readline, b""):
                texto = linha.decode("utf-8", errors="replace").rstrip()
                if texto:
                    log.debug("host nativo: %s", texto)
        except Exception:
            pass

    def _ler(self, stream) -> None:
        """Desembrulha envelopes até o pipe fechar."""
        try:
            while True:
                cab = _ler_exacto(stream, _TAM_CABECALHO)
                if len(cab) < _TAM_CABECALHO:
                    break
                tamanho, conn = struct.unpack("<II", cab)
                # `tamanho` conta o `conn` e o payload. O `4 - 4 = 0` seguinte é o
                # caso degenerado que um executável com um bug mandaria: sem
                # payload não há nada a entregar, e aceitar isso deixaria o
                # stream dessincronizado para sempre.
                if tamanho < 4:
                    log.warning("RFCOMM: envelope invalido (tamanho %d).", tamanho)
                    break
                payload = _ler_exacto(stream, tamanho - 4)
                if len(payload) < tamanho - 4:
                    break
                if conn == CONN_CONTROLE:
                    self._on_controlo(payload)
                else:
                    self._on_bytes(conn, payload)
        except Exception as e:
            log.debug("RFCOMM: lecteur terminou: %s", e)
        finally:
            self._erro.set()

    def enviar(self, conn: int, payload: bytes) -> None:
        proc = self._proc
        if proc is None or proc.stdin is None or proc.poll() is not None:
            return
        try:
            proc.stdin.write(_envelope(conn, payload))
            proc.stdin.flush()
        except (BrokenPipeError, ValueError, OSError) as e:
            # Pipe partido é o modo normal de o executativo morrer a meio, e
            # merce de ser tratado como fim de vida e não como erro: a próxima
            # sessão volta a lançá-lo.
            log.debug("RFCOMM: pipe terminado: %s", e)
            self._erro.set()

    def a_vivo(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def parar(self) -> None:
        proc = self._proc
        self._proc = None
        if proc is None:
            return
        try:
            if proc.stdin is not None:
                proc.stdin.close()
        except Exception:
            pass
        try:
            proc.terminate()
        except Exception:
            pass
        try:
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


def suportado() -> bool:
    """Se este sistema operativo tem um caminho RFCOMM.

    **Só Windows.** O `RfcommServiceProvider` é WinRT. O Linux já tem o BLE, que é
    melhor — sem MTU de 23 bytes e sem fragmentação — e por isso os dois
    transportes não arrancam ao mesmo tempo.

    Isto **não** diz que o Bluetooth funciona nesta máquina, só que pode. Sem
    adaptador, ou com o Bluetooth desligado nas definições, o `iniciar()` falha e
    o aviso vai para o log.
    """
    return sys.platform.startswith("win")


def _caminho_host() -> str:
    """Onde está o executável nativo, ao lado da aplicação.

    Vive em `native/` na árvore do repo e, instalado, ao lado do executável — que
    é onde o `build.bat` o tem de pôr. Procura nos dois sítios porque os testes
    correm na árvore e a app correta da pasta do `.exe`.
    """
    from pathlib import Path

    aqui = Path(__file__).resolve()
    candidatos = [
        aqui.parent.parent / "native" / "maouse-bluetooth-host.exe",
        aqui.parent.parent / "maouse-bluetooth-host.exe",
        # Onde `native/build-host.bat` deixa o executavel em desenvolvimento.
        # Sem esta entrada o servidor arranca mas nao acha o host, e o
        # sintoma e "RFCOMM nao arrancou" sem dizer porquê.
        aqui.parent.parent / "build" / "rfcomm-host" / "maouse-bluetooth-host.exe",
    ]
    for c in candidatos:
        if c.is_file():
            return str(c)
    return str(candidatos[0])


class _Sessao:
    """O que se sabe de um telemóvel, entre ligar e largar.

    Uma sessão por ligação, e o reassembly vive aqui e não no servidor: duas
    ligações a meio de mensagens diferentes não se podem misturar, e um buffer
    partilhado produziria comandos trocados entre dois telefones.

    A diferença para o BLE é o endereço: aqui a ligação é um socket com um número
    que muda a cada vez, e o limitador de tentativas conta por *origem*. Por isso
    o endereço vem do executável nativo, que é quem sabe quem se ligou. Sem ele
    cai-se no número da ligação, que é o mesmo que o BLE faria se o BlueZ não
    mandasse o endereço — funcional, mas quem se engana três vezes a desligar e
    voltar a ligar ganha outra vez as tentativas todas.
    """

    __slots__ = ("conn", "endereco", "authed", "frames")

    def __init__(self, conn: int):
        self.conn = int(conn)
        self.endereco = ""
        self.authed = False
        self.frames = _Frames()


class RemoteRFCOMM:
    """Servidor RFCOMM que transporta os mesmos comandos do WebSocket.

    A interface pública é a de `RemoteBLE` — `start`, `stop`, `is_running`,
    `connected_count`, `codigo_ativo` — para que trocar um pelo outro seja uma
    linha onde a aplicação decide qual arrancar, e não um emaranhado de
    ramificações.
    """

    def __init__(self, cfg, remote, code=None, host=None):
        self._cfg = cfg
        self._remote = remote
        self._code = code if code is not None else _code_de(cfg)
        # **O limitador é o do `RemoteServer`**, não um novo. Os três transportes
        # autenticam contra o mesmo código de 6 dígitos, e um atacante que vá a
        # WiFi passar a Bluetooth não pode ficar com o contador limpo — nem
        # trocando de Bluetooth para Classic. O `getattr` com alternativa é o que
        # faz isto funcionar com um dublê de servidor (os testes).
        self._limiter = getattr(remote, "limiter", None) or AuthLimiter()
        self._host = host
        self._sessoes: dict[int, _Sessao] = {}
        self._lock = threading.Lock()

    # ── Identidade ───────────────────────────────────────────────────

    @property
    def codigo_ativo(self) -> str:
        """O código com que o `auth` é comparado.

        Quem manda é o `RemoteServer`: é lá que o código é garantido válido e
        gerado se o `settings.json` trouxer o `remote_token` antigo. Comparar
        contra uma cópia seria o caminho para o WiFi aceitar e o Bluetooth recusar
        com o mesmo código — e essa falha só aparece a quem liga por Bluetooth, que
        é exactamente o que o utilizador foi fazer de propósito.
        """
        codigo = getattr(self._remote, "code", None)
        if isinstance(codigo, str) and valid_code(codigo):
            return codigo
        return self._code

    # ── Ciclo de vida ────────────────────────────────────────────────

    def start(self) -> bool:
        """Arranca o servidor RFCOMM. Devolve `True` se o host ficou de pé."""
        if self._host is not None and self._host.a_vivo():
            return False
        if self._host is None:
            self._host = _HostProcesso(
                _caminho_host(), self._on_bytes, self._on_controlo,
            )
        if not self._host.iniciar():
            self._host = None
            return False
        log.info("RFCOMM: servidor arrancado (servico %s).", SERVICE_UUID)
        return True

    def stop(self) -> None:
        """Fecha o servidor e liberta as sessões."""
        host, self._host = self._host, None
        with self._lock:
            self._sessoes.clear()
        if host is not None:
            try:
                host.parar()
            except Exception as e:
                log.debug("RFCOMM: falha ao parar o host: %s", e)

    def is_running(self) -> bool:
        host = self._host
        return host is not None and host.a_vivo()

    def connected_count(self) -> int:
        with self._lock:
            return len(self._sessoes)

    # ── Mensagens do executável nativo ───────────────────────────────

    def _on_controlo(self, payload: bytes) -> None:
        """O que o executável diz de si: serviço registado, telefone a entrar.

        Um telefone que entra é uma sessão nova. A anterior do mesmo endereço
        morre: dois telefones com o mesmo endereço é um, e deixar as duas a
        coexistir com o mesmo endereço daria ao limitador de tentativas duas
        contas separadas para a mesma pessoa.
        """
        try:
            msg = json.loads(payload.decode("utf-8", errors="replace"))
        except Exception:
            return
        if not isinstance(msg, dict):
            return
        evento = msg.get("event")
        if evento == "ligado":
            conn = int(msg.get("conn", 0) or 0)
            endereco = str(msg.get("endereco", "") or "")
            with self._lock:
                # Se o endereço é conhecido, a sessão que o tinha era a mesma
                # pessoa a reconectar-se e já não deve contar.
                for sid, s in list(self._sessoes.items()):
                    if s.endereco and s.endereco == endereco:
                        self._sessoes.pop(sid, None)
                self._sessoes[conn] = _Sessao(conn)
                self._sessoes[conn].endereco = endereco
            log.info("RFCOMM: ligacao de %s.", endereco or f"#{conn}")
        elif evento == "desligado":
            conn = int(msg.get("conn", 0) or 0)
            with self._lock:
                self._sessoes.pop(conn, None)
        elif evento == "erro":
            log.warning("RFCOMM: host nativo: %s", msg.get("texto", "?"))

    def _on_bytes(self, conn: int, payload: bytes) -> None:
        """Bytes de um telefone, que não têm relação com as mensagens.

        Um pacote de RFCOMM não é uma mensagem nem parte de uma: o sistema
        operativo entrega o stream aos bocados, e um bocado pode ser meio
        cabeçalho, três mensagens, ou o fim de uma e o todo de outra. É o
        `_Frames` que sabe onde acaba uma mensagem e começa a outra.
        """
        with self._lock:
            sessao = self._sessoes.get(conn)
            if sessao is None:
                sessao = _Sessao(conn)
                self._sessoes[conn] = sessao
        for frame in sessao.frames.feed(payload):
            self._on_frame(sessao, frame)

    # ── Comandos ─────────────────────────────────────────────────────

    def _on_frame(self, sessao: _Sessao, frame: bytes) -> None:
        data = decode_frame(frame)
        if not data:
            log.debug("RFCOMM: fragmento que nao e comando (%d bytes).", len(frame))
            return
        cmd = data.get("cmd")
        if not sessao.authed:
            self._fazer_auth(sessao, cmd, data)
            return
        if self._remote is None:
            return
        if cmd == "ping":
            self._responder(sessao, {"ok": True, "pong": True})
            return
        # Um comando de rato pode segurar a GIL durante o tempo que quiser, e o
        # WebSocket sofre exactamente o mesmo. O que **não** se faz é despachar
        # para outra thread: o `RemoteServer` não é thread-safe, e o arbitro já
        # resolve o problema que essa thread serviria. Por isso isto corre na
        # thread leitora do host, tal como no BLE corre no loop do BlueZ.
        began = False
        try:
            trace("REMOTE-RFCOMM recv %s", json.dumps(data, ensure_ascii=False))
            if self._remote.on_command_begin:
                self._remote.on_command_begin()
            began = True
            note = self._remote._handle(cmd, data)
        except Exception as e:
            log.debug("RFCOMM: comando %s falhou: %s", cmd, e)
            self._responder(sessao, {"ok": False, "error": str(e)})
            return
        finally:
            if began and self._remote.on_command_end:
                self._remote.on_command_end()
        trace("REMOTE-RFCOMM done  %s", cmd)
        self._responder(sessao, {"ok": True, "note": note})

    def _fazer_auth(self, sessao: _Sessao, cmd, data) -> None:
        """Autentica a sessão, ou recusa e fecha-lhe a porta.

        É o mesmo código, o mesmo limite de tentativas e a mesma comparação em
        tempo constante que o BLE faz. O que muda é que a origem é o endereço do
        telefone e não o do Bluetooth: o limite é por pessoa, não por tecnologia,
        e por isso esta linha e a do BLE vão buscar o **mesmo** `AuthLimiter` ao
        `RemoteServer`.
        """
        # A chave do limite é o endereço do telefone. É o mesmo endereço que a
        # sessão usa, e por isso que uma sessão nova do mesmo aparelho **não**
        # recomeça a contar: sem isto, fechar e voltar a ligar era o gesto mais
        # barato para o atacante.
        fonte = sessao.endereco or f"conn#{sessao.conn}"
        if not self._limiter.allow(fonte):
            log.warning("RFCOMM: %s esta bloqueado por tentativas.", fonte)
            self._responder(sessao, {
                "cmd": "auth", "ok": False, "error": "auth_locked",
                "retry_after": int(self._limiter.locked_for(fonte)) + 1,
            })
            self._fechar(sessao)
            return
        # `code` é o nome actual; `token` é o de antes do código de 6 dígitos, e
        # um build de desenvolvimento já instalado no telemóvel ainda o manda. Uma
        # linha, e não volta a ser preciso reinstalar a app para experimentar.
        candidate = data.get("code", data.get("token"))
        if cmd == "auth" and hmac.compare_digest(
            normalise_code(candidate), self.codigo_ativo
        ):
            self._limiter.success(fonte)
            sessao.authed = True
            log.info("Telemovel autenticado por RFCOMM (%s).", fonte)
            if self._remote is not None:
                self._remote._note_activity()
            self._responder(sessao, {
                "cmd": "auth", "ok": True,
                "w": getattr(self._remote._mouse, "screen_w", 1920) if self._remote else 1920,
                "h": getattr(self._remote._mouse, "screen_h", 1080) if self._remote else 1080,
            })
        else:
            if cmd == "auth":
                self._limiter.fail(fonte)
                log.warning("RFCOMM: codigo errado de %s.", fonte)
            self._responder(sessao, {"cmd": "auth", "ok": False,
                                      "error": "auth_required"})
            self._fechar(sessao)

    def _fechar(self, sessao: _Sessao) -> None:
        """Esquece a sessão. Quem falhou não fica com estado para o lado seguinte."""
        with self._lock:
            if self._sessoes.get(sessao.conn) is sessao:
                self._sessoes.pop(sessao.conn, None)

    def _responder(self, sessao: _Sessao, payload: dict) -> None:
        """Envia uma resposta à ligação.

        Uma mensagem, um prefixo de tamanho. Sem os 18 bytes do BLE: aqui não há
        MTU apertado, e mandar um corpo de 18 bytes quando o link leva milhares é
        gastar MTU a fingir que ainda estamos no Bluetooth.
        """
        host = self._host
        if host is None:
            return
        try:
            host.enviar(sessao.conn, _frame(encode_command(payload)))
        except Exception as e:
            log.debug("RFCOMM: falha ao responder a #%s: %s", sessao.conn, e)
