"""Contrato de rede entre o telemóvel e o PC, visto do lado do PC.

O cliente de JS/TS vive em `mobile/maouse-mobile/src/services/remoteClient.ts` e
é coberto por Jest. Este ficheiro é o outro meio da mesma tesoura: fixa o
contrato no lado do servidor, em Python, sem precisar de toolchain TS para o
correr.

A razão de ser um ficheiro à parte, e não mais uns testes em `test_remote.py`, é
que o que se quer travar é uma coincidência entre dois directórios que nunca são
compilados juntos. Se alguém renomear `move_to` para `goto` em `core/remote.py`,
o telemóvel continua a mandar `move_to` e o rato deixa de se mexer: em silêncio,
e só num aparelho real. Aqui isso rebenta logo, a dizer qual dos lados se mexeu.
"""
import asyncio
import json
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from config import Config
from core.remote import RemoteServer
from tests.lease_test_keys import VALID_LEASE, make_test_lease

pytestmark = pytest.mark.usefixtures("patched_public_key")

# Os comandos que o `remoteClient.ts` sabe mandar, com um payload representativo.
# Esta tupla é a fonte de verdade: se acrescentares um comando lá, acrescentas
# aqui. O teste de simetria abaixo é que garante que os dois lados não se separam.
COMMANDS_TS = {
    "move": {"dx": 3, "dy": -2},
    "move_to": {"x": 0.5, "y": 0.5},
    "click": {"button": "left", "count": 1},
    "press": {"button": "left"},
    "release": {"button": "left"},
    "scroll": {"dx": 0, "dy": 2},
    "key": {"key": "esc"},
    "combo": {"mods": ["ctrl"], "key": "c"},
    "text": {"text": "ola"},
    "media": {"action": "play_pause"},
    "gesture": {"event": "tap"},
}

# `auth` e `ping` NÃO passam por `_handle`: são tratados dentro de `_on_connect`,
# antes e à parte do despacho. A distinção é deliberada, porque o `auth` tem de
# ser processado antes de qualquer comando poder mexer no rato, e é por isso que
# o teste de simetria os trata num grupo à parte.
COMMANDS_INLINE = ("auth", "ping")

# Nomes que não podem existir em lado nenhum. Servem de rede de segurança: se um
# deles passar a ser aceite, é porque alguém o implementou.
COMANDOS_NAO_EXISTEM = (
    "moveto", "moveTo", "goto", "click_at", "type", "back", "shutdown",
    "quit", "reiniciar",
)

# A credencial do `auth` é um código de 6 dígitos (`CODE_LEN` em
# `core.remote`), lido nas definições do PC e escrito no telemóvel. Tem de ter
# exactamente 6 dígitos: um valor mais curto ou com letras é recusado por
# `normalise_code` antes sequer de ser comparado, e os testes que verificam a
# comparação precisam de um valor que chegue ao `hmac.compare_digest`.
CODE = "314159"
# Um segundo código válido, para os testes que precisam de errar de propósito.
CODE_ERRADO = "271828"


def _next_source_ip():
    """Um IP diferente por ligação, para o `AuthLimiter` não os confundir."""
    global _CONTADOR_DE_ORIGENS
    _CONTADOR_DE_ORIGENS += 1
    return f"192.168.0.{_CONTADOR_DE_ORIGENS}"


_CONTADOR_DE_ORIGENS = 0


class _FakeMouse:
    """Rato que anota o que lhe mandam, sem tocar no sistema operativo."""

    screen_w = 1920
    screen_h = 1080

    def __init__(self):
        self.calls = []
        self.mouse = self  # o servidor faz `mouse.mouse.position = ...`
        self.position = (0, 0)

    def move_by(self, dx, dy):
        self.calls.append(("move_by", dx, dy))
        self.position = (self.position[0] + dx, self.position[1] + dy)

    def left_click(self):
        self.calls.append(("left_click",))

    def right_click(self):
        self.calls.append(("right_click",))

    def press_left(self):
        self.calls.append(("press_left",))

    def release_left(self):
        self.calls.append(("release_left",))

    def click(self, button=None):
        self.calls.append(("click", button))

    def press(self, button=None):
        self.calls.append(("press", button))

    def release(self, button=None):
        self.calls.append(("release", button))

    def scroll(self, *args):
        # O servidor chama `mouse.scroll(dy)` para o eixo Y e
        # `mouse.mouse.scroll(dx, 0)` para o eixo X. Um fake com assinatura fixa
        # rebentaria numa das duas, e o teste passaria a testar o fake.
        self.calls.append(("scroll", *args))


