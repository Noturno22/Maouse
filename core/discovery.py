"""Descoberta automatica do PC na rede local (mDNS).

O telefone precisa de encontrar o PC sem que ninguem escreva um IP a mao. Este
modulo e a metade do PC: anuncia `_maouse._tcp` por mDNS e publica a porta onde
o `core.remote.RemoteServer` esta a escutar. A metade do telefone
(`NsdManager`) e nativa do Android e vive em
`mobile/maouse-mobile/plugins/with-maouse-native/`.

Quatro decisoes que nao sao obvias:

* **O token de autenticacao nunca vai nos TXT.** mDNS nao tem autenticacao:
  qualquer coisa na mesma rede le os TXT em claro, sempre que quiser. Um token
  nos TXT seria o mesmo que pregar a senha a porta da rua. O anuncio leva
  `v` (versao do protocolo) e `id` (identificador opaco da maquina), e nada
  mais; o token viaja so no primeiro comando `auth`, dentro de uma ligacao ja
  estabelecida. As chaves TXT sao uma *allowlist* (`_txt_properties`), nao uma
  blocklist, precisamente para que ninguem consiga acrescentar o token como
  se fosse mais um metadado.

* **Nao se anuncia nada sem interface.** Sem um endereco IPv4 de rede local, o
  SRV fica apontado para um sitio que nao responde e o telefone gasta a
  sondagem a falar com o vazio. Falha-se aqui, em silencio: o produto continua
  a funcionar com o IP escrito a mao, que e o que fazia antes de existir
  isto.

* **O `zeroconf` e importado aqui dentro, e nao no topo do modulo.** O
  `main.py` importa este modulo ao nivel do modulo, e um `ImportError` ai
  seria a Maouse a nao arrancar num ambiente onde o `zeroconf` nao chegou a
  ser instalado — trocava "sem descoberta automatica" por "sem Maouse". A
  promessa e o contrario, e a promessa e que vale: este e o unico sitio do
  produto que precisa do pacote.

* **O `id` sobrevive a arranques, mesmo sem hardware de que o tirar.**
  `uuid.getnode()` nao devolve sempre um endereco de hardware (ver
  `_hardware_id`), e sem isso o telefone via um "PC novo" a cada arranque.
"""
from __future__ import annotations

import hashlib
import os
import socket
import uuid

from config import user_data_dir
from core.log import get_logger

log = get_logger("discovery")

# Como o `NsdManager` do Android escreve o tipo, e sem ponto final. E o que se
# compara com o que a app le, para os dois lados dizerem a mesma coisa.
SERVICE_TYPE = "_maouse._tcp"

# O `zeroconf` exige o tipo qualificado: duas declaracoes, uma so constante
# publica. Sem isto, `ServiceInfo` levanta `BadTypeInNameException` a meio da
# construcao.
_MDNS_TYPE = SERVICE_TYPE + ".local."

# Versao do protocolo que o telefone tem de falar. Sobe quando o formato da
# ligacao mudar de forma incompativel, para um telefone antigo dizer "nao
# sei" em vez de ligar e falar coisas sem sentido.
PROTOCOL_VERSION = "1"

# Ficheiro onde se guarda o id gerado, para o caso de nao haver hardware de que
# o tirar. Ficheiro e nao `settings.json` porque este valor tem de sobreviver a
# um `settings.json` apagado, e nao pode ser uma preferencia que o utilizador
# apague sem saber o que esta a trocar.
_ID_FILE = "device_id"


def _zeroconf():
    """O modulo `zeroconf`, ou `None` se nao estiver instalado.

    O `ImportError` e apanhado aqui e nao no topo do modulo, e a raza esta no
    docstring: `main.py` importa este modulo ao nivel do modulo. Deixar a
    dependencia para dentro torna a falha *desta* funcionalidade e nao da
    aplicacao inteira.
    """
    try:
        import zeroconf
    except Exception as e:
        # Ausente,Versao incompativel, `.so` partido num ambiente alheio: nada
        # disto e motivo para a Maouse nao arrancar.
        log.info("Descoberta mDNS indisponivel (%s). Sem descoberta automatica.", e)
        return None
    return zeroconf


def _hardware_id() -> str | None:
    """Endereco de hardware desta maquina em hex, ou `None` se nao houver.

    O bit multicast do primeiro octeto diz o que o valor e. Por RFC 4122 (§4.5)
    um endereco com esse bit ligado **nao** e um IEEE address: e o valor
    pseudo-aleatorio que o `uuid` gera quando nao encontra hardware. Naquela
    maquina o id mudava de valor conforme o processo, porque o unico sitio que
    o memorizava era o modulo `uuid` — que morre com o processo.

    E por isso que o sinal tem de ser o bit, e nao "o `getnode()` devolveu
    alguma coisa": devolver alguma coisa e o caso normal, e nao prova nada.
    """
    try:
        node = int(uuid.getnode())
    except Exception:
        return None
    if node <= 0 or node >= (1 << 48):
        return None
    if (node >> 40) & 1:
        return None
    return f"{node:012x}"


