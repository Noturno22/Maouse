"""A ajuda diz ao utilizador que atalho é que o gesto prime.

Isto é a quarta tabela deste repo escrita à mão que já divergiu do seu par, e a
única em que a divergência é visível para quem paga: o banner de arranque
(main.py) anunciava `fechar/abrir punho x2=Ctrl+D` e `bye bye=Ctrl+E`, e o
código prima `win+d` e `win+down` (core/engine.py:618 e 623). Quem seguisse a
instrução carregava Ctrl+D — que no Excel duplica a linha, e no Explorer nada
— e a janela não minimizava. Não há erro, não há excepção: o programa
funciona, e a instrução é que está errada.

Duas fontes de verdade para a mesma lista, e nenhuma a verificar a outra:

* `core/overlay.py` — o painel de ajuda do preview OpenCV. **Estava certo.**
* `i18n.py` (`help.g.wind` = "Win+D", `help.g.min` = "minimizar (Win+↓)") — a
  ajuda da janela PySide, em 7 línguas. **Estava certo.**
* `main.py:540-541` — o banner de consola, em cada arranque. **Estava errado.**

As duas que estavam certas são a prova de que se sabe ler o código para conferir
o que se escreve: `test_gesture_labels.py` faz exactamente isso com os rótulos
dos badges, e o valor de um `Enum` não é o que o utilizador lê. O que faltava
era o mesmo trato para a ajuda.

O teste compara a ajuda com o que o motor realmente prima, lido do código. Se
alguém mudar um atalho no motor, a ajuda tem de mudar com ele. Se alguém
copiar uma ajuda de uma versão antiga, isto falha.
"""

import ast
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _arvore(rel):
    with open(os.path.join(RAIZ, rel), encoding="utf-8") as f:
        return ast.parse(f.read())


#: O que a ajuda escreve, traduzido para o que o `pynput` lhe chama.
#:
#: As setas: a ajuda escreve "Win+↓" e `engine.py:623` escreve "win+down".
#: São o mesmo atalho em duas grafias, e sem esta equivalência o teste acusaria
#: um erro que não existe.
#:
#: "Maj": a ajuda francesa escreve "Alt+Maj" porque a tecla se escreve assim num
#: teclado francês — dizer "Shift" a um utilizador francês seria mandar-lo
#: procurar uma tecla que não existe na teclado dele. A ajuda está certa; a
#: guarda é que estava errada, e sem esta equivalência acusava 7 línguas de
#: mentira por causa de uma.
NOME_PARA_PYNPUT = {
    "↓": "down", "↑": "up", "←": "left", "→": "right",
    "maj": "shift",  # teclado francês
}

#: O que o motor prime, para além dos que passam por `_keyboard_shortcut`.
#: Estes vão por `core/hotkeys.py`, que faz `_ALT.press(Key.tab)` e
#: `_media_tap(Key.media_play_pause)`: não aparecem como argumento de string, e
#: sem eles uma guarda que só vê a metade pequena do codebase obriga a ajuda a
#: mentir sobre a outra metade.
#:
#: Cada entrada diz de onde vem, para que `test_..._ainda_existe` possa
#: verificá-la uma a uma. A primeira versão era um conjunto de strings com um
#: `if a == "alt+tab" else ...` ao lado — uma entrada nova entrava ali sem
#: ninguém dizer de onde veio, que é a forma silenciosa de um guard deixar de
#: proteger o que diz proteger.
FORA_DO_SHORTCUT = {
    "alt+tab": ("core/hotkeys.py", "Key.tab"),
    "alt+shift+tab": ("core/hotkeys.py", "Key.shift_l"),
    "media_play_pause": ("core/hotkeys.py", "media_play_pause"),
}


def _normaliza(s):
    """`Win+↓` e `win+down` são o mesmo atalho.

    Parte-se só pelo `+`. A primeira versão partia também pelas setas, o que
    deitava fora a própria seta em vez de a converter: `"Win+↓"` dava três
    partes, `["win", "", ""]`, o filtro ficava com `"win"` e o teste acusava um
    atalho inventado. A regra que daqui sai: um normalizador que não se
    imprime não se pode depurar.
    """
    return "+".join(
        NOME_PARA_PYNPUT.get(p.strip().lower(), p.strip().lower())
        for p in re.split(r"\+", s)
        if p.strip()
    )


