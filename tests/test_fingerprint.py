"""Tests for machine fingerprint -> stable machine_id.

O teste antigo `test_fingerprint_components_nonempty` fazia `assert comps`, e
`collect_components()` devolve sempre um dicionário com três chaves — portanto
passava **com as três componentes vazias**. Um teste que se chama "nonempty" e
que não verificava se nenhum valor tem conteúdo, durante tempo suficiente para
que ninguém reparasse.

Não era um teste inútil, era pior: era um teste que, ao passar, dizia que a
identidade da máquina estava garantida. Não estava.
"""
import hashlib

import core.fingerprint as fp


def test_machine_id_deterministic():
    a = fp.machine_id()
    b = fp.machine_id()
    assert a == b
    assert len(a) >= 32


def test_machine_id_hex():
    mid = fp.machine_id()
    assert all(c in "0123456789abcdef" for c in mid)


def test_a_maquina_tem_pelo_menos_uma_componente_real():
    """A guarda que o `assert comps` fingia ser.

    Falha — de propósito — numa máquina que não produz nenhuma identidade, e a
    mensagem diz porquê. É o comportamento correcto para um teste: o utilizador
    dessa máquina recebe um erro que explica o problema, em vez de uma
    activação que partilha a identidade com todas as outras.
    """
    comps = fp.collect_components()
    vazias = [k for k, v in comps.items() if not v]
    assert not fp.degenerate(comps), (
        f"nenhuma componente de hardware foi lida: {comps}. O machine_id passa "
        f"a ser o mesmo em todas as maquinas neste estado "
        f"({list(vazias)} vazias), e a licença de uma valida noutra. Num "
        f"Windows 11 recente isto é plausível: o wmic já não vem instalado, e "
        f"falta o acesso ao registo."
    )


def test_degenerate_diz_o_que_diz_o_seu_nome(monkeypatch):
    """`degenerate()` tem de responder pelo que o nome promete, nos dois
    sentidos. Um guarda que só sabe dizer que sim é meia guarda."""
    vazio = {"machine_guid": "", "disk_serial": "", "board_uuid": ""}
    cheio = {"machine_guid": "abc", "disk_serial": "", "board_uuid": ""}
    assert fp.degenerate(vazio) is True
    assert fp.degenerate(cheio) is False


def test_o_machine_id_degradado_e_partilhado_entre_maquinas(monkeypatch):
    """Documenta, de forma executável, um buraco que ainda está aberto.

    Com as três componentes vazias, o `machine_id` é o sha256 de uma string
    constante: **o mesmo número em todas as máquinas degradadas**. E
    `core/licensing.py:163` valida a licença por esse valor, o que quer dizer
    que a licença de uma máquina funciona noutra.

    Este teste não está a aprovar o comportamento: está a torná-lo visível e a
    impedir que desapareça em silêncio. Quando o buraco for fechado — fazendo
    `machine_id()` recusar, e `licensing.py` decidir o que fazer sem identidade
    estável — este teste tem de mudar, e a mensagem dele é a nota do porquê.

    O `test_machine_id_deterministic` passa neste estado (`a == b`), que é
    exactamente o ponto: o determinismo é a **única** propriedade garantida, e
    ela é satisfeita tanto por uma identidade boa como por uma partilhada.
    """
    monkeypatch.setattr(fp, "_read_machine_guid", lambda: "")
    monkeypatch.setattr(fp, "_wmic", lambda *_a, **_k: "")

    comps = fp.collect_components()
    assert fp.degenerate(comps), "sanity: monkeypatch nao degradou nada"

    mid = fp.machine_id()
    esperado = hashlib.sha256(
        b"board_uuid=|disk_serial=|machine_guid="
    ).hexdigest()
    assert mid == esperado, (
        f"o machine_id degradado mudou de {esperado[:16]}... para {mid[:16]}... "
        f"Não é uma boa notícia por si só — significa que esta constante, "
        f"compartilhada por todas as máquinas sem identidade, já não é a que "
        f"está no código e ninguém reparou."
    )
