# Gravar um corpus de mãos reais

Comando:

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
2. **Uma mão só no enquadramento.** Só a mão **do cursor** é gravada, e o
   cursor é a mão que aparece **mais à direita** no preview. A outra mão fica
   fora de vista. Se a faixa avisar `2 MAOS NO ECRA`, mexe a mão que está a
   fazer os gestos até ficar a ser a da direita.
3. **Não interrompas uma pose a meio.** Deixa cada gesto 2–3 segundos
   estável. O `SETTLE` que fica entre gestos é o que o `--replay-settle-guard-ms`
   mede, e só existe se as transições forem reais.

`neste` na faixa é os frames do segmento atual. **Se ficar em `0f`, a etiqueta
foi posta sem mão à vista** — corrige antes de seguir, porque a etiqueta
errada não se desfaz.

`x` limpa a sessão **toda**. `Q` sai e grava.

## A sequência

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

## Depois

```
.venv\Scripts\python.exe main.py --replay data\sessao1.npz --replay-settle-guard-ms 300
```

Este é o número que vai para terceiros (`HARDWARE/PROBLEMAS_KNOWN.md` §1.1–1.2
dependem dele). Se ele não sair, é a recolha que está errada, não o número.

## Se correr mal

O ficheiro **não** se grava até `Q`. Se fechares a janela à força, perdes a
sessão. É por isso que a fase 1 e a fase 3 são só "mão fora": dão-te a
confirmação de que a máquina está a gravar antes de gastares os 20 minutos.
