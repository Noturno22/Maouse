"""Testes do transporte RFCOMM (`core/remote_rfcomm.py`).

O host nativo é substituído por um dublê, e é essa a razão de este ficheiro
existir: o que se prova aqui — o reassembly do framing, o limite de tentativas e
o dispatch para o `RemoteServer` — corre numa máquina sem adaptador de
Bluetooth, sem serviço RFCOMM registado e sem telefone nenhum ligado.

O que **não** se prova aqui é o que só o WinRT pode dar: que o
`RfcommServiceProvider` publica o serviço e que um telefone Android consegue
ligar-se. Esse teste precisa de hardware e é manual.
"""
from __future__ import annotations

import json

from core.remote import AuthLimiter
from core.remote_ble import decode_frame, encode_command
from core.remote_rfcomm import (
    RemoteRFCOMM,
    _envelope,
    _frame,
    _Frames,
    _ler_exacto,
    suportado,
)


class RatoFalso:
    """O mínimo que o `RemoteServer` lhexe, sem `pynput` nem ecrã."""

    screen_w = 1920
    screen_h = 1080


class RemotoFalso:
    """Dublê do `RemoteServer`: regista o que lhe foi pedido, não executa."""

    def __init__(self, limiter=None):
        self._mouse = RatoFalso()
        self.comandos = []
        self.ganos = 0
        self.on_command_begin = None
        self.on_command_end = None
        if limiter is not None:
            self.limiter = limiter

    def _note_activity(self):
        self.ganos += 1

    def _handle(self, cmd, data):
        self.comandos.append((cmd, data))
        return cmd.upper()


class PipeFalso:
    """Um stream que devolve os bytes aos bocados, como um pipe faz."""

    def __init__(self, dados, pedaco=1):
        self._d = dados
        self._pedaco = pedaco

    def read(self, n):
        n = min(n, self._pedaco)
        pedaco, self._d = self._d[:n], self._d[n:]
        return pedaco


class HostFalso:
    """Dublê do executável nativo.

    Guarda o que a Maouse lhe manda e sabe fingir um telefone a entrar e a falar.
    """

    def __init__(self):
        self.enviados = []
        self.iniciado = False
        self.parado = False
        self.rf = None

    # ── HostNativo ──
    def iniciar(self):
        self.iniciado = True
        return True

    def parar(self):
        self.parado = True

    def enviar(self, conn, payload):
        self.enviados.append((conn, bytes(payload)))

    def a_vivo(self):
        return self.iniciado and not self.parado

    # ── O que o executável nativo faria ──
    def ligar(self, conn, endereco="AA:BB:CC:DD:EE:FF"):
        self.rf._on_controlo(json.dumps(
            {"event": "ligado", "conn": conn, "endereco": endereco}
        ).encode())

    def desligar(self, conn):
        self.rf._on_controlo(json.dumps(
            {"event": "desligado", "conn": conn}
        ).encode())

    def entregar(self, conn, data):
        """Escreve um comando como o telefone escreve: tamanho à frente."""
        self.rf._on_bytes(conn, _frame(encode_command(data)))

    def entregas(self, conn):
        """O que o telefone recebeu, remontado e descodificado."""
        buf = _Frames()
        out = []
        for c, payload in self.enviados:
            if c == conn:
                out.extend(buf.feed(payload))
        return [decode_frame(f) for f in out]

    def entrega_bruta(self, conn, data):
        """Corta o stream em pedaços de 7 bytes, para forçar o reassembly.

        O que se corta é o stream, não a mensagem: o telefone escreve a mesma
        coisa, mas o sistema operativo podeParti-la onde lhe apetecer.
        """
        bruto = _frame(encode_command(data))
        for i in range(0, len(bruto), 7):
            self.rf._on_bytes(conn, bruto[i:i + 7])


