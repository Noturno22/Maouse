"""Fonte unica de verdade sobre as dependencias do produto.

Existe por causa de um bug real, encontrado a 2026-09-28: `cryptography` e
importado por `core/licensing.py` (a verificacao de licenca, ou seja, o gate
Pro do produto) mas **nao estava em nenhum dos manifestos de instalacao**. O
`setup.bat` produzia um ambiente onde `import core.licensing` rebenta com
`ModuleNotFoundError`.

O CI nao o apanhava porque instalava tr coisa que trazia `cryptography` por
outro caminho: `license-server/requirements.txt`. Um manifesto pode estar errado
e o pipeline continua verde — o que e exactamente o que aconteceu.

Este modulo le os imports do codigo com `ast` e expoe-os, para que os testes
comparam os manifestos com o codigo em vez de uns com os outros. Sem isto
haveria uma segunda copia da verdade (o `pyproject.toml`) que diverge em
silencio — que e como o bug aconteceu da primeira vez.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# O que o produto empacotavel importa. `main.py`, `config.py` e `i18n.py` sao
# modulos de topo (fora de `core`/`ui`) e por isso precisam de `py-modules` no
# pyproject — ver `test_modulos_de_topo_sao_empacotados`.
SOURCE_FILES = ("main.py", "config.py", "i18n.py")
SOURCE_DIRS = ("core", "ui")

# Modulo importado -> nome da distribuicao no PyPI. So entram aqui os que
# diferem do nome do modulo; o resto assume que sao iguais.
MODULE_TO_DIST = {
    "cv2": "opencv-python",
    "faster_whisper": "faster-whisper",
    "piper": "piper-tts",
    "PIL": "Pillow",
}

# Dependencias so para Windows. O `core/snap.py` faz o import dentro de um
# try/except, por isso o produto corre no Linux sem elas — mas o manifesto
# partilhado nao as pode declarar sem marcar.
WINDOWS_ONLY = frozenset({"uiautomation"})

# Directorios do repo que **nao** fazem parte do produto empacotavel. `tools` e
# o harness de avaliacao (importado por `main.py --replay`, dentro de uma
# funcao) e nao runtime: nao se distribui e nao vai em `py-modules`.
NON_PACKAGED = frozenset(
    {"tools", "tests", "license_server", "license", "dist", "web", "node_modules"}
)

# Manifestos de instalacao que tem de bater certo com o `pyproject.toml`.
# `requirements-build.txt` fica de fora de proposito: `pyinstaller` e uma
# dependencia de build, nao de runtime.
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


def local_top_level_modules() -> set[str]:
    """Modulos de topo do repo que o codigo importa — precisam de `py-modules`.

    Exclui `core`/`ui` (que sao `packages`, nao `py-modules`), a stdlib, e o
    que nao e distribuido (`NON_PACKAGED`).
    """
    return {
        name
        for name in imported_modules()
        if name not in sys.stdlib_module_names
        and name not in SOURCE_DIRS
        and name not in NON_PACKAGED
        and _module_is_local(name)
    }


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


def read_pyproject_dependencies() -> dict[str, str | None]:
    """`[project].dependencies` -> {distribuicao: marcador ou None}.

    Feito a mao em vez de `tomllib` para o modulo correr tambem em Python 3.10,
    que e o `requires-python` declarado no proprio pyproject.
    """
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r"^dependencies\s*=\s*\[(.*?)\]", text, re.S | re.M)
    if not match:
        return {}
    out: dict[str, str | None] = {}
    for spec in re.findall(r'"([^"]+)"', match.group(1)):
        base, marker = _split_marker(spec)
        out[_dist_name(base)] = marker
    return out


def read_pyproject_py_modules() -> set[str]:
    """`[tool.setuptools].py-modules` -> conjunto de nomes."""
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r"^py-modules\s*=\s*\[(.*?)\]", text, re.S | re.M)
    if not match:
        return set()
    return {s.strip() for s in re.findall(r'"([^"]+)"', match.group(1))}
