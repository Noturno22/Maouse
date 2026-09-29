"""Testes da descoberta mDNS do PC (core.discovery).

O teste que realmente importa aqui e `test_token_nunca_vai_nos_txt`: os TXT de
mDNS sao lidos em claro por tudo o que esteja na rede, sem autenticacao nem
permissao. Se o token acabar la, qualquer vizinho do WiFi entra no PC. Os
restes existem porque a alternativa a mDNS funcionar e a Maouse nao arrancar, e
isso nao pode depender de o Avahi estar instalado.
"""
import pytest

from config import Config
from core.discovery import (
    _MDNS_TYPE,
    SERVICE_TYPE,
    MaouseAdvertiser,
    device_id,
)

TOKEN = "e7f3a9c1b2d40856"
ENDERECO = "192.168.0.10"


class FakeZC:
    """Zeroconf que regista o que lhe mandam, sem tocar na rede."""

    def __init__(self):
        self.registered = []
        self.unregistered = []
        self.closed = 0

    def register_service(self, info):
        self.registered.append(info)

    def unregister_service(self, info):
        self.unregistered.append(info)

    def close(self):
        self.closed += 1


class ZCQueNaoConstrói:
    def __init__(self, exc):
        self._exc = exc

    def __call__(self):
        raise self._exc


class ZCQueFalhaNoRegister(FakeZC):
    def register_service(self, info):
        raise RuntimeError("sem avahi por aqui")


def _cfg(**kw):
    cfg = Config()
    cfg.remote_port = 8765
    cfg.remote_token = TOKEN
    for k, v in kw.items():
        setattr(cfg, k, v)
    return cfg


def _adv(**kw):
    kw.setdefault("cfg", _cfg())
    kw.setdefault("zc_factory", FakeZC)
    kw.setdefault("addresses", [ENDERECO])
    return MaouseAdvertiser(**kw)


# ── A identidade do anuncio ────────────────────────────────────────────────

def test_tipo_de_servico_como_o_android_escreve():
    # O Android grava o tipo sem ponto final. E o mesmo tipo que o `zeroconf`
    # quer qualificado, por isso as duas formas tem de sair daqui.
    assert SERVICE_TYPE == "_maouse._tcp"
    assert _MDNS_TYPE == "_maouse._tcp.local."


def test_nome_completo_tem_o_ponto_que_separa_o_rotulo():
    # Regressao. O `zeroconf` separa o rotulo do tipo pelo ultimo `._`. O
    # rotulo por omissao acaba em digito (o `device_id`), e sem o ponto o
    # `_maouse` cola-se ao numero: o tipo deixa de ser reconhecido e o erro
    # que sai diz que o nome "nao comeca por _", a apontar para o sitio errado.
    adv = _adv()
    assert adv.full_name() == f"Maouse {device_id()}._maouse._tcp.local."
    assert f"{device_id()}." in adv.full_name()


@pytest.mark.parametrize("rotulo", ["Maouse", "PC da Sala", "a1b2c3d4", "x"])
def test_nome_completo_e_aceite_pelo_zeroconf(rotulo):
    # O `build_info` levanta se o nome estiver mal, e um nome mal so rebenta
    # no arranque da Maouse — ou seja, no sitio mais caro possivel.
    info = _adv(name=rotulo).build_info()
    assert info.name == f"{rotulo}._maouse._tcp.local."
    assert info.type == "_maouse._tcp.local."


def test_porta_anunciada_e_a_do_servidor_real():
    info = _adv(cfg=_cfg(remote_port=9123)).build_info()
    assert info.port == 9123


def test_endereco_anunciado_e_o_de_rede_local():
    import socket

    info = _adv(addresses=[ENDERECO, "192.168.0.11"]).build_info()
    assert [socket.inet_ntoa(a) for a in info.addresses] == [
        ENDERECO,
        "192.168.0.11",
    ]


def test_device_id_e_curto_estavel_e_nao_o_mac():
    a, b = device_id(), device_id()
    assert a == b, "o id tem de sobreviver a arranques, e o telefone precisa dele"
    assert len(a) == 8
    int(a, 16)  # hexadecimal puro


# ── O teste que segura a porta ─────────────────────────────────────────────

def test_token_nunca_vai_nos_txt():
    # mDNS nao tem autenticacao: os TXT sao lidos em claro por qualquer
    # coisa na rede, sempre que quiser. Um token aqui e o mesmo que pregar a
    # senha a porta da rua. Se este teste falhar, alguem met um campo novo no
    # `_txt_properties` e nao pensou nisto.
    adv = _adv(cfg=_cfg(remote_token=TOKEN))
    info = adv.build_info()
    assert TOKEN.encode() not in info.text
    assert TOKEN not in info.name
    assert TOKEN not in str(info.server)
    assert TOKEN not in repr(info.addresses)