def _srv(remoto=None, codigo="123456", limiter=None):
    host = HostFalso()
    rf = RemoteRFCOMM(
        type("C", (), {"remote_code": codigo})(),
        remoto if remoto is not None else RemotoFalso(limiter=limiter),
        host=host,
    )
    host.rf = rf
    rf.start()
    return rf, host


def _autenticado(rf, host, conn=1, endereco="AA:BB:CC:DD:EE:FF", codigo="123456"):
    host.ligar(conn, endereco)
    host.entregar(conn, {"cmd": "auth", "code": codigo})


class TestEnvelope:
    """O canal com o executável nativo."""

    def test_envelope_declara_tamanho_e_ligacao(self):
        env = _envelope(7, b"abc")
        assert len(env) == 11
        # 4 + len(payload), e a ligação — que é o que um pipe só não diz.
        assert int.from_bytes(env[0:4], "little") == 7
        assert int.from_bytes(env[4:8], "little") == 7
        assert env[8:] == b"abc"

    def test_ler_exacto_reune_leituras_parciais(self):
        dados = _envelope(3, b"payload")
        # Um byte de cada vez: é o que um pipe faz quando o escritor e o
        # leitor não estão em fase.
        assert _ler_exacto(PipeFalso(dados, pedaco=1), len(dados)) == dados

    def test_ler_exacto_devolve_o_que_houver_quando_o_pipe_fecha(self):
        assert _ler_exacto(PipeFalso(b"curto", pedaco=99), 99) == b"curto"


class TestFraming:
    """RFCOMM é um stream; as mensagens do protocolo não são."""

    def test_comando_longo_chega_inteiro_partido_em_muitos_cachos(self):
        rf, host = _srv()
        _autenticado(rf, host)
        texto = "a" * 500

        # Cortado em pedaços de 7 bytes, para obrigar ao reassembly.
        host.entrega_bruta(1, {"cmd": "text", "text": texto})

        assert rf._remote.comandos[-1] == ("text", {"cmd": "text", "text": texto})

    def test_duas_ligacoes_nao_misturam_fragmentos(self):
        rf, host = _srv()
        _autenticado(rf, host, conn=1, endereco="AA")
        _autenticado(rf, host, conn=2, endereco="BB")

        # Os dois comandos partidos, a intercalar, como duas ligações a fazer
        # isto ao mesmo tempo.
        a = _frame(encode_command({"cmd": "text", "text": "um"}))
        b = _frame(encode_command({"cmd": "text", "text": "dois"}))
        host.rf._on_bytes(1, a[:4])
        host.rf._on_bytes(2, b[:4])
        host.rf._on_bytes(1, a[4:])
        host.rf._on_bytes(2, b[4:])

        textos = [d["text"] for c, d in rf._remote.comandos if c == "text"]
        assert textos == ["um", "dois"]

    def test_move_binario_viaja_em_decimos_de_pixel(self):
        rf, host = _srv()
        _autenticado(rf, host)
        host.entregar(1, {"cmd": "move", "dx": 12, "dy": -4})
        # O caminho binário do BLE é o mesmo aqui: 5 bytes, não 32 de JSON.
        cmd, data = rf._remote.comandos[-1]
        assert (cmd, data["dx"], data["dy"]) == ("move", 12.0, -4.0)


