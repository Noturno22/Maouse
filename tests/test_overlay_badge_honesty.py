"""O ecrã não pode dizer que não há mão quando há mão.

O `BADGES` de `core/overlay.py` tem 11 entradas e o `Gesture` tem 13 membros.
Faltam `THUMB_DOWN` e `ROCK`, e os dois são produzidos pelo motor:

* `core/gestures.py:248` — o caminho **geométrico** devolve `THUMB_DOWN`;
* `core/gestures.py:260` devolve `ROCK`, e `:297` deixa a IA confirmá-lo
  (`ml_g == Gesture.ROCK and geo == Gesture.ROCK`), portanto também sai do
  classificador das 9 classes.

O `draw_overlay` procurava o rótulo com `BADGES.get(hf.gesture,
BADGES[Gesture.NONE])`. Para esses dois gestos o fallback é o de `NONE`: o
overlay desenhava **"SEM MAO"**, a cinzento, com a mão no enquadramento.

Isto não é um rótulo em falta, é o pior sinal possível no pior sitio. O badge
é a única resposta que o utilizador tem em tempo real sobre o que o
reconhecedor achou que ele fez. Se ele faz o gesto, o classificador concorda, e
o ecrã diz que não há mão, a conclusão dele é "isto não funciona" — e a
repetição do gesto é a tentativa cansativa que este projecto existe para tirar.
Não há excepção, não há log, não há como isto ser notado por quem não tenha
a mão à frente.

Este teste percorre `Gesture.__members__` e **não** uma lista escrita à mão.
É a mesma lição do `test_gesture_labels.py`: a iteração sobre o `Enum` não vê
aliases, e o `PEACE` apagado em silêncio (Onda 1 §1.4) passou numa verificação
feita com a iteração. `__members__` vê.
"""

from __future__ import annotations

import pytest

from core.gestures import Gesture
from core.overlay import BADGES, COLOR_SEM_ROTULO, _badge


class _MaoFicticia:
    """O mínimo que `_badge` lê. Não construir um `HandFrame` inteiro para
    verificar uma busca de dicionário éumpouover de 21 pontos."""  # noqa: E501

    def __init__(self, gesto):
        self.gesture = gesto


def _gestos_do_codigo():
    """Os gestos que `core/gestures.py` produz, lidos do próprio ficheiro.

    Aceita as duas formas em que aparecem: `geo = Gesture.ROCK` (como estão
    hoje) e `return Gesture.ROCK`. Se um dia passar a ser uma tabela ou um
    `match`, isto devolve menos e o `assert` abaixo diz qual é o problema — em
    vez de a lista esvaziar e o resto do ficheiro deixar de olhar para o motor
    sem que ninguém dê por isso.
    """
    import ast
    import inspect

    arvore = ast.parse(inspect.getsource(inspect.getmodule(Gesture)))
    vistos = set()
    for no in ast.walk(arvore):
        alvo = no.value if isinstance(no, (ast.Assign, ast.Return)) else None
        if not (isinstance(alvo, ast.Attribute) and isinstance(alvo.value, ast.Name)):
            continue
        if alvo.value.id == "Gesture":
            vistos.add(alvo.attr)
    assert len(vistos) >= 10, (
        f"a leitura de 'que gestos o codigo produz' devolveu {len(vistos)}: "
        f"{sorted(vistos)}. Se `core/gestures.py` passar a produzi-los por "
        f"outra via, esta lista esvazia e o resto do ficheiro deixa de olhar "
        f"para o motor — que é a razão de ele aqui estar."
    )
    return {getattr(Gesture, n) for n in vistos}


