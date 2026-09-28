"""Coerencia entre o codigo e os manifestos de dependencias.

Nao e um teste de estilo. Cada teste aqui existe porque ja apanhou um bug real
ou porque apanharia um que ainda nao aconteceu:

* `cryptography` era importado por `core/licensing.py` e nao estava em nenhum
  manifesto de instalacao. O `setup.bat` produzia um ambiente onde
  `import core.licensing` rebenta. O CI nao via nada porque `cryptography`
  chegava pelo manifesto do license-server.
* `pyproject.toml` declarava 1 dependencia em 16 e nao empacotava `config.py`
  nem `i18n.py` — modulos de topo importados ao nivel do modulo por 6+ ficheiros.
  `pip install airmouse` instalava um pacote que nao arranca.
* `comtypes` estava em `requirements.txt` sem ser importado por lado nenhum
  (vem como dependencia transitiva do `uiautomation`).
* `requirements-linux.txt` nao era instalado por ninguem, por isso podia
  apodrecer em silencio — o que e como a alegacao do `websockets>=13.0`
  sobreviveu duas semanas sem ninguem a testar.

A regra: o codigo e a fonte. Os manifestos tem de concordar com ele, e nao uns
com os outros.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import check_deps  # noqa: E402


class TestImportsEstaoDeclarados:
    """Cada import externo tem de estar em TODOS os manifestos de runtime.

    Este e o teste que teria apanhado o `cryptography` em falta.
    """

    def test_pyproject_declara_tudo_o_que_o_codigo_importa(self):
        required = set(check_deps.third_party_dists())
        declared = set(check_deps.read_pyproject_dependencies())
        assert required - declared == set(), (
            "O codigo importa mas o pyproject.toml nao declara: "
            f"{sorted(required - declared)}. Um `pip install airmouse` instala um "
            "pacote que rebenta no primeiro import."
        )

    @pytest.mark.parametrize("manifest", check_deps.RUNTIME_MANIFESTS)
    def test_manifestos_de_runtime_declaram_tudo(self, manifest: str):
        required = set(check_deps.third_party_dists())
        # O manifesto Linux omite as dependencias so-Windows de proposito.
        if manifest == "requirements-linux.txt":
            required -= check_deps.WINDOWS_ONLY
        declared = set(check_deps.read_requirements(manifest))
        assert required - declared == set(), (
            f"{manifest} nao declara {sorted(required - declared)}, que o codigo "
            "importa. O `setup.bat` usa este ficheiro — o produto nao arranca."
        )


class TestSemDependenciasFantasmas:
    """O que esta declarado e tem de ser usado.

    `comtypes` estava declarado e nao importado: `uiautomation` ja o traz como
    dependencia transitiva. Declarar dependencias transitivasdirectly e o que
    transforma um floor legitimo num floor de gueto.
    """

    @pytest.mark.parametrize("manifest", check_deps.RUNTIME_MANIFESTS)
    def test_manifestos_nao_declaram_nada_que_o_codigo_nao_use(self, manifest: str):
        used = set(check_deps.third_party_dists())
        # O manifesto Linux omite as dependencias so-Windows de proposito.
        if manifest == "requirements-linux.txt":
            used -= check_deps.WINDOWS_ONLY
        declared = set(check_deps.read_requirements(manifest))
        assert declared - used == set(), (
            f"{manifest} declara {sorted(declared - used)}, que nada no codigo "
            "importa. Ou e residuo, ou e dependencia transitiva que devia "
            "deixar de ser fixada aqui."
        )

    def test_pyproject_nao_declara_nada_que_o_codigo_nao_use(self):
        used = set(check_deps.third_party_dists())
        declared = set(check_deps.read_pyproject_dependencies())
        assert declared - used == set(), (
            f"pyproject.toml declara {sorted(declared - used)}, que nada importa."
        )


class TestManifestosConcordamComPyproject:
    """`requirements*.txt` e `pyproject.toml` nao podem divergir.

    Divergencia entre manifestos e a forma silenciosa de um pacote funcionar
    para quem usa `setup.bat` e nao funcionar para quem faz `pip install`.
    """

    @pytest.mark.parametrize(
        ("manifest", "omitir"),
        [("requirements.txt", set()), ("requirements-linux.txt", check_deps.WINDOWS_ONLY)],
    )
    def test_mesmo_conjunto_de_distribuicoes(
        self, manifest: str, omitir: set[str]
    ):
        esperado = set(check_deps.read_pyproject_dependencies()) - omitir
        assert set(check_deps.read_requirements(manifest)) == esperado, (
            f"{manifest} diverge do pyproject.toml. Divergencia entre manifestos "
            "e a forma silenciosa de o pacote funcionar para quem usa setup.bat e "
            "nao funcionar para quem faz pip install."
        )

    def test_windows_only_so_no_manifesto_do_windows(self):
        """`uiautomation` e opcional em Linux (import guardado em `core/snap.py`)."""
        linux = check_deps.read_requirements("requirements-linux.txt")
        windows = check_deps.read_requirements("requirements.txt")
        for dist in check_deps.WINDOWS_ONLY:
            assert dist in windows, f"{dist} falta em requirements.txt"
            assert dist not in linux, (
                f"{dist} e so para Windows e nao pode estar em requirements-linux.txt"
            )

    def test_manifesto_windows_marca_a_dependencia_do_windows(self):
        """A dependencia so-Windows tem de estar marcada no pyproject.

        Sem o marcador, um `pip install airmouse` no Linux tenta instalar
        `uiautomation` — que e puro mas nao pertence a um produto Linux.
        """
        marker = check_deps.read_pyproject_dependencies().get("uiautomation")
        assert marker is not None, (
            "uiautomation precisa de `; sys_platform == 'win32'` no pyproject.toml"
        )
        assert "win32" in marker


class TestModulosDeTopoSaoEmpacotados:
    """`config` e `i18n` sao modulos de topo, nao pacotes.

    Sao importados ao nivel do modulo (`from config import Config`) por 6+
    ficheiros de `core/`. Se o pyproject nao os declarar em `py-modules`, o
    pacote instalado nao os inclui e o primeiro import rebenta.
    """

    def test_modulos_de_topo_importados_estao_declarados(self):
        required = check_deps.local_top_level_modules()
        declared = check_deps.read_pyproject_py_modules()
        assert required - declared == set(), (
            f"pyproject.toml nao empacota {sorted(required - declared)} em "
            "`py-modules`, mas o codigo importa-os. Sao modulos de topo: sem "
            "esta lista nao viajam dentro do pacote."
        )

    def test_o_repo_tem_algum_modulo_de_topo_a_embacotar(self):
        """Impede que o teste passe a vazio se a leitura de imports partir."""
        assert check_deps.local_top_level_modules() >= {"config", "i18n"}
