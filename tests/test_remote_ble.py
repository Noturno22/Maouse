"""Testes do transporte BLE (`core/remote_ble.py`).

O que estes testes **não** provam, e é importante dizer: que o BlueZ aceita a
aplicação. Isso só se prova contra o `bluetoothd` real, e quem o provou foi o
item 25 do `PROGRESSO.md` (e a correcção continua a não ter teste, porque um
`bluetoothd` num CI não é uma coisa que se instale). O que fica coberto aqui é
a parte que se pode estragar a escrever código: o framing, a codificação, o
`auth` e as armadilhas do D-Bus que custaram uma tarde na altura.
"""
import asyncio
import os
import re
import subprocess
import sys
import threading
import time

import pytest

from core import remote_ble
from core.remote_ble import (
    ATT_WRITE_MAX,
    CHUNK_BODY,
    FLAGS_RX,
    FLAGS_TX,
    RX_PATH,
    RX_UUID,
    SERVICE_PATH,
    SERVICE_UUID,
    TX_PATH,
    TX_UUID,
    FrameBuffer,
    RemoteBLE,
    decode_frame,
    encode_command,
    split_frame,
)

_TEM_DBUS = remote_ble._dbus() is not None


class RatoFalso:
    """O mínimo que o `RemoteServer` lhexe, sem `pynput` nem ecrã."""

    screen_w = 1920
    screen_h = 1080

    def __init__(self):
        self.chamados = []

    def move_by(self, dx, dy):
        self.chamados.append(("move", dx, dy))

    def left_click(self):
        self.chamados.append(("click",))


class RemotoFalso:
    """Dublê do `RemoteServer`: regista o que lhe foi pedido, não executa."""

    def __init__(self):
        self._mouse = RatoFalso()
        self.comandos = []
        self.ganos = 0
        self.on_command_begin = None
        self.on_command_end = None

    def _note_activity(self):
        self.ganos += 1

    def _handle(self, cmd, data):
        self.comandos.append((cmd, data))
        return cmd.upper()


def _srv(remoto=None, codigo="123456"):
    return RemoteBLE(type("C", (), {"remote_code": codigo})(),
                    remoto if remoto is not None else RemotoFalso())


class TestFraming:
    """O BLE não tem mensagens; tem escritas de 20 bytes."""

    def test_mensagem_curta_vao_num_fragmento_so(self):
        chunks = split_frame(b"12345")
        assert len(chunks) == 1
        assert chunks[0] == b"\x00\x0512345"

    def test_o_que_cabe_numa_escrita_esta_no_fragmento(self):
        # O valor de uma característica é `MTU - 3` = 20 bytes com a MTU
        # por omissão, e o cabeçalho de 2 bytes sai desse total. Passar disto
        # era o link layer truncar em silêncio, que é o pior sítio para uma
        # falha ser detectada.
        for n in (0, 1, 17, 18, 19, 20, 21, 100):
            for chunk in split_frame(b"x" * n):
                assert len(chunk) <= ATT_WRITE_MAX

    def test_volta_a_original(self):
        for n in (1, 20, 21, 1000):
            original = b"z" * n
            buf = FrameBuffer()
            saida = []
            for chunk in split_frame(original):
                saida.extend(buf.feed(chunk))
            assert saida == [original]

    def test_duas_mensagens_seguidas_saem_separadas(self):
        # Uma moldura por mensagem. `split_frame` parte UMA mensagem, e nao um
        # fluxo: o telefone envia o `auth` e logo a seguir o `move`, e sao
        # duas molduras, nao uma so.
        buf = FrameBuffer()
        saida = []
        for frame in (b"auth", b"move", b"ping"):
            for chunk in split_frame(frame, body=2):
                saida.extend(buf.feed(chunk))
        assert saida == [b"auth", b"move", b"ping"]

    def test_uma_mensagem_so_no_fim(self):
        # O erro clássico de um reassembler: entregar assim que a escrita chega.
        # O rato mexia com meio comando.
        buf = FrameBuffer()
        assert buf.feed(b"\x00\x0a" + b"1234") == []
        assert buf.feed(b"\x00\x0a" + b"5678") == []
        assert buf.feed(b"\x00\x0a" + b"90") == [b"1234567890"]

    def test_fragmento_perdido_no_meio_nao_cola_das_mensagens(self):
        # Perde-se o segundo fragmento de "AB". O terceiro traz "CD".
        # Colar as duas metades daria "ABCD", que o telefone nunca escreveu.
        buf = FrameBuffer()
        assert buf.feed(b"\x00\x02AB") == [b"AB"]
        assert buf.feed(b"\x00\x02CD") == [b"CD"]

    def test_total_que_muda_a_meio_descarta_o_que_faltava(self):
        # Perdeu-se um fragmento e o emissor recomeçou a contagem. Sem o
        # descarte, a mensagem seguinte saia com bytes em cima do inicio da
        # anterior — o rato a executar um comando que ninguem escreveu.
        buf = FrameBuffer()
        assert buf.feed(b"\x00\x0a1234") == []
        assert buf.feed(b"\x00\x04XYZW") == [b"XYZW"]

    def test_o_resto_apos_uma_mensagem_continua_a_seguinte(self):
        buf = FrameBuffer()
        assert buf.feed(b"\x00\x02ab") == [b"ab"]
        assert buf.feed(b"\x00\x03cde") == [b"cde"]

    def test_cabecalho_impossivel_nao_acumula_para_sempre(self):
        # Sem tecto, um `total` enorme fazia o buffer crescer para sempre com
        # uma escrita de cada vez. Isto impede que dois bytes estragados
        # fiquem presos a acumular memoria para sempre.
        buf = FrameBuffer(max_frame=1024)
        buf.feed((2000).to_bytes(2, "big") + b"x" * 20)
        assert buf.feed(b"\x00\x0a" + b"y" * 10) == [b"y" * 10]

    def test_fragmento_muito_curto_e_ignorado(self):
        buf = FrameBuffer()
        assert buf.feed(b"\x01") == []
        assert buf.feed(b"") == []


