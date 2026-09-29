"""Controlo remoto por Bluetooth (BLE) — o PC como peripheral GATT.

Este módulo é **só o transporte**. Não repete uma única linha da camada de
comandos: o que entra aqui sai como o mesmo `dict` que o WebSocket produz, e é
entregue ao mesmo `RemoteServer._handle`. A alternativa — um servidor BLE com os
seus próprios `mouse.move_by`/`_type_text` — seria uma segunda implementação do
mesmo rato, e as duas divergem no primeiro bug.

    telefone --write-->  RX  (fragmentos)  -->  FrameBuffer --> {cmd, ...}
    telefone <--notify--  TX  (respostas)

Quatro decisões que não são óbvias:

* **O `dbus_next` é importado dentro de uma função**, pelo mesmo motivo que o
  `zeroconf` em `core/discovery.py`: o `main.py` importa este módulo ao nível do
  módulo, e um `ImportError` aqui seria a Maouse a não arrancar. Bluetooth é um
  extra — quem não o tem fica com o WiFi, que é o que já existia.

* **O token de autenticação vai por BLE como vai por WiFi.** Uma ligação BLE é
  mais difícil de escutar do que uma ligação TCP (é pareada, e oAdvertising exige
  consentimento), mas não é uma ligação autenticada: o token é a única coisa
  entre um telemóvel qualquer e o rato de alguém. Reusar `remote_token` e
  `auth` como primeira mensagem mantém uma só credencial para o utilizador
  gerir, e uma só política para a auditoria ler.

* **O caminho quente (`move`) é binário, o resto é o mesmo JSON do WebSocket.**
  Não por elegância: a MTU por omissão do BLE são 23 bytes, o que deixa 20
  utilizáveis por escrita. `{"cmd":"move","dx":12,"dy":-4}` são 32 bytes, ou
  seja **duas escritas ATT** para o comando que o utilizador gera a cada
  gesto. Com o intervalo de conexão típico (7,5–30 ms) isso esgota a ligação
  antes de metade dos comandos. O binário são 5 bytes e uma escrita. O resto
  dos comandos (clique, tecla, texto) é raro e não paga a complexidade de um
  opcode cada — daí o caminho duplo, com o JSON a ser o caso geral.

* **O `Value` da característica de escrita é o gatilho, não um buffer.** O BlueZ
  chama `WriteValue` por cada escrita da característica; não existe "escreve e
  depois pergunta". Quem manda é quem tem o dado, e o `dbus-next` entrega o
  valor já desembrulhado.
"""
from __future__ import annotations

import asyncio
import json
import threading

from core.log import get_logger, trace

log = get_logger("remote-ble")

# UUIDs 128 bits gerados para isto; não são de nenhum perfil adotado. O telefone
# tem de trazer estes valores à letra — estão em `plugins/with-maouse-native`.
SERVICE_UUID = "D9905F51-F497-49A4-88DF-784D82249EFD"
RX_UUID = "4C7F582E-BD6F-40ED-B181-AE537DD154ED"
TX_UUID = "64DB3D43-0354-4142-8EBE-EDE62429DD8A"

# Caminhos de objecto exportados no bus de sistema. O BlueZ não exige um
# prefixo em particular, mas começa por `/org/bluez/…` nos exemplos e o
# `RegisterApplication` devolve o caminho que lhe dermos.
APP_PATH = "/org/maouse/app0"
SERVICE_PATH = APP_PATH + "/svc0"
RX_PATH = SERVICE_PATH + "/rx"
TX_PATH = SERVICE_PATH + "/tx"

