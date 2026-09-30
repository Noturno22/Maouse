"""Descoberta automatica do PC na rede local (mDNS).

O telefone precisa de encontrar o PC sem que ninguem escreva um IP a mao. Este
modulo e a metade do PC: anuncia `_maouse._tcp` por mDNS e publica a porta onde
o `core.remote.RemoteServer` esta a escutar. A metade do telefone
(`NsdManager`) e nativa do Android e vive em
`mobile/maouse-mobile/plugins/with-maouse-native/`.

Duas decisoes que nao sao obvias:

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
"""
from __future__ import annotations

import hashlib
import socket
import uuid

from zeroconf import ServiceInfo, Zeroconf

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


def device_id() -> str:
    """Identificador curto e opaco desta maquina, estavel entre arranques.

    Serve so para o telefone reconhecer "e o mesmo PC" entre sessoes. Nao e
    credencial e nao protege nada: quem quiser falar com o PC precisa do token.

    Deriva de `uuid.getnode()` (o MAC) por hash, e nao pelo MAC em claro,
    porque o anuncio e visivel por qualquer vizinho da rede.
    """
    return hashlib.sha256(f"maouse-{uuid.getnode()}".encode()).hexdigest()[:8]


class MaouseAdvertiser:
    """Anuncia o servidor remoto do PC em `_maouse._tcp` por mDNS.

    Uma instancia por processo. `start()` e `stop()` sao idempotentes e nunca
    levantam: uma falha de mDNS (sem Avahi, sem rede, interface a mudar) tem de
    custar ao utilizador a descoberta automatica e nada mais.
    """

    def __init__(self, cfg, name: str | None = None, zc_factory=None,
                 addresses=None):
        self._cfg = cfg
        self._zc_factory = zc_factory or Zeroconf
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

    def build_info(self) -> ServiceInfo | None:
        """Monta o `ServiceInfo`, ou `None` se nao ha endereco para anunciar."""
        addrs = self._lan_addresses()
        if not addrs:
            return None
        return ServiceInfo(
            _MDNS_TYPE,
            self.full_name(),
            port=int(self._cfg.remote_port),
            # mDNS e UDP/IPv4 aqui. `lan_ips()` ja devolve so IPv4 de rede
            # local, e suporte a IPv6 no browse do Android lida-se melhor
            # depois, com o telefone a escolher, do que adivinhado aqui.
            addresses=[socket.inet_aton(a) for a in addrs],
            properties=self._txt_properties(),
        )

    def start(self) -> bool:
        """Comeca a anunciar. Devolve `True` se o anuncio ficou registado."""
        if self._running:
            return True
        info = self.build_info()
        if info is None:
            log.info(
                "Descoberta mDNS desativada: sem endereco de rede local. "
                "O controlo remoto continua a funcionar com o IP escrito a mao."
            )
            return False
        try:
            zc = self._zc_factory()
        except Exception as e:
            # Sem Avahi, sem permissao, interface a cair: nenhuma destas e
            # motivo para a Maouse nao arrancar.
            log.info("Descoberta mDNS indisponivel (%s). Sem descoberta automatica.", e)
            return False
        try:
            zc.register_service(info)
        except Exception as e:
            log.info("Nao foi possivel anunciar %s por mDNS (%s).", SERVICE_TYPE, e)
            try:
                zc.close()
            except Exception:
                pass
            self._zc = None
            return False
        self._zc = zc
        self._info = info
        self._running = True
        log.info("Servico %s anunciado na porta %d.", SERVICE_TYPE,
                 int(self._cfg.remote_port))
        return True

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