class TestCodificacao:
    def test_move_e_binario_e_menor_que_o_json(self):
        # A razão de o caminho quente existir, em números: a MTU por omissão
        # deixa 20 bytes, e o JSON do `move` são 32 — duas escritas ATT para o
        # comando que o utilizador faz a cada gesto.
        binario = encode_command({"cmd": "move", "dx": 12, "dy": -4})
        import json as _json
        js = _json.dumps({"cmd": "move", "dx": 12, "dy": -4},
                         separators=(",", ":")).encode()
        assert len(binario) == 5
        assert len(js) > len(binario)
        # O move tem de caber numa escrita sem fragmentar; o JSON não, que é
        # exactamente o motivo de existirem os dois caminhos.
        assert len(binario) <= CHUNK_BODY
        assert len(js) > CHUNK_BODY

    def test_move_volta_com_o_mesmo_valor(self):
        for dx, dy in ((12, -4), (0, 0), (-1, 1), (33.3, -7.7)):
            dados = decode_frame(encode_command({"cmd": "move", "dx": dx, "dy": dy}))
            assert dados["cmd"] == "move"
            assert dados["dx"] == pytest.approx(dx, abs=0.06)
            assert dados["dy"] == pytest.approx(dy, abs=0.06)

    def test_move_guarda_a_parte_fraccionaria(self):
        # `_move_rel` acumula o resto para o cursor nao tremer. Se o telefone
        # mandasse inteiros, meio pixel ia-se a cada comando.
        dados = decode_frame(encode_command({"cmd": "move", "dx": 0.5, "dy": 0}))
        assert dados["dx"] == pytest.approx(0.5)

    def test_outro_comando_e_o_json_do_websocket(self):
        payload = {"cmd": "text", "text": "olá mundo"}
        import json as _json
        assert decode_frame(encode_command(payload)) == payload
        assert encode_command(payload) == _json.dumps(
            payload, ensure_ascii=False, separators=(",", ":")
        ).encode()

    def test_move_fora_do_int16_cai_para_json(self):
        # 40000 decimos = 4000 px. Transbordar o `int16` daria um `dx` negativo,
        # e o rato andava para o lado oposto em vez de nao andar.
        dados = {"cmd": "move", "dx": 4000, "dy": 0}
        assert encode_command(dados)[0] != remote_ble.OP_MOVE
        assert decode_frame(encode_command(dados))["dx"] == 4000

    def test_lixo_vira_comando_vazio(self):
        assert decode_frame(b"") == {}
        assert decode_frame(b"{isto nao e json") == {}
        assert decode_frame(b"[1, 2, 3]") == {}, "uma lista nao e um comando"

    def test_o_que_so_tem_1_byte_e_o_comeco_do_move(self):
        # `b"\x01"` a solo pode ser um `move` truncado ou lixo. Devolve vazio
        # e o comando nunca chega ao rato: melhor do que mover o rato com `dy`
        # a ler fora do buffer.
        assert decode_frame(b"\x01") == {}


class TestAuth:
    """O código de 6 dígitos é a única coisa entre um telemóvel e o rato."""

    def _correr(self, srv, frames):
        sessao = remote_ble._Session("AA:BB")
        async def cena():
            for f in frames:
                await srv._on_frame(sessao, f)
        asyncio.run(cena())
        return sessao

    def test_codigo_errado_nao_chega_ao_rato(self):
        remoto = RemotoFalso()
        srv = _srv(remoto, codigo="123456")
        sessao = self._correr(srv, [encode_command(
            {"cmd": "auth", "code": "654321"})])
        assert remoto.comandos == [], "um código errado moveu o rato"
        assert sessao.authed is False

    def test_sem_codigo_nada_mais_passa(self):
        remoto = RemotoFalso()
        srv = _srv(remoto, codigo="123456")
        # A resposta existe mas é recusada: um `ok` aqui seria o código errado
        # a ser aceite em vez de recusado.
        resposta = self._correr(srv, [encode_command({"cmd": "move", "dx": 9, "dy": 9})])
        assert remoto.comandos == []
        assert resposta != b"ok"

    def test_codigo_certo_autentica_e_depois_passa(self):
        remoto = RemotoFalso()
        srv = _srv(remoto, codigo="123456")
        sessao = self._correr(srv, [
            encode_command({"cmd": "auth", "code": "123456"}),
            encode_command({"cmd": "move", "dx": 5, "dy": -2}),
        ])
        assert sessao.authed is True
        assert [c for c, _ in remoto.comandos] == ["move"]
        assert remoto.ganos >= 1

    def test_sessao_nao_autenticada_e_removida(self):
        srv = _srv(codigo="123456")
        asyncio.run(srv._on_frame(remote_ble._Session("AA:BB"),
                                  encode_command({"cmd": "auth", "code": "000000"})))
        assert srv.connected_count == 0

    def test_o_ping_antes_do_auth_nao_e_respondido_com_pong(self):
        remoto = RemotoFalso()
        srv = _srv(remoto, codigo="123456")
        self._correr(srv, [encode_command({"cmd": "ping"})])
        assert remoto.comandos == []


def _propriedade(iface, nome):
    """A propriedade D-Bus tal como o daemon a vai ler.

    `iface.service` e o VALOR — o `@dbus_property` substitui o atributo pelo
    valor, e e o valor que o BlueZ lê. O que a introspecção mostra é o
    descritor, e é aí que vivem a assinatura e o `access`. Sem isto, um teste
    de contrato D-Bus acaba a testar `str` e passa sempre.
    """
    for p in iface._get_properties(iface):
        if p.name == nome:
            return p
    raise AssertionError(f"{iface.name} nao tem a propriedade {nome!r}")