# `Flags` da `GattCharacteristic1` é um **array de strings** (`as`), não a
# bitfield `q` que a documentação do BlueZ suggest e que qualquer pessoa
# escreveria primeiro. O `parse_chrc_flags()` do daemon faz
# `dbus_message_iter_get_arg_type(&iter) != DBUS_TYPE_ARRAY` e devolve `false`
# se não for array — e o `chrc_create()` que chama isto tem, no fim,
# `app->failed = true`, o que transforma uma característica inválida em
#
#     org.bluez.Error.Failed: No valid service object found
#
# que não diz nada sobre a característica. O mesmo erro sai se o `Service` não
# for um caminho de objecto, ou se nenhum proxy chegou: três causas, uma
# mensagem. Foi o teste diferencial contra o `bluetoothd` real que isolaram isto
# (só o serviço regista; com uma característica, deixa de registar).
#
# Valores aceites: `broadcast`, `read`, `write`, `write-without-response`,
# `notify`, `indicate`, `authenticated-signed-writes`, `extended-properties`,
# `reliable-write`, `writable-auxiliaries`, `secure-read`, `secure-write`,
# `authorization`.
#
# `rx` leva `write` E `write-without-response` porque o telefone escolhe: os
# comandos do rato vão sem resposta (perde um pacote, que é um gesto perdido —
# aceitável), o `auth` e a confirmação de escrita vão com resposta (perder o
# `auth` seria perder a sessão). `tx` é só `notify`: o PC nunca lê nada do
# telemóvel por esta via, e um `read` aqui só abre superfície.
FLAGS_RX = ["write", "write-without-response"]
FLAGS_TX = ["read", "notify"]

# O valor de uma característica é `MTU - 3` bytes. A MTU por omissão do BLE é
# 23, portanto **20 bytes no total** — e o cabeçalho de 2 bytes do framing sai
# desse total, logo o corpo leva 18. Confundir "20" com o corpo produz
# fragmentos de 22 bytes, que o link layer recorta sem devolver erro nenhum: o
# telefone escreve, o PC recebe lixo, e a falha aparece só como "o rato não
# obedece". Negociação de MTU pelo telefone só увеz este número, nunca o
# diminui, portanto 18 é o pior caso e é com ele que o código tem de funcionar.
ATT_WRITE_MAX = 20
CHUNK_BODY = ATT_WRITE_MAX - 2

# Opcode do caminho binário. `0x01` = move. O valor de `dx`/`dy` vai em décimos
# de píxel (`int16`), o que preserva a parte fraccionária que o acumulador de
# `_move_rel` usa para o cursor não tremer entre comandos de meio píxel.
OP_MOVE = 0x01
MOVE_SCALE = 10

# O `RegisterApplication` tem um timeout por omissão de 25 s, e na **primeira**
# chamada o BlueZ ainda está a inicializar o GATT — o pedido morre antes de o
# daemon responder. É o que devolve `NoReply` numa máquina sã, e lê-se
# exactamente como "a política de segurança bloqueou a resposta", que não é o
# caso. O item 25 do PROGRESSO.md conta a meia hora perdida com isto.
REGISTER_TIMEOUT_S = 60.0


def _dbus():
    """O `dbus_next`, ou `None` se não estiver instalado.

    Só o lado *peripheral* é usado aqui, que vive em `dbus_next.service` — o
    `dbus_next.gatt` (papel de central, para o telemóvel) não é necessário e
    não é exigido.
    """
    try:
        from dbus_next import BusType, Message

        # `MessageBus` do `dbus_next.aio`, e não o do topo: o topo só
        # reexporta o do GLib (sincrónico, com mainloop própria) e este módulo
        # corre num `asyncio` — o `await bus.connect()` do outro nem existe.
        # Importar o errado não dá erro nenhum aqui: dá um objecto sem
        # `connect`, e a falha só apareceria mais tarde, já longe da causa.
        from dbus_next.aio import MessageBus
        from dbus_next.constants import PropertyAccess
        from dbus_next.service import ServiceInterface, dbus_property, method

        return _DBusApi(
            BusType, MessageBus, PropertyAccess, ServiceInterface,
            dbus_property, method, Message,
        )
    except Exception as e:
        log.info("Bluetooth indisponivel (%s). Sem controlo por BLE.", e)
        return None


class _DBusApi:
    """O que `_dbus()` traz de volta, num sítio só.

    Existe porque os *decorators* do `dbus_next` são avaliados no momento em que
    a classe é definida — e esta classe só pode ser definida quando o `dbus_next`
    chegou a ser importado. Guardar os símbolos num objecto e usá-los
    programaticamente adia a definição das interfaces para o `start()`, que é
    onde o `ImportError` já foi resolvido.
    """

    def __init__(self, bus_type, message_bus, property_access,
                 service_interface, dbus_property, method, message):
        self.BusType = bus_type
        self.MessageBus = message_bus
        self.PropertyAccess = property_access
        self.ServiceInterface = service_interface
        self.dbus_property = dbus_property
        self.method = method
        self.Message = message