class TestAuth:
    def test_codigo_certo_autentica_e_devolve_as_dimensoes_do_ecra(self):
        rf, host = _srv()
        _autenticado(rf, host)
        assert rf._remote.comandos == []          # o auth não é um comando
        r = host.entregas(1)[-1]
        assert r["cmd"] == "auth"
        assert r["ok"] is True
        assert (r["w"], r["h"]) == (1920, 1080)
        assert rf._remote.ganos == 1              # o rato sabe que houve actividade

    def test_codigo_errado_recusa_e_fecha_a_sessao(self):
        rf, host = _srv()
        host.ligar(1)
        host.entregar(1, {"cmd": "auth", "code": "000000"})
        assert host.entregas(1)[-1]["error"] == "auth_required"
        assert rf.connected_count() == 0

    def test_comando_antes_de_autenticar_nao_passa(self):
        rf, host = _srv()
        host.ligar(1)
        host.entregar(1, {"cmd": "click"})
        assert rf._remote.comandos == []
        assert host.entregas(1)[-1]["error"] == "auth_required"

    def test_o_token_antigo_ainda_serve(self):
        # Um build de desenvolvimento já instalado no telefone ainda manda
        # `token`; rejeitá-lo obrigava a reinstalar a app para experimentar.
        rf, host = _srv()
        host.ligar(1)
        host.entregar(1, {"cmd": "auth", "token": "123456"})
        assert host.entregas(1)[-1]["ok"] is True

    def test_o_limite_e_o_do_remoto_e_nao_um_novo(self):
        # Se o RFCOMM tivesse o seu próprio contador, um atacante que falhasse
        # cinco vezes por WiFi e passasse a Bluetooth recomeçava do zero.
        limiter = AuthLimiter(max_failures=2, window_s=60, lock_s=300)
        rf, host = _srv(limiter=limiter)
        assert rf._limiter is limiter

    def test_bloqueia_apos_varias_falhas_e_diz_quando_desbloqueia(self):
        limiter = AuthLimiter(max_failures=3, window_s=60, lock_s=300)
        rf, host = _srv(limiter=limiter)

        for _ in range(3):
            host.ligar(1)
            host.entregar(1, {"cmd": "auth", "code": "000000"})
        assert host.entregas(1)[-1]["error"] == "auth_required"

        # A quarta tentativa, com o código certo, já não entra.
        host.ligar(1)
        host.entregar(1, {"cmd": "auth", "code": "123456"})
        ultima = host.entregas(1)[-1]
        assert ultima["error"] == "auth_locked"
        assert ultima["retry_after"] > 0

    def test_desligar_e_voltar_a_ligar_nao_zera_o_limite(self):
        # Fechar e voltar a ligar é o gesto mais barato para o atacante. A
        # tentativa é contada pelo endereço, não pelo número da ligação.
        limiter = AuthLimiter(max_failures=2, window_s=60, lock_s=300)
        rf, host = _srv(limiter=limiter)

        host.ligar(1)
        host.entregar(1, {"cmd": "auth", "code": "000000"})
        host.desligar(1)
        host.ligar(9)                      # ligação nova, mesmo telefone
        host.entregar(9, {"cmd": "auth", "code": "000000"})
        host.ligar(4)
        host.entregar(4, {"cmd": "auth", "code": "123456"})

        assert host.entregas(4)[-1]["error"] == "auth_locked"