@pytest.mark.skipif(not _TEM_DBUS, reason="dbus-next e' dependencia so de Linux")
class TestPropriedadesGatt:
    """As duas coisas que o BlueZ descarta se errarem, e os sinais (`Flags`).

    Um `Service` passado como `str` faz o BlueZ deitar fora a característica *e*
    o serviço inteiro — dois sítios de falha para uma causa, e nenhuma mensagem
    de erro a dizer qual.
    """

    def _ifs(self):
        api = remote_ble._dbus()
        srv = _srv()
        return api, srv, remote_ble._build_interfaces(api, srv)

    def test_service_e_um_caminho_de_objecto(self):
        # A anotacao `-> "o"` e o que diz ao BlueZ que o return e um caminho
        # de objecto; o valor em si e um `str` normal (o `dbus-next` 0.2.3 nao
        # tem um tipo `ObjectPath`). O que nao pode e' devolver outra coisa:
        # o `Service` lido como `s` faz o daemon descartar a caracteristica e
        # o servico inteiro.
        _api, _srv_, (_service, rx, _tx) = self._ifs()
        # `rx.service` e o VALOR: o `@dbus_property` substitui a classe pelo
        # descritor, e o `BlueZ` le o valor. Chamar `rx.service()` dava
        # `TypeError: 'str' object is not callable`.
        assert isinstance(rx.service, str)
        assert rx.service == SERVICE_PATH
        assert rx.service.startswith("/")

    def test_os_valores_que_o_telefone_le(self):
        _api, _srv_, (service, rx, tx) = self._ifs()
        assert service.uuid == SERVICE_UUID
        assert service.primary is True
        assert rx.uuid == RX_UUID and tx.uuid == TX_UUID
        # `Flags` é um array de strings, não uma bitfield. Com `q`, o
        # `parse_chrc_flags()` do daemon rebenta e o `RegisterApplication`
        # falha com "No valid service object found".
        assert rx.flags == FLAGS_RX == ["write", "write-without-response"]
        assert tx.flags == FLAGS_TX == ["read", "notify"]
        assert all(isinstance(f, str) for f in rx.flags + tx.flags)
        assert service.includes == []

    def test_o_caminho_da_caracteristica_aponta_para_o_servico(self):
        _api, _srv_, (_service, rx, _tx) = self._ifs()
        assert RX_PATH.startswith(SERVICE_PATH)
        assert TX_PATH.startswith(SERVICE_PATH)


@pytest.mark.skipif(not _TEM_DBUS, reason="dbus-next e' dependencia so de Linux")
class TestContratoGattDbus:
    """O que o BlueZ exige de cada propriedade, verificado sobre a interface.

    Estes testes existem por causa de um bug que a suite inteira nao apanhou:
    `Flags` estava como bitfield `q` e o registo no `bluetoothd` real falhava
    com `No valid service object found` — mensagem que fala do *servico* quando
    o problema e a *caracteristica*. Todos os testes passavam porque olhavam
    para os objectos Python, que estavam correctos, e nao para as assinaturas
    D-Bus que o daemon le na introspeccao.

    A regra daqui: cada propriedade verifica a **assinatura D-Bus** que a BlueZ
    le, nao apenas o valor.
    """

    def test_flags_e_um_array_de_strings_e_nao_uma_bitfield(self):
        # `parse_flags()` no gatt-database.c faz
        #   dbus_message_iter_get_arg_type(&iter) != DBUS_TYPE_ARRAY  -> return false
        # e o `chrc_create()` que a chama poe `app->failed = true`, o que
        # transforma um `Flags` mal formado em
        #   org.bluez.Error.Failed: No valid service object found
        api, _srv, (_s, rx, _tx) = TestPropriedadesGatt()._ifs()
        for chrc in (rx, _tx):
            assert isinstance(chrc.flags, list)
            assert chrc.flags, "uma caracteristica sem flags nao faz nada"
            for flag in chrc.flags:
                assert isinstance(flag, str)
                assert flag in {
                    "broadcast", "read", "write", "write-without-response",
                    "notify", "indicate", "authenticated-signed-writes",
                    "extended-properties", "reliable-write",
                    "writable-auxiliaries", "secure-read", "secure-write",
                    "authorization",
                }, f"flag desconhecida: {flag!r}"

    def test_rx_tem_escrita_e_tx_tem_notificacao(self):
        api, _srv, (_s, rx, tx) = TestPropriedadesGatt()._ifs()
        assert "write" in rx.flags or "write-without-response" in rx.flags
        assert "notify" in tx.flags
        assert "write" not in tx.flags, "o PC nao aceita comandos do telefone"

    def test_notifying_aceita_escrita(self):
        # Quem escreve `Notifying` e o daemon, via `Properties.Set`, quando a
        # CCC muda. Declarada como so-leitura, o BlueZ recebe
        # `PropertyReadOnly` ao activar as notificacoes e o telefone fica
        # ligado sem nunca receber resposta.
        #
        # O `.setter` existe na classe, mas o que decide e o `access` com que o
        # `@dbus_property` foi declarado: e isso que vai para a introspeccao.
        api, _srv, (_s, _rx, tx) = TestPropriedadesGatt()._ifs()
        prop = _propriedade(tx, "Notifying")
        assert prop.access is api.PropertyAccess.READWRITE, (
            "Notifying tem de ser readwrite: e o daemon que a escreve"
        )

    def test_service_e_um_caminho_de_objecto(self):
        # `parse_path()` no BlueZ exige `DBUS_TYPE_OBJECT_PATH`; uma `s` faz o
        # daemon deitar fora a caracteristica.
        api, _srv, (_s, rx, _tx) = TestPropriedadesGatt()._ifs()
        prop = _propriedade(rx, "Service")
        assert prop.signature == "o", "o Service e um caminho de objecto, nao `s`"
        assert isinstance(rx.service, str)
        assert rx.service == SERVICE_PATH