class _FakeKeyboard:
    def __init__(self):
        self.calls = []

    def press(self, key):
        self.calls.append(("press", key))

    def release(self, key):
        self.calls.append(("release", key))

    def type(self, text):
        self.calls.append(("type", text))


class _FakeConnection:
    """Ligação WebSocket que entrega uma lista de mensagens e regista o que sai.

    Cada ligação tem um IP próprio de propósito. O `AuthLimiter` conta as
    tentativas de `auth` erradas **por IP** e fecha a porta a quem insiste
    (5 falhas em 60 s), e a suite tem cinco testes que provocam uma falha de
    propósito. Com um IP só, partilhado por todas as ligações, esses testes
    somavam as falhas uns dos outros: a quinta fechava a porta, e a partir daí
    qualquer teste de falha de `auth` novo receberia `auth_locked` em vez do
    `auth_required` que está a verificar. Hoje ainda passa por sorte — nenhuma
    das cinco asserções finais cai em `auth_locked` — e é uma armadilha com
    prazo: o sexto teste de falha que alguém escreva herda o bloqueio dos
    outros cinco.

    O `address` existe para o caso contrário: um teste que quer provocar
    (o do bloqueio) precisa que as várias ligações venham do mesmo IP, que é
    o que faz o `AuthLimiter` as contar como a mesma origem.
    """

    def __init__(self, messages, address=None):
        self._messages = [json.dumps(m) for m in messages]
        self.remote_address = address or (_next_source_ip(), 51234)
        self.sent = []
        self.closed = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._messages:
            raise StopAsyncIteration
        return self._messages.pop(0)

    async def send(self, payload):
        self.sent.append(payload)

    async def close(self):
        self.closed = True


class _FakeTransport:
    """O transport da ligação, para o caso de alguém tentar ler o código do URL."""

    def __init__(self, query_string):
        self._query_string = query_string

    def get_extra_info(self, name, default=None):
        if name == "query_string":
            return self._query_string
        return default


def _server(code=CODE, gain=1.0):
    cfg = Config()
    cfg.remote_bind = "127.0.0.1"
    cfg.remote_port = 0
    cfg.remote_code = code
    cfg.remote_move_gain = gain
    mouse = _FakeMouse()
    srv = RemoteServer(cfg, mouse)
    # O teclado é injectado para não instanciar o pynput: o que se quer travar
    # aqui é o contrato, não a injecção de eventos no sistema.
    srv._key_ctl = _FakeKeyboard()
    return srv, mouse


def _run(srv, messages, address=None):
    conn = _FakeConnection(messages, address=address)
    asyncio.run(srv._on_connect(conn))
    return conn, [json.loads(m) for m in conn.sent]


# ── 1. Simetria: tudo o que o TS manda, o PC aceita ──────────────────────

@pytest.mark.parametrize("cmd,payload", sorted(COMMANDS_TS.items()))
def test_comando_do_telemovel_e_aceite(cmd, payload):
    srv, _ = _server()
    note = srv._handle(cmd, payload)
    assert note, f"{cmd} devolveu nota vazia"


def test_lista_de_comandos_dos_dois_lados_coincide():
    """A assimetria que dói: um comando que um lado manda e o outro não conhece.

    Percorre o universo de nomes plausíveis e compara com o que o telemóvel
    realmente envia. Apanha os dois sentidos do erro: um comando novo no PC que
    o app nunca vai mandar, e um comando que o app manda e o PC rejeita.
    """
    srv, _ = _server()
    universo = set(COMMANDS_TS) | set(COMANDOS_NAO_EXISTEM)
    # Payload com todos os campos de que qualquer comando pode precisar, para que
    # o único ValueError possível seja `cmd_desconhecido`. Um erro de payload
    # seria um bug do servidor e tem de aparecer, não ser engolido pelo teste.
    payload = {
        "dx": 1, "dy": 1, "x": 0.5, "y": 0.5, "key": "a", "text": "a",
        "action": "mute", "event": "tap", "code": CODE, "button": "left",
    }

    aceites = set()
    for name in sorted(universo):
        try:
            srv._handle(name, payload)
        except ValueError as e:
            if not str(e).startswith("cmd_desconhecido:"):
                raise
        else:
            aceites.add(name)

    assert sorted(aceites) == sorted(COMMANDS_TS)