class TestComandos:
    def test_ping_responde_pong(self):
        rf, host = _srv()
        _autenticado(rf, host)
        host.entregar(1, {"cmd": "ping"})
        assert host.entregas(1)[-1] == {"ok": True, "pong": True}

    def test_comando_vai_ao_handle_com_o_dict_intacto(self):
        rf, host = _srv()
        _autenticado(rf, host)
        host.entregar(1, {"cmd": "click", "button": "left"})
        assert rf._remote.comandos[-1] == ("click", {"cmd": "click", "button": "left"})

    def test_o_arbitro_e_avisado_à_cada_comando(self):
        # O comando pode segurar o rato; é o arbitro que o cede à câmara.
        rf, host = _srv()
        _autenticado(rf, host)
        estado = []
        rf._remote.on_command_begin = lambda: estado.append("begin")
        rf._remote.on_command_end = lambda: estado.append("end")
        host.entregar(1, {"cmd": "click"})
        assert estado == ["begin", "end"]

    def test_comando_que_falha_responde_com_o_erro(self):
        rf, host = _srv()
        _autenticado(rf, host)

        def explode(cmd, data):
            raise ValueError("sem ecrã")

        rf._remote._handle = explode
        host.entregar(1, {"cmd": "click"})
        r = host.entregas(1)[-1]
        assert r["ok"] is False
        assert "sem ecrã" in r["error"]

    def test_lixo_nao_e_comando(self):
        rf, host = _srv()
        _autenticado(rf, host)
        # Uma mensagem bem formada cujo corpo não é JSON.
        host.rf._on_bytes(1, _frame(b"nao sou json"))
        assert rf._remote.comandos == []

    def test_tamanho_absurdo_e_descartado(self):
        # Sem este tecto, um tamanho enorme faria o PC reservar a memória toda.
        rf, host = _srv()
        _autenticado(rf, host)
        antes = len(host.enviados)
        host.rf._on_bytes(1, (10 * 1024 * 1024).to_bytes(4, "big") + b"xxxx")
        assert rf._remote.comandos == []
        assert len(host.enviados) == antes

    def test_cabeçalho_cortado_a_meio_da_mesma_forma(self):
        # Foi este o caso que pegou no bug: cortar o stream mesmo a meio dos
        # bytes do tamanho tem de dar a mesma mensagem.
        rf, host = _srv()
        _autenticado(rf, host)
        bruto = _frame(encode_command({"cmd": "click"}))
        for i in range(0, len(bruto), 2):
            host.rf._on_bytes(1, bruto[i:i + 2])
        assert rf._remote.comandos[-1][0] == "click"

    def test_duas_mensagens_numa_leitura_so(self):
        # Uma leitura pode trazer mais do que uma mensagem.
        rf, host = _srv()
        _autenticado(rf, host)
        host.rf._on_bytes(1, _frame(encode_command({"cmd": "click"}))
                          + _frame(encode_command({"cmd": "press"})))
        cmds = [c for c, _ in rf._remote.comandos]
        assert cmds[-2:] == ["click", "press"]


class TestCodigoAtivo:
    def test_prefere_o_codigo_do_remoto(self):
        # Se cada transporte comparasse com a sua cópia, o WiFi aceitava e o
        # Bluetooth recusava com o mesmo código — e isso só se descobre a quem
        # liga por Bluetooth, que foi de propósito.
        remoto = RemotoFalso()
        remoto.code = "654321"
        rf = RemoteRFCOMM(type("C", (), {"remote_code": "111111"})(), remoto,
                         host=HostFalso())
        assert rf.codigo_ativo == "654321"

    def test_sem_codigo_no_remoto_usa_o_da_config(self):
        rf = RemoteRFCOMM(type("C", (), {"remote_code": "111111"})(),
                         RemotoFalso(), host=HostFalso())
        assert rf.codigo_ativo == "111111"


class TestCicloDeVida:
    def test_start_stop_e_estado(self):
        rf, host = _srv()
        assert rf.is_running() is True
        rf.stop()
        assert rf.is_running() is False
        assert host.parado is True

    def test_stop_esquece_as_sessoes(self):
        rf, host = _srv()
        _autenticado(rf, host)
        assert rf.connected_count() == 1
        rf.stop()
        assert rf.connected_count() == 0

    def test_desligar_marca_a_sessao_como_terminada(self):
        rf, host = _srv()
        _autenticado(rf, host)
        host.desligar(1)
        assert rf.connected_count() == 0

    def test_reconectar_com_o_mesmo_endereco_substitui_a_sessao(self):
        rf, host = _srv()
        _autenticado(rf, host, conn=1, endereco="AA")
        host.ligar(2, endereco="AA")
        assert rf.connected_count() == 1

    def test_soportado_responde_so_no_windows(self):
        # O BLE resolve o Linux e é melhor; os dois não arrancam ao mesmo tempo.
        import sys
        assert suportado() is sys.platform.startswith("win")


class TestSemHardware:
    """Nenhum destes testes toca em Bluetooth, e é de propósito."""

    def test_o_host_nunca_e_um_processo_real(self):
        rf, host = _srv()
        # O dublê entra pelo construtor, por isso `start()` não chega a lançar
        # nada — nem procura o executável.
        assert host.iniciado is True
        assert rf._host is host
