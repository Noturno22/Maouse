"""O nome da tarefa agendada também era "AirMouse JARVIS" antes de 2026-09-29.

O rename passou o produto inteiro a "Maouse" e, com ele, o nome da tarefa de
arranque automático. Mas o nome da tarefa não vive no código: vive em dois
`.bat` que o git trata como texto e que ninguém abre depois de os escrever.

O que acontece a quem já tinha a versão antiga instalada: corre o
`uninstall_startup.bat` novo, que vai apagar a tarefa "Maouse JARVIS" — que não
existe — imprime "Arranque automatico removido." na mesma, e a "AirMouse JARVIS"
fica intacta. O `install_startup.bat` novo também não a limpa: cria a
"Maouse JARVIS" ao lado da antiga e o utilizador fica com duas tarefas em
ONLOGON sem saber qual tirar.

O que isso NÃO é: dois softares a correr. `acquire_single_instance()`
(`main.py:151`) faz o segundo processo sair com código 1. Fica o `echo` de
sucesso a mentir — que é o que impede o utilizador de reparar no resto.

Estes testes lêem os dois `.bat` e exigem que ambos conheçam os dois nomes.
Não é uma tautologia como `PACKAGE = "..."` repetido num teste: os dois
ficheiros são independentes, e o bug foi exactamente um deles ficar para trás.

Quando houver outro rename, este teste é o que tem de ser actualizado — e é
suposto que falhe até que o seja, porque cada nome esquecido aqui é um
arranque duplicado no PC de um utilizador real.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTALL = REPO_ROOT / "install_startup.bat"
UNINSTALL = REPO_ROOT / "uninstall_startup.bat"

NOME_ATUAL = "Maouse JARVIS"
NOME_ANTIGO = "AirMouse JARVIS"


@pytest.fixture(scope="module")
def scripts() -> dict[str, str]:
    return {
        "install": INSTALL.read_text(encoding="utf-8", errors="replace"),
        "uninstall": UNINSTALL.read_text(encoding="utf-8", errors="replace"),
    }


def _tarefas_que_apaga(texto: str) -> set[str]:
    """Nomes de tarefa passados a `schtasks /Delete`."""
    return set(re.findall(r'schtasks\s+/Delete\s+/TN\s+"([^"]+)"', texto))


def _tarefas_que_cria(texto: str) -> set[str]:
    return set(re.findall(r'schtasks\s+/Create\s+/F\s+/TN\s+"([^"]+)"', texto))


def _consulta_antes_de_apagar(texto: str, nome: str) -> bool:
    """O `if not errorlevel 1` que evita gritar erro quando a tarefa não existe.

    Sem isto, o `schtasks /Delete` de um nome inexistente imprime um ERROR
    confuso ao utilizador no meio da desinstalação.
    """
    for bloco in re.split(r"(?m)^schtasks ", texto):
        if f'/Delete /TN "{nome}"' in bloco:
            return "/Query /TN" in bloco.split("\n", 1)[0] or re.search(
                r'schtasks /Query /TN "([^"]+)"', bloco
            ) is not None
    return False


class TestOUninstallApagaOsDoisNomes:
    def test_apaga_a_tarefa_antiga_e_a_actual(self, scripts):
        apagadas = _tarefas_que_apaga(scripts["uninstall"])
        assert apagadas == {NOME_ATUAL, NOME_ANTIGO}, (
            f"o uninstall apaga {apagadas}. Quem instalou antes de 2026-09-29 "
            f"fica com a tarefa '{NOME_ANTIGO}' viva e arranca a aplicacao duas "
            f"vezes depois de instalar a nova."
        )

    def test_consulta_antes_de_apagar(self, scripts):
        for nome in (NOME_ATUAL, NOME_ANTIGO):
            assert _consulta_antes_de_apagar(scripts["uninstall"], nome), (
                f"falta o schtasks /Query antes de apagar '{nome}'"
            )

    def test_nao_diz_removido_a_peso(self, scripts):
        """"Arranque automatico removido." só depois de apagar alguma coisa.

        A versão anterior imprimia a frase incondicionalmente, aconteça o que
        acontecer — que é como um uninstall que não desinstala passa por
        uninstall.
        """
        texto = scripts["uninstall"]
        i_frase = texto.find("Arranque automatico removido")
        i_uso = texto.find("echo Arranque automatico removido")
        assert i_frase != -1, "a frase de sucesso desapareceu do uninstall"
        # a frase tem de estar no ramo "alguma foi removida", não fora de tudo
        ramo = texto[max(0, i_uso - 400): i_uso]
        assert re.search(r"if\s+%OK%\s*==\s*0", ramo) or "OK" in ramo, (
            "a confirmação deixou de depender de o ter sido removido algo"
        )


class TestOInstallLimpaAlegado:
    def test_cria_a_tarefa_actual(self, scripts):
        assert _tarefas_que_cria(scripts["install"]) == {NOME_ATUAL}

    def test_tira_a_tarefa_antiga_antes_de_criar_a_nova(self, scripts):
        """O `uninstall` limpa, mas ninguém é obrigado a correr o uninstall.

        Sem esta linha, quem saltou esse passo fica com as duas tarefas em
        ONLOGON mesmo tendo o `uninstall` já corrigido.
        """
        texto = scripts["install"]
        i_apaga = texto.find(f'schtasks /Delete /TN "{NOME_ANTIGO}"')
        i_cria = texto.find("schtasks /Create")
        assert i_apaga != -1, (
            f"o install nao limpa a tarefa '{NOME_ANTIGO}' de quem ja tinha a "
            "versao anterior"
        )
        assert i_apaga < i_cria, "a tarefa antiga tem de sair antes de criar a nova"