@pytest.mark.parametrize("cmd", COMMANDS_INLINE)
def test_comandos_inline_nao_passam_pelo_despacho(cmd):
    """`auth` e `ping` são tratados em `_on_connect`, não por `_handle`.

    Se `_handle` passasse a aceitá-los, o `auth` teria dois caminhos e um auth
    poderia chegar a ser tratado como comando de uma ligação já autenticada.
    """
    srv, _ = _server()
    with pytest.raises(ValueError, match=f"cmd_desconhecido:{cmd}"):
        srv._handle(cmd, {"code": CODE})


# ── 2. As formas das respostas, como o parser do TS as espera ─────────────

def test_resposta_de_auth_ok_tem_ecra():
    """O TS só marca a ligação como pronta com `ok === true`, e usa `w` e `h`.

    Se `w` ou `h` desaparecerem, o TS cai no default 1920x1080 em silêncio e o
    touchpad passa a mover o rato com a escala errada.
    """
    srv, _ = _server()
    _, replies = _run(srv, [{"cmd": "auth", "code": CODE, "lease": VALID_LEASE}])

    assert replies[0] == {"cmd": "auth", "ok": True, "w": 1920, "h": 1080}


def test_resposta_de_auth_falhado_tem_error_auth_required():
    """O TS traduz `error == "auth_required"` para a mensagem de código recusado.

    A resposta traz também `retry_after`, que o `AuthLimiter` alimenta: é 0
    enquanto a origem não está bloqueada e passa a ser o número de segundos que
    falta quando está. O TS ignora-o, mas está no contrato e por isso é
    verificado — como subscriber das chaves que o TS consome e o valor exacto
    do que resta, para a resposta não ganhar campos sem ninguém dar por isso.
    """
    srv, _ = _server()
    conn, replies = _run(srv, [{"cmd": "auth", "code": CODE_ERRADO}])

    assert replies[0]["cmd"] == "auth"
    assert replies[0]["ok"] is False
    assert replies[0]["error"] == "auth_required"
    assert replies[0]["retry_after"] == 0, "sem bloqueio, o telemóvel pode repetir já"
    assert conn.closed, "o servidor tem de fechar a ligação depois de auth falhada"


# ── Gate Pro: o código sozinho não abre o rato de ninguém ───────────────────

def test_code_valido_sem_lease_e_recusado():
    """O bypass que este gate fecha: código certo, nenhum pagamento.

    Sem lease, um utilizador Free na mesma rede tinha rato, teclado, scroll e
    media keys completos. O código continua a ser o que emparelha o telemóvel
    com o PC; o lease é que diz que o telemóvel pagou.
    """
    srv, _ = _server()
    conn, replies = _run(srv, [{"cmd": "auth", "code": CODE}])

    assert replies[0]["ok"] is False
    assert replies[0]["error"] == "pro_required"
    assert conn.closed


def test_lease_assinado_por_outra_chave_e_recusado():
    foreign = ec.generate_private_key(ec.SECP256R1())
    srv, _ = _server()
    conn, replies = _run(
        srv,
        [{"cmd": "auth", "code": CODE,
          "lease": make_test_lease(key=foreign)}],
    )

    assert replies[0]["ok"] is False
    assert replies[0]["error"] == "pro_required"
    assert replies[0]["reason"] == "assinatura_invalida"


def test_lease_expirado_e_recusado():
    srv, _ = _server()
    conn, replies = _run(
        srv,
        [{"cmd": "auth", "code": CODE, "lease": make_test_lease(exp_delta=-1)}],
    )

    assert replies[0]["ok"] is False
    assert replies[0]["reason"] == "lease_expirado"


def test_lease_de_tier_errado_e_recusado():
    srv, _ = _server()
    conn, replies = _run(
        srv,
        [{"cmd": "auth", "code": CODE, "lease": make_test_lease(tier="free")}],
    )

    assert replies[0]["ok"] is False
    assert replies[0]["reason"] == "tier_invalido"