class TestOBadgeNaoMente:
    def test_um_gesto_reconhecido_nao_diz_sem_mao(self):
        """O bug. Para qualquer gesto que o motor produza, o rótulo tem de ser
        o do gesto — nunca o de `NONE`."""
        for gesto in sorted(_gestos_do_codigo(), key=lambda g: g.name):
            if gesto is Gesture.NONE:
                continue
            rotulo, _cor = _badge(_MaoFicticia(gesto))
            assert rotulo != BADGES[Gesture.NONE][0], (
                f"o motor produz {gesto.name} e o overlay ia mostrar "
                f"{BADGES[Gesture.NONE][0]!r}. O utilizador que fez o gesto "
                f"vê que o programa não está a ver a mão, e repete-o."
            )

    @pytest.mark.parametrize("nome", ["THUMB_DOWN", "ROCK"])
    def test_os_dois_que_faltavam_agora_dizem_o_que_sao(self, nome):
        """Estes dois não é que o rótulo seja bonito: é que seja o do
        ``name``. A palavra que o utilizador deve ler é decisão do dono do
        produto, e tomá-la aqui dentro de um bug de ecrã seria tomá-la sem ele
        dar por isso."""
        gesto = getattr(Gesture, nome)
        rotulo, _cor = _badge(_MaoFicticia(gesto))
        assert rotulo == nome

    def test_a_cor_de_um_gesto_por_nomear_nao_e_a_de_nenhum_outro(self):
        """A propriedade, não a constante.

        A primeira versão comparava `cor == COLOR_SEM_ROTULO`, ou seja, o módulo
        consigo próprio — mudava-se a constante e o teste continuava verde,
        porque **importa a mesma constante que mudou**. Era uma guarda que não
        podia falhar, pela quinta vez nesta série.

        O que interessa é que dois estados diferentes não se vejam iguais: o
        esqueleto da mão é desenhado com esta cor, e se um gesto por nomear
        tiver a cor de um gesto já decidido, o utilizador não tem como
        distinguir. E em particular não pode ter a cor de "sem mão", que é
        exactamente o estado que este bug confundia com o gesto.
        """
        cor = COLOR_SEM_ROTULO
        assert cor != BADGES[Gesture.NONE][1], (
            f"{cor} é a cor de 'sem mão'. Um gesto que o motor reconheceu e "
            f"ainda não tem rótulo não pode ser desenhado como 'sem mão' — é o "
            f"mesmo bug por outra via."
        )
        for gesto, (_rotulo, c) in BADGES.items():
            if gesto is Gesture.NONE:
                continue
            assert cor != c, (
                f"{cor} é também a cor de {gesto.name!r}. Dois estados que se "
                f"veem iguais não são estados que o utilizador consiga ler."
            )

    def test_sem_mao_continua_a_dizer_sem_mao(self):
        """O outro lado da guarda: se isto deixar de ser verdade, o overlay
        cala-se e o utilizador perde a informação de que a mão saiu do
        enquadramento. Um guard que só proíbe um lado deixa passar o outro."""
        rotulo, _cor = _badge(_MaoFicticia(Gesture.NONE))
        assert rotulo == BADGES[Gesture.NONE][0]

    def test_os_gestos_com_badge_continuam_iguais(self):
        """A correcção não pode ter mexido no que já funcionava: um
        `BADGES.get` que passa a devolver outra coisa para `PINCH` é uma
        regressão que o teste do rótulo não veria."""
        for gesto, (rotulo, cor) in BADGES.items():
            if gesto is Gesture.NONE:
                continue
            assert _badge(_MaoFicticia(gesto)) == (rotulo, cor), gesto.name

    def test_badges_nao_tem_membros_que_nao_existem(self):
        """O outro sentido: uma entrada órfã em `BADGES` também é uma tabela
        que divergiu, e na direcção que ninguém vê — a chave está lá, o
        membro não."""
        for gesto in BADGES:
            assert isinstance(gesto, Gesture), f"{gesto!r} nao e um Gesture"


def test_a_lista_de_gestos_diz_o_que_o_codigo_diz():
    """Guarda de sanidade sobre a própria extracção.

    A primeira versão desta guarda contava quantas vezes `core/overlay.py`
    citava `Gesture.` e acusava acima de um limite. Contava também o que está
    nos *docstrings* — que é onde esta correcção se descreve —, e o número que
    dá não significa nada. Um teste que mede a coisa errada é pior do que não
    ter teste: fica verde e dá a falsa sensação de estar a vigiar.

    O que vigia é o que interessa, e está nos testes de cima: `BADGES` não pode
    ter uma chave que não seja membro do `Enum`, e nenhum membro que o motor
    produz pode ficar sem o rótulo que é o dele.
    """
    assert Gesture.ROCK in _gestos_do_codigo(), "sanity: o motor produz ROCK"
    assert Gesture.THUMB_DOWN in _gestos_do_codigo(), "sanity: e THUMB_DOWN"
