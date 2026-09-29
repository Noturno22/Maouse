"""Tests for machine fingerprint -> stable machine_id.

O teste antigo `test_fingerprint_components_nonempty` fazia `assert comps`, e
`collect_components()` devolve sempre um dicionário com três chaves — portanto
passava **com as três componentes vazias**. Um teste que se chama "nonempty" e
que não verificava se nenhum valor tem conteúdo, durante tempo suficiente para
que ninguém reparasse.

Não era um teste inútil, era pior: era um teste que, ao passar, dizia que a
identidade da máquina estava garantida. Não estava.

E o teste seguinte desta lista aguentava o buraco aberto de propósito, para que
não desaparecesse em silêncio. Hoje está fechado, e o teste passou a afirmar que
está: mesmo parágrafo, sentido contrário.
"""
import hashlib
import json
import os
import pathlib
import types

import pytest

import core.fingerprint as fp

# A constante que o buraco produzia: sha256 da string com as três componentes
# vazias, a mesma em todas as máquinas que não liam hardware. Está escrita aqui
# à mão de propósito — é a referência contra a qual se mede o fecho, e um
# teste que calcula o valor esperado com a mesma fórmula do código não está a
# medir nada.
ID_PARTILHADO_ANTIGO = "751f034653eeaa33"


@pytest.fixture
def sem_hardware(monkeypatch):
    """Uma máquina que não produziu identidade nenhuma.

    Monkeypatcha as **duas** fontes. Patchar só uma não chega:
    `collect_components` lê três componentes e basta uma encher para
    `degenerate()` dizer que não.
    """
    monkeypatch.setattr(fp, "_read_machine_guid", lambda: "")
    monkeypatch.setattr(fp, "_wmic", lambda *_a, **_k: "")


