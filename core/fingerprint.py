"""Hardware fingerprint -> deterministic machine_id (SHA-256)."""
import hashlib
import logging
import os
import secrets
import socket
import subprocess

import config
from config import user_data_dir

log = logging.getLogger(__name__)

# Ficheiro do sal, **fora** do store de licença. Ver `_fallback_salt`.
_SALT_FILE = "machine_salt.txt"


def _read_machine_guid() -> str:
    """O MachineGuid do registo do Windows, ou "" se não houver.

    O `except` é estreito de propósito. A primeira versão era `except
    Exception: pass`, que é indistinguível de não ter o bloco: quando a
    activação falha, a única pista que sobrava era "não funciona", e um
    `PermissionError` no registo e um `ImportError` fora do Windows são
    problemas completamente diferentes com consertos completamente
    diferentes. `OSError` cobre o `FileNotFoundError` e o `PermissionError` que
    o `winreg` levanta, e `ImportError` cobre a ausência do módulo.
    """
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SOFTWARE\Microsoft\Cryptography") as k:
            val, _ = winreg.QueryValueEx(k, "MachineGuid")
            return str(val)
    except (OSError, ImportError) as e:
        log.debug("MachineGuid do registo indisponivel: %r", e)
    for p in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
        try:
            with open(p) as fh:
                return fh.read().strip()[:128]
        except OSError as e:
            log.debug("%s indisponivel: %r", p, e)
    return ""


def _wmic(namespace_class: str) -> str:
    """O número de série de `wmic`, ou "" se não houver.

    Vale a pena notar que o `wmic` foi descontinuado e já não vem no Windows 11
    recente: aqui volta a "", e o `machine_guid` do registo passa a ser a única
    componente. Numa máquina em que também ele falhe, as três ficam vazias — e
    ver `degenerate()` para o que isso significa.
    """
    try:
        out = subprocess.run(
            ["wmic", namespace_class, "get", "SerialNumber"],
            capture_output=True, text=True, timeout=8).stdout
        lines = [line.strip() for line in out.splitlines() if line.strip()]
        return lines[-1] if len(lines) > 1 else ""
    except (OSError, subprocess.SubprocessError) as e:
        log.debug("wmic %s indisponivel: %r", namespace_class, e)
        return ""


def collect_components() -> dict:
    return {
        "machine_guid": _read_machine_guid(),
        "disk_serial": _wmic("diskdrive"),
        "board_uuid": _wmic("baseboard"),
    }


def degenerate(comps: dict | None = None) -> bool:
    """A máquina não produziu nenhuma identidade.

    Quando isto é verdade, o `machine_id` deixou de ser derivado de hardware e
    passou a ser derivado de um sal local (`_degraded_id()`). Deixou de ser a
    mesma constante em todas as máquinas degradadas — a licença de uma deixou de
    validar noutra — mas deixou de ser prova de que a máquina é aquela, que era
    o que o `licensing.py` (`:163`) tacitamente assumia ao validar a licença por
    este valor. Por isso a resposta viaja agora com o id: `machine_identity()`
    devolve o par, e o servidor sabe quais os ids em que não deve confiar.

    Existe como função, e não como comparação espalhada pelo código, para que a
    condição tenha um nome só. O nome é o que permite escrever um teste que
    detecte o caso, em vez de um teste que verifica se um dicionário tem chaves.
    """
    if comps is None:
        comps = collect_components()
    return not any(v for v in comps.values())


def _salt_dir() -> str:
    """Onde gravar o sal -- e, sobretudo, onde **nao** gravar.

    `config.user_data_dir()` tem um fallback: se nao houver onde criar o
    directorio de dados do utilizador, devolve o directorio do pacote. Para
    settings e para modelos isso e razoavel (e melhor que nada). Para um
    segredo de identidade e exactamente o contrario:

    * o directorio do pacote e **partilhado** por todos os utilizadores daquela
      instalacao num install portatil -- e o sal e o que separa as maquinas,
      entao gravar la volta a partir a identidade que este ficheiro existe
      para fechar;
    * em desenvolvimento e a raiz do repositorio, e o sal aparecia no
      `git status` como ficheiro por commitar.

    Por isso aqui esse caminho devolve "" e o chamador trata-o como "nao ha
    onde gravar": pior, mas honesto. E o `degraded` continua a ser verdadeiro,
    que e o que importa -- nunca se inventa uma identidade porque o ficheiro
    ficou bonito.
    """
    d = user_data_dir()
    try:
        # `normcase`, e nao uma comparacao de strings: no Windows os caminhos
        # nao distinguem maiusculas e `abspath` nao normaliza a caixa. A versao
        # anterior comparava `...\DEV\maouse` com `...\DEV\Maouse`, dava
        # "diferentes" e a guarda nunca disparava -- um guard que nao pode
        # falhar. Foi o teste que o apanhou, ao usar `pathlib`, que devolve a
        # caixa que o disco tem.
        pacote = os.path.dirname(os.path.abspath(config.__file__))
        if os.path.normcase(os.path.abspath(d)) == os.path.normcase(pacote):
            return ""
    except (NameError, OSError, TypeError):
        pass
    return d