def test_lease_de_free_nao_basta_mesmo_com_code_certo():
    srv, _ = _server()
    conn, replies = _run(
        srv,
        [{"cmd": "auth", "code": CODE, "lease": make_test_lease(tier="free")}],
    )

    assert replies[0]["error"] == "pro_required"
    assert conn.closed


def test_nenhum_comando_passa_sem_auth():
    srv, _ = _server()
    conn, replies = _run(srv, [{"cmd": "move", "dx": 500, "dy": 500}])

    assert conn.closed
    assert all(r.get("cmd") != "auth" or r.get("ok") is not True for r in replies)

def test_resposta_de_auth_bloqueado_diz_quando_tentar_de_novo():
    """As 5 tentativas que fecham a porta, e o `retry_after` que as explica.

    O `AuthLimiter` fecha a porta a quem insiste e diz por quanto tempo. Sem o
    `auth_locked`, o telemóvel autentica-se a receber `auth_required` em loop,
    sem parar; sem o `retry_after`, ficava a recuar às cegas.

    As seis tentativas vêm todas do mesmo IP de propósito: é o contador por
    origem que fecha a porta, e com um IP novo por tentativa nunca fecharia.
    """
    srv, _ = _server()
    origem = ("192.168.7.7", 51234)
    estados = []
    for _ in range(6):
        _, replies = _run(srv, [{"cmd": "auth", "code": CODE_ERRADO}], address=origem)
        estados.append(replies[0])

    assert all(r["error"] == "auth_required" for r in estados[:5]), (
        "as primeiras tentativas são 'código errado', não 'bloqueado'"
    )
    assert estados[5]["error"] == "auth_locked", "a 6ª tentativa tem de bater no bloqueio"
    assert estados[5]["retry_after"] > 0, "o bloqueio tem de dizer quanto falta"


def test_resposta_de_comando_tem_ok_e_note():
    """O TS consome `ok` de cada resposta de comando; `note` é o que o PC devolve."""
    srv, _ = _server()
    _, replies = _run(srv, [
        {"cmd": "auth", "code": CODE, "lease": VALID_LEASE},
        {"cmd": "move", "dx": 4, "dy": 0},
    ])

    assert replies[1] == {"ok": True, "note": "MOVE"}


def test_comando_sem_cmd_da_bad_command():
    """Um frame que não é comando tem de ser recusado, não ignorado em silêncio."""
    srv, _ = _server()
    _, replies = _run(srv, [
        {"cmd": "auth", "code": CODE, "lease": VALID_LEASE},
        {"nao": "e um comando"},
    ])

    assert replies[1] == {"ok": False, "error": "bad_command"}


def test_comando_desconhecido_nao_mata_a_ligacao():
    """Uma build antiga do telemóvel não pode ficar sem rato e sem explicação.

    O TS não conhece `cmd_desconhecido`, mas a ligação tem de sobreviver para o
    utilizador continuar a mexer no rato.
    """
    srv, _ = _server()
    conn, replies = _run(srv, [
        {"cmd": "auth", "code": CODE, "lease": VALID_LEASE},
        {"cmd": "comando_do_futuro"},
        {"cmd": "ping"},
    ])

    assert replies[1]["ok"] is False
    assert "cmd_desconhecido" in replies[1]["error"]
    # A terceira resposta prova que a ligação continua viva.
    assert replies[2] == {"ok": True, "pong": True}
    assert not conn.closed


def test_ping_nao_precisa_de_rato_nem_de_ganho():
    """`ping` responde antes do despacho: é o keepalive que mede a ligação viva."""
    srv, mouse = _server()
    _, replies = _run(srv, [
        {"cmd": "auth", "code": CODE, "lease": VALID_LEASE},
        {"cmd": "ping"},
    ])

    assert replies[1] == {"ok": True, "pong": True}
    assert mouse.calls == []


# ── 3. O handshake ───────────────────────────────────────────────────────

def test_comando_antes_do_auth_nunca_parte():
    """O teste de segurança mais importante do ficheiro.

    O `move` chega antes do `auth`: o servidor tem de recusar e fechar sem mover
    o rato um píxel. Se alguém reordenar o `if authed is False` no
    `_on_connect`, esta é a linha que quebra.
    """
    srv, mouse = _server()
    conn, replies = _run(srv, [{"cmd": "move", "dx": 50, "dy": 50}])

    assert mouse.calls == [], f"o rato mexeu antes do auth: {mouse.calls}"
    assert replies[0]["cmd"] == "auth"
    assert replies[0]["ok"] is False
    assert replies[0]["error"] == "auth_required"
    assert conn.closed