@pytest.fixture
def hostname_fixo(monkeypatch):
    """Um hostname, para provar que ele **não** é o que separa as máquinas."""
    monkeypatch.setattr(fp, "socket", types.SimpleNamespace(
        gethostname=lambda: "DESKTOP-A1B2C3"))


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
    mensagem diz porquê. Continua a ser o comportamento correcto para um teste: o
    utilizador dessa máquina recebe um erro que explica o problema, em vez de
    uma activação que partilha a identidade com todas as outras.
    """
    comps = fp.collect_components()
    vazias = [k for k, v in comps.items() if not v]
    assert not fp.degenerate(comps), (
        f"nenhuma componente de hardware foi lida: {comps}. Vale a pena saber "
        f"que isto ja nao parte a licenca entre maquinas — o id passa a derivar "
        f"de um sal local, e a prova de que a maquina e aquela passou a ser o "
        f"sal ({vazias} vazias). Mas quem quiser continua a poder recolher."
    )


def test_degenerate_diz_o_que_diz_o_seu_nome(monkeypatch):
    """`degenerate()` tem de responder pelo que o nome promete, nos dois
    sentidos. Um guarda que só sabe dizer que sim é meia guarda."""
    vazio = {"machine_guid": "", "disk_serial": "", "board_uuid": ""}
    cheio = {"machine_guid": "abc", "disk_serial": "", "board_uuid": ""}
    assert fp.degenerate(vazio) is True
    assert fp.degenerate(cheio) is False
    assert fp.degenerate(cheio) is False, (
        "`degenerate()` nao e um dicionario novo de cada vez: o mesmo valor "
        "tem de dar a mesma resposta, senao quem o avalia duas vezes na mesma "
        "execução pode ver duas maquinas diferentes."
    )


def test_o_machine_id_degradado_ja_nao_e_partilhado_entre_maquinas(
        sem_hardware, monkeypatch, tmp_path):
    """O buraco que este teste documentava está fechado. Este é o fecho.

    Antes: com as três componentes vazias o `machine_id` era o sha256 de uma
    string constante — o mesmo número em **todas** as máquinas degradadas — e
    `core/licensing.py:163` validava a licença por ele, o que punha a licença de
    uma máquina a funcionar noutra.

    Agora: o id degradado deriva de um sal gravado nos dados do utilizador. Duas
    máquinas no mesmo estado dão ids **diferentes**, que é o que interessa.

    O `test_machine_id_deterministic` continua a passar neste estado (`a == b`),
    e continua a não dizer nada sobre isto: o determinismo é a única
    propriedade que ele mede, e é satisfeita tanto por uma identidade boa como
    por uma que não prova nada. Este teste mede a outra.
    """
    comps = fp.collect_components()
    assert fp.degenerate(comps), "sanity: monkeypatch nao degradou nada"

    # Duas "maquinas" = dois directórios de utilizador = dois sais.
    monkeypatch.setattr(fp, "user_data_dir", lambda: str(tmp_path / "maq-a"))
    a = fp.machine_id()
    monkeypatch.setattr(fp, "user_data_dir", lambda: str(tmp_path / "maq-b"))
    b = fp.machine_id()

    assert a != b, (
        "duas maquinas degradadas deram o mesmo machine_id: a licenca de uma "
        "volta a validar noutra, que era o buraco"
    )
    assert not a.startswith(ID_PARTILHADO_ANTIGO), (
        f"o id degradado voltou a ser a constante partilhada "
        f"{ID_PARTILHADO_ANTIGO}... A constante e o que o buraco era; voltar a "
        f"ela reabre o buraco."
    )
    assert not b.startswith(ID_PARTILHADO_ANTIGO)


def test_o_id_degradado_muda_com_a_maquina_e_nao_so_com_o_hostname(
        sem_hardware, hostname_fixo, monkeypatch, tmp_path):
    """O hostname **não** é o que separa duas máquinas degradadas.

    O Windows batiza as máquinas de `DESKTOP-XXXX` por omissão, e esse sufixo
    é uma sequência, não um identificador: há várias máquinas com o mesmo
    hostname em uso ao mesmo tempo. Se a separação viesse do hostname, clonar o
    hostname de outra máquina devolveria a partilha que o teste anterior fecha.

    O hostname entra no id para um humano conseguir ler de que máquina se
    trata. O que o separa é o sal, e é por isso que este teste força as duas a
    terem o mesmo hostname e mesmo assim exige ids diferentes.
    """
    monkeypatch.setattr(fp, "user_data_dir", lambda: str(tmp_path / "maq-a"))
    a = fp.machine_id()
    monkeypatch.setattr(fp, "user_data_dir", lambda: str(tmp_path / "maq-b"))
    b = fp.machine_id()
    assert a != b, (
        "duas maquinas com o MESMO hostname deram o mesmo machine_id. O "
        "hostname entra no id para ser legivel por um humano, nao para separar: "
        "o Windows chama DESKTOP-XXXX a varias maquinas ao mesmo tempo."
    )


def test_o_id_degradado_so_muda_com_o_sal_e_nao_entre_chamadas(
        sem_hardware, monkeypatch, tmp_path):
    """Estável dentro da mesma máquina, que é o que a licença exige.

    O outro lado da mesma moeda: se o id oscilasse a cada arranque, a licença
    presa a ele deixava de valer. Determinismo e separação precisam dos dois, e
    um sem o outro não chega.
    """
    monkeypatch.setattr(fp, "user_data_dir", lambda: str(tmp_path))
    a = fp.machine_id()
    b = fp.machine_id()
    assert a == b, "o id degradado mudou entre chamadas na mesma maquina"


def test_o_sal_sobe_ao_disco_e_so_um_ficheiro(sem_hardware, monkeypatch, tmp_path):
    """O sal é gravado uma vez e reutilizado, senão o id muda a cada arranque.

    E tem de ser um ficheiro só. Se cada chamada escrevesse um sal novo, o id
    seria diferente em cada `machine_id()` e a licença presa a ele deixava de
    valer — que é o modo de falha mais caro e o mais difícil de ver, porque
    parece um problema de rede.
    """
    monkeypatch.setattr(fp, "user_data_dir", lambda: str(tmp_path))
    primeiro = fp.machine_id()

    sal = tmp_path / fp._SALT_FILE
    assert sal.is_file(), f"o sal nao foi gravado em {sal}"
    conteudo = sal.read_text(encoding="ascii").strip()
    assert conteudo, "o sal foi gravado vazio"
    assert fp.machine_id() == primeiro, "o sal nao foi reutilizado"


def test_apagar_a_licenca_nao_muda_a_maquina(sem_hardware, monkeypatch, tmp_path):
    """Apagar a licença tem de continuar a ser uma operação sobre a licença.

    O sal vive no directório de dados do utilizador e **não** no store da
    licença, precisamente por causa disto. Se tivesse directas o mesmo sítio,
    apagar a licença para a reemitir mudaria a identidade da máquina — e quem
    tivesse pago ficaria com uma licença presa ao `machine_id` antigo, sem
    forma de a recuperar. Um bug que só aparece na segunda reemissão, a
    alguém que já pagou duas vezes.
    """
    monkeypatch.setattr(fp, "user_data_dir", lambda: str(tmp_path))
    antes = fp.machine_id()

    store = tmp_path / "licenca.json"
    store.write_text(json.dumps({"lease": "x", "machine_id": antes}),
                     encoding="utf-8")
    store.unlink()

    assert fp.machine_id() == antes, (
        "apagar a loja da licenca mudou o machine_id. O sal tem de sobreviver a "
        "isso: e a identidade da maquina, nao da licenca."
    )


def test_fica_de_parede_quando_nao_ha_onde_gravar_o_sal(
        sem_hardware, monkeypatch, tmp_path):
    """Sem sítio para o sal, tem de funcionar na mesma — e dizer que é fraco.

    O caso é um directório de dados apontado para um sítio onde não se pode
    escrever. Recusar a activação seria pior: seria uma máquina esquisita
    transformada num ticket de suporte para quem já pagou. O que não pode
    acontecer é o `degraded` virar `False` só porque o id ficou bonito.
    """
    # `user_data_dir` aponta para dentro de um **ficheiro**: o `makedirs` rebenta
    # com NotADirectoryError, que é um OSError — o caminho que o `except` apanha.
    # Não se faz monkeypatch a `os.makedirs`: isso muda o `os.makedirs` do
    # processo inteiro e parte os testes vizinhos.
    bloqueio = tmp_path / "bloqueio"
    bloqueio.write_text("sou um ficheiro, nao um directorio")
    monkeypatch.setattr(fp, "user_data_dir", lambda: str(bloqueio / "dentro"))

    mid, degradado = fp.machine_identity()
    assert degradado is True, (
        "sem onde gravar o sal o id passou a ser considerado forte. Continua a "
        "derivar do hostname, e o hostname nao e identidade."
    )
    assert len(mid) == 64 and all(c in "0123456789abcdef" for c in mid)
    assert mid == fp.machine_identity()[0], "o id de recurso oscilou"


def test_a_forca_da_identidade_viaja_com_o_id(monkeypatch, tmp_path):
    """`machine_identity()` tem de dar a resposta que `machine_id()` não dá.

    Um hash bem formado não diz se por baixo havia hardware ou nada — e quem
    valida uma licença precisa de saber qual dos dois viu. É a diferença entre
    um identificador e uma afirmação sobre uma máquina.
    """
    monkeypatch.setattr(fp, "_read_machine_guid", lambda: "abc")
    monkeypatch.setattr(fp, "_wmic", lambda *_a, **_k: "")
    mid, degradado = fp.machine_identity()
    assert degradado is False
    assert mid == fp.machine_id(), (
        "machine_id() devolve outra coisa: os dois tem de concordar no id, ou "
        "quem valida a licenca e quem avalia a forca dessa validacao discordam"
    )

    monkeypatch.setattr(fp, "_read_machine_guid", lambda: "")
    monkeypatch.setattr(fp, "_wmic", lambda *_a, **_k: "")
    monkeypatch.setattr(fp, "user_data_dir", lambda: str(tmp_path))
    mid2, degradado2 = fp.machine_identity()
    assert degradado2 is True
    assert mid2 != mid, (
        "a maquina sem identidade deu o mesmo id da maquina com identidade. "
        "O par devia ser o que distingue, e nao esta a distinguir."
    )


def test_o_sal_nunca_vai_para_o_directorio_do_pacote(sem_hardware, monkeypatch, tmp_path):
    """O sal é um segredo **por máquina**, e o pacote é partilhado.

    `config.user_data_dir()` tem um fallback: se não conseguir criar o
    directório de dados do utilizador, devolve o directório do pacote. Para
    settings e para modelos isso é razoável. Para o sal é o contrário do que
    se quer: num install portátil, o directório do pacote é o **mesmo** para
    todos os utilizadores, e o sal é precisamente o que os separa — gravá-lo
    ali devolveria a partilha que este módulo existe para fechar.

    Este teste chegou tarde e porque o ficheiro apareceu no `git status`: um
    `LOCALAPPDATA` apontado para um sítio inválido faz `makedirs` rebentar, o
    fallback entra, e o sal é gravado ao lado do código. Em dev, isso é a raiz
    do repositório; num produto congelado, é a pasta do `.exe`.

    E o caminho é montado com a **caixa trocada** de propósito. No Windows os
    caminhos não distinguem maiúsculas, e a primeira versão desta guarda
    comparava strings: `...\\DEV\\maouse` e `...\\DEV\\Maouse` são o mesmo
    sítio e duas strings diferentes, e a guarda passava a nunca disparar. Um
    guard que não pode falhar não é um guard — e este só foi visto porque o
    teste traz a caixa do disco, não a que estava no código.
    """
    pacote_dir = str(pathlib.Path(fp.config.__file__).resolve().parent)
    trocada = pacote_dir.swapcase()
    assert trocada != pacote_dir, (
        "sanity: a caixa trocada ficou igual a original, o teste nao esta a "
        "exercitar a comparacao sem distincao de caixa"
    )
    assert os.path.isabs(trocada), (
        f"sanity: o caminho de teste deixou de ser absoluto: {trocada!r}. "
        f"Um caminho como 'C:Users' e relativo ao drive, e o teste passaria "
        f"por uma razao errada."
    )
    monkeypatch.setattr(fp, "user_data_dir", lambda: trocada)

    assert fp._salt_dir() == "", (
        f"_salt_dir() aceitou o directorio do pacote ({pacote_dir}) como sitio "
        f"para o sal. E' onde o sal foi parar na raiz do repo."
    )

    antes = set(os.listdir(pacote_dir))
    mid, degradado = fp.machine_identity()
    depois = set(os.listdir(pacote_dir))
    assert depois == antes, (
        f"o sal foi gravado no directorio do pacote: "
        f"{depois - antes}. Partilhado e' partilhado."
    )
    assert degradado is True, (
        "sem sal gravado, a identidade deixou de ser declarada fraca. "
        "Hostname nao e identidade, e o par tem de dizer isso."
    )
    assert len(mid) == 64, "a identidade de recurso tem de continuar a ser um id"


def test_o_sal_vai_para_os_dados_do_utilizador_e_nao_para_o_pacote(
        sem_hardware, monkeypatch, tmp_path):
    """O caminho normal continua a ser o directório de dados do utilizador.

    O teste anterior pode passar de duas maneiras: `_salt_dir` a recusar o
    pacote, ou `_salt_dir` a devolver "" sempre. Este diz qual das duas é a
    certa, porque a segunda cumpre a letra e falha o produto: sem sal não há
    separação nenhuma, e era o buraco que veio fazer.
    """
    monkeypatch.setattr(fp, "user_data_dir", lambda: str(tmp_path))
    assert fp._salt_dir() == str(tmp_path)
    fp.machine_identity()
    assert (tmp_path / fp._SALT_FILE).is_file(), (
        "num directorio de dados do utilizador normal o sal tem de ser "
        "gravado: e' esse o caminho que separa as maquinas"
    )


def test_machine_id_e_a_segunda_metade_do_par(monkeypatch, tmp_path):
    """`machine_id()` tem de ser o id, e não outra coisa disfarçada.

    Existe porque há chamadores que só querem um hash. Se um dia alguém mudar
    esta função para devolver o par, ou o id com um prefixo, quem chama fica
    com uma string que parece um hash e não é — e a validação da licença passa
    a falhar em silêncio, no servidor, em produção.
    """
    monkeypatch.setattr(fp, "user_data_dir", lambda: str(tmp_path))
    mid = fp.machine_id()
    assert isinstance(mid, str), "machine_id() deixou de devolver uma string"
    assert len(mid) == 64, "machine_id() deixou de devolver um sha256"
    assert hashlib.sha256(mid.encode()).hexdigest() != mid, (
        "machine_id() parece estar a devolver o hash do hash"
    )
