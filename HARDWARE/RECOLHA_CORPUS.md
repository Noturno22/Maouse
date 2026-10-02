# Gravar um corpus de mãos reais

Isto é o procedimento operativo. O *porquê* de cada regra — porque é um ficheiro
e não treze, porque a tecla vai antes da pose — está no `PROGRESSO.md` §itens
25 e no bloqueador #4.

## Primeiro, um ensaio de 60 s

Não comeces pela sessão a sério. Grava uma volta só para `data\smoke.npz` e
confirma que a janela abre, que o painel responde às teclas e que o ficheiro é
gravado no fim. Se algo estiver errado, perdeste um minuto em vez de três.

**O ficheiro de ensaio não serve para medir nada** — um minuto não tem tempo de
mão ausente nem transições suficientes. Serve para provar que a máquina grava.

Depois faz a sessão a sério, noutro ficheiro.

## Comando

```
.venv\Scripts\python.exe main.py --record data\sessao1.npz
```

Quando aparecer, clica **uma vez** na janela do preview (sem `--record-live` o
rato está mudo, portanto o clique não faz nada ao sistema) e deixa-a com o
foco. As teclas só chegam à janela que tem o foco.

## As três regras

1. **A tecla vai ANTES de adoptares a pose.** A etiqueta vale a partir do
   momento em que a carregaste, não de quando viste o gesto. Se adoptares a
   pose primeiro, os primeiros frames ficam com a etiqueta anterior — e esse
   erro fica no ficheiro para sempre.
2. **Gestos com a mão direita, e só ela no enquadramento.** Só a mão **do
   cursor** é gravada, e o cursor segue a mão que tem a palma mais à direita no
   frame espelhado — ou seja, a tua **mão direita** (o preview vem espelhado,
   como num espelho). A mão esquerda fora de vista. Se a faixa avisar
   `2 MAOS NO ECRA`, mexe a mão que está a gesticular até ficar à direita.
3. **Não interrompas uma pose a meio.** Deixa cada gesto 2–3 segundos
   estável. O `SETTLE` que fica entre gestos é o que o `--replay-settle-guard-ms`
   mede, e só existe se as transições forem reais.

`neste` na faixa é os frames do segmento atual. **Se ficar em `0f`, a etiqueta
foi posta sem mão à vista** — corrige antes de seguir, porque a etiqueta
errada não se desfaz.

`x` limpa a sessão **toda**. `Q` sai e grava.

## A sequência

Uma volta são ~60 s: 10 s de mão fora + 13 gestos × 3 s + 10 s de mão fora.
Três voltas são ~3 min.

| Fase | O quê | Tecla |
|---|---|---|
| 1 | mão fora do enquadramento, ~10 s | `0` |
| 2 | mão aberta, ~3 s | `1` |
| | um dedo, ~3 s | `2` |
| | pinça indicador+polegar, ~3 s | `3` |
| | pinça indicador+médio, ~3 s | `4` |
| | punho, ~3 s | `5` |
| | dois dedos, ~3 s | `6` |
| | três dedos, ~3 s | `7` |
| | polegar para cima, ~3 s | `8` |
| | polegar para baixo, ~3 s | `9` |
| | mindinho, ~3 s | `d` |
| | ok, ~3 s | `c` |
| | horns, ~3 s | `g` |
| 3 | mão fora do enquadramento, ~10 s | `0` |
| 4 | `Q` — sai e grava | `Q` |

**Entre gestos não saltes poses.** Passa por uma mão neutra. É a transição que
mede o debounce; um salto de PINCH para PEACE sem passar por nada não é uma
transição, é um corte, e o corpus perde a única coisa que mede a latência.

Repete a fase 2 **duas ou três vezes**, variando distância, ângulo e luz. Duas
voltas iguais chegam a dar 13 classes com poucas centenas de frames cada; três
voltas com condições diferentes dão o que a matriz de compatibilidade do
`HARDWARE/LAB.md` precisa.

**As fases 1 e 3 não são decorativas.** São o tempo de mão ausente, e é o
único sítio onde se mede se o rato se mexe sozinho. Um ficheiro por gesto não
teria nenhum.

## Depois

```
.venv\Scripts\python.exe main.py --replay data\sessao1.npz --replay-settle-guard-ms 300
```

O `--replay` não usa câmara nem toca no rato: relê as landmarks do ficheiro,
corre o classificador outra vez frame a frame e compara com as etiquetas que
puseste. Sai:

| Linha | O que te diz |
|---|---|
| `F1 macro` | o número que vai para terceiros |
| `gesto  P R F1 N` | por classe; `N` baixo = essa classe quase não foi gravada |
| `cliques fantasma` | cliques em frames que não eram de clique. O número que o cliente sente |
| `latencia clique p50/p95` | o custo do debounce |
| `Transicao` | frames em `SETTLE`, excluídos do F1 |

Se o F1 não sair, é a recolha que está errada, não o número. Ver
`HARDWARE/PROBLEMAS_KNOWN.md` §1.1–1.2, que é onde este número vai parar.

## Se correr mal

O ficheiro **não** se grava até `Q`. Se fechares a janela à força, perdes a
sessão. É por isso que se grava primeiro um ensaio de 60 s.