def test_txt_e_uma_allowlist_fechada():
    # Nao e uma blocklist. Uma chave nova nao entra por omissao, tem de ser
    # escrita aqui — e e ai que se repara no que vai sair em claro.
    chaves = set(_adv()._txt_properties())
    assert chaves == {b"v", b"id"}


def test_txt_nao_tem_so_o_id():
    # Um TXT vazio seria o mais seguro de todos, e nao serve: sem `v` o
    # telefone nao sabe se fala o mesmo protocolo, e sem `id` nao reconhece o
    # mesmo PC entre sessoes.
    props = _adv()._txt_properties()
    assert props[b"v"] == b"1"
    assert props[b"id"] == device_id().encode()


# ── Arrancar e parar sem partir a Maouse ───────────────────────────────────

def test_start_regista_o_anuncio():
    zc = FakeZC()
    adv = _adv(zc_factory=lambda: zc)
    assert adv.start() is True
    assert adv.running is True
    assert len(zc.registered) == 1
    assert zc.registered[0].name == adv.full_name()


def test_start_duas_vezes_registra_so_uma():
    zc = FakeZC()
    adv = _adv(zc_factory=lambda: zc)
    adv.start()
    assert adv.start() is True, "ja esta a anunciar"
    assert len(zc.registered) == 1


def test_stop_retira_o_anuncio_antes_de_fechar():
    # Fechar a interface sozinha deixa o registo a expirar por TTL, e nesse
    # intervalo o telefone ainda encontra um PC que ja nao responde.
    zc = FakeZC()
    adv = _adv(zc_factory=lambda: zc)
    adv.start()
    adv.stop()
    assert len(zc.unregistered) == 1
    assert zc.closed == 1
    assert adv.running is False


def test_stop_sem_start_nao_levanta():
    # `main.py` fecha aquilo que conseguiu abrir; nao pode rebentar num
    # `finally` por causa de um anuncio que nunca chegou a existir.
    _adv().stop()
    _adv().stop()


def test_stop_duas_vezes_e_inofensivo():
    zc = FakeZC()
    adv = _adv(zc_factory=lambda: zc)
    adv.start()
    adv.stop()
    adv.stop()
    assert zc.closed == 1, "o segundo stop nao pode fechar outra vez"
    assert len(zc.unregistered) == 1


# ── As falhas que nao podem custar a aplicacao ─────────────────────────────

def test_sem_endereco_de_rede_nao_anuncia():
    # Sem interface, o SRV fica apontado para um sitio que nao responde e o
    # telefone gasta a sondagem a falar com o vazio. E o `build_info` devolve
    # None em vez de registar um anuncio inutil.
    adv = _adv(addresses=[])
    assert adv.build_info() is None
    zc = FakeZC()
    adv = _adv(addresses=[], zc_factory=lambda: zc)
    assert adv.start() is False
    assert zc.registered == []


def test_zeroconf_que_nao_constroi_nao_levanta():
    # Sem Avahi, sem permissao, rede a cair. Nenhuma destas e motivo para a
    # Maouse nao arrancar: o comando remoto por IP escrito a mao continua.
    adv = _adv(zc_factory=ZCQueNaoConstrói(OSError("no avahi")))
    assert adv.start() is False
    assert adv.running is False


def test_register_que_falha_nao_deixa_o_zeroconf_aberto():
    # Se o registo falha e o `Zeroconf` ficar por fechar, cada tentativa
    # passa a prender mais sockets, e a segunda tentativa ja falha por falta
    # de descritores em vez de pelo motivo certo.
    zc = ZCQueFalhaNoRegister()
    adv = _adv(zc_factory=lambda: zc)
    assert adv.start() is False
    assert adv.running is False
    assert zc.closed == 1, "o zeroconf aberto no falhar tem de ser fechado"


def test_falha_no_registro_permite_tentar_de_novo():
    # A rede pode voltar. Um `start()` que falhou tem de ficar limpo para o
    # proximo, e nao meio registado.
    zc = ZCQueFalhaNoRegister()
    adv = _adv(zc_factory=lambda: zc)
    adv.start()
    bom = FakeZC()
    adv._zc_factory = lambda: bom
    assert adv.start() is True
    assert len(bom.registered) == 1


def test_excepcao_no_stop_nao_sobe():
    class ZCQueBrokeNoClose(FakeZC):
        def close(self):
            raise RuntimeError("ja estava morto")

    zc = ZCQueBrokeNoClose()
    adv = _adv(zc_factory=lambda: zc)
    adv.start()
    adv.stop()
    assert adv.running is False