def atalhos_que_o_codigo_prima():
    """Lido do `core/engine.py`, não escrito à mão — pela mesma razão que este
    teste existe."""
    vistos = set()
    for no in ast.walk(_arvore(os.path.join("core", "engine.py"))):
        if not isinstance(no, ast.Call):
            continue
        f = no.func
        nome = getattr(f, "attr", None) or getattr(f, "id", None)
        if nome != "_keyboard_shortcut":
            continue
        for a in no.args:
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                vistos.add(_normaliza(a.value))
    return vistos | set(FORA_DO_SHORTCUT)


#: `Ctrl+Shift+P`, `Win+↓`, `alt+tab`. Não `Ctrl+C` sozinho nem
#: `PALMAS (x3)`: exige uma tecla modificadora, que é o que distingue um
#: atalho de uma palavra com maiúscula.
#:
#: A parte da tecla é `[\w←-↓]+` e não `\S+` de propósito: `\S+` também agarra
#: o fecho de parênteses — "(Win+↓)" dava `win+)` — e juntava `Ctrl+C / Ctrl+V`
#: num atalho só, que é um atalho que ninguém prime. Um guard que produz
#: atalhos inventados acaba a ser desligado por quem já não acredita nele.
#: Nome de tecla como a ajuda o escreve. `maj` é o Shift do teclado francês e
#: entra aqui, e não só em `NOME_PARA_PYNPUT`, porque ocupa o lugar de um
#: *modificador* dentro do atalho: sem ele, "Alt+Maj+Tab" era lido como
#: "Alt+Maj" e a guarda acusava a tradução francesa de prometer um atalho que
#: não existe. Estava ela certa, estava a guarda errada.
#:
#: Não há entradas para `strg` ou `umschalt` porque nenhuma das traduções
#: Alemãs as usa — o texto alemão ficou com "Shift". quando uma tradução as usar, é
#: aí que a entrada se acrescenta, e não antes: uma tabela de traduções que
#: ninguém traduziu é a mesma tabela duplicada com outro nome.
MODIFICADORES = r"(?:ctrl|control|cmd|alt|opt|shift|win|super|meta|maj)"
RE_ATALHO = re.compile(
    # Vários modificadores encadeados: "Alt+Shift+Tab" é um atalho, e a
    # primeira versão do padrão parava no primeiro "+", devolvendo "Alt+Shift" —
    # um atalho que o motor não prime, ou seja, um erro inventado.
    rf"\b{MODIFICADORES}(?:\s*\+\s*{MODIFICADORES})*\s*\+\s*[\w\u2190-\u2193]+",
    re.IGNORECASE,
)


def atalhos_nas_strings_de(rel):
    """Todos os atalhos citados nas strings de um ficheiro.

    Sem filtro por nome de variável ou de função, de propósito. A primeira
    versão filtrava por `show_help` e por `log.info`, e um rename do `lines`
    local no painel — ou a ajuda passar a ser construida em vez de literal —
    deixava a lista vazia e o teste **verde a não verificar nada**. Um guard que
    fica em silêncio quando lhe mudam o nome é o pior tipo: parece que está a
    vigiar. Filtrar por nome só se paga se o filtro puder ser verificado, e
    aqui não pode.

    Os comentários não entram (não estão na AST), que era a preocupação que
    justificava o filtro: nenhuma string de `main.py` ou `core/overlay.py`
    cita um atalho que o motor não prime, à excepção dos dois que é o bug.
    """
    achados = {}
    for no in ast.walk(_arvore(rel)):
        if not (isinstance(no, ast.Constant) and isinstance(no.value, str)):
            continue
        for m in RE_ATALHO.finditer(no.value):
            achados.setdefault(_normaliza(m.group(0)), no.lineno)
    return achados


