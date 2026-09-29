"""Fonte unica de verdade sobre as dependencias do produto.

Existe por causa de um bug real, encontrado a 2026-09-28: `cryptography` e
importado por `core/licensing.py` (a verificacao de licenca, ou seja, o gate
Pro do produto) mas **nao estava em nenhum dos manifestos de instalacao**. O
`setup.bat` produzia um ambiente onde `import core.licensing` rebenta com
`ModuleNotFoundError` — e, como `main.py:35` importa esse modulo ao nivel do
modulo, onde a aplicacao inteira nao arrancava.

O CI nao o apanhava porque instalava uma coisa que trazia `cryptography` por
outro caminho: `license-server/requirements.txt`. Um manifesto pode estar errado
e o pipeline continua verde — o que e exactamente o que aconteceu.

Este modulo le os imports do codigo com `ast` e expoe-os, para que os testes
comparem os manifestos com o **codigo** em vez de uns com os outros. A
alternativa — um manifesto que declara as dependencias e outro que tambem
declara, e testes a comparar os dois — e o que deixou o bug passar:havia duas
listas, e a que o `setup.bat` usava estava errada sem ninguem dar por isso.

O `pyproject.toml` deixa de ter `[project].dependencies` por esta razao: o
produto e entregue por PyInstaller, nao por pip, e manter a segunda lista era
justamente o risco.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# O que o produto importa. `main.py`, `config.py` e `i18n.py` sao modulos de
# topo, fora de `core`/`ui`, e por isso entram a parte: sao eles que puxam
# `import config` para dentro de `core/` e para o produto empacotado.
SOURCE_FILES = ("main.py", "config.py", "i18n.py")
SOURCE_DIRS = ("core", "ui")

# Modulo importado -> nome da distribuicao no PyPI. So entram aqui os que
# diferem do nome do modulo; o resto assume que sao iguais.
MODULE_TO_DIST = {
    "cv2": "opencv-python",
    "faster_whisper": "faster-whisper",
    "piper": "piper-tts",
    "PIL": "Pillow",
    # O `pip` instala `dbus-next`, o `import` e `dbus_next`. Sem esta linha o
    # scanner via o modulo a mao e o manifesto declara a distribuicao, e a
    # comparacao dos dois nomes nunca bate: o teste de manifests acusaria uma
    # dependencia em falta que esta declarada, ou deixaria passar uma que nao
    # esta.
    "dbus_next": "dbus-next",
}

# Dependencias so para Windows. O `core/snap.py` faz o import dentro de um
# try/except, por isso o produto corre no Linux sem elas — e por isso o
# `requirements-linux.txt` as omite de proposito.
WINDOWS_ONLY = frozenset({"uiautomation"})

# O inverso: dependencias so para Linux, que o `requirements.txt` (o manifesto
# do Windows) omite. `dbus-next` fala com o `bluetoothd` pela D-Bus de sistema,
# que é uma coisa de Linux — no Windows não há BlueZ para publicar um peripheral
# GATT, e a dependencia só custaria uma falha de instalação. Fica em lista
# própria, e não em `WINDOWS_ONLY`, porque o nome desse conjunto passaria a
# mentir: `uiautomation` é o que o Windows precisa, `dbus-next` é o que o
# Windows dispensa.
LINUX_ONLY = frozenset({"dbus-next"})

# Manifestos de instalacao de que o produto depende. `requirements-build.txt`
# fica de fora de proposito: `pyinstaller` e dependencia de build, nao de
# runtime. E `license-server/requirements.txt` tambem: e do servidor, e nao
# deve contar como cobertura para o cliente.
RUNTIME_MANIFESTS = ("requirements.txt", "requirements-linux.txt")


def _module_is_local(name: str) -> bool:
    """True se `name` for um modulo deste repositorio, nao um pacote externo.

    Um `Path.glob("*.py")` devolve `config.py`, por isso a comparacao e por
    `stem`. E um directorio conta como local mesmo sem `__init__.py`, porque o
    Python 3 trata isso como namespace package — que e o caso do `tools/`.
    """
    if name in {p.stem for p in REPO_ROOT.glob("*.py")}:
        return True
    return (REPO_ROOT / name).is_dir()


def iter_source_files() -> list[Path]:
    """Todos os ficheiros Python que o produto empacotavel inclui."""
    files = [REPO_ROOT / f for f in SOURCE_FILES if (REPO_ROOT / f).is_file()]
    for d in SOURCE_DIRS:
        files += sorted((REPO_ROOT / d).rglob("*.py"))
    return files


def imported_modules() -> dict[str, set[str]]:
    """Mapa `modulo de topo` -> conjunto de ficheiros que o importam."""
    found: dict[str, set[str]] = {}
    for path in iter_source_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
        rel = path.relative_to(REPO_ROOT).as_posix()
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module.split(".")[0]]
            for name in names:
                found.setdefault(name, set()).add(rel)
    return found


def third_party_dists() -> dict[str, set[str]]:
    """Mapa `distribuicao` -> ficheiros que a importam, ja sem modulos locais.

    Um modulo e considerado local se for um `.py` da raiz, um pacote do repo, ou
    da biblioteca padrao. Qualquer outra coisa tem de estar declarada num
    manifesto — e se nao estiver, o import rebenta na máquina de quem instala.
    """
    out: dict[str, set[str]] = {}
    for module, files in imported_modules().items():
        if module in sys.stdlib_module_names or _module_is_local(module):
            continue
        out.setdefault(MODULE_TO_DIST.get(module, module), set()).update(files)
    return out


def _split_marker(spec: str) -> tuple[str, str | None]:
    """`"foo>=1; sys_platform == 'win32'"` -> `("foo>=1", "sys_platform == 'win32'")`."""
    base, sep, marker = spec.partition(";")
    return base.strip(), (marker.strip() if sep else None)


def _dist_name(spec: str) -> str:
    """`"foo>=1.2"` -> `"foo"`, preservando o `==` exacto (pins)."""
    return re.split(r"[<>=!~\[; ]", spec, maxsplit=1)[0].strip()


def read_requirements(filename: str) -> dict[str, str | None]:
    """Manifesto pip -> {distribuicao: marcador ou None}."""
    out: dict[str, str | None] = {}
    for raw in (REPO_ROOT / filename).read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        base, marker = _split_marker(line)
        out[_dist_name(base)] = marker
    return out
