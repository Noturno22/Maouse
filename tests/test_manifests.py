"""Coerencia entre o codigo e os manifestos de que a instalacao depende.

Nao e um teste de estilo. Cada teste aqui existe porque ja apanhou um bug real:

* `cryptography` era importado por `core/licensing.py` e nao estava em nenhum
  manifesto de instalacao. O `setup.bat` instalava um ambiente onde a aplicacao
  nao arrancava — `main.py:35` importa `core.licensing` ao nivel do modulo.
  O CI nao via nada porque `cryptography` chegava pelo manifesto do
  license-server, por uma porta das traseiras que ninguem tinha mapeado.
* `comtypes` estava em `requirements.txt` sem ser importado por lado nenhum
  (vem como dependencia transitiva do `uiautomation`).
* `requirements-linux.txt` nao era instalado por ninguem, por isso podia
  apodrecer em silencio — e o `cryptography` em falta era exactamente esse
  formato de bug.

A regra: **o codigo e a fonte.** Os manifestos tem de concordar com os imports
que o codigo faz de facto, e nao uns com os outros. Um teste que compara duas
listas de dependencias entre si nao apanha o caso em que as duas estao erradas
iguais — que e como o `cryptography` sobreviveu.

Deliberadamente **nao** se compara com o `pyproject.toml`: ate 2026-09-28 ele
tinha `[project].dependencies` com uma lista propria, e comparar as duas listas
era precisamente o risco que se queria eliminar. O produto e entregue por
PyInstaller, nao por pip.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import check_deps  # noqa: E402

# O manifesto Linux omite as dependencias so-Windows de proposito: o
# `core/snap.py` faz o import guardado, e o produto corre no Linux sem elas.
_ONLY_WINDOWS_OMISSIONS = {"requirements-linux.txt": check_deps.WINDOWS_ONLY}


def _esperado(manifest: str) -> set[str]:
    """Distribuicoes que `manifest` tem de declarar, ja com as omissoes certas."""
    return set(check_deps.third_party_dists()) - _ONLY_WINDOWS_OMISSIONS.get(manifest, set())


class TestImportsEstaoDeclarados:
    """Cada import externo tem de estar em todos os manifestos de runtime.

    Este e o teste que teria apanhado o `cryptography` em falta.
    """

    @pytest.mark.parametrize("manifest", check_deps.RUNTIME_MANIFESTS)
    def test_manifestos_de_runtime_declaram_tudo(self, manifest: str):
        declarado = set(check_deps.read_requirements(manifest))
        falta = _esperado(manifest) - declarado
        assert falta == set(), (
            f"{manifest} nao declara {sorted(falta)}, que o codigo importa. "
            "O `setup.bat` instala este ficheiro — o produto nao arranca."
        )

    def test_o_scan_encontra_alguma_dependencia(self):
        """Trava o teste acima contra passar a vazio se a leitura de imports partir.

        Sem isto, um `ast.parse` que passa a devolver arvores vazias daria
        verde ao manifesto mais incompleto de todos.
        """
        assert len(check_deps.third_party_dists()) >= 10


class TestSemDependenciasFantasmas:
    """O que esta declarado tem de ser usado.

    `comtypes` estava declarado e nao importado: `uiautomation` ja o traz como
    dependencia transitiva. Declarar dependencias transitivas directamente e o
    que transforma um floor legitimo num floor de gueto.
    """

    @pytest.mark.parametrize("manifest", check_deps.RUNTIME_MANIFESTS)
    def test_manifestos_nao_declaram_nada_que_o_codigo_nao_use(self, manifest: str):
        declarado = set(check_deps.read_requirements(manifest))
        sobra = declarado - _esperado(manifest)
        assert sobra == set(), (
            f"{manifest} declara {sorted(sobra)}, que nada no codigo importa. Ou "
            "e residuo, ou e dependencia transitiva que devia deixar de ser "
            "fixada aqui."
        )


class TestManifestosEstaoBemFormados:
    """Nenhuma linha de manifesto pode ter duas especificacoes coladas.

    `requirements-linux.txt` nao terminava em newline. O `printf '>>'` do
    costume — que e a forma natural de acrescentar uma dependencia a um
    manifesto — colava-a a ultima linha existente e produzia
    `cryptography>=42dbus-next>=0.2.3`. O `read_requirements` le isso como
    `cryptography`, porque parte a linha no `>`. A dependencia nova
    desaparecia em silencio: o `TestImportsEstaoDeclarados` via a
    declaracao e via-a, e o `setup.bat` instalava um ambiente sem ela.

    Nao ha guarda pelo conteudo que apanhe isto, porque a linha nao fica
    invalida — fica valida e errada, que e o pior formato de bug. A
    definicao de "duas especificacoes" ignora o marker de ambiente
    (`; python_version<"3.9"`), senao toda a dependencia com extras
    contava como colada.
    """

    _OPERADORES = re.compile(r"==|>=|<=|~=|!=|[<>]")

    @pytest.mark.parametrize("manifest", check_deps.RUNTIME_MANIFESTS)
    def test_manifesto_termina_em_newline(self, manifest: str):
        bruto = (Path(check_deps.REPO_ROOT) / manifest).read_text(encoding="utf-8")
        assert bruto.endswith("\n"), (
            f"{manifest} nao termina em newline. Acrescentar uma dependencia "
            "cola-a a ultima linha e a dependencia desaparece em silencio."
        )

    @pytest.mark.parametrize("manifest", check_deps.RUNTIME_MANIFESTS)
    def test_nenhuma_linha_tem_duas_versoes_coladas(self, manifest: str):
        for numero, raw in enumerate(
            (Path(check_deps.REPO_ROOT) / manifest).read_text(encoding="utf-8").splitlines(), 1
        ):
            linha = raw.split("#", 1)[0].strip()
            if not linha:
                continue
            sem_marker = linha.partition(";")[0]
            operadores = self._OPERADORES.findall(sem_marker)
            assert len(operadores) <= 1, (
                f"{manifest}:{numero} tem {len(operadores)} operadores de versao: "
                f"{linha!r}. Sao especificacoes coladas — provavelmente um ficheiro "
                "sem newline final, com uma dependencia acrescentada por cima da ultima."
            )


class TestManifestosNaoDivergem:
    """O Windows e o Linux so podem diferir nas dependencias so-Windows.

    Divergencia entre manifestos e a forma silenciosa de um produto funcionar
    para quem instala no Windows e nao funcionar para quem instala no Linux.
    """

    def test_requirements_linux_e_requirements_menos_o_so_windows(self):
        windows = set(check_deps.read_requirements("requirements.txt"))
        linux = set(check_deps.read_requirements("requirements-linux.txt"))
        assert windows - linux == set(check_deps.WINDOWS_ONLY), (
            f"os dois manifestos diferem em {sorted(windows ^ linux)}, mas a unica "
            f"diferenca legítima e {sorted(check_deps.WINDOWS_ONLY)}"
        )
        assert linux - windows == set(), (
            f"requirements-linux.txt declara {sorted(linux - windows)}, que o "
            "manifesto do Windows nao declara. A variante Linux nao pode ser "
            "mais exigente que a outra."
        )

    def test_a_so_windows_so_esta_no_manifesto_do_windows(self):
        windows = check_deps.read_requirements("requirements.txt")
        linux = check_deps.read_requirements("requirements-linux.txt")
        for dist in check_deps.WINDOWS_ONLY:
            assert dist in windows, f"{dist} falta em requirements.txt"
            assert dist not in linux, (
                f"{dist} e so para Windows e nao pode estar em requirements-linux.txt"
            )
