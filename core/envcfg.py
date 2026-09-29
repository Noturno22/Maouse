"""Leitura de valores de um ficheiro `.env` sem dependências externas.

Existe para que settings de desenvolvimento (endpoint do license-server,
chaves de API) possam ser definidos num ficheiro em vez de exportados no
shell — o utilizador não tem de lembrar `MAOUSE_LICENSE_URLS=... python
main.py` a cada arranque.

Precedência: variável de ambiente > ficheiro `.env`. O `.env` NUNCA é
versionado (ver .gitignore) e nunca substitui uma env var já definida.
"""
import os

# Ordem de procura do `.env`. O primeiro existente com a chave pedida ganha.
# - cwd: `python main.py` a partir da raiz do repo
# - raiz do projeto: o utilizador pode correr de outro diretório
_CANDIDATES = (
    ".env",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
)


def _parse(path: str) -> dict:
    values: dict[str, str] = {}
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                if not key:
                    continue
                values[key] = val.strip().strip('"').strip("'")
    except OSError:
        return {}
    return values


def env_value(name: str, files=None) -> str:
    """Devolve o valor de `name`: primeiro a env var, depois o `.env`.

    Devolve "" se não estiver em nenhum dos dois. Nunca levanta.
    """
    val = os.environ.get(name)
    if val and val.strip():
        return val.strip()
    for path in (files if files is not None else _CANDIDATES):
        if not path or not os.path.isfile(path):
            continue
        found = _parse(path).get(name)
        if found:
            return found
    return ""


def env_int(name: str, default: int = 0, files=None) -> int:
    """Como `env_value` mas convertido para int (0/valor inválido -> default)."""
    raw = env_value(name, files=files)
    if not raw:
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default