class TestNotifying:
    """O corpo de um `PropertiesChanged` é `[interface, alteradas, invalidadas]`.

    Ler `body[0]` como se fosse o nome da propriedade faz a função nunca
    disparar, e a falha parece-se com um telefone que não quer notificações.
    """

    class MsgFalso:
        def __init__(self, body):
            self.message_type = type("T", (), {"name": "SIGNAL"})()
            self.interface = "org.freedesktop.DBus.Properties"
            self.path = TX_PATH
            self.body = body

    def _srv_com_sessao(self):
        srv = _srv()
        srv._sessions["AA:BB"] = remote_ble._Session("AA:BB")
        return srv

    def test_liga_e_desliga(self):
        srv = self._srv_com_sessao()
        srv._on_properties_changed(self.MsgFalso([
            "org.bluez.GattCharacteristic1", {"Notifying": True}, [],
        ]))
        assert srv._sessions["AA:BB"].notifying is True
        srv._on_properties_changed(self.MsgFalso([
            "org.bluez.GattCharacteristic1", {"Notifying": False}, [],
        ]))
        assert srv._sessions["AA:BB"].notifying is False

    def test_uma_propriedade_outra_nao_mexe_em_nada(self):
        srv = self._srv_com_sessao()
        srv._on_properties_changed(self.MsgFalso([
            "org.bluez.GattCharacteristic1", {"Flags": 12}, [],
        ]))
        assert srv._sessions["AA:BB"].notifying is False

    def test_nao_e_sinal_e_ignorado(self):
        srv = self._srv_com_sessao()
        msg = self.MsgFalso(["org.bluez.GattCharacteristic1", {"Notifying": True}, []])
        msg.message_type = type("T", (), {"name": "METHOD_RETURN"})()
        srv._on_properties_changed(msg)
        assert srv._sessions["AA:BB"].notifying is False


class TestSessoes:
    def test_o_buffer_e_por_ligacao(self):
        # Dois telemóveis a meio de mensagens diferentes não podem misturar
        # fragmentos: era o rato a executar comandos trocados.
        a = remote_ble._Session("AA:BB")
        b = remote_ble._Session("CC:DD")
        # A meio da mesma moldura de 3 bytes, um com "ab" e o outro com "cd".
        assert a.frames.feed(b"\x00\x03ab") == []
        assert b.frames.feed(b"\x00\x03cd") == []
        assert a.frames.feed(b"\x00\x03c") == [b"abc"]
        assert b.frames.feed(b"\x00\x03e") == [b"cde"]

    def test_a_chave_vem_das_options_do_bluez(self):
        opts = {"Address": "30:F7:72:5F:56:4C", "AddressType": "public"}
        assert RemoteBLE._device_key(opts) == "30:F7:72:5F:56:4C"
        assert RemoteBLE._device_key({}) == "?"

    @pytest.mark.skipif(not _TEM_DBUS, reason="exige as interfaces D-Bus construidas")
    def test_escrita_de_outra_caracteristica_e_ignorada(self):
        srv = _srv()
        _service, _rx, tx = remote_ble._build_interfaces(
            remote_ble._dbus(), srv)
        # A notificação do PC não pode entrar pelo mesmo caminho que os
        # comandos: fechava um ciclo e o telefone executava o que escrevesse.
        srv._tx = tx
        srv._on_written(tx, b"\x00\x01x", {})
        assert srv._sessions == {}