class TestAAjudaNaoMente:
    def shortcuts_que_o_codigo_prima(self):
        reais = atalhos_que_o_codigo_prima()
        assert "win+d" in reais and "win+down" in reais, (
            "esta guarda deixou de encontrar os atalhos do motor: se o motor "
            "mudar de atalho, a lista tem de mudar com ele — à mão, que é "
            "exactamente o que esta guarda existe para não fazer."
        )
        return reais

    def _confere(self, rel, minimo, onde):
        reais = self.shortcuts_que_o_codigo_prima()
        achados = atalhos_nas_strings_de(rel)
        assert len(achados) >= minimo, (
            f"{rel} só tem {len(achados)} atalho(s) citados e este teste "
            f"esperava {minimo}. A ajuda mudou de forma — deixou de ser "
            f"literal, passou a ser construida — e a guarda passou a não "
            f"verificar nada. Uma guarda que fica em silêncio quando lhe mudam "
            f"o nome é o pior tipo: parece que continua a vigiar."
        )
        falsos = {a: ln for a, ln in achados.items() if a not in reais}
        assert not falsos, (
            f"{onde} cita atalhos que o motor nunca prima: "
            + ", ".join(f"{a} ({rel}:{ln})" for a, ln in sorted(falsos.items()))
            + ". Ou o motor prime e o texto está errado, ou o texto promete um "
            "atalho que não existe. Quem o leia é um cliente a pagar: uma "
            "instrução errada não dá erro nenhum, dá a impressão de que o "
            "gesto não funciona — e o cliente conclui que o software é que é."
        )

    def test_banner_de_arranque(self):
        """`main.py:540-541` anunciava `Ctrl+D` e `Ctrl+E`. O motor prima
        `win+d` (engine.py:618) e `win+down` (engine.py:623).

        Quem seguisse a instrução carregava Ctrl+D, que no Excel duplica a
        linha e no Explorer não faz nada, e a janela não minimizava. O
        programa não dá erro nenhum: funciona, e a instrução é que mente.
        """
        self._confere("main.py", 4, "o banner de arranque")

    def test_painel_de_ajuda(self):
        self._confere(os.path.join("core", "overlay.py"), 5, "o painel de ajuda")

    def test_ajuda_i18n(self):
        """A ajuda da janela PySide, nas 7 línguas.

        `test_i18n.py` já garante que as 7 línguas têm as mesmas chaves — ou
        seja, que concordam **entre si**. O que faltava era concordarem com o
        motor: sete línguas a dizer a mesma coisa errada é sete vezes mais
        difícil de reparar, porque cada uma passa a ser fonte das outras seis.
        """
        reais = self.shortcuts_que_o_codigo_prima()
        import i18n

        vistos = 0
        for chave, d in i18n._STRINGS.items():
            if not chave.startswith("help.g."):
                continue
            for ling, texto in d.items():
                for m in RE_ATALHO.finditer(texto):
                    vistos += 1
                    a = _normaliza(m.group(0))
                    assert a in reais, (
                        f"i18n[{chave!r}][{ling!r}] cita {m.group(0)!r} ({a!r}) "
                        f"e o motor nunca prima isso. As 7 línguas têm de "
                        f"concordar com o motor, não entre si."
                    )
        assert vistos >= 14, (
            f"só {vistos} atalhos citados nas chaves help.g.* (esperado >=14, "
            f"7 línguas x 2). Ou a ajuda perdeu os atalhos, ou passaram a ser "
            f"construidas e este teste já não olha para elas."
        )

    def test_a_lista_fora_do_shortcut_ainda_existe(self):
        """Se `FORA_DO_SHORTCUT` crescer sem o motor mudar, a guarda passou a
        aceitar o que o motor não prime — que é o modo como uma guarda morre
        sem dar erro.

        Cada entrada declara o ficheiro e o atributo do pynput que a provam, e
        esta testagem vai uma a uma. É a quarta vez nesta série que um guard
        meu passava com o bug dentro. A regra não mudou: um guard que não
        consegue falhar não é um guard.
        """
        for a, (rel, prova) in FORA_DO_SHORTCUT.items():
            fonte = open(os.path.join(RAIZ, rel), encoding="utf-8").read()
            assert prova in fonte, (
                f"{a!r} está na lista de atalhos que o código prima, mas "
                f"{prova!r} já não aparece em {rel}. A lista foi adivinhada em "
                f"vez de lida: é o mesmo erro que a tabela escrita à mão, só "
                f"que mais difícil de ver."
            )