def _fallback_salt() -> str:
    """Um sal aleatorio, gravado uma vez nos dados do utilizador.

    Vive num ficheiro **a parte** do store de licenca, de proposito. Se
    vivesse no mesmo sitio, apagar a licenca para a reemitir mudaria tambem a
    identidade da maquina -- e quem tinha pago ficaria com uma licenca presa ao
    `machine_id` antigo, sem forma de a recuperar. Apagar a licenca tem de
    continuar a ser uma operacao sobre a licenca.

    Devolve "" se nao houver onde gravar. Aí o hostname fica a ser a unica
    coisa que distingue a maquina: melhor do que a constante partilhada de
    antes, mas nao igual. `degraded` continua a dizer a verdade nos dois casos --
    e e para isso que ele existe, para nao ter de mentir sobre o que o hash
    protege.
    """
    d = _salt_dir()
    if not d:
        log.error(
            "os dados do utilizador nao dao onde gravar o sal de maquina e o "
            "fallback seria o directorio do pacote, que e partilhado: nao se "
            "grava la. O machine_id deriva so do hostname."
        )
        return ""
    path = os.path.join(d, _SALT_FILE)
    try:
        with open(path, encoding="ascii") as fh:
            sal = fh.read().strip()
        if sal:
            return sal
    except OSError:
        pass
    sal = secrets.token_hex(16)
    tmp = path + ".tmp"
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(tmp, "w", encoding="ascii") as fh:
            fh.write(sal)
        os.replace(tmp, path)
    except OSError as e:
        log.error(
            "nao ha onde gravar o sal de maquina em %s (%r): o machine_id passa "
            "a derivar so do hostname, que o Windows batiza de DESKTOP-XXXX e "
            "repetido em varias maquinas. Continua a funcionar, e continua a "
            "ser fraco.", path, e,
        )
        return ""
    return sal


def _degraded_id() -> str:
    """Identidade de recurso, para uma maquina que nao deu identidade nenhuma.

    Ja nao e uma constante partilhada: o sal e por maquina, entao a licenca de
    uma maquina neste estado deixa de validar noutra. E o que fica e honesto
    -- fraco, e por isso mesmo o `degraded` viaja com o id ate ao servidor.
    """
    sal = _fallback_salt()
    try:
        host = socket.gethostname() or ""
    except OSError as e:
        log.debug("hostname indisponivel: %r", e)
        host = ""
    return hashlib.sha256(f"degraded|salt={sal}|host={host}".encode()).hexdigest()


def machine_identity() -> tuple:
    """(machine_id, degradado) -- a fonte unica da identidade da maquina.

    O par e a resposta a pergunta "esta identidade aguenta?", que `machine_id()`
    nao conseguia responder: devolvia um hash, e um hash bem formado nao diz se
    por baixo havia hardware ou nada. Quem chama precisa de saber qual dos dois
    viu, para poder avisar quem paga e dizer ao servidor em que confiar.
    """
    comps = collect_components()
    if degenerate(comps):
        log.error(
            "nenhuma componente de hardware foi lida (%s). O machine_id passa a "
            "derivar de um sal local em vez de hardware: deixa de ser partilhado "
            "entre maquinas, mas deixa de ser prova de nada, e o servidor trata "
            "estes ids como suspeitos.", comps,
        )
        return _degraded_id(), True
    joined = "|".join(f"{k}={comps[k]}" for k in sorted(comps))
    return hashlib.sha256(joined.encode()).hexdigest(), False


def machine_id() -> str:
    """So o id. Quem so precisa de um hash usa este; quem precisa de avaliar a
    forca da identidade usa `machine_identity()`."""
    return machine_identity()[0]
