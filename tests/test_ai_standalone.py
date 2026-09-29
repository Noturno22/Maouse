"""A IA sozinha, medida contra as etiquetas do corpus.

Porque este ficheiro existe
---------------------------
`--replay-gate` dá F1 macro 1.0000 **com e sem a IA** — a saída é idêntica linha
a linha, porque num corpus sintético as regras geométricas resolvem tudo antes de
o modelo ser consultado. Ou seja: o portão de regressão, que tem sido verde em
todos os commits, **não vê a IA**. Um retreino que produzisse pesos inúteis
passaria o portão com o mesmo conforto de antes.

Este teste mede o que o portão não mede: o `GestureAI` sozinho, no mesmo corpus,
contra as mesmas etiquetas. É o número que muda quando os pesos mudam.

O que o número mede — e o que não mede
--------------------------------------
Mede a **lista de classes**, não a qualidade dos pesos. Motivo: no corpus
sintético o modelo acerta as 9 classes que conhece a 100% e erra as 3 que não
conhece a 100%. Não é sorte: `PINKY → SHAKA` 12/12, `ONE → ROCK` 6/8,
`THUMB_DOWN → FIST` 4/4 — cada gesto cai na classe mais próxima que existe.
Erigir-se aqui uma afirmação sobre a qualidade do modelo seria ler uma
distribuição sintética como se fosse mãos reais, que é o erro que o `source:
"synthetic"` do corpus existe para impedir.

A regra que este teste fixa
---------------------------
Cada gesto **que o modelo consegue representar** tem de ser classificado certo.
Os gestos que ele não consegue não são falhados aqui — são contados, e é isso
que diz qual é o estrangulamento. Quando o retreino para 13 classes trouxer
`ONE`, `PINKY` e `THUMB_DOWN` para dentro de `CLASSES`, este teste começa a
exigir também esses, sem ninguém lhe tocar. Fica mais forte sozinho, que é o
único sítio onde isso acontece.
"""
from collections import Counter
from pathlib import Path

import pytest

from core.corpus import SETTLE_LABEL, Corpus
from core.gesture_ai import CLASSES, GestureAI

RAIZ = Path(__file__).resolve().parents[1]
FIXTURE = RAIZ / "tests" / "fixtures" / "corpus_regressao_v1.npz"
MODELO = RAIZ / "models" / "gesture_mlp.npz"


@pytest.fixture(scope="module")
def ia_sozinha():
    """(acertos, total) por nome de gesto, com o modelo sozinho.

    Percorre `replay_with_conf()` e classifica cada mão com `GestureAI.classify`
    — o caminho real, o mesmo que `HandPool` usa. Exclui os frames `SETTLE`
    (transição), como o portão também exclui: quem está a meio de mudar de pose
    não pertence a nenhuma classe.
    """
    if not MODELO.is_file():
        pytest.skip(f"modelo ausente: {MODELO}")
    ai = GestureAI(str(MODELO))
    corpus = Corpus.load(str(FIXTURE))
    acertos, total = Counter(), Counter()
    for _t, hands, _sides, labels, _active, _confs in corpus.replay_with_conf():
        for mao, real in zip(hands, labels, strict=True):
            if real == SETTLE_LABEL:
                continue
            prev, _conf = ai.classify(mao)
            if prev is None:
                continue
            total[real] += 1
            if prev.name == real:
                acertos[real] += 1
    return acertos, total


def test_o_corpus_diz_que_e_sintetico(ia_sozinha):
    """Este ficheiro só vale a pena se os dados forem o que dizem ser.

    Sem isto, um dia estes números passam a ser lidos como desempenho em mãos
    reais porque alguém não reparou na origem. O `meta` do corpus diz
    `generator: make_corpus_fixture.py` e `device: nenhum (gerado)`; o teste é
    que garante que ninguém troca a fixture por dados reais sem que a
    afirmação deste ficheiro seja revista com ela.
    """
    corpus = Corpus.load(str(FIXTURE))
    assert corpus.is_synthetic, (
        f"o corpus deixou de ser sintetico (source={corpus.source!r}). "
        f"Se passou a ser maos reais, os numeros deste ficheiro passam a "
        f"medir algo diferente e a nota do topo tem de ser reescrita — a "
        f"partir da leitura errada, que e o que custa caro."
    )


def test_a_ia_acede_a_todas_as_classes_que_o_modelo_declara(ia_sozinha):
    """A parte que o portão não cobre: o modelo tem de acertar o que tem.

    Chão em 1.00, e não em 0.9. É deliberado: no corpus sintético, o modelo
    erra exclusivamente as classes que **não tem**, e esta é a única
    afirmação sobre pesos que os dados synthéticos suportam. Um chão mais baixo
    deixaria passar um modelo degradado em silêncio, que é o que o `--replay-gate`
    já faz hoje e que este ficheiro existe para não repetir.
    """
    acertos, total = ia_sozinha
    modelos = {g.name for g in CLASSES}

    representadas = {nome: (acertos[nome], total[nome])
                     for nome in total if nome in modelos}
    assert representadas, (
        f"nenhum gesto do corpus pertence a CLASSES ({modelos}). O corpus ou as "
        f"classes mudaram e este teste deixou de estar a medir o que diz medir."
    )

    maus = {nome: par for nome, par in representadas.items() if par[0] != par[1]}
    assert not maus, (
        f"a IA errou em classes que o modelo declara ter: {maus}. "
        f"Num corpus sintetico isto nao e a mao do utilizador a falhar: e o "
        f"modelo. E o `--replay-gate` nao o apanha -- da 1.0000 com `--no-ai`."
    )


def test_o_que_a_ia_nao_sabe_diz_o_estrangulamento(ia_sozinha):
    """As classes que faltam são a informação, não um defeito a esconder.

    Este teste **não** falha quando o modelo não sabe um gesto: fixa que,
    enquanto faltar, ele erra **todos** os frames desse gesto. É assim que se
    distingue "ainda não foi treinado para isto" de "treinado e ainda falha",
    que é a distinção que diz se o próximo passo é recolher dados ou debugging.
    """
    acertos, total = ia_sozinha
    modelos = {g.name for g in CLASSES}

    fora = {nome: (acertos[nome], total[nome])
            for nome in total if nome not in modelos}
    for nome, (ok, n) in fora.items():
        assert ok == 0, (
            f"o modelo NAO tem a classe {nome} e mesmo assim acertou {ok}/{n}. "
            f"Ou a lista de classes não é a que o `CLASSES` diz, ou o terreno "
            f"muda. As duas coisas sao erradas, e uma delas cala a "
            f"mediacao de `test_a_ia_acede_a_todas_as_classes_que_o_modelo_declara`."
        )