def _generated_id() -> str:
    """Id aleatorio de 8 hex, guardado no directorio do utilizador.

    So e usado quando `_hardware_id()` nao devolve nada. Se a gravacao falhar
    (sem permissao, disco cheio) o id do processo fica assim mesmo — o
    telefone veria um "PC novo" neste arranque, que e melhor do que a
    aplicacao nao arrancar.
    """
    path = os.path.join(user_data_dir(), _ID_FILE)
    try:
        with open(path, encoding="utf-8") as fh:
            guardado = fh.read().strip()
        if guardado:
            return guardado
    except OSError:
        pass
    gerado = uuid.uuid4().hex[:8]
    try:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(gerado)
    except OSError as e:
        log.info("Nao foi possivel guardar o id desta maquina (%s).", e)
    return gerado


def device_id() -> str:
    """Identificador curto e opaco desta maquina, estavel entre arranques.

    Serve so para o telefone reconhecer "e o mesmo PC" entre sessoes. Nao e
    credencial e nao protege nada: quem quiser falar com o PC precisa do token.

    Deriva de `uuid.getnode()` **quando esse valor e mesmo um endereco de
    hardware** (ver `_hardware_id`), e nao pelo MAC em claro, porque o anuncio
    e visivel por qualquer vizinho da rede. Sem hardware de que tirar, deriva
    de um id guardado em disco — a alternativa, derivar do valor pseudo-aleatorio
    do `uuid`, dava um PC diferente a cada arranque.
    """
    material = _hardware_id() or _generated_id()
    return hashlib.sha256(f"maouse-{material}".encode()).hexdigest()[:8]


