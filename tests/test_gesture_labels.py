"""O `value` do `Gesture` é lido por alguém — quem lê o código — e é falso.

Onda 1 §1.4 de `docs/RECONHECIMENTO_MAOS.md` mandava renomear `Gesture.FIST` de
"arrastar" para "scroll", chmodando-se de "zero risco, mudança puramente
textual". Feito à letra, **parte o enum**.

Um `Enum` com dois membros de valor igual não tem dois membros: o segundo vira
*alias* do primeiro. Com `FIST = "scroll"` e o `PEACE = "scroll"` que já lá
estava, `Gesture.PEACE is Gesture.FIST` — verificado, não suposto. E aí,
sem uma única excepção:

- `Gesture.PEACE.name` devolve `"FIST"`, e o `PEACE` desaparece de
  `list(Gesture)`, de `LABEL_NAMES` do corpus e das classes do `gesture_ai.py`;
- os 7 sítios que comparam `Gesture.PEACE` passam a comparar FIST — incluindo
  o brilho em `core/engine.py:428` e o `twohand.py:603`;
- o `BADGES` e o `GESTURE_LABELS`, keyed por membro, respondem com a cor do
  FIST para o PEACE.

É o mesmo silêncio do `cryptography` em falta e da variável definida e vazia: o
que muda de significado não é o que rebenta.

A outra meia da verdade: o ficheiro é "zero risco" porque **ninguém lê o
`value`**. O que o utilizador vê é o `BADGES` de `core/overlay.py:13` e o
`GESTURE_LABELS` de `ui/theme.py:29`, e os dois já diziam a verdade —
FIST -> "SCROLL", PEACE -> "DOIS DEDOS". A mentira do §1.4 era para quem lê o
código, não para quem usa a aplicação; o plano citava o overlay como motivo e o
overlay nunca esteve errado.

Por isso a correcção são **dois** valores, não um. `FIST` passa a dizer o que
faz, e `PEACE` tem de sair de lá para um rótulo próprio — "dois dedos", que é o
que o overlay já lhe põe e a descrição que serve os dois modos (mão direita
muda o brilho, mão esquerda a interface).
"""

from __future__ import annotations

from core.gestures import Gesture

# Os dois rótulos que a Onda 1 §1.4 mandava mexer, e o que cada um tem de dizer.
# O valor do enum tem de ser o mesmo que o do badge que o utilizador lê, porque
# são a mesma informação em dois sítios: quando divergem, um dos dois mente.
PAR = {
    Gesture.FIST: "SCROLL",
    Gesture.PEACE: "DOIS DEDOS",
}


def test_valores_do_enum_sao_unicos():
    """O guard que faltava. Sem ele, o §1.4 à letra apaga um gesto em silêncio.

    Noutro enum, valor repetido é erro de estilo. Num `Enum` do Python é um
    *alias*: o membro desaparece da iteração e passa a devolver o nome do outro.

    E é por isso que este teste usa `__members__` e **não** a iteração. Com
    `FIST = "scroll"` e `PEACE = "scroll"`, `for g in Gesture` dá um só membro e
    o teste passa a dizer que não há repetidos — o alias é invisível à
    iteração. `__members__` devolve os dois. Esta versão foi escrita depois de
    a anterior ter passado com o bug presente.
    """
    valores = [m.value for m in Gesture.__members__.values()]
    repetidos = {v for v in valores if valores.count(v) > 1}
    assert not repetidos, (
        f"valores repetidos {repetidos}: em Python o segundo membro vira ALIAS "
        f"do primeiro e some de list(Gesture). Os valores têm de ser únicos."
    )
    assert len(valores) == len(set(Gesture.__members__)), "sanity"


def test_o_gesto_peace_continua_a_ser_o_gesto_peace():
    """A consequência concreta do alias, escrita para não ser ambígua.

    Se `PEACE` tivesse colado no `FIST`, `PEACE.name` passaria a ser "FIST" e o
    corpus gravaria etiqueta de FIST num frame que é PEACE — o treino da IA
    passaria a aprender a resposta errada a partir de dados apparently bons.
    """
    assert Gesture.PEACE is not Gesture.FIST
    assert Gesture.PEACE.name == "PEACE"
    assert Gesture.PEACE.value != Gesture.FIST.value


def test_nenhum_membro_se_muda_de_nome():
    nomes = [g.name for g in Gesture]
    assert len(nomes) == len(set(nomes))
    # 13 membros: NONE + 12 gestos. O numero e o que se perde num alias.
    assert len(nomes) == 13, f"esperado 13 membros, obtive {len(nomes)}: {nomes}"


def test_fist_nao_diz_arrastar():
    """A mentira original, escrita como regressão para não voltar."""
    assert Gesture.FIST.value != "arrastar", (
        "FIST e um punho fechado que desloca o scroll por delta "
        "(core/gestures.py:338-346). Dizer 'arrastar' manda quem leia o codigo "
        "procurar um gesto de arrastar que nao existe."
    )


def test_o_enum_concorda_com_o_badge_que_o_utilizador_ve():
    """Enum e badge são a mesma informação em dois sítios.

    Este é o teste que teria apanhado o §1.4 antes de ele ser escrito: se o
    valor do enum e o rótulo do overlay divergem, um dos dois mente ao leitor.
    Só se verifica o par que o §1.4 mexeu — os restantes divergem por
    abreviatura ("clique esquerdo" vs "CLIQUE ESQ") e reconciliá-los é trabalho
    de copy, não de correcção de uma mentira.
    """
    from core.overlay import BADGES

    for gesto, badge in PAR.items():
        assert gesto.value.upper() == badge, (
            f"{gesto.name}: o enum diz {gesto.value!r} e o overlay diz {badge!r}. "
            f"O utilizador le o overlay; quem le o codigo le o enum."
        )
        assert BADGES[gesto][0] == badge, (
            f"{gesto.name}: o BADGES do overlay mudou para {BADGES[gesto][0]!r}"
        )