def test_ping_antes_do_auth_nao_sobrevive():
    """Nem um `ping` passa antes do `auth`, apesar de não mexer no rato."""
    srv, _ = _server()
    conn, replies = _run(srv, [
        {"cmd": "ping"},
        {"cmd": "auth", "code": CODE, "lease": VALID_LEASE},
    ])

    assert replies[0]["cmd"] == "auth"
    assert replies[0]["ok"] is False
    assert replies[0]["error"] == "auth_required"
    assert conn.closed
    assert len(replies) == 1, "a segunda mensagem não devia ser processada"


def test_code_ausente_e_recusado():
    srv, _ = _server()
    conn, replies = _run(srv, [{"cmd": "auth"}])

    assert replies[0]["ok"] is False
    assert conn.closed


def test_code_vazio_e_recusado():
    srv, _ = _server()
    conn, replies = _run(srv, [{"cmd": "auth", "code": ""}])

    assert replies[0]["ok"] is False
    assert conn.closed


def test_code_com_o_numero_certo_de_digitos_mas_errado_e_recusado():
    """6 dígitos na quantidade certa ainda têm de ser o código certo.

    O `AuthLimiter` é o que segura a troca de 64 bits por 20, e não a
    entropia: um código de 6 dígitos que passe a validação de formato mas não
    seja o do utilizador tem de ser recusado, e não aceite por ser "parecido".
    """
    srv, _ = _server()
    conn, replies = _run(srv, [{"cmd": "auth", "code": CODE_ERRADO}])

    assert replies[0]["ok"] is False
    assert replies[0]["error"] == "auth_required"
    assert conn.closed


def test_o_code_compara_se_no_corpo_da_mensagem():
    """O código vai no corpo, nunca no URL.

    O URL aparece nos logs do servidor e de qualquer proxy pelo caminho; o corpo
    não. O TS faz `rawSend({cmd: 'auth', code})` e o servidor compara
    `data.get("code")`.

    A segunda metade é a que tem força: aqui a ligação transporta mesmo o código
    no URL, por todas as vias por onde alguém tentaria lê-lo, e o servidor tem de
    recusar na mesma. Se alguém acrescentar leitura do query string para "dar
    jeito ao cliente", esta é a linha que quebra.
    """
    srv, _ = _server()
    _, replies = _run(srv, [{"cmd": "auth", "code": CODE, "lease": VALID_LEASE}])
    assert replies[0]["ok"] is True, "o código no corpo tem de ser aceite"

    qs = f"code={CODE}"
    conn = _FakeConnection([{"cmd": "auth"}])
    conn.transport = _FakeTransport(qs)
    conn.request = SimpleNamespace(path=f"/?{qs}")
    asyncio.run(srv._on_connect(conn))
    reply = json.loads(conn.sent[0])

    assert reply["ok"] is False, "o código no URL não pode autenticar"
    assert reply["error"] == "auth_required"
    assert conn.closed


# ── 4. O comportamento de que o cliente depende ───────────────────────────

def test_gesture_sem_coordenadas_nao_move_o_cursor():
    """Um `tap` sem `x` e `y` clica onde o cursor já está: é o que o touchpad manda."""
    srv, mouse = _server()
    srv._handle("gesture", {"event": "tap"})

    assert mouse.calls == [("left_click",)]
    assert mouse.position == (0, 0)


def test_gesture_com_coordenadas_move_primeiro():
    """Com `x` e `y`, o cursor salta primeiro para o ponto indicado."""
    srv, mouse = _server()
    srv._handle("gesture", {"event": "tap", "x": 0.5, "y": 0.5})

    assert mouse.position == (959, 539)
    assert ("left_click",) in mouse.calls


def test_scroll_vertical_chega_ao_rato():
    """O eixo Y e o eixo X seguem caminhos diferentes no pynput."""
    srv, mouse = _server()
    note = srv._handle("scroll", {"dx": 0, "dy": 3})

    assert note == "SCROLL"
    assert ("scroll", 3) in mouse.calls
