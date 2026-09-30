"""Invariantes de nome que, quando partem, não dão sinal visível.

Existe por causa do rename de 2026-09-29 (AirMouse -> Maouse), que passou por
~110 ficheiros e trocou valores que o servidor **rejeita** quando não batem
certo. Divergir aqui não dá crash: dá uma resposta de erro normal
(`pacote_errado`, `produto_errado`) contra um servidor real, ou um
`os.environ.get` que devolve `""` e o produto degrada-se em silêncio. São as
duas classes de bug que já nos custaram tempo — o `cryptography` em falta nos
manifests, e o `pack` divergente do esperado. Nenhum dos dois aparece num
teste, porque nenhum dos dois dá exception.

`license-server/tests/test_mobile_entitle.py` **não** apanha nada disto: ele
declara o seu próprio `PACKAGE = "..."` e manda esse valor. Um teste que
repete a constante passa sempre, aconteça o que acontecer ao resto. Por isso
aqui cada valor é lido do sítio onde é realmente declarado.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MOBILE = REPO_ROOT / "mobile" / "maouse-mobile"
PLUGIN = MOBILE / "plugins" / "with-maouse-native"
KOTLIN = PLUGIN / "templates" / "android"


def _deve_encontrar(caminho: Path, padrao: str, grupo: int = 1) -> str:
    """Extrai um valor, e falha alto se o padrão deixar de bater certo.

    O erro deliberado aqui é "o código mudou de forma", não "o valor mudou".
    Se alguém mover a constante, este teste avisa — em vez de devolver `None` e
    passar a comparação por cima de uma lista de `None` que é igual a ela própria.
    """
    texto = caminho.read_text(encoding="utf-8")
    achado = re.search(padrao, texto, re.MULTILINE)
    rel = caminho.relative_to(REPO_ROOT).as_posix()
    assert achado is not None, (
        f"{rel} já não declara o valor neste formato. O teste precisa de ser "
        f"atualizado para a nova forma — não o é que o valor pode mudar à vontade."
    )
    return achado.group(grupo)


class TestPackageAndroid:
    """O `android.package` tem de ser o mesmo em todos os que o declaram.

    O servidor compara o `package_name` que a app envia com o que espera e
    responde `pacote_errado` se não bater. Do lado do utilizador isso é uma app
    que não reconhece a subscrição: sem crash, sem erro, só o Pro que não chega.
    """

    def _valor_do_servidor(self) -> str:
        return _deve_encontrar(
            REPO_ROOT / "license-server" / "app.py",
            r'os\.getenv\(\s*"MAOUSE_MOBILE_PACKAGE_NAME"\s*,\s*"([^"]+)"',
        )

    def test_app_json_declara_o_package_nas_tres_chaves(self):
        """`android.package`, `ios.bundleIdentifier` e `extra.androidPackage`.

        Confirmado contra a referência de app config do Expo SDK 57: a
        `applicationId` do Android vem de `android.package`; `bundleIdentifier`
        é a chave do iOS; e `extra` é um objeto livre que o cliente lê em
        runtime via `Constants.expoConfig.extra`.

        São três leituras independentes do mesmo facto, e o cliente tem um
        fallback hardcoded — logo, um erro aqui fica tapado pelo fallback até
        alguém mudar o `extra`, e só aparece como `pacote_errado` em produção.
        """
        config = json.loads((MOBILE / "app.json").read_text(encoding="utf-8"))
        expo = config["expo"]
        valores = {
            "expo.android.package": expo["android"]["package"],
            "expo.ios.bundleIdentifier": expo["ios"]["bundleIdentifier"],
            "expo.extra.androidPackage": expo["extra"]["androidPackage"],
        }
        assert len(set(valores.values())) == 1, (
            f"O package diverge dentro do próprio app.json: {valores}"
        )

    def test_o_package_e_o_mesmo_em_todos_os_declarantes(self):
        esperado = self._valor_do_servidor()

        declarantes: dict[str, str] = {
            # o que o config plugin injeta no código nativo durante o prebuild
            "plugins/with-maouse-native/index.js": _deve_encontrar(
                PLUGIN / "index.js", r'const PACKAGE_NAME\s*=\s*"([^"]+)"'
            ),
            # o fallback do cliente quando o `extra` não vem
            "src/hooks/useProEntitlement.ts": _deve_encontrar(
                MOBILE / "src" / "hooks" / "useProEntitlement.ts",
                r"extra\?\.androidPackage as string\)\s*\|\|\s*'([^']+)'",
            ),
            # o valor que o deploy define
            "render.yaml": _deve_encontrar(
                REPO_ROOT / "render.yaml",
                r"key:\s*MAOUSE_MOBILE_PACKAGE_NAME\s*\n\s*value:\s*(\S+)",
            ),
        }
        # `package` de declaration, não os `import com.facebook.react...`.
        # O `SystemControllerModule.kt` tem BOM, daí o `\ufeff?`.
        for kotlin in sorted(KOTLIN.glob("*.kt")):
            declarantes[f"templates/android/{kotlin.name}"] = _deve_encontrar(
                kotlin, r"^[^\S\n]*\ufeff?package\s+(\S+)"
            )

        divergentes = {n: v for n, v in declarantes.items() if v != esperado}
        assert not divergentes, (
            f"O servidor aceita '{esperado}' e estes divergem: {divergentes}. "
            "O servidor responde `pacote_errado` e o utilizador fica sem Pro, "
            "sem erro visível."
        )

    def test_o_package_actual_e_o_esperado(self):
        """Trava o valor, não só a coerência.

        A coerência sozinha passa se alguém trocar o package em todos os sítios
        de uma vez. Este teste diz qual é o valor, para o motivo do rename ficar
        explícito e a lista de sítios a actualizar ficar escrita.
        """
        assert self._valor_do_servidor() == "com.maouse.mobile"


class TestProductIdMobile:
    """O mesmo invariante para o product id — mesma validação, mesmo modo de falhar."""

    def test_o_product_id_e_o_mesmo_em_todos_os_declarantes(self):
        esperado = _deve_encontrar(
            REPO_ROOT / "license-server" / "app.py",
            r'os\.getenv\(\s*"MAOUSE_MOBILE_PRODUCT_ID"\s*,\s*"([^"]+)"',
        )
        declarantes: dict[str, str] = {
            "render.yaml": _deve_encontrar(
                REPO_ROOT / "render.yaml",
                r"key:\s*MAOUSE_MOBILE_PRODUCT_ID\s*\n\s*value:\s*(\S+)",
            ),
            "src/hooks/useProEntitlement.ts": _deve_encontrar(
                MOBILE / "src" / "hooks" / "useProEntitlement.ts",
                r"extra\?\.mobileProductId as string\)\s*\|\|\s*'([^']+)'",
            ),
        }
        config = json.loads((MOBILE / "app.json").read_text(encoding="utf-8"))
        declarantes["app.json#extra.mobileProductId"] = config["expo"]["extra"]["mobileProductId"]

        divergentes = {n: v for n, v in declarantes.items() if v != esperado}
        assert not divergentes, (
            f"O servidor espera '{esperado}' e estes divergem: {divergentes}. "
            "O produto id também é validado no servidor."
        )


class TestVariaveisDeAmbienteDoRender:
    """O que o Render define tem de ser o que o código lê.

    `render.yaml` é a única fonte versionada do que o serviço recebe em
    produção. Uma variável lá que ninguém lê é ruído; pior é a inversa — o código
    ler um nome que o Render não define dá `""` e o serviço degrada-se sem
    erro, que foi exactamente como o `cryptography` em falta conseguiu passar
    por uma instalação que arrancava.
    """

    def _declaradas_no_render(self) -> set[str]:
        texto = (REPO_ROOT / "render.yaml").read_text(encoding="utf-8")
        return set(re.findall(r"^\s*-\s*key:\s*(\w+)\s*$", texto, re.MULTILINE))

    def _lidas_pelo_servidor(self) -> set[str]:
        modulos = sorted((REPO_ROOT / "license-server").glob("*.py"))
        fonte = "\n".join(p.read_text(encoding="utf-8") for p in modulos)
        return set(
            re.findall(r'(?:os\.getenv|os\.environ(?:\.get)?)\(\s*["\']?([A-Z][A-Z0-9_]+)', fonte)
        )

    def test_nada_definido_no_render_e_ignorado(self):
        declaradas = self._declaradas_no_render()
        assert declaradas, "o parse do render.yaml devolveu nada — o teste está partido"
        orfas = declaradas - self._lidas_pelo_servidor()
        assert not orfas, (
            f"O Render define mas o código nunca lê: {sorted(orfas)}. "
            "Ou a variável trocou de nome, ou já não é usada — nos dois casos "
            "o render.yaml está a mentir sobre o que o serviço recebe."
        )

    def test_nada_lido_por_pelo_codigo_esta_declarado(self):
        lidas = self._lidas_pelo_servidor()
        em_branco = lidas - self._declaradas_no_render()
        assert not em_branco, (
            f"O código lê mas o Render não define: {sorted(em_branco)}. "
            "Vão chegar como string vazia em produção, sem aviso."
        )

    def test_toda_var_do_exemplo_que_seja_nossa_e_lida(self):
        """`.env.example` documenta o que o ambiente local precisa de ter.

        Direcção única de propósito: uma variável nossa no exemplo que ninguém
        lê é ruído, mas é barato. O que seria caro é a inversa — uma variável
        que o código lê e que o exemplo não documenta, porque aí o ambiente de
        desenvolvimento fica incompleto sem ninguém dar por isso. Essa é a
        direcção que este teste apanha, e é a que o rename podia ter partido.

        Só entram as variáveis `MAOUSE_*`: o `.env.example` também traz chaves
        de terceiros (`OPENAI_API_KEY`, `GROQ_API_KEY`) que não são config
        nossa, e cujo prefixo ninguém deve renomear.
        """
        exemplo = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
        declaradas = {
            m.group(1)
            for m in re.finditer(r"^\s*#?\s*(MAOUSE_[A-Z0-9_]+)\s*=", exemplo, re.MULTILINE)
        }
        assert declaradas, "o parse do .env.example devolveu nada — o teste está partido"

        fonte = "\n".join(
            p.read_text(encoding="utf-8")
            for p in (
                *sorted((REPO_ROOT / "license-server").glob("*.py")),
                REPO_ROOT / "core" / "licensing.py",
                REPO_ROOT / "ui" / "license_dlg.py",
            )
        )
        lidas = set(
            re.findall(
                r'(?:os\.getenv|os\.environ(?:\.get)?|env_value|env_int)\(\s*["\']?(MAOUSE_[A-Z0-9_]+)',
                fonte,
            )
        )
        nunca_lidas = declaradas - lidas
        assert not nunca_lidas, (
            f"O .env.example documenta mas o código nunca lê: {sorted(nunca_lidas)}. "
            "O ambiente de desenvolvimento vai encher isto e não vai acontecer nada."
        )