class MaouseAdvertiser:
    """Anuncia o servidor remoto do PC em `_maouse._tcp` por mDNS.

    Uma instancia por processo. `start()` e `stop()` sao idempotentes e nunca
    levantam: uma falha de mDNS (sem Avahi, sem rede, interface a mudar) tem de
    custar ao utilizador a descoberta automatica e nada mais.
    """

    def __init__(self, cfg, name: str | None = None, zc_factory=None,
                 addresses=None):
        self._cfg = cfg
        # `None` significa "usa o `Zeroconf` de verdade, resolvido no `start()`".
        # Nao se pode guardar a classe no construtor: isso tornaria o import de
        # `zeroconf` obrigatorio no momento em que este objecto e criado, que
        # e antes de se saber se a descoberta esta sequer ligada.
        self._zc_factory = zc_factory
        # Enderecos a anunciar. Por omissao, os IPv4 de rede local desta
        # maquina (ver `core.remote.lan_ips`). Injetavel para os testes
        # correrem sem rede.
        self._addresses = addresses
        # `zeroconf` exige que o nome da instancia seja unico dentro do tipo.
        # Derivar do id evita a colisao de dois PCs com o mesmo nome: o segundo
        # a registar seria silenciosamente renomeado pelo daemon, e o telefone
        # veria um "Maouse-2" que ninguem reconhece.
        self._name = name or f"Maouse {device_id()}"
        self._zc = None
        self._info = None
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    @property
    def port(self) -> int | None:
        """A porta anunciada neste momento, ou `None` se nao ha anuncio.

        E o que a janela usa para decidir se republica: o anuncio tem de
        seguir a porta do servidor, e sem isto mudava-se a porta e o telefone
        continuava a encontrar o PC na antiga.
        """
        return self._info.port if self._info is not None else None

    @property
    def info(self):
        """O `ServiceInfo` registado, ou `None` se nunca arrancou.

        Existe para os testes e para diagnostico; o resto do produto usa
        `running`.
        """
        return self._info

    def _txt_properties(self) -> dict:
        """TXT do anuncio — allowlist fechada.

        Se acrescentar aqui uma chave, ela passa a ir em claro para toda a
        rede. O token nao entra, e a raza esta no docstring do modulo.
        """
        return {
            b"v": PROTOCOL_VERSION.encode(),
            b"id": device_id().encode(),
        }

    def _lan_addresses(self) -> list:
        if self._addresses is not None:
            return list(self._addresses)
        from core.remote import lan_ips

        return lan_ips()

    def full_name(self) -> str:
        """Nome completo da instancia: `rotulo._maouse._tcp.local.`.

        O ponto entre o rotulo e o tipo e obrigatorio e nao decorativo. O
        `zeroconf` separa o rotulo do tipo pelo ultimo `._`; sem o ponto, um
        rotulo que acabe em digito (que e o caso do `device_id()`) cola o
        `_maouse` ao numero e o analisador deixa de reconhecer o tipo, com um
        `BadTypeInNameException` a dizer que o nome "nao comeca por _" — uma
        mensagem que aponta completamente para o lado errado.
        """
        return f"{self._name}.{_MDNS_TYPE}"

    def build_info(self):
        """Monta o `ServiceInfo`, ou `None` se nao ha o que anunciar.

        `None` cobre duas situacoes — nao ha `zeroconf` instalado, ou nao ha
        endereco de rede local — porque em ambas nao ha anuncio possivel e
        nenhuma delas e erro.
        """
        zc = _zeroconf()
        if zc is None:
            return None
        addrs = self._lan_addresses()
        if not addrs:
            return None
        return self._build_info(addrs, zc)

    def _build_info(self, addrs, zc):
        """O `ServiceInfo` a partir do que ja esta resolvido, ou `None`.

        O `try` e porque `socket.inet_aton` levanta com um endereco mal
        formado, e `lan_ips()` filtra os enderecos que nao presta mas nao
        valida o resto. Um `start()` que levanta por causa de um endereco
        estragado no `settings.json` de outra pessoa seria exactamente o
        oposto do que este modulo promete.
        """
        try:
            return zc.ServiceInfo(
                _MDNS_TYPE,
                self.full_name(),
                port=int(self._cfg.remote_port),
                # mDNS e UDP/IPv4 aqui. `lan_ips()` ja devolve so IPv4 de rede
                # local, e suporte a IPv6 no browse do Android lida-se melhor
                # depois, com o telefone a escolher, do que adivinhado aqui.
                addresses=[socket.inet_aton(a) for a in addrs],
                properties=self._txt_properties(),
            )
        except Exception as e:
            log.info("Anuncio mDNS mal formado (%s). Sem descoberta automatica.", e)
            return None

    def start(self) -> bool:
        """Comeca a anunciar. Devolve `True` se o anuncio ficou registado."""
        if self._running:
            return True
        zc = _zeroconf()
        if zc is None:
            return False
        addrs = self._lan_addresses()
        if not addrs:
            log.info(
                "Descoberta mDNS desativada: sem endereco de rede local. "
                "O controlo remoto continua a funcionar com o IP escrito a mao."
            )
            return False
        info = self._build_info(addrs, zc)
        if info is None:
            return False
        try:
            zc_instance = (self._zc_factory or zc.Zeroconf)()
        except Exception as e:
            # Sem Avahi, sem permissao, interface a cair: nenhuma destas e
            # motivo para a Maouse nao arrancar.
            log.info("Descoberta mDNS indisponivel (%s). Sem descoberta automatica.", e)
            return False
        try:
            zc_instance.register_service(info)
        except Exception as e:
            log.info("Nao foi possivel anunciar %s por mDNS (%s).", SERVICE_TYPE, e)
            try:
                zc_instance.close()
            except Exception:
                pass
            self._zc = None
            return False
        self._zc = zc_instance
        self._info = info
        self._running = True
        log.info("Servico %s anunciado na porta %d.", SERVICE_TYPE,
                 int(self._cfg.remote_port))
        return True

    def restart(self) -> bool:
        """Republica o anuncio, para apanhar uma porta ou uma rede nova.

        Nao e um `start()` a mais: `start()` com o anuncio ja em ar devolvia
        `True` sem mudar nada, que e o comportamento certo para quem so quer
        "anuncia se ainda nao anuncia" e o errado para quem acaba de mudar a
        porta do servidor. Devolve `True` se o anuncio ficou registado, tal
        como `start()`.
        """
        self.stop()
        return self.start()

    def stop(self) -> None:
        """Deixa de anunciar. Seguro de chamar mesmo sem `start()`."""
        zc, info = self._zc, self._info
        self._zc = None
        self._info = None
        self._running = False
        if zc is None:
            return
        # Retirar o anuncio antes de fechar: fechar a interface sozinha deixa
        # o registo a expirar por TTL, e durante esse intervalo o telefone
        # continua a encontrar um PC que ja nao responde. Chamar `stop()` duas
        # vezes seguidas tem de ser inofensivo, e e por isso que `zc` e `info`
        # sao limpos ANTES do trabalho: a segunda chamada ja nao tem nada.
        if info is not None:
            try:
                zc.unregister_service(info)
            except Exception as e:
                log.debug("Retirada do anuncio mDNS falhou: %s", e)
        try:
            zc.close()
        except Exception as e:
            log.debug("Fecho do zeroconf falhou: %s", e)
