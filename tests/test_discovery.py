"""Testes da descoberta mDNS do PC (core.discovery).

O teste que realmente importa aqui e `test_token_nunca_vai_nos_txt`: os TXT de
mDNS sao lidos em claro por tudo o que esteja na rede, sem autenticacao nem
permissao. Se o token acabar la, qualquer vizinho do WiFi entra no PC. Os
restes existem porque a alternativa a mDNS funcionar e a Maouse nao arrancar, e
isso nao pode depender de o Avahi estar instalado.
"""
import os
import subprocess
import sys

import pytest

from config import Config
from core import discovery
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


class TestDeviceIdNaoDependeDoMac:
    """O `id` tem de sobreviver a arranques mesmo sem hardware de que o tirar.

    `uuid.getnode()` nao devolve sempre um endereco de hardware. Quando nao
    devolve, devolve um valor pseudo-aleatorio com o bit multicast ligado
    (RFC 4122 §4.5) que so e estavel enquanto o processo vive — porque o
    unico sitio que o memoriza e o modulo `uuid`. Derivar o anuncio de
    ai dava um "PC novo" a cada arranque, e o telefone nunca reconheceria a
    mesma maquina.
    """

    def test_getnode_que_nao_e_hardware_e_rejeitado(self, monkeypatch):
        # 0x5b95ac792c49: o valor que `getnode()` devolveu nesta maquina, e que
        # nao e o MAC de interface nenhuma. Bit multicast ligado.
        monkeypatch.setattr(discovery.uuid, "getnode", lambda: 0x5B95AC792C49)
        assert discovery._hardware_id() is None

    def test_getnode_que_e_hardware_e_aceite(self, monkeypatch):
        # 0x30f7725f564b: o MAC do `wlp13s0`, bit multicast desligado.
        monkeypatch.setattr(discovery.uuid, "getnode", lambda: 0x30F7725F564B)
        assert discovery._hardware_id() == "30f7725f564b"

    def test_getnode_que_levanta_da_none(self, monkeypatch):
        def lanca():
            raise OSError("sem /sys e sem netlink")

        monkeypatch.setattr(discovery.uuid, "getnode", lanca)
        assert discovery._hardware_id() is None

    def test_id_sem_hardware_vem_do_ficheiro_e_repete_entre_chamadas(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setattr(discovery.uuid, "getnode", lambda: 0x5B95AC792C49)
        monkeypatch.setattr(discovery, "user_data_dir", lambda: str(tmp_path))
        monkeypatch.setattr(discovery.uuid, "uuid4", lambda: _uuid4_fixo())

        primeiro = device_id()

        ficheiro = tmp_path / discovery._ID_FILE
        assert ficheiro.exists(), "sem hardware, o id tem de ficar guardado"
        assert ficheiro.read_text(encoding="utf-8").strip() == "01234567"

        # O `device_id` e chamado varias vezes por anuncio (rotulo e TXT), e
        # outra vez no arranque seguinte. E o ficheiro que as une: se a segunda
        # chamada gerasse um valor novo, o telefone veria dois PCs.
        assert device_id() == primeiro
        assert device_id() == primeiro

    def test_ficheiro_ja_preenchido_nao_e_reescrito(self, monkeypatch, tmp_path):
        # Um `settings.json` (ou um `user_data_dir`) reescrito nao pode trocar
        # o id de uma maquina que ja foi pareada com o telefone.
        monkeypatch.setattr(discovery.uuid, "getnode", lambda: 0x5B95AC792C49)
        monkeypatch.setattr(discovery, "user_data_dir", lambda: str(tmp_path))
        (tmp_path / discovery._ID_FILE).write_text("abcd1234", encoding="utf-8")
        monkeypatch.setattr(discovery.uuid, "uuid4", lambda: _uuid4_fixo())

        discovery.device_id()
        assert (tmp_path / discovery._ID_FILE).read_text(
            encoding="utf-8") == "abcd1234"

    def test_sem_permissao_para_escrever_nao_levanta(self, monkeypatch, tmp_path):
        # Nao ha disco onde guardar: e para isso que o id e gerado e nao lido.
        # A aplicacao tem de arrancar na mesma.
        monkeypatch.setattr(discovery.uuid, "getnode", lambda: 0x5B95AC792C49)
        monkeypatch.setattr(discovery, "user_data_dir", lambda: "/proc/nao/escrevivel")
        monkeypatch.setattr(discovery.uuid, "uuid4", lambda: _uuid4_fixo())
        assert len(device_id()) == 8


def _uuid4_fixo():
    import uuid

    return uuid.UUID("0123456789abcdef0123456789abcdef")


# ── O anúncio tem de dizer a verdade sobre o servidor ─────────────────────

class _ServidorFalso:
    def __init__(self, running=True):
        self.is_running = running


class _JanelaFalsa:
    """O minimo que `_apply_discovery` toca, sem construir a janela toda.

    Chamar o metodo com um `self` emprestado e o que torna a decisao
    testavel sem camara, tracker e event loop Qt — que e o que a deixava
    testavel, e portanto a deixar o anuncio mentir em silencio.
    """

    def __init__(self, cfg, servidor, anuncio):
        self._cfg = cfg
        self._remote = servidor
        self._discovery = anuncio


def _janela(servidor, anuncio, cfg, descoberta=True):
    """(metodo, janela) para chamar `_apply_discovery` sem construir a janela.

    A `cfg` e a mesma do anunciador, como em `main.py`: sao o mesmo objecto, e
    dois objectos diferentes fariam o teste passar sem que a janela e o
    anuncio vissem a mesma porta.
    """
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from ui.main_window import MainWindow

    cfg.remote_discovery = descoberta
    return MainWindow._apply_discovery, _JanelaFalsa(cfg, servidor, anuncio)


class TestAnuncioSegueOPortao:
    """Mudar a porta nas definicoes tem de republicar o anuncio.

    Sem isto, o `_maouse._tcp` continuava a apontar para a porta antiga: o
    telefone encontrava o PC e levava com uma ligacao recusada. E o inverso
    tambem — desligar o remoto pela UI deixava o anuncio no ar.
    """

    def test_mudar_a_porta_republica_o_anuncio(self):
        cfg = _cfg()
        zc = FakeZC()
        anuncio = _adv(cfg=cfg, zc_factory=lambda: zc)
        assert anuncio.start() is True
        metodo, janela = _janela(_ServidorFalso(), anuncio, cfg)

        cfg.remote_port = 9123
        metodo(janela)

        assert anuncio.port == 9123, "o anuncio ficou na porta antiga"
        assert len(zc.unregistered) == 1, "o anuncio velho tem de sair do ar"
        assert len(zc.registered) == 2, "e tem de entrar outro com a porta nova"

    def test_porta_igual_nao_toca_em_nada(self):
        cfg = _cfg()
        zc = FakeZC()
        anuncio = _adv(cfg=cfg, zc_factory=lambda: zc)
        anuncio.start()
        metodo, janela = _janela(_ServidorFalso(), anuncio, cfg)

        metodo(janela)

        assert zc.unregistered == [], "anunciar o que ja esta certo seria churn"
        assert len(zc.registered) == 1

    def test_desligar_o_remoto_retira_o_anuncio(self):
        cfg = _cfg()
        zc = FakeZC()
        anuncio = _adv(cfg=cfg, zc_factory=lambda: zc)
        anuncio.start()
        metodo, janela = _janela(_ServidorFalso(running=False), anuncio, cfg)

        metodo(janela)

        assert anuncio.running is False
        assert len(zc.unregistered) == 1

    def test_desligar_a_descoberta_retira_o_anuncio(self):
        cfg = _cfg()
        anuncio = _adv(cfg=cfg)
        anuncio.start()
        metodo, janela = _janela(_ServidorFalso(), anuncio, cfg, descoberta=False)

        metodo(janela)

        assert anuncio.running is False

    def test_anuncio_que_falhou_no_arranque_tenta_de_nova(self):
        # A rede pode voltar depois do arranque. E por isso que o objecto e
        # entregue a janela mesmo quando o `start()` falhou.
        cfg = _cfg()
        anuncio = _adv(cfg=cfg, zc_factory=ZCQueNaoConstrói(OSError("sem avahi")))
        metodo, janela = _janela(_ServidorFalso(), anuncio, cfg)

        metodo(janela)
        assert anuncio.running is False, "o injetor continua a falhar, claro"

        anuncio._zc_factory = FakeZC
        metodo(janela)
        assert anuncio.running is True, "a rede voltou e o anuncio nao voltou"

    def test_sem_anunciador_nao_levanta(self):
        metodo, janela = _janela(_ServidorFalso(), None, _cfg())
        metodo(janela)



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


# ── A dependencia que a aplicacao nao pode ter no arranque ───────────────

class TestSemZeroconfInstalado:
    """Sem o `zeroconf` instalado, perde-se a descoberta — nunca a Maouse.

    O `main.py` importa este modulo ao nivel do modulo. Com o `zeroconf`
    importado no topo deste ficheiro, um `ImportError` aqui era um
    `ImportError` la, e a aplicacao nao arrancava. E o que aconteceu de facto
    num venv instalado antes deste modulo existir.
    """

    def test_importar_o_modulo_nao_precisa_do_zeroconf(self):
        # Provado noutro processo: aqui o `zeroconf` ja esta importado, e um
        # import no topo deste modulo passaria o teste sem dizer nada.
        r = subprocess.run(
            [sys.executable, "-c", _SEM_ZEROCONF],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr
        assert "OK" in r.stdout

    def test_main_importa_sem_o_zeroconf(self):
        # A promessa do modulo, provada na coisa que a faz: o `main.py`.
        r = subprocess.run(
            [sys.executable, "-c", _SEM_ZEROCONF + "\nimport main"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr

    def test_start_sem_zeroconf_devolve_false_e_nao_levanta(self, monkeypatch):
        # `zc_factory` injetado nao chega: e o `build_info` que precisa do
        # `ServiceInfo` verdadeiro para montar o anuncio.
        monkeypatch.setattr(discovery, "_zeroconf", lambda: None)
        adv = _adv()
        assert adv.build_info() is None
        assert adv.start() is False
        assert adv.running is False

    def test_restart_sem_zeroconf_nao_levanta(self, monkeypatch):
        monkeypatch.setattr(discovery, "_zeroconf", lambda: None)
        adv = _adv()
        assert adv.restart() is False


# Pseudo-subprocesso: bloqueia o `zeroconf` no `sys.meta_path` antes de
# qualquer import, que e o que um ambiente sem o pacote instalado faz.
_SEM_ZEROCONF = """
import sys

class _BloqueiaZeroconf:
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] == "zeroconf":
            raise ModuleNotFoundError("No module named %r" % name)
        return None

sys.meta_path.insert(0, _BloqueiaZeroconf())
sys.modules.pop("zeroconf", None)
print("OK")
"""