# ── Framing ─────────────────────────────────────────────────────────
# O BLE não tem mensagens: tem escritas de tamanho fixo. Cada fragmento leva o
# comprimento *total* da mensagem em 2 bytes, e o receptor acumula até ter esse
# tamanho.
#
# Repetir o total em cada fragmento recupera o caso em que se perde o *primeiro*
# fragmento: o próximo e lido como se comecasse uma mensagem, o total nao bate certo
# com o que já estava acumulado, e o receptor recomeça em vez de colar bytes de
# duas mensagens diferentes.
#
# O que isto **não** cobre é perder um fragmento no meio com o total igual ao
# perdido — ai nao ha nada para comparar e o receptor entrega bytes de duas
# mensagens emendados. Comandos do rato e o `auth` cabem num fragmento cada, e
# o que precisa mesmo de fragmentar é texto longo, onde um comando trocado é
# texto errado e não um rato a disparar: para esse caso o enquadramento é
# aceitável. A alternativa seria numerar os fragmentos (3 bytes em vez de 2,
# deixando o corpo com 17), que é o que se deve fazer se algum dia um comando
# multi-fragmento precisar de entrega garantida.


def split_frame(frame: bytes, body: int = CHUNK_BODY) -> list[bytes]:
    """Parte uma mensagem em fragmentos, cada um com o total à frente."""
    frame = bytes(frame)
    body = max(4, min(int(body), ATT_WRITE_MAX - 2))
    total = len(frame)
    if total == 0:
        return []
    out = []
    off = 0
    while off < total:
        body_chunk = frame[off:off + body]
        off += len(body_chunk)
        out.append(total.to_bytes(2, "big") + body_chunk)
    return out


class FrameBuffer:
    """Junta fragmentos em mensagens completas.

    Um objecto por ligação: duas ligações a meio de mensagens diferentes não se
    podem misturar, e um `FrameBuffer` partilhado produziria comandos trocados
    entre dois telemóveis.
    """

    # Teto do que se acumula sem dar a mensagem por perdida. Uma mensagem de
    # texto pode ser grande (`{"cmd":"text","text":…}`), mas não pode ser
    # maior que isto: sem limite, um par de bytes malicioso numa escrita
    # inválida nunca permitiria ao sítio recarregar a memória.
    MAX_FRAME = 64 * 1024

    def __init__(self, max_frame: int = None):
        self._buf = bytearray()
        self._total: int | None = None
        self._max = int(max_frame or self.MAX_FRAME)

    def feed(self, chunk: bytes) -> list[bytes]:
        """Acumula um fragmento e devolve as mensagens que ficaram completas."""
        if len(chunk) < 2:
            return []
        total = int.from_bytes(chunk[:2], "big")
        body = bytes(chunk[2:])
        if total == 0 or total > self._max:
            # Cabeçalho que não faz sentido: descarta o que estava a acumular,
            # porque já não se sabe onde acaba a mensagem anterior.
            self._buf.clear()
            self._total = None
            return []
        if self._total is None:
            self._total = total
        elif self._total != total:
            # Um fragmento perdido no meio muda o total. Recomeçar é o
            # comportamento honesto; colar as duas metades daria ao rato
            # comandos que ninguém mandou.
            self._buf.clear()
            self._total = total
        self._buf.extend(body)
        out = []
        while self._total is not None and len(self._buf) >= self._total:
            out.append(bytes(self._buf[:self._total]))
            del self._buf[:self._total]
            # Uma mensagem só chega à ponta depois do seu último fragmento, e
            # cada fragmento traz cabeçalho próprio. O que sobrar no buffer já
            # não pertence a nenhuma mensagem, porque o total novo só aparece no
            # fragmento seguinte — o que fica é lixo de um escrita cortada.
            self._buf.clear()
            self._total = None
        return out


# ── Codificação ──────────────────────────────────────────────────────


def encode_command(data: dict) -> bytes:
    """Serializa um comando para o que vai por BLE.

    Só o `move` tem caminho binário; tudo o resto é o mesmo JSON do WebSocket,
    porque um opcode por comando seria mais código do que o que poupa.
    """
    if data.get("cmd") == "move":
        try:
            dx = int(round(float(data.get("dx", 0)) * MOVE_SCALE))
            dy = int(round(float(data.get("dy", 0)) * MOVE_SCALE))
        except (TypeError, ValueError):
            return _json_frame(data)
        # `int16` transbordado viraria negativo e o rato andaria para o lado
        # errado em vez de não andar. Um gesto de 3000 px num evento é
        # impossível, mas um `dx` de `None` do cliente não é.
        if not (-32768 <= dx <= 32767 and -32768 <= dy <= 32767):
            return _json_frame(data)
        return bytes([OP_MOVE]) + dx.to_bytes(2, "big", signed=True) + \
            dy.to_bytes(2, "big", signed=True)
    return _json_frame(data)