class TestSemDbusNext:
    def test_importar_sem_a_dependencia_nao_e_fatal(self):
        # `main.py` importa este módulo ao nível do módulo. Um `ImportError`
        # aqui seria a Maouse a não arrancar — o mesmo crash do `cryptography`
        # em falta, e o mesmo que o `zeroconf` em `core/discovery.py`.
        codigo = """
import sys
# `find_spec`, e nao `find_module`/`load_module`: esse par pertence ao protocolo
# que o Python 3.12 removeu. Um finder que o implementa ainda e' consultado e
# depois IGNORADO -- o import passava limpo e o `dbus_next` do disco era
# encontrado. O teste so falhava onde a dependencia ESTA instalada, que e o CI
# (`requirements-linux.txt`); onde ela falta, o `_dbus()` devolvia `None` pela
# razao errada e o teste passava sem nunca ter bloqueado nada.
class Bloqueia:
    def find_spec(self, nome, caminho=None, target=None):
        if nome == "dbus_next" or nome.startswith("dbus_next."):
            raise ImportError("sem dbus_next")
        return None
sys.meta_path.insert(0, Bloqueia())
import core.remote_ble as m
assert m._dbus() is None
print("OK")
"""
        r = subprocess.run([sys.executable, "-c", codigo],
                           capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, r.stderr
        assert "OK" in r.stdout

    def test_e_main_que_aguenta_a_ausencia(self):
        codigo = """
import sys
# `find_spec`, e nao `find_module`/`load_module`: esse par pertence ao protocolo
# que o Python 3.12 removeu. Um finder que o implementa ainda e' consultado e
# depois IGNORADO -- o import passava limpo e o `dbus_next` do disco era
# encontrado. O teste so falhava onde a dependencia ESTA instalada, que e o CI
# (`requirements-linux.txt`); onde ela falta, o `_dbus()` devolvia `None` pela
# razao errada e o teste passava sem nunca ter bloqueado nada.
class Bloqueia:
    def find_spec(self, nome, caminho=None, target=None):
        if nome == "dbus_next" or nome.startswith("dbus_next."):
            raise ImportError("sem dbus_next")
        return None
sys.meta_path.insert(0, Bloqueia())
print("OK")
"""
        r = subprocess.run([sys.executable, "-c", codigo + "\nimport main\n"],
                           capture_output=True, text=True, timeout=120)
        assert r.returncode == 0, r.stderr
        assert "OK" in r.stdout

    def test_start_sem_dbus_next_devolve_false_e_nao_levanta(self):
        srv = _srv()
        srv._api = None
        original = remote_ble._dbus
        remote_ble._dbus = lambda: None
        try:
            async def cena():
                await srv._amain()
            asyncio.run(cena())
        finally:
            remote_ble._dbus = original
        assert srv.is_running is False


# ── A thread da aplicação, e quem a manda sair ──────────────────────────────

def _threads_ble():
    return [t for t in threading.enumerate() if t.name == "maouse-remote-ble"]


@pytest.fixture
def sem_dbus(monkeypatch):
    """`_dbus()` devolve `None`: o registo falha ao fim de uns milissegundos.

    É o caminho de falha mais comum em campo — `dbus-next` não instalado, ou
    `bluetoothd` parado — e o que se tinha de provar que não deixa nada para
    trás.
    """
    monkeypatch.setattr(remote_ble, "_dbus", lambda: None)


class TestCicloDeVida:
    """O `start()` que falha tem de devolver as mãos.

    O `main.py` e a janela **descartam** o objecto quando `start()` devolve
    `False` (`ble = None`), sem nunca lhe chamar `stop()`. O `start()` é o único
    sítio que sabe que falhou, e portanto o único que pode limpar. Sem isso, cada
    falha deixava uma thread viva **e** uma ligação ao bus de sistema aberta até
    ao fim do processo — invisível, porque o `start()` já devolveu `False`.
    """

    def test_start_falhado_nao_deixa_thread_ma(self, sem_dbus):
        antes = len(_threads_ble())
        srv = _srv()
        assert srv.start() is False
        _esperar()
        assert len(_threads_ble()) == antes, (
            "a thread do BLE ficou viva depois de o registo falhar"
        )

    def test_start_falhado_nao_prende_a_segunda_tentativa(self, monkeypatch):
        """A thread morta é o que torna a segunda tentativa possível.

        Com a thread ainda viva, `start()` via a guarda `is_alive()` e devolvia
        `False` sem tentar — o BLE ficava impossível de recuperar sem matar a
        aplicação, e o único sintoma era o Bluetooth não voltar a funcionar
        depois de o utilizador o ter desligado e ligado outra vez.
        """
        tentativas = []

        def _conta():
            tentativas.append(1)
            return None

        monkeypatch.setattr(remote_ble, "_dbus", _conta)
        srv = _srv()
        assert srv.start() is False
        _esperar()
        assert srv.start() is False
        _esperar()
        assert len(tentativas) == 2, (
            "a segunda chamada a start() nao chegou a tentar registar de novo"
        )

    def test_stop_e_idempotente(self, sem_dbus):
        srv = _srv()
        srv.start()
        _esperar()
        srv.stop()
        srv.stop()
        assert len(_threads_ble()) == 0


def _esperar(timeout=2.0):
    """Deixa a thread do BLE chegar ao fim, sem a Testar por sonolencia."""
    fim = time.monotonic() + timeout
    while _threads_ble() and time.monotonic() < fim:
        time.sleep(0.01)


# ── Quem é o dono do peripheral ─────────────────────────────────────────────

class _ServidorFalso:
    is_running = True


class _BleFalso:
    def __init__(self, running=True):
        self.is_running = running
        self.paradas = 0

    def stop(self):
        self.paradas += 1
        self.is_running = False


class _ToastFalso:
    def __init__(self):
        self.mensagens = []

    def show_toast(self, texto, danger=False):
        self.mensagens.append(texto)


class _JanelaBleFalsa:
    """O mínimo que `_apply_ble` toca, sem construir a janela toda."""

    def __init__(self, cfg, servidor, ble):
        self._cfg = cfg
        self._remote = servidor
        self._ble = ble
        self._toast = _ToastFalso()


def _janela_ble(servidor, ble, remoto_ble=True):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from ui.main_window import MainWindow

    cfg = type("C", (), {})()
    cfg.remote_ble = remoto_ble
    return MainWindow._apply_ble, _JanelaBleFalsa(cfg, servidor, ble)


class TestUmSoPeripheral:
    """O `RemoteBLE` que o `main.py` arrancou é o mesmo que a janela usa.

    Regressão real: o `main.py` criava e arrancava o objecto mas **não o
    passava** à janela, que punha `self._ble = None`. Ao primeiro `_apply_ble()`
    — ou seja, à primeira gravação das definições do remoto — a janela construía
    um segundo `RemoteBLE` e o arrancava: duas threads, duas ligações ao bus de
    sistema, e duas aplicações GATT registadas **nos mesmos caminhos de
    objecto** (`/org/maouse/app0/...`), o que o BlueZ não resolve a favor de
    ninguém.
    """

    def test_ble_ja_arrancado_nao_e_duplicado(self, monkeypatch):
        """`_apply_ble` não pode arrancar um segundo peripheral.

        Com um `RemoteBLE` já a correr na janela, chegar aqui era sinal de que
        algures se tinha perdido a referência — e o preço era duas aplicações
        GATT nos mesmos caminhos de objecto, sem que nenhuma sabes qual estava
        a servir o telefone.
        """
        metodo, janela = _janela_ble(_ServidorFalso(), _BleFalso(running=True))

        construtoras = []
        monkeypatch.setattr(
            remote_ble, "RemoteBLE",
            lambda *a, **k: construtoras.append(1),
        )

        metodo(janela)

        assert construtoras == [], "a janela construiu um segundo RemoteBLE"
        assert janela._ble is not None and janela._ble.is_running

    def test_o_main_precisa_de_passar_o_ble_a_janela(self):
        """Guarda de cablagem: `ble` tem de chegar ao `self._ble` da janela.

        Isto **não** é prova de comportamento — `_apply_ble` é testada em cima, e
        construir a `MainWindow` a sério exige câmara, tracker e event loop Qt.
        O que este teste apanha é o caso em que o `main.py` arranca o objecto e
        a janela o deita fora no `__init__`, que é exactamente o que aconteceu:
        nenhuma das outras apanhava, porque todas partiam de uma janela que já
        tinha o objecto.
        """
        import inspect

        import main as main_mod
        from ui.main_window import MainWindow

        assert "ble" in inspect.signature(main_mod.run_gui).parameters
        assert "ble" in inspect.signature(MainWindow.__init__).parameters
        assert "ble=ble" in inspect.getsource(main_mod.main), (
            "o main() arranca o BLE mas nao o passa a run_gui"
        )
        assert "self._ble = ble" in inspect.getsource(MainWindow.__init__), (
            "a janela recebe o BLE e deita-o fora — e volta a arranjar um no "
            "primeiro _apply_ble, nos mesmos caminhos de objecto"
        )


# ── A interface não pode oferecer o que o código não faz ───────────────────

class TestSuportado:
    """Só Linux — e a interface tem de dizer isso, não escondê-lo.

    A implementação fala com o `bluetoothd` pela D-Bus de sistema. O Windows não
    tem BlueZ nem D-Bus de sistema, e o `dbus-next` está em `LINUX_ONLY` por isso
    exacto. A checkbox aparecia no `.exe` do Windows onde o botão nunca pode
    funcionar: o `start()` devolvia `False`, a Maouse escrevia um aviso no log a
    cada arranque, e o utilizador via um botão que não fazia nada.
    """

    def test_so_linux(self, monkeypatch):
        for plat, esperado in (
            ("linux", True), ("win32", False), ("darwin", False),
            ("cygwin", False), ("freebsd13", False),
        ):
            monkeypatch.setattr(remote_ble.sys, "platform", plat)
            assert remote_ble.suportado() is esperado, plat

    def test_a_checkbox_diz_por_que_esta_desligada(self, monkeypatch):
        """Desligada **e a dizer porquê** — não desligada e calada.

        Desaparecer esconde a funcionalidade a quem compara a Maouse com a
        documentação; ficar clicável é pior que as duas coisas, porque o
        `start()` falha em silêncio do ponto de vista de quem está a olhar para
        o ecrã.
        """
        import os as _os

        _os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication

        import config
        import ui.settings_dlg as sd
        from core.licensing import Tier

        class _Lic:
            tier = Tier.FREE

        app = QApplication.instance() or QApplication([])
        assert app is not None

        monkeypatch.setattr(remote_ble.sys, "platform", "win32")
        dlg = sd.SettingsDialog(config.Config(), "NORMAL", license_mgr=_Lic())
        try:
            ch = dlg._remote_ble_ch
            assert ch.isEnabled() is False, "a checkbox do BLE esta clicavel no Windows"
            assert ch.isChecked() is False
            dica = ch.toolTip()
            assert "Linux" in dica, (
                f"a checkbox esta desligada sem dizer porque: {dica!r}"
            )
        finally:
            dlg.deleteLater()

    def test_no_linux_a_checkbox_esta_normal(self, monkeypatch):
        import os as _os

        _os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication

        import config
        import ui.settings_dlg as sd
        from core.licensing import Tier

        class _Lic:
            tier = Tier.FREE

        app = QApplication.instance() or QApplication([])
        assert app is not None

        monkeypatch.setattr(remote_ble.sys, "platform", "linux")
        dlg = sd.SettingsDialog(config.Config(), "NORMAL", license_mgr=_Lic())
        try:
            ch = dlg._remote_ble_ch
            assert ch.isEnabled() is True
            assert "Linux" not in ch.toolTip(), (
                "a dica de Linux ficou no caminho de quem pode usar a opcao"
            )
        finally:
            dlg.deleteLater()


# ── O telefone tem de mandar pelo mesmo caminho que o estado ───────────────

class TestAFachadaNaSaoApanhadaPelaRaiz:
    """Ninguém fora de `src/services/` importa o cliente cru.

    A `RemoteStore` é o que diz à app que o PC está ligado, e ela passa pela
    **fachada** (`remoteTransport`), que escolhe `wifi` ou `ble`. O `App.tsx`
    importava o `remoteClient` — o WebSocket cru — e mandava o gesto por aí. Por
    WiFi funcionava por acidente, porque o `ws` *é* o transporte activo nessa
    altura; por BLE, o `status` ficava `connected` e o gesto saía por um
    WebSocket que nunca tinha sido aberto. O rato não mexia, a UI mostrava
    "PC remoto" ligado, e nada no ecrã dizia porquê.

    Isto apanha **a classe**, não o caso: o padrão é o singleton `remote` a ser
    importado de fora de `src/services/`. Os *tipos* (`RemoteScreenInfo`,
    `RemoteClientCallbacks`) e o `buildWsUrl` continuam a ser importados
    directamente — partilhar tipos e um construtor de URL não é saltar a
    fachada, e `bleRemoteClient.ts` e `store/remote.ts` fazem-no com razão.

    **O que este teste não é**: não prova que um gesto chegue ao PC. O que fica
    depois deste import — a MTU negociada, a fragmentação, e a fila de escrita
    do `BleRemoteModule.kt`, que não entrega o 2.º gesto em diante quando o
    Android não devolve o `onCharacteristicWrite` — não é observável daqui. O
    que este teste garante é mais estreito e é verdade: o comando sai pelo
    transporte que o `status` diz estar activo.
    """

    RAIZ = "mobile/maouse-mobile"

    def _imports_de_remoteClient(self, path):
        """Os `import` de `path` que venham do modulo `remoteClient`.

        Devolve `[(nomes, origem)]` com os nomes já normalizados, chaves e
        `as` fora. Três coisas que as primeiras versões deste método fizeram
        mal, e as três davam um teste verde que não protegia nada:

        * comparava `'remote' in ['{ remote }']`, que e `False` para sempre;
        * o padrão não atravessava linhas, por isso o import multi-linha do
          `bleRemoteClient.ts` não contava — `[^;]` com `DOTALL` resolve, e o
          `;` é o que impede a passagem para a declaração seguinte;
        * e sem ancoragem, um `import` escrito **dentro de um comentário** era
          lido como o início da declaração, e o nome que o teste comparava
          saía `"import { remote }"`. Aconteceu com o comentário que este
          mesmo commit acrescenta ao `App.tsx` para explicar a armadilha.
          Ancorar o `import` ao início da linha, com `MULTILINE`, só casa onde
          uma declaração começa mesmo — que é como o código está escrito.
        """
        try:
            fonte = open(path, encoding="utf-8").read()
        except OSError:
            return []
        achados = []
        padrao = r"^\s*import\s+([^;]*?)\s+from\s+'([^']*remoteClient)'"
        for m in re.finditer(padrao, fonte, re.DOTALL | re.MULTILINE):
            nomes = [
                n.strip().strip("{}").strip()
                for n in m.group(1).split(",")
            ]
            achados.append((nomes, m.group(2)))
        return achados

    def _varre_a_app(self):
        """Todos os ficheiros `.ts`/`.tsx` da app, e confirma que os viu."""
        vistos, maus = [], []
        for base, _dirs, ficheiros in os.walk(self.RAIZ):
            if "node_modules" in base or "android" in base or "ios" in base:
                continue
            for f in ficheiros:
                if not f.endswith((".ts", ".tsx")):
                    continue
                caminho = os.path.join(base, f)
                vistos.append(caminho)
                for nomes, origem in self._imports_de_remoteClient(caminho):
                    # `remoteClient` e `bleRemoteClient` sao ficheiros
                    # diferentes; so o primeiro conta.
                    if os.path.basename(origem) != "remoteClient":
                        continue
                    if "remote" in nomes:
                        maus.append(os.path.relpath(caminho, self.RAIZ))
        # Sem isto o teste passa a vazio quando `RAIZ` esta errado, que e
        # exactamente o modo de falha que o `nomes` partido teve. O piso e
        # baixo de proposito — a app tem 19 ficheiros de codigo, e o que
        # intere e nao dar zero, mais o `App.tsx` estar entre eles.
        assert len(vistos) >= 15, (
            f"a varredura viu so {len(vistos)} ficheiros — o caminho "
            f"{self.RAIZ!r} esta errado e este teste nao estaria a ver nada"
        )
        assert any(v.endswith("App.tsx") for v in vistos), (
            "a varredura nao chegou ao App.tsx, que e o ficheiro que esta a ser "
            "protegido"
        )
        return maus

    def test_nada_fora_dos_services_importa_o_singleton(self):
        maus = self._varre_a_app()
        assert not maus, (
            "importam o `remote` (o cliente WebSocket cru) em vez da fachada "
            f"`remoteTransport`: {maus}. O `status` vem da fachada, que cobre "
            "wifi E ble — por BLE o gesto iria por um WebSocket nunca aberto."
        )

    def test_a_varredura_encontra_o_caso_que_conhecemos(self):
        """A guarda so vale se apanha a occorrencia que ja sabemos que existe.

        Nao e um teste do produto: e um teste *da guarda*. Um teste que le
        source e silencioso quando o caminho ou o padrao mudam, e o preco de nao
        dar conta e um teste verde que nao protege nada. Os dois casos abaixo
        sao reais, verificados agora: `bleRemoteClient.ts` tem o import
        **multi-linha** (que e o que um `.*?` sem `DOTALL` nao via) e
        `store/remote.ts` importa `buildWsUrl`, que e um valor e nao o
        singleton — os dois tem de ser vistos e ninguno dos dois pode ser
        complainado.
        """
        alvos = {
            "import multi-linha de tipos, que nao e o singleton":
                os.path.join("src", "services", "bleRemoteClient.ts"),
            "import de `buildWsUrl`, que e um valor e nao o singleton":
                os.path.join("src", "store", "remote.ts"),
        }
        for descricao, rel in alvos.items():
            caminho = os.path.join(self.RAIZ, rel)
            achados = self._imports_de_remoteClient(caminho)
            assert achados, f"{rel} devia importar de remoteClient e nao importou ({descricao})"
            for nomes, _origem in achados:
                assert "remote" not in nomes, (
                    f"{rel} importa o singleton `remote` ({descricao}) — e so a "
                    "fachada o pode usar"
                )

        # E o inverso: a fachada usa o cliente cru, e por isso tem de ser
        # encontrada — se a fachada mudar de forma, este aviso e para ser
        # actualizado, nao para o teste adiar.
        fachada = os.path.join(self.RAIZ, "src", "services", "remoteTransport.ts")
        achados = self._imports_de_remoteClient(fachada)
        assert achados, (
            "a fachada deixou de importar de `remoteClient` — a forma mudou e "
            "este teste deve ser actualizado, nao adiado"
        )
        assert any("RemoteClient" in n for nomes, _ in achados for n in nomes), (
            "a fachada importa de `remoteClient` mas nao nenhum nome conhecido; "
            f"viu {achados}"
        )

    def test_a_raiz_manda_os_gestos_pela_fachada(self):
        """O ponto exacto que estava partido, dito sem ambiguidade."""
        app = os.path.join(self.RAIZ, "App.tsx")
        fonte = open(app, encoding="utf-8").read()
        assert "from './src/services/remoteTransport'" in fonte, (
            "o App.tsx deixou de importar a fachada — e ele e quem envia o "
            "gesto que a camara capta para o PC"
        )
        assert "from './src/services/remoteClient'" not in fonte, (
            "o App.tsx voltou a importar o cliente cru"
        )
        # E tem de ser o `gesture` a passar por la: um import correcto que
        # ninguem usa nao corrige nada.
        assert re.search(r"remote\.gesture\(", fonte), (
            "a fachada esta importada mas o `gesture` nao e chamado — o import "
            "foi corrigido e o comando continua a nao sair"
        )


class _AdaptadorFalso:
    """Regista o que a Maouse manda pôr no `Adapter1` do BlueZ."""

    def __init__(self, inicial=False, falhar_em=()):
        self.inicial = inicial
        self.falhar_em = falhar_em
        self.escritos = []

    async def _adapter_prop(self, path, nome):
        return self.inicial

    async def _set_adapter_prop(self, path, nome, valor, assinatura):
        self.escritos.append((nome, valor, assinatura))
        if nome in self.falhar_em:
            return False
        return True


class TestAnuncioDoAdaptador:
    """O `Discoverable` do adaptador, que e o que faz o telefone encontrar o PC.

    Medido no `bluetoothd` real: o serviço GATT registava-se e o `bluetoothctl
    show` listava o UUID, mas o `Discoverable` ficava a `no` e um telefone a
    varrer nao via nada. O registo do GATT **nao** anuncia nada sozinho.
    """

    def _ble(self, adaptador):
        ble = remote_ble.RemoteBLE.__new__(remote_ble.RemoteBLE)
        ble._discoverable_antes = None
        ble._adapter_caminho = "/org/bluez/hci0"
        ble._adapter_prop = adaptador._adapter_prop
        ble._set_adapter_prop = adaptador._set_adapter_prop
        return ble

    def test_ligar_mete_discoverable_e_tira_o_timeout(self):
        """O timeout por omissao e 180s: aos 3 minutos o PC caca-se sozinho."""
        adaptador = _AdaptadorFalso(inicial=False)
        ble = self._ble(adaptador)

        assert asyncio.run(ble._advertise("/org/bluez/hci0", True)) is True
        assert ("DiscoverableTimeout", 0, "u") in adaptador.escritos, (
            "o DiscoverableTimeout ficou no omissao: o PC desaparece sozinho ao "
            "fim de 180 segundos, sem erro e sem log"
        )
        assert ("Discoverable", True, "b") in adaptador.escritos

    def test_o_timeout_vem_antes_do_discoverable(self):
        """Se inverter, o `Discoverable` liga com o timeout velho ainda la."""
        adaptador = _AdaptadorFalso(inicial=False)
        ble = self._ble(adaptador)

        asyncio.run(ble._advertise("/org/bluez/hci0", True))
        nomes = [e[0] for e in adaptador.escritos]
        assert nomes.index("DiscoverableTimeout") < nomes.index("Discoverable")

    def test_desligar_repõe_o_que_estava(self):
        """`Discoverable` e do adaptador, nosso nao: se o utilizador o tinha
        ligado para outra coisa, nao temos direito de o desligar por ele."""
        adaptador = _AdaptadorFalso(inicial=False)
        ble = self._ble(adaptador)
        asyncio.run(ble._advertise("/org/bluez/hci0", True))

        adaptador.escritos.clear()
        asyncio.run(ble._advertise("/org/bluez/hci0", False))
        assert adaptador.escritos == [("Discoverable", False, "b")]

    def test_desligar_respeita_o_que_ja_estava_ligado(self):
        adaptador = _AdaptadorFalso(inicial=True)
        ble = self._ble(adaptador)
        asyncio.run(ble._advertise("/org/bluez/hci0", True))

        adaptador.escritos.clear()
        asyncio.run(ble._advertise("/org/bluez/hci0", False))
        assert adaptador.escritos == [("Discoverable", True, "b")], (
            "tinhamos lido que o Discoverable estava `true` e na o desligámos "
            "mesmo assim: e um utilizaador, nao nosso, que o tinha ligado"
        )

    def test_o_antes_so_e_lido_uma_vez(self):
        """Se o relesse a cada `on`, um `on` no meio restore e voltava a ler
        `false` — o valor ja alterado por nos — e nunca mais se restaura."""
        adaptador = _AdaptadorFalso(inicial=False)
        ble = self._ble(adaptador)

        async def _cenario():
            await ble._advertise("/org/bluez/hci0", True)
            await ble._advertise("/org/bluez/hci0", False)
            await ble._advertise("/org/bluez/hci0", True)

        asyncio.run(_cenario())
        assert ble._discoverable_antes is False

    def test_timeout_recusado_nao_e_fatal(self):
        """O `DiscoverableTimeout` pode ser recusado; o `Discoverable=true` e o
        que interessa, e nao ha razao para nao tentar."""
        adaptador = _AdaptadorFalso(inicial=False, falhar_em=("DiscoverableTimeout",))
        ble = self._ble(adaptador)

        assert asyncio.run(ble._advertise("/org/bluez/hci0", True)) is True
        assert ("Discoverable", True, "b") in adaptador.escritos

    def test_se_o_discoverable_falhar_devolve_false(self):
        """O `start()` usa este booleano para avisar que o telefone nao vai
        encontrar o PC; devolver `true` a falhar era mentir em silencio."""
        adaptador = _AdaptadorFalso(inicial=False, falhar_em=("Discoverable",))
        ble = self._ble(adaptador)

        assert asyncio.run(ble._advertise("/org/bluez/hci0", True)) is False


class TestOsSinaisNaoDeixamOAdaptadorAnunciavel:
    """`SIGINT` e `SIGTERM` tem de fazer o mesmo: sair e repor o adaptador.

    Isto e um teste de fonte, e nao finge ser outra coisa. Medido com a Maouse
    real e o `bluetoothd` real (`/tmp/opencode/test_signal.sh`, que se lanca a
    aplicacao a serio, manda o sinal e mede `Discoverable` antes e depois): um
    `bluetoothd` num CI nao se instala. O que este teste prende e a correccao,
    que e o que se desfaz sem dar por isso.
    """

    def _main(self):
        with open(os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py"
        ), encoding="utf-8") as f:
            return f.read()

    def test_o_sigterm_esta_registado(self):
        """`kill`, o `systemd` e o logout mandam `SIGTERM`. Sem registo, o
        default mata o processo a meio e o adaptador fica anunciavel."""
        assert "signal(_sig.SIGTERM" in self._main(), (
            "o SIGTERM deixou de estar registado: um `kill` mata a Maouse sem "
            "teardown e o `Discoverable` fica em `true` para sempre"
        )

    def test_o_sigint_esta_registado(self):
        assert "signal(_sig.SIGINT" in self._main()

    def test_sair_pede_um_quit_e_nao_so_fechar_a_janela(self):
        """`window.close()` **nao** sai da aplicacao: com a bandeja a correr o
        `QApplication` fica vivo, a janela fecha e o processo fica la. Foi
        medido — o `Discoverable` voltava ao normal e a Maouse nao saia."""
        fonte = self._main()
        assert re.search(r"singleShot\(\s*0,\s*app\.quit\s*\)", fonte), (
            "fechar a janela nao encerra a aplicacao com a bandeja activa; o "
            "pedido de saida tem de ser `app.quit()`"
        )

    def test_o_sigterm_tem_rede_de_seguranca(self):
        """Se o event loop estiver preso, `quit()` nao chega a correr e quem
        mandou o sinal fica a espera de um `SIGKILL` que nao repõe nada."""
        assert re.search(r"singleShot\(\s*10000,\s*lambda: os\._exit\(0\)", self._main()), (
            "o SIGTERM ficou sem rede: um event loop preso deixa o `kill` a "
            "esperar e o adaptador anunciavel"
        )
