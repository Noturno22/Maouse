"""Hardware fingerprint -> deterministic machine_id (SHA-256)."""
import hashlib
import logging
import subprocess

log = logging.getLogger(__name__)


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

    Quando isto é verdade, o `machine_id` passa a ser o sha256 de uma string
    constante — **o mesmo em todas as máquinas degradadas**. E `licensing.py`
    valida a licença por `machine_id` (`:163`), o que significa que duas
    máquinas nesse estado aceitam a mesma licença uma da outra.

    Existe como função, e não como comparação espalhada pelo código, para que a
    condição tenha um nome só. O nome é o que permite escrever um teste que
    detecte o caso, em vez de um teste que verifica se um dicionário tem chaves.
    """
    if comps is None:
        comps = collect_components()
    return not any(v for v in comps.values())


def machine_id() -> str:
    comps = collect_components()
    if degenerate(comps):
        log.error(
            "nenhuma componente de hardware foi lida (%s): o machine_id passa a "
            "ser o mesmo em todas as maquinas neste estado, e a licenca de uma "
            "valida noutra. Nao e um aviso, e um buraco de receita.",
            comps,
        )
    joined = "|".join(f"{k}={comps[k]}" for k in sorted(comps))
    return hashlib.sha256(joined.encode()).hexdigest()