def _json_frame(data: dict) -> bytes:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def decode_frame(frame: bytes) -> dict:
    """O inverso de `encode_command`, para o que vem do telemóvel."""
    if frame[:1] == bytes([OP_MOVE]) and len(frame) == 5:
        dx = int.from_bytes(frame[1:3], "big", signed=True)
        dy = int.from_bytes(frame[3:5], "big", signed=True)
        return {"cmd": "move", "dx": dx / MOVE_SCALE, "dy": dy / MOVE_SCALE}
    try:
        out = json.loads(frame.decode("utf-8", errors="replace"))
    except Exception:
        return {}
    return out if isinstance(out, dict) else {}


# ── Interfaces GATT ─────────────────────────────────────────────────
# Construídas dentro de funções, e não no topo do módulo, porque os *decorators*
# do `dbus_next` são avaliados ao definir a classe — e esta classe só pode ser
# definida se o `dbus_next` já tiver sido importado. Ver `_DBusApi`.


def _build_interfaces(api, server):
    """As três interfaces que o BlueZ vai interrogar, sobre `server`.

    É uma função e não uma classe ao nível do módulo por causa dos decorators:
    se a definição fosse avaliada na importação, importar este módulo sem o
    `dbus_next` instalado seria um `ImportError` no import — exactamente o crash
    que o import tardio existe para evitar.

    As duas coisas que custaram uma tarde (item 25 do `PROGRESSO.md`):

    * A propriedade `Service` de uma característica é um **caminho de objecto**
      (`o`), não uma string. Passada como `str` o BlueZ lê o `s` errado e
      descarta a característica *e o serviço inteiro* — dois sítios de falha
      para uma causa. Aqui é `-> 'o'` e devolve-se um `dbus_next.ObjectPath`.

    * As propriedades têm de ser `@dbus_property`, e não um `dict` de `Variant`
      à mão. O `@dbus_property` gera a interface `org.freedesktop.DBus.Properties`
      com a assinatura certa, que é o que o BlueZ lê. É também a razão de o
      `ObjectManager` devolver as propriedades **vazias** se não for assim: o
      BlueZ pergunta com `GetAll`, e um atributo normal não responde a isso.
    """
    dbus_property, method = api.dbus_property, api.method
    read = api.PropertyAccess.READ
    readwrite = api.PropertyAccess.READWRITE

    class GattService(api.ServiceInterface):
        def __init__(self):
            super().__init__("org.bluez.GattService1")
            self._includes = []

        @dbus_property(access=read, name="Primary")
        def primary(self) -> "b":
            # Serviço primário: é o que faz o telefone mostrar a Maouse como um
            # peripheral e não como um intervalo de serviço solto no ar.
            return True

        @dbus_property(access=read, name="UUID")
        def uuid(self) -> "s":
            return SERVICE_UUID

        @dbus_property(access=read, name="Includes")
        def includes(self) -> "ao":
            return self._includes

    class GattCharacteristic(api.ServiceInterface):
        def __init__(self, path, uuid, service, flags, value, label):
            super().__init__("org.bluez.GattCharacteristic1")
            self._path = path
            self._uuid = uuid
            self._service = service
            self._flags = flags
            self._value = bytes(value or b"")
            self._label = label
            self._notifying = False
            self._descriptors = []

        @dbus_property(access=read, name="UUID")
        def uuid(self) -> "s":
            return self._uuid

        @dbus_property(access=read, name="Service")
        def service(self) -> "o":
            # `o` na anotação, e um `str` normal no return: é a anotação que
            # diz ao BlueZ que isto é um caminho de objecto. Ver a nota da
            # função — passar o caminho como `s` faz o BlueZ deitar fora a
            # característica e o serviço inteiro.
            return self._service

        @dbus_property(access=read, name="Flags")
        def flags(self) -> "as":
            return self._flags

        @dbus_property(access=readwrite, name="Notifying")
        def notifying(self) -> "b":
            # O BlueZ escreve isto, não nós: passa a `True` quando o telefone
            # subscreveu as notificações. É o único sinal fiável de que há
            # quem esteja do outro lado a ler.
            #
            # Por isso a propriedade é `readwrite` e não só de leitura: quem a
            # escreve é o daemon, via `org.freedesktop.DBus.Properties.Set`
            # quando a CCC muda de estado. Declarada como leitura, o BlueZ
            # recebe `PropertyReadOnly` ao activar as notificações e o
            # telemóvel fica ligado, à espera de respostas que nunca chegam —
            # falha silenciosa, e a única pista é o rato que não confirma.
            return self._notifying

        @notifying.setter
        def notifying(self, val: "b"):
            self._notifying = bool(val)

        @dbus_property(access=readwrite, name="Value")
        def value(self) -> "ay":
            return self._value

        @value.setter
        def value(self, val: "ay"):
            # O BlueZ não lê a `Value` por `read` para notificar: notificar é
            # exactamente isto, escrever a propriedade. Sem o setter o
            # `PropertiesChanged` nunca sai.
            self._value = bytes(val or b"")
            self._pending = None

        @dbus_property(access=read, name="Descriptors")
        def descriptors(self) -> "ao":
            return self._descriptors

        @method(name="ReadValue")
        def read_value(self, options: "a{sv}") -> "ay":
            return self._value

        @method(name="WriteValue")
        async def write_value(self, value: "ay", options: "a{sv}"):
            # `value` chega por cópia, e o `dbus-next` entrega-o como `bytes`
            # já desembrulhado. É aqui que a aplicação de um comando acontece:
            # o BlueZ não tem "escreve depois confirma".
            #
            # As `options` vão atrás porque são o **único** sítio onde o BlueZ
            # diz de que ligação veio a escrita — é assim que se sabe a quem
            # pertence o buffer de fragmentos. Sem elas, dois telemóveis
            # ligados ao mesmo PC trocavam meia mensagem à força.
            self._value = bytes(value or b"")
            await server._on_written(self, self._value, options)

    service = GattService()
    rx = GattCharacteristic(RX_PATH, RX_UUID, SERVICE_PATH, FLAGS_RX, b"", "rx")
    tx = GattCharacteristic(TX_PATH, TX_UUID, SERVICE_PATH, FLAGS_TX, b"", "tx")
    return service, rx, tx


class _Session:
    """O que se sabe de um telemóvel, entre ligar e largar.

    Uma sessão por ligação. O `FrameBuffer` e o estado de autenticação vivem
    aqui e não no servidor, porque duas ligações nunca podem misturar os
    fragmentos uma da outra.
    """

    __slots__ = ("device", "authed", "frames", "notifying")

    def __init__(self, device):
        self.device = device
        self.authed = False
        self.frames = FrameBuffer()
        self.notifying = False


class RemoteBLE:
    """Servidor GATT que transporta os mesmos comandos do WebSocket.

    Recebe o `RemoteServer` já construído e chama-lhe `_handle` — o mesmo que o
    WebSocket chama. Não duplica a camada de comandos, e é por isso que uma
    correcção ao rato pelo WiFi aparece no Bluetooth sem tocar em nada aqui.
    """

    def __init__(self, cfg, remote, token=None):
        self._cfg = cfg
        self._remote = remote
        self._token = token if token is not None else (
            getattr(cfg, "remote_token", "") or ""
        )
        self._api = None
        self._bus = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._app_path = None
        self._service = None
        self._rx = None
        self._tx = None
        self._sessions: dict[str, _Session] = {}
        self._ready = threading.Event()

    # ── Ciclo de vida ────────────────────────────────────────────────
    def start(self) -> bool:
        """Regista a aplicação GATT. Devolve `True` se o BlueZ a aceitou."""
        if self._thread and self._thread.is_alive():
            return False
        self._ready.clear()
        self._thread = threading.Thread(
            target=self._thread_main, name="maouse-remote-ble", daemon=True
        )
        self._thread.start()
        # O `RegisterApplication` é síncrono dentro do loop, mas a resposta
        # chega por D-Bus: sem esta espera, `start()` devolveria `True` a um
        # servidor que ainda não foi registado e a janela anunciaria um
        # peripheral que não existe.
        if not self._ready.wait(timeout=REGISTER_TIMEOUT_S + 5.0):
            log.error("O registo BLE nao respondeu a tempo.")
            self._join()
            return False
        if self._app_path is None:
            # O registo nao foi aceite. `_thread_main` ja fechou o bus e vai
            # sair, por isso aqui so se espera por ela: tentar *desligar* um bus
            # que a propria thread esta a fechar seria uma corrida, e o
            # `result(timeout=...)` do `stop()` custaria segundos a um caminho
            # que devolve em milissegundos.
            self._join()
            return False
        return True

    def _join(self):
        """Espera que a thread da aplicacao saia, sem perder a referencia.

        A referencia so e largada quando a thread ja morreu. Uma que fique presa
        (o `RegisterApplication` pendurado) continua alcancavel por `stop()`,
        que e o que a pode ainda desligar; perdê-la aqui era trocar um leak por
        um `RuntimeError` de loop fechado.
        """
        t = self._thread
        if t is not None:
            t.join(timeout=3.0)
            if not t.is_alive():
                self._thread = None
        self._app_path = None
        self._ready.clear()

    def _close_bus(self):
        """Solta o que a thread abriu: os objectos exportados e o bus.

        Corre dentro da thread, no loop do BlueZ. Sem isto, uma falha de
        registo deixava a ligacao ao bus de sistema aberta ate ao fim do
        processo — invisivel, porque `start()` ja devolveu `False` e ninguem
        mais olha para o objecto.
        """
        self._unexport_all()
        if self._bus is not None:
            try:
                self._bus.disconnect()
            except Exception as e:
                log.debug("Fecho do bus de sistema falhou: %s", e)

    def stop(self) -> None:
        """Desregista a aplicação e fecha a ligação ao bus."""
        loop, bus = self._loop, self._bus
        if loop is not None and bus is not None:
            async def _shutdown():
                try:
                    if self._app_path:
                        gatt = await self._gatt_manager()
                        if gatt is not None:
                            await gatt.call_unregister_application(self._app_path)
                except Exception as e:
                    log.debug("Desregistar a aplicacao GATT falhou: %s", e)
                self._unexport_all()
                bus.disconnect()

            try:
                asyncio.run_coroutine_threadsafe(_shutdown(), loop).result(timeout=5.0)
            except Exception as e:
                log.debug("Falha ao parar o servidor BLE: %s", e)
        self._join()

    @property
    def is_running(self) -> bool:
        return self._app_path is not None

    @property
    def connected_count(self) -> int:
        return len([s for s in self._sessions.values() if s.authed])

    def _thread_main(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        try:
            loop.run_until_complete(self._amain())
        except Exception as e:
            log.error("Servidor BLE falhou: %s", e)
            self._ready.set()
        if self._app_path is None:
            # **O registo falhou, e esta thread não tem nada para servir.**
            # Sem esta saída, caía-se no `run_forever()` abaixo e ficava à espera
            # de trabalho que nunca chega — e o que ficava preso era a thread *e*
            # a ligação ao bus de sistema, até ao fim do processo, invisível
            # porque o `start()` já devolveu `False` e mais ninguém olha para o
            # objecto. Pior ainda: a segunda vez que o utilizador tocasse na
            # opção, `start()` voltava a ver `self._thread.is_alive()` e
            # recusava-se a tentar, o que tornava o BLE impossível de recuperar
            # sem matar a aplicação.
            self._close_bus()
            loop.close()
            self._loop = None
            return
        try:
            loop.run_forever()
        finally:
            for task in asyncio.all_tasks(loop):
                task.cancel()
            loop.close()
            self._loop = None

    async def _adapter_path(self, message_cls) -> str | None:
        """O caminho do adaptador que tem `GattManager1`, ou `None`.

        O `GattManager1` **não** está em `/org/bluez`: está no próprio adaptador
        (`/org/bluez/hci0`, `/org/bluez/hci1`, …), e o número do controlador
        não é previsível. Pedir a interface à raiz dá `interface not found on
        this object: org.bluez.GattManager1` — uma mensagem de erro perfeitamente
        clara sobre a coisa errada, porque `/org/bluez` existe e tem interfaces
        (só que outras).

        O que funciona é o `ObjectManager` do **caminho `/`**, que é onde o BlueZ
        lista tudo o que exporta.
        """
        if self._bus is None:
            return None
        try:
            reply = await self._bus.call(message_cls(
                destination="org.bluez", path="/",
                interface="org.freedesktop.DBus.ObjectManager",
                member="GetManagedObjects",
            ))
        except Exception as e:
            log.info("Nao foi possivel listar os adaptadores (%s).", e)
            return None
        try:
            objects = reply.body[0]
        except Exception:
            return None
        if not isinstance(objects, dict):
            return None
        for path, interfaces in objects.items():
            if isinstance(interfaces, dict) and "org.bluez.Adapter1" in interfaces:
                return path
        return None

    async def _gatt_manager(self):
        """Proxy de `org.bluez.GattManager1` do adaptador, ou `None`.

        É o `GattManager1` que tem o `RegisterApplication`; o `Adapter1` só sabe
        Advertising e não regista aplicações GATT.
        """
        if self._bus is None:
            return None
        path = await self._adapter_path(self._api.Message)
        if path is None:
            log.info("BlueZ sem adaptador. Sem controlo por BLE.")
            return None
        try:
            node = await self._bus.introspect("org.bluez", path)
            obj = self._bus.get_proxy_object("org.bluez", path, node)
            return obj.get_interface("org.bluez.GattManager1")
        except Exception as e:
            log.info("BlueZ sem GattManager1 em %s (%s). Sem controlo por BLE.",
                     path, e)
            return None

    async def _amain(self):
        self._api = _dbus()
        if self._api is None:
            self._ready.set()
            return
        try:
            self._bus = self._api.MessageBus(bus_type=self._api.BusType.SYSTEM)
            await self._bus.connect()
        except Exception as e:
            log.info("Sem bus de sistema (%s). Sem controlo por BLE.", e)
            self._ready.set()
            return

        gatt = await self._gatt_manager()
        if gatt is None:
            self._ready.set()
            return

        # Exportar o serviço e as características ANTES do registo. Ao contrário
        # do `RegisterObject` (o outro sentido do GATT), o BlueZ vai ao bus
        # introspectar cada caminho durante o registo; um caminho que não
        # responda com `org.bluez.GattService1` faz o registo falhar.
        self._service, self._rx, self._tx = _build_interfaces(self._api, self)
        try:
            self._bus.export(SERVICE_PATH, self._service)
            self._bus.export(RX_PATH, self._rx)
            self._bus.export(TX_PATH, self._tx)
        except Exception as e:
            log.error("Nao foi possivel exportar o servico GATT: %s", e)
            self._ready.set()
            return

        self._bus.add_message_handler(self._on_properties_changed)

        try:
            # `RegisterApplication` **não devolve nada** — na BlueZ é
            # `GDBUS_ASYNC_METHOD(..., NULL /* out args */, ...)`, e por isso
            # a resposta chega vazia e o `dbus-next` dá `None`. Atribuir esse
            # `None` ao `_app_path` fazia o registo correr bem e o `start()`
            # responder `False` na mesma: um serviço publicado que a aplicação
            # acredita não estar lá. O caminho é o que foi enviado.
            await gatt.call_register_application(APP_PATH, {})
            self._app_path = APP_PATH
        except Exception as e:
            # `org.bluez.Error.Failed - No object received` a esta altura já é
            # o BlueZ a falar: a resposta veio, e o pedido é que estava
            # incompleto. Não é uma barreira de permissões.
            log.info("RegisterApplication falhou (%s). Sem controlo por BLE.", e)
            self._unexport_all()
            self._ready.set()
            return

        log.info("BLE: servico %s registado (%s).", SERVICE_UUID, self._app_path)
        self._ready.set()

    def _unexport_all(self):
        for path in (RX_PATH, TX_PATH, SERVICE_PATH):
            try:
                self._bus.unexport(path)
            except Exception:
                pass

    # ── Mensagens do BlueZ ───────────────────────────────────────────
    def _on_properties_changed(self, msg):
        """Acompanha `Notifying` para saber se o telefone quer as respostas.

        Sem isto o PC escreve para o vazio e o telefone fica à espera de um
        `pong` que nunca chega — a falha mais silenciosa de todas, porque o rato
        continua a funcionar e a parecer que está tudo bem.

        O corpo de um `PropertiesChanged` é `[interface, alteradas, invalidadas]`.
        O nome da propriedade **não** está em `body[0]`: `body[0]` é o nome da
        interface (`org.bluez.GattCharacteristic1`) e as propriedades estão nas
        chaves de `body[1]`. Ler `body[0]` como se fosse o nome faz esta função
        nunca disparar — e a falha é invisível, porque um `Notifying` que nunca
        é lido parece-se com um telefone que não quer notificações.
        """
        if getattr(msg.message_type, "name", "") != "SIGNAL":
            return
        if msg.interface != "org.freedesktop.DBus.Properties":
            return
        try:
            _interface, changed, _invalidated = msg.body
        except Exception:
            return
        if "Notifying" not in changed:
            return
        try:
            value = bool(changed["Notifying"].value)
        except Exception:
            value = bool(changed["Notifying"])
        if msg.path != TX_PATH:
            return
        for session in self._sessions.values():
            session.notifying = value
        log.debug("BLE: notificacoes %s", "ligadas" if value else "desligadas")

    @staticmethod
    def _device_key(options) -> str:
        """Identifica a ligação a partir do dicionário de opções do BlueZ.

        O `WriteValue` traz `a{sv}` com `Address` e `AddressType` (e `Type`
        quando vem por bonding). O que interessa é a ligação, não o
        dispositivo: o mesmo telemóvel pode ter duas ligações e elas não podem
        compartilhar um buffer de fragmentos.
        """
        try:
            for key in ("Address", "Device", "Type"):
                if key in options and options[key] is not None:
                    return str(options[key])
        except Exception:
            pass
        return "?"

    def _on_written(self, char, value, options) -> None:
        """Uma escrita do telefone chegou; executa os comandos que fechou.

        Corre dentro do loop do BlueZ, que é o mesmo loop que serve o bus de
        sistema. Um comando do rato pode segurar a GIL durante o tempo que
        quiser (`text` a escrever letra a letra), e o WebSocket sofre exactamente
        o mesmo — é para isso que existem `on_command_begin`/`on_command_end`, que
        cedem o rato à câmara durante a execução. O que **não** se faz é
        despachar o comando para outra thread: o `RemoteServer` não é
        thread-safe, e o arbitro já resolve o problema que a thread serviria.
        """
        if char is not self._rx:
            return
        session = self._sessions.get(self._device_key(options))
        if session is None:
            session = _Session(self._device_key(options))
            self._sessions[session.device] = session
        for frame in session.frames.feed(value):
            asyncio.ensure_future(self._on_frame(session, frame))

    async def _on_frame(self, session, frame):
        data = decode_frame(frame)
        if not data:
            log.debug("BLE: fragmento que nao e comando (%d bytes)", len(frame))
            return
        cmd = data.get("cmd")
        if not session.authed:
            if cmd == "auth" and data.get("token") == self._token:
                session.authed = True
                log.info("Telemovel autenticado por BLE.")
                if self._remote is not None:
                    self._remote._note_activity()
                await self._reply(session, {
                    "cmd": "auth", "ok": True,
                    "w": getattr(self._remote._mouse, "screen_w", 1920) if self._remote else 1920,
                    "h": getattr(self._remote._mouse, "screen_h", 1080) if self._remote else 1080,
                })
            else:
                await self._reply(session, {"cmd": "auth", "ok": False,
                                           "error": "auth_required"})
                self._sessions.pop(session.device, None)
            return
        if self._remote is None:
            return
        if cmd == "ping":
            await self._reply(session, {"ok": True, "pong": True})
            return
        began = False
        try:
            trace("REMOTE-BLE recv %s", json.dumps(data, ensure_ascii=False))
            if self._remote.on_command_begin:
                self._remote.on_command_begin()
            began = True
            note = self._remote._handle(cmd, data)
        except Exception as e:
            log.debug("Comando BLE %s falhou: %s", cmd, e)
            await self._reply(session, {"ok": False, "error": str(e)})
            return
        finally:
            if began and self._remote.on_command_end:
                self._remote.on_command_end()
        trace("REMOTE-BLE done  %s", cmd)
        await self._reply(session, {"ok": True, "note": note})

    async def _reply(self, session, payload):
        """Envia uma resposta pela característica de notificação.

        A notificação *é* a escrita da propriedade `Value` — o BlueZ watched-a e
        manda-a. Escrever mais do que uma MTU aqui é truncado sem aviso, que é a
        razão de isto passar por `split_frame` como o resto.
        """
        if self._tx is None or not session.notifying:
            return
        for chunk in split_frame(encode_command(payload)):
            try:
                self._tx.value = chunk
            except Exception as e:
                log.debug("Falha ao notificar o telemovel: %s", e)
                return
