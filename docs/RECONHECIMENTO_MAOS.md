# Mãouse Desktop — Reconhecimento de Mãos e Gestos

Documento técnico de referência. **Parte 1** descreve exactamente como o
reconhecimento funciona hoje, fase por fase, com referências de código.
**Parte 2** faz a análise de lacunas face ao hand tracking da Meta Quest.
**Parte 3** é o plano para chegar a esse nível.

Estado do repositório em 2026-09-28.
Referência de gestos para o utilizador: `GESTOS.md`.

---

## ÍNDICE

- [Parte 1 — Como funciona hoje](#parte-1--como-funciona-hoje)
  - [1.1 Visão geral do pipeline](#11-visão-geral-do-pipeline)
  - [1.2 Fase 1 — Captura](#12-fase-1--captura)
  - [1.3 Fase 2 — Pré-processamento](#13-fase-2--pré-processamento)
  - [1.4 Fase 3 — Inferência (MediaPipe)](#14-fase-3--inferência-mediapipe)
  - [1.5 Fase 4 — Despacho por mão](#15-fase-4--despacho-por-mão-handpool)
  - [1.6 Fase 5 — Classificação geométrica](#16-fase-5--classificação-geométrica)
  - [1.7 Fase 6 — IA confirmadora (MLP)](#17-fase-6--ia-confirmadora-mlp)
  - [1.8 Fase 7 — Escolha de mão](#18-fase-7--escolha-de-mão)
  - [1.9 Fase 8 — Movimento do cursor](#19-fase-8--movimento-do-cursor)
  - [1.10 Fase 9 — Gestos compostos](#110-fase-9--gestos-compostos-e-duas-mãos)
  - [1.11 Fase 10 — Gesto → Evento](#111-fase-10--gesto--evento)
  - [1.12 Referência de gestos](#112-referência-de-gestos)
  - [1.13 Referência de configuração](#113-referência-de-configuração)
  - [1.14 Mapa de ficheiros](#114-mapa-de-ficheiros)
  - [1.15 Cobertura de testes](#115-cobertura-de-testes)
  - [1.16 Limitações conhecidas](#116-limitações-conhecidas)
- [Parte 2 — Lacunas face à Meta Quest](#parte-2--lacunas-face-à-meta-quest)
  - [2.1 Como a Meta faz](#21-como-a-meta-faz)
  - [2.2 Tabela comparativa](#22-tabela-comparativa)
  - [2.3 As 6 lacunas estruturais](#23-as-6-lacunas-estruturais)
- [Parte 3 — Plano para nível profissional](#parte-3--plano-para-nível-profissional)
  - [3.0 Princípio](#30-princípio-medir-antes-de-otimizar)
  - [3.1 Onda 0 — Instrumentação](#31-onda-0--instrumentação-e-métricas)
  - [3.2 Onda 1 — Alto ROI, sem ML](#32-onda-1--correções-de-alto-roi-sem-ml)
  - [3.3 Onda 2 — Features à Meta](#33-onda-2--arquitectura-de-features-à-meta)
  - [3.4 Onda 3 — ML real](#34-onda-3--ml-real)
  - [3.5 Onda 4 — Identidade e oclusão](#35-onda-4--identidade-oclusão-e-continuidade)
  - [3.6 Onda 5 — Menos gestos, melhores](#36-onda-5--redução-do-conjunto-de-gestos)
  - [3.7 Roadmap](#37-roadmap)
  - [3.8 Métricas de aceitação](#38-métricas-de-aceitação)
  - [3.9 Riscos](#39-riscos-e-não-objetivos)

---

# Parte 1 — Como funciona hoje

## 1.1 Visão geral do pipeline

O motor vive em `core/engine.py:191` (`process_frame`) e é **partilhado sem
divergência** pelo preview OpenCV e pela janela PySide6 — ambos consomem o
mesmo contexto devolvido por `make_engine_ctx` (`core/engine.py:112`). A
garantia de paridade total é explícita no docstring do módulo.

```
                          ┌──────────────────────────────────────┐
  thread da câmara ──────▶│ 1. CameraStream.read() → (frame,seq) │
  (core/camera.py:84)     └───────────────┬──────────────────────┘
                                          │  (descarta se seq repetido)
                                          ▼
                          ┌──────────────────────────────────────┐
                          │ 2. mirror (flip) · CLAHE opcional   │
                          └───────────────┬──────────────────────┘
                                          ▼
                          ┌──────────────────────────────────────┐
                          │ 3. HandTracker.process()  → MediaPipe │
                          │    21 landmarks (x,y,z) por mão      │
                          └───────────────┬──────────────────────┘
                                          ▼
                          ┌──────────────────────────────────────┐
                          │ 4. HandPool → 1 GestureEngine / mão   │
                          │    (dedup + opposition de labels)     │
                          └───────────────┬──────────────────────┘
                                          ▼
                          ┌──────────────────────────────────────┐
                          │ 5. GEOMETRIA  (GestureEngine.update)  │
                          │    pinça · Schmitt · dedos           │
                          ├──────────────────────────────────────┤
                          │ 6. MLP confirmador  (gate estrito)    │
                          └───────────────┬──────────────────────┘
                                          ▼
                          ┌──────────────────────────────────────┐
                          │ 7. Escolha: cursor = maior X         │
                          │          comandos = menor X (lado)   │
                          └───────────────┬──────────────────────┘
                                          ▼
                          ┌──────────────────────────────────────┐
                          │ 8. MOVIMENTO                         │
                          │    OneEuro → AccelCurve → deadzone   │
                          │    → cap → predição → SmoothEmitter  │
                          └───────────────┬──────────────────────┘
                                          ▼
                          ┌──────────────────────────────────────┐
                          │ 9. Gestos compostos (2 mãos, mão    │
                          │    esquerda, compostos/velocidade)   │
                          └───────────────┬──────────────────────┘
                                          ▼
                          ┌──────────────────────────────────────┐
                          │10. _transition() → evento → acção    │
                          └──────────────────────────────────────┘
```

**Princípio de desenho dominante actual: heurística afinada à mão.**
Praticamente todos os limiares de `config.py` existem para corrigir um caso
concreto observado no hardware de referência. A IA existe mas está
**subordinada** à geometria — nunca a pode contrariar.

## 1.2 Fase 1 — Captura

`core/camera.py` — classe `CameraStream`.

| Aspecto | Implementação |
|---|---|
| Backend | `cv2.CAP_DSHOW` com fallback para o default (`core/camera.py:40`) |
| Resolução | 640×480 (configurável, `config.py:21-22`) |
| FourCC | MJPG — evita descompactação JPEG por frame em CPU |
| Buffer | `CAP_PROP_BUFFERSIZE = 1` (best-effort) |
| Frequência pedida | 30 fps |

A captura corre numa **thread dedicada** (`_capture_loop`, `core/camera.py:84`)
que faz overwrite do último frame sob `Lock`. O loop principal **nunca bloqueia**
na câmara: `read()` devolve `(frame, seq)` e se o `seq` não avançou o engine
descarta a iteração (`core/engine.py:225-227`). Isto evita acumular latência de
captura em máquinas lentas — um frame atrasado é melhor do que processar a
backlog.

`try_boost_exposure` (`core/camera.py:101`) é chamado uma única vez quando o
realce de luz baixa é activado.

## 1.3 Fase 2 — Pré-processamento

`core/engine.py:229-248`, pela ordem:

1. **Espelho** — `cv2.flip(frame, 1)` se `cfg.mirror` (default `True`,
   `config.py:23`). Não é cosmético: como o tracking corre sobre o frame já
   espelhado, a posição X no ecrã passa a definir de forma fiável qual é a mão
   esquerda e qual é a direita (ver [1.8](#18-fase-7--escolha-de-mão)).
2. **Realce de luz baixa** (opt-in, `cfg.low_light_boost`, `config.py:68`) —
   `LightBoost` (`core/light.py:3`) mede a média de cinza de cada 15 frames e
   usa histerese: liga abaixo de 40, desliga acima de 60, exigindo 8 medições
   consecutivas em cada sentido. Quando activo, aplica CLAHE
   (`clipLimit=2.0`, tiles 8×8) **apenas ao canal L** em espaço LAB,
   preservando a cor.
3. **Conversão para RGB** — `cv2.cvtColor(..., COLOR_BGR2RGB)` porque o
   MediaPipe Tasks com `ImageFormat.SRGB` espera RGB.

## 1.4 Fase 3 — Inferência (MediaPipe)

`core/tracker.py` — classe `HandTracker`.

| Parâmetro | Valor | Referência |
|---|---|---|
| Modelo | `hand_landmarker.task` (float16) | `config.py:149` |
| Modo | `RunningMode.VIDEO` | `core/tracker.py:76` |
| Mãos | `num_hands`, clampado a `[1, 2]` | `core/tracker.py:57` |
| `min_hand_detection_confidence` | 0.5 | `core/tracker.py:78` |
| `min_hand_presence_confidence` | 0.5 | `core/tracker.py:79` |
| `min_tracking_confidence` | 0.5 | `core/tracker.py:80` |
| Delegate | GPU se `--gpu`, senão CPU | `core/tracker.py:58-70` |

**Aquisição do modelo** — `ensure_model` (`core/tracker.py:23`): resolve o asset
empacotado; se não houver, descarrega para o directório do utilizador (o path
pode não ser gravável, ex. `Program Files`). Download para `.part` e
`os.replace` atómico, limpando o parcial em caso de falha.

**Fallback de GPU** — se `create_from_options` com `Delegate.GPU` levantar
excepção, imprime aviso e reconstrói em CPU.

**Saída** (`core/tracker.py:84-100`): lista de 21 landmarks `(x, y, z)`
normalizados, mais o label de handedness.

⚠️ **O score de confiança é descartado** — só o `category_name` é lido. É uma
das lacunas da [Parte 2](#23-as-6-lacunas-estruturais).

## 1.5 Fase 4 — Despacho por mão (HandPool)

`core/twohand.py:196` — classe `HandPool`. Mantém **uma `GestureEngine` por mão**
com reset individual, para que perder uma mão não destrua o estado da outra.

`update()` (`core/twohand.py:211`) faz duas correções:

1. **Deduplicação** — o MediaPipe por vezes devolve a mesma mão real detectada
   duas vezes. Com palmas a menos de `0.18` (fracção da largura) uma é
   descartada, evitando um falso "2 mãos" no Free e gestos de duas mãos indevidos.
2. **Opposição de labels** — com duas mãos reais distintas, se ambas vierem
   marcadas `Right`, o segundo `Right` é renomeado `Left`. Comentário explícito:
   *"o MediaPipe desta câmara marca ambas 'Right'"*.

Quando um label não aparece num frame, a `GestureEngine` correspondente é
`reset()` — o que descarta o buffer temporal, a histerese do Schmitt e os
acumuladores de scroll/volume.

## 1.6 Fase 5 — Classificação geométrica

`core/gestures.py:80` — `GestureEngine.update(landmarks, width, height)`. É o
cérebro do reconhecimento. Devolve `(HandFrame, event, value)`.

### 1.6.1 Escala e normalização

```
scale  = dist(pulso, landmark_9)                 # proxy do tamanho da mão
too_far = scale < cfg.min_hand_scale_px (55 px)  →  Gesture.NONE
```

Mãos pequenas (longe da câmara) são rejeitadas antes de qualquer classificação.

### 1.6.2 Pinça — 2D e 3D combinadas

O ponto mais refined do código. Duas razões calculadas para polegar↔indicador e
polegar↔médio, cada uma em 2D e 3D:

- **2D** (`core/gestures.py:91-92`): fiável de frente para a câmara, onde os
  dedos se separam na projecção.
- **3D** (`core/gestures.py:96-105`): imune à inclinação da mão
  (*foreshortening*). A coordenada `y` é corrigida pelo aspecto
  `height/width` antes do cálculo.
- Nota deliberada em `core/gesture_ai.py:44-49`: o `z` do MediaPipe já é
  **scale-free e independente da distância**; dividi-lo pela escala 2D em px
  esmagaria o sinal 3D para ~0.003.

Combinam-se assim:

| Razão | Fórmula | Porquê |
|---|---|---|
| `pinch_ratio` (clique esq.) | **`min(2D, 3D)`** | De frente, o z-noise do MediaPipe infla o 3D acima do limiar; de lado, o 2D colapsa. O mínimo é robusto aos dois casos. |
| `pinch_mid_ratio` (clique dir.) | **só 3D** | A projecção 2D colapsa quando o polegar se curva sobre a palma durante o agarrar, e produziria cliques-direitos fantasma. |

### 1.6.3 Dedos dobrados — Schmitt trigger

`core/gestures.py:122-134`. Em vez de comparar `ratio < 1.0`, usa **histerese**
com o estado do frame anterior como memória:

| Estado anterior | Condição para continuar dobrado | Margem |
|---|---|---|
| dobrado (`True`) | `ratio < 1.06` | tem de esticar **bastante** para abrir |
| esticado (`False`) | `ratio < 0.94` | tem de dobrar **bastante** para fechar |

Onde `ratio = dist(tip, pulso) / dist(pip, pulso)`.

Razão documentada: sem isto, um dedo a pairar no limiar faz o gesto tremer
frame a frame — `ONE↔OPEN`, `PEACE↔THREE`, `FIST↔THUMB_UP`.

### 1.6.4 Predicados de gesto

`core/gestures.py:151-228`. Cada predicado combina `curled[]` (com histerese) e
`_clearly_curled(idx)` (teste estrito `dist(tip,pulso) <= 0.92 * dist(pip,pulso)`,
sem histerese, usado para exigir dedos **certamente** dobrados):

| Gesto | Predicado |
|---|---|
| `peace` | indicador e médio esticados; anelar e mindinho claramente dobrados |
| `three` | indicador, médio e anelar esticados; mindinho claramente dobrado |
| `rock` | indicador e mindinho esticados; médio e anelar claramente dobrados |
| `one_finger` | indicador esticado, resto dobrado, **e sem pinça de índice activa** |
| `pinky_only` | mindinho esticado, restantes dobrados |
| `thumb_pinky` | polegar para o lado (`dist(ponta, landmark 5) / scale > 1.05`) + mindinho esticado + resto dobrado. **Corrigido na Onda 1 §1.3** — antes media a ponta contra o `landmark 3` com `dx > 0.3·scale`, limiar geometricamente impossível |
| `thumb_up` | punho + ponta do polegar acima de todos os MCPs (0.15·scale) **e** `dy > 0.55·segmento` |
| `thumb_down` | espelho exacto do `thumb_up` |

O polegar é o caso mais difícil porque não segue a mesma anatomia dos outros
dedos — daí a verificação explícita de **direcção** (`dy_up > 0.55 · seg`) e não
só de separação.

Para o `thumb_pinky` a medida é a **distância da ponta do polegar à base do
indicador (`landmark 5`), normalizada pela escala** — não um deslocamento contra
o IP do próprio polegar. A razão está em §1.16 (limitação 11): medir o
deslocamento contra o `landmark 3` e exigir `dx > 0.3 · scale` é fisicamente
impossível, porque a falange distal do polegar mede ~0.28 da escala. A medida
nova separa o que se quer dizer: **polegar para o lado ≈ 1.23**, **polegar
recolhido sobre a palma ≈ 0.85**. O limiar 1.05 fica no meio, longe dos dois.

### 1.6.5 Cadeia de prioridade

`core/gestures.py:230-256`. Ordem de avaliação — a primeira que casa ganha:

```
too_far           → NONE
all_curled        → THUMB_UP | THUMB_DOWN | FIST
pinch_mid_on      → PINCH_MID
pinch_index_on    → PINCH
three             → THREE
peace             → PEACE
rock              → ROCK
thumb_pinky       → SHAKA
pinky_only        → PINKY
one_finger        → ONE
default           → OPEN
```

A pinça **precede** `three`/`peace` deliberadamente: uma pinça posiciona
indicador e polegar juntos, o que pode imitar um gesto de dedos e produziria
cliques errados. `one_finger` exige `not self._pinch_index_on` pelo mesmo motivo.

### 1.6.6 `fully_open`

`core/gestures.py:261-265`. Verdadeiro quando o gesto resolvido é `OPEN` e
**nenhuma** das pinças está activa. Usado pelo detector da mão esquerda para
abrir o alternador de janelas quase de imediato (`left_hand_open_fast_s = 0.6s`
em vez de `left_hand_open_switch_s = 1.2s`), com deriva máxima muito mais
apertada (15 px vs 45 px) — ver [1.10](#110-fase-9--gestos-compostos-e-duas-mãos).

### 1.6.7 Debounce e compromisso

`core/gestures.py:295-331`. Contador de frames consecutivos do candidato; só
promove a `self._committed` quando atinge `need_frames`:

| Caso | `need_frames` |
|---|---|
| gesto normal | `cfg.gesture_stable_frames` (2) |
| `PINCH` / `PINCH_MID` | `cfg.pinch_stable_frames` (1) |
| **pinça profunda** (ratio < `pinch_on_ratio` × 0.75) | **1** |
| libertar clique/arrastar (de `PINCH`/`PINCH_MID`/`FIST` → `OPEN`) | **1** |

Racional: a histerese do Schmitt já absorve o ruído, por isso a confirmação
adicional custaria latência sem ganhar robustez. A pinça profunda e a
libertação são as duas acções mais latency-críticas.

### 1.6.8 Scroll e volume por acumulador

`core/gestures.py:335-360`. Movimentos contínuos, não gestures discretos:

- **Scroll** (com `FIST`): ponto médio das pontas de indicador e médio, delta
  acumulado até `cfg.scroll_deadzone_px` (2 px) → evento `scroll`.
- **Volume** (com `THREE`): média das pontas de indicador, médio e anelar, até
  `cfg.volume_deadzone_px` (6 px) → evento `volume`.

Quando o gesto sai do estado, o acumulador e a referência são zerados — sem
rampa de entrada/saída, é um deadzone puro.

## 1.7 Fase 6 — IA confirmadora (MLP)

`core/gesture_ai.py` — classe `GestureAI`.

| Aspecto | Detalhe |
|---|---|
| Formato | `.npz` com `w1/b1`, `w2/b2`, `w3/b3` (`core/gesture_ai.py:78-81`) |
| Topologia | 120 → oculto → oculto → 9 (`tanh`, `tanh`, softmax) |
| Classes | `OPEN, PINCH, PINCH_MID, FIST, PEACE, THREE, THUMB_UP, ROCK, SHAKA` (`core/gesture_ai.py:10-20`) |
| Features | 120 = 60 da frame actual + 60 da média da janela (`core/gesture_ai.py:61-71`) |
| Janela | `cfg.ai_window` = 5 frames, deque (`core/gestures.py:55`) |
| Confiança mínima | `cfg.ai_confidence_min` = 0.72 (`config.py:156`) |

**Normalização** (`_normalize`, `core/gesture_ai.py:29`) — invariantes:

1. **Translação**: tudo relativo ao pulso (landmark 0).
2. **Rotação**: o vector pulso→landmark_9 define o eixo θ; os pontos são rodados
   por `−arctan2` para que a mão fique canónica independentemente da sua
   orientação na câmara.
3. **Escala**: `x, y` divididos pela escala 2D; `z` **não** dividido (é já
   scale-free).
4. Frames 2D legados são promovidos a 3D com `z = 0`.

**O gate é o ponto crítico** (`core/gestures.py:267-293`). A IA pode apenas
**confirmar** o que a geometria já viu:

- A lista `ml_ok` mapeia cada classe da IA a um predicado geométrico
  correspondente. Se a IA disser `PEACE` mas a geometria não viu `peace`, é
  ignorado.
- `ml_g == OPEN` **jamais** cancela um clique já activo (`geo_click` guard).
- Se a IA confirmar `PINCH`/`PINCH_MID` com ratio abaixo de `pinch_off_ratio`,
  o Schmitt é forçado a `on` (`core/gestures.py:290-293`) — assim um clique
  demasiado rápido para o debounce ainda é apanhado.

**Dados de treino** — `tools/train_gesture_ai.py` gera por **síntese**: uma
cadeia cinemática de dedos (`_chain`, `_thumb`) com `synthesize()`, `augment()`
e `jitter_real()`. Existe `load_real()` (mínimo 30 amostras por classe) e uma
via `real_path` com `real_copies=4`, mas a base é maioritariamente sintética.
É uma das lacunas centrais da
[Parte 2](#23-as-6-lacunas-estruturais): a Meta treina explicitamente sobre
diversidade de tom de pele, iluminação, forma de mão, distância e orientação.

**Distribuição do modelo** — `ensure_ai_model` (`core/gesture_ai.py:107`) tem
três níveis de fallback: asset empacotado → cópia local → download de release
GitHub. A validação de forma em `__init__` (`core/gesture_ai.py:82-91`) detecta
modelos obsoletos pelo número de classes ou de features e dá instrução de
retreinar.

## 1.8 Fase 7 — Escolha de mão

`core/engine.py:45-108`. **Este é o ponto mais contra-intuitivo do sistema.**

O label `Left`/`Right` do MediaPipe é **descartado para efeitos de escolha**.
Os comentários de `core/engine.py:46-58` explicam porquê: *"o label MediaPipe
(instável nesta câmara — chega a marcar as duas como 'Right' e a oscilar)"*.

Em vez disso usa-se a **posição X no ecrã**, que é determinística porque
depende apenas do espelho:

| | `mirror = True` (default) | `mirror = False` |
|---|---|---|
| Mão **de comandos** (esquerda física) | `x < width/2` | `x >= width/2` |
| Mão **do cursor** (direita física) | maior `x` | maior `x` |

- `_command_hand_frame` (`core/engine.py:45`) filtra pela metade e escolhe o
  menor X. Devolve `None` se não houver mão na metade esperada — o que impede
  que a mão do cursor seja tomada por mão de comandos.
- `_cursor_hand_frame` (`core/engine.py:87`) escolhe simplesmente o maior X.

**Troca de mão activa** (`core/engine.py:268-279`): quando o `HandFrame` do
cursor deixa de ser o mesmo objecto, o engine faz reset completo de `filters`,
`last_palm`, `prev_filtered`, `jump_streak`, `fast_until` e `emitter.clear()`.
Sem isto, o filtro One Euro arrastaria o histórico da mão anterior e produziria
um salto.

⚠️ **Nota importante**: `core/hand_lock.py` implementa um `HandLock` com
continuidade de trajectória (`radius_frac`, `lost_grace_frames`) que seria
exactamente o mecanismo certo — mas **está desligado**. Não é instanciado nem
importado pelo `engine.py`. Existe apenas teste próprio (`tools/test_hand_lock.py`)
e uma secção de config (`config.py:146-147`).

## 1.9 Fase 8 — Movimento do cursor

`core/engine.py:402-490`. Cinco estágios.

### 1.9.1 Rejeição de saltos

Antes de filtrar, o engine protege-se contra teleportes do tracker:

```
d = dist(palma, last_palm);  limit = cfg.max_jump_frac × width (0.35)
d <= limit  → reset streak, aceitar
saltou mas dentro de fast_until (0.5s após streak) → aceitar
jump_streak < 2  → rejeitar, streak++, glitches++
senão           → aceitar, streak=0, fast_until = now + 0.5s
```

Aceita 2 saltos seguidos antes de ficar cego, para não bloquear movimento
legítimo rápido. `E.glitches` é acumulado e reportado no selftest.

### 1.9.2 One Euro Filter

`core/filters.py:14` — `OneEuroFilter`, aplicado a X e Y em parelha
(`FilterPair2D`). Filtro de cutoff adaptativo:

```
cutoff = min_cutoff + beta × |velocidade filtrada|
```

Lento quando a mão está parada (mata tremor), rápido quando se mexe (mata lag).
Presets em `SMOOTH_PRESETS`: SUAVE (0.9/0.02), NORMAL (1.4/0.028), REACTIVO
(2.2/0.05).

⚠️ **Filtrado apenas a palma.** As landmarks dos dedos são usadas cruas por todo
o `GestureEngine` — o jitter dos dedos não passa por nenhum filtro.

### 1.9.3 Ganho, deadzone e portas

```
gain = cfg.move_gain (2.0) × AccelCurve(vx, vy)
mdx  = (fx - prev_fx) × gain × s
```

`AccelCurve` (`core/filters.py:83`) — `t = |v| / ref_speed` (1400),
`gain = min + (max - min) × t^1.7`. Expoente > 0 = curva de potência: mais
precisa devagar, mais agressiva a varrer. Alternativa smoothstep se
`expo <= 0`.

**Escala uniforme** (`core/engine.py:439-441`): `s = min(screen_w/w, screen_h/h)`.
Escala por eixo daria distorção num ecrã 16:9 a partir de uma câmara 4:3 — o
comentário identifica isso como causa de *"movimento bugado"* neste PC.

Três portas de supressão, por ordem:

| Porta | Condição | Efeito |
|---|---|---|
| Deadzone | `abs(md) < cfg.deadzone_px` (1.0) | anula o eixo |
| Repouso por velocidade | `filters.velocity < cfg.still_velocity_px` (25 px/s) | anula ambos |
| Cap de velocidade | `|v| > ref_speed × 4 × move_gain` | escala `mdx/mdy` |

O cap é aplicado ao **deslocamento**, não a `vx/vy`. Comentário em
`core/engine.py:466-470` explica a correcção: antes, um salto do tracker abaixo
do limiar de salto era amplificado por `gain × s` e tornava-se um teleporte.

### 1.9.4 Predição e emissor

```
lead = (vx, vy) × predict_ms/1000          # predict_ms = 0.0 (desligado)
E.emitter.push(mdx + lead + snap_pull, mdy + …, dt)
```

`SmoothEmitter` (`core/motion.py:9`) é a peça que resolve o problema central de
uma câmara a 15 fps num rato que espera 125 Hz. Thread dedicada a **~180 Hz**
(`emitter_rate_hz`) com acumulador fracionário:

```
frac = min(period / span, 1.0)
emitir = bx × frac ;  bx -= emitido        # conservação: nem perde nem duplica
```

Dois detalhes críticos de robustez:

1. **Ressincronização sem rajada** (`core/motion.py:79-85`): se a iteração
   demorar mais que um período, `next_tick = now` em vez de disparar N
   emissões de catch-up. O comentário identifica isto como causa de
   micro-tropeções e movimento "aos solavancos".
2. **Flush final** (`core/motion.py:90-97`): após 2.5×`span` sem push, emite
   exactamente o resto. O bug anterior somava `bx×frac + bx`, duplicando a
   fracção e violando a conservação.

`max_pending_px = 600` limita o backlog. `clear()` é chamado em todas as
transições de clique e troca de mão.

### 1.9.5 Auto-afinação

`core/autotune.py` — `AutoTuner`, alimentado a cada frame aceite
(`core/engine.py:491`). Mantém EMAs de velocidade e de jitter, e a cada
`autotune_interval_s` (1.5 s):

| Detecção | Ajuste |
|---|---|
| `v_ema < 60` **e** `jitter_ema > 90` → tremor | `min_cutoff × 0.9`, `beta × 0.94` |
| `v_ema > 650` **e** `jitter_ema < 0.22 × v_ema` → resposta lenta | `min_cutoff + 0.04` (ou `× 1.05`) |
| > 3 inversões/s durante 2 janelas e `v_ema > 120` → *twitch* | `move_gain × 0.96` |
| < 0.7 inversões/s e `v_ema > 420` → alcance | `move_gain × 1.03` |

O ganho é limitado a ±`gain_trim_frac` (20%) em torno do ganho definido pelo
utilizador, para nunca alterar a sensibilidade que o utilizador escolheu.

## 1.10 Fase 9 — Gestos compostos e duas mãos

`core/twohand.py` — todos baseados em posição/velocidade, não em classificação.

| Classe | Linha | Lógica | Gesto |
|---|---|---|---|
| `ClapDetector` | `:16` | 2 mãos, exige separação prévia, aproximação com `v > 2.0·scale` e `d < 1.35·scale`, 2 frames, cooldown 1.2s | Abrir/fechar assistente 3D |
| `MagnifierCtl` | `:90` | 2 mãos ambas `OPEN` durante 5 frames entra; afastar/aproximar em passos de `0.85·scale`; sai se uma mão cair durante 0.35s | Lupa do Windows (Cmd +/-) |
| `FistCycleDetector` | `:287` | Conta transições `FIST→OPEN` numa janela de 2.5s | Win+D |
| `FistHoldDetector` | `:327` | `hold_s = 0.8` contínuo + `cooldown_s = 2.5`; exige soltar o punho para re-armar | Alt+F4 (destrutivo) |
| `WaveDetector` | `:365` | ≥ 3 inversões de X com amplitude ≥ 15 px em 1.5s | Win+Down (minimizar) |
| `LeftHandDetector` | `:522` | ver abaixo | comandos da mão esquerda |

`MultiClapDetector` (`:408`) e `DualWaveDetector` (`:475`) existem e têm
testes, mas **não são instanciadas pelo engine** — o Alt+Tab faz-se hoje pelo
`LeftHandDetector`.

### `LeftHandDetector` em detalhe (`core/twohand.py:522`)

Mão de comandos totalmente separada da mão do cursor:

| Mecanismo | Regras |
|---|---|
| **PEACE → GUI** | rising edge após 3 frames (`left_hand_gesture_stable_frames`), cooldown 0.8s. **Funciona também no Free** — é a única excepção a `allow_commands`. |
| **Open hold → alternador** | `OPEN` mantida: `0.6s` se `fully_open` com deriva ≤ 15 px, senão `1.2s` com deriva ≤ 45 px. Anti-drift: se a palma se mover mais, o hold é anulado. |
| **SWIPE → Alt+Tab** | `|dx| ≥ 55 px` **e** `|dx| > 2.0·|dy|` **e** velocidade ≥ 220 px/s, dentro de janela 0.5s, cooldown 0.8s. |
| **Scroll vertical** | deadzone 24 px, acumulador com detecção de dominância vertical. |
| **Pick mode** | Com o alternador aberto, mantém Alt premido (`ALT_HOLD_TIMEOUT_S = 1.3`); swipes navegam sem soltar; soltar a mão confirma e liberta. |
| **Grace de perda** | `left_hand_lost_grace_s = 0.3` — uma perda de 1-2 frames não reinicia hold/PEACE/swipe. |

**Gate Pro/Free** — `allow_commands` desliga swipe/alternador/scroll no Free;
`E.left_hand` é instanciado **sempre** (`core/engine.py:145`) para o PEACE
continuar a funcionar.

## 1.11 Fase 10 — Gesto → Evento

`core/gestures.py:380` — `_transition(previous, current)` traduz a mudança de
gesto commitido num evento. Só as **bordas** geram eventos.

| Evento | Condição | Efeito no engine |
|---|---|---|
| `left_down` | entrou em `PINCH` | `_click_assist` + `press_left` + freeze 100 ms + flash + `emitter.clear()` |
| `left_up` | saiu de `PINCH` | `release_left` + `emitter.clear()` |
| `right_click` | entrou em `PINCH_MID` | idem, clique direito |
| `copy` | entrou em `PINKY` | Ctrl+C |
| `paste` | entrou em `SHAKA` | Ctrl+V |
| `play_pause` | entrou em `THUMB_UP` | `_handle_media_event` |
| `scroll` / `volume` | acumulado contínuo | `mouse.scroll(v × scroll_gain_factor)` |

`LEFT_BUTTON_GESTURES = (PINCH,)` — o único gesto que conta como botão esquerdo
presionado. `PINCH` está também em `MOVE_GESTURES` (`core/engine.py:42`):
mover **e** clicar simultaneamente, que é o que permite arrastar.

**Safety nets** no consumidor (`core/engine.py:503-507`): se a mão desaparecer
com o botão premido, `click_release_grace_s = 0.12` força a libertação — evita
botão preso por perda de tracking.

`left_up` é o **único** evento processado mesmo com a app em pausa
(`core/engine.py:511`), para que o botão nunca fique premido.

## 1.12 Referência de gestos

`Gesture` enum — `core/gestures.py:12`:

| Valor | Rótulo UI | Gesto | Acção |
|---|---|---|---|
| `NONE` | sem mão | — | não move |
| `OPEN` | mover | mão aberta | **mover cursor** |
| `ONE` | mover (1 dedo) | só indicador | **mover cursor** |
| `PINCH` | clique esquerdo | polegar + indicador | **clique / arrastar** |
| `PINCH_MID` | clique direito | polegar + médio | clique direito |
| `FIST` | arrastar | punho | scroll vertical (por delta) |
| `PEACE` | scroll | indicador + médio | scroll (mão esq.) / brilho (mão dir. 2 mãos) |
| `THREE` | volume | 3 dedos | volume |
| `THUMB_UP` | play/pausa | punho + polegar cima | play/pausa |
| `THUMB_DOWN` | deslike | punho + polegar baixo | gate de UI |
| `PINKY` | copiar | só mindinho | Ctrl+C |
| `SHAKA` | colar | polegar + mindinho | Ctrl+V |
| `ROCK` | interface | indicador + mindinho | (via mão esquerda) |

Mãos que movem o cursor: `MOVE_GESTURES = {OPEN, ONE, PINCH}`
(`core/engine.py:42`).

⚠️ **Inconsistência de nomenclatura a resolver**: o enum diz
`FIST = "arrastar"` e `PEACE = "scroll"`, mas na prática `FIST` produz
**scroll** e `PEACE` está desviado para brilho/interfaces. Os rótulos são
legados de uma versão anterior da taxonomia e confundem quem lê o overlay.

## 1.13 Referência de configuração

Todos em `config.py`, persistidos em `settings.json` (ver `config.py:280+`).

### Reconhecimento

| Chave | Default | Efeito |
|---|---|---|
| `num_hands` | 2 | mãos detectadas |
| `min_hand_scale_px` | 55.0 | rejeição de mãos pequenas |
| `pinch_on_ratio` | 0.42 | Schmitt on |
| `pinch_off_ratio` | 0.58 | Schmitt off |
| `pinch_stable_frames` | 1 | debounce da pinça |
| `gesture_stable_frames` | 2 | debounce dos restantes |
| `click_release_grace_s` | 0.12 | anti-botão-preso |
| `ai_enabled` / `ai_confidence_min` / `ai_window` | True / 0.72 / 5 | MLP |
| `max_jump_frac` | 0.35 | rejeição de teleports |
| `warmup_frames` | 10 | frames ignorados no arranque |
| `low_light_boost` | False | CLAHE |
| `hand_lock_radius_frac` / `hand_lost_grace_frames` | 0.30 / 10 | **desligado** |

### Movimento

| Chave | Default | Efeito |
|---|---|---|
| `move_gain` | 2.0 | ganho base |
| `deadzone_px` | 1.0 | deadzone por eixo |
| `still_velocity_px` | 25.0 | porta de repouso |
| `filter_min_cutoff` / `filter_beta` | 1.4 / 0.028 | One Euro |
| `accel_min_gain` / `max_gain` / `ref_speed` / `expo` | 1.2 / 3.0 / 1400 / 1.7 | curva |
| `predict_ms` | 0.0 | predição (desligada) |
| `emitter_rate_hz` | 180 | frequência de emissão |
| `scroll_gain_factor` / `scroll_deadzone_px` | 0.06 / 2.0 | scroll |

### Comandos da mão esquerda

| Chave | Default |
|---|---|
| `left_hand_commands` | True (gate Pro) |
| `left_hand_swipe_min_px` / `_dom` / `_min_speed_px_s` / `_window_s` | 55 / 2.0 / 220 / 0.5 |
| `left_hand_cooldown_s` | 0.8 |
| `left_hand_gesture_stable_frames` / `left_hand_lost_grace_s` | 3 / 0.3 |
| `left_hand_open_switch_s` / `_open_switch_max_move_px` | 1.2 / 45 |
| `left_hand_open_fast_s` / `_open_fast_max_move_px` | 0.6 / 15 |
| `left_hand_fist_close_hold_s` / `_cooldown_s` | 0.8 / 2.5 |
| `left_hand_scroll_deadzone_px` | 24 |

### Compostos

`clap_enabled` True · `magnifier_enabled` True · `fist_cycle_count` 2 ·
`fist_cycle_window_s` 2.5 · `wave_min_reversals` 3 · `wave_window_s` 1.5 ·
`wave_min_amplitude_px` 15 · `brightness_step` 10

### Auto-afinação

`autotune_enabled` True · `autotune_interval_s` 1.5 ·
`filter_min_cutoff_min/max` 0.7/2.4 · `filter_beta_min/max` 0.012/0.055 ·
`gain_trim_frac` 0.2

## 1.14 Mapa de ficheiros

| Ficheiro | Papel no reconhecimento |
|---|---|
| `core/camera.py` | Captura assíncrona, exposição |
| `core/tracker.py` | MediaPipe HandLandmarker, GPU/CPU, download do modelo |
| `core/twohand.py` | `HandPool`, detectores compostos, `LeftHandDetector` |
| `core/gestures.py` | `Gesture` enum, `HandFrame`, `GestureEngine` — **cérebro** |
| `core/gesture_ai.py` | MLP, normalização invariante, distribuição do modelo |
| `core/engine.py` | Orquestração, escolha de mão, movimento, eventos |
| `core/filters.py` | One Euro + curva de aceleração |
| `core/motion.py` | `SmoothEmitter` 180 Hz, predição |
| `core/autotune.py` | Auto-afinação de filtro e ganho |
| `core/light.py` | Detecção de luz baixa com histerese |
| `core/hand_lock.py` | `HandLock` — **código morto, não ligado** |
| `core/mouse_ctl.py` | Escrita no rato |
| `core/hotkeys.py` | Atalhos (Alt+F4, Win+D, Cmd+±) |
| `core/commands.py` | Comandos unificados · `_click_assist` |
| `ui/overlay.py` · `ui/gesture_badge.py` | Esqueleto e gesto no ecrã |
| `core/corpus.py` | Formato do corpus `.npz`, `CorpusRecorder`, rótulos (`SETTLE`) |
| `tools/train_gesture_ai.py` | Treino do MLP (síntese + real) |
| `tools/collect_gestures.py` | Colecção de dados reais |
| `tools/eval_recognition.py` | **Harness de métricas** — F1 por gesto, cliques fantasma, latência |
| `tools/make_corpus_fixture.py` | Gera o corpus de regressão determinístico (`tests/fixtures/`) |
| `tools/debug_hands_sides.py` | Diagnóstico de labels/handedness |
| `tools/test_click_latency.py` | Medição de latência de clique |

## 1.15 Cobertura de testes

Suíte `pytest` completa, verde em CI (`.github/workflows/ci.yml`).
Relevantes para o reconhecimento:

| Ficheiro | Cobre |
|---|---|
| `test_filters.py` | One Euro, `AccelCurve` |
| `test_gesture_ai.py` | MLP, normalização, validação de modelo obsoleto |
| `test_gesture_ai_integration.py` | gate IA ↔ geometria |
| `test_move_gesture.py` | `MOVE_GESTURES`, transição de cursor |
| `test_fist_hold.py` | `FistHoldDetector` |
| `test_open_switch_move.py` | anti-drift do hold aberto |
| `test_motion_helpers.py` | `lead_offset`, emissor |
| `test_pause_toggle.py` | pausa não bloqueia `left_up` |
| `test_corpus.py` | formato `.npz`, rótulos, `SETTLE`, `replay()` |
| `test_corpus_recorder.py` | `CorpusRecorder` ligado ao engine |
| `test_engine_recording.py` | gravação durante o loop real |
| `test_eval_recognition.py` | métricas, exclusão de `SETTLE`, aceitação |
| `test_corpus_fixture.py` | **portão de regressão**: fixture ↔ baseline comitado |

Diagnóstico em `tools/`: `test_hand_lock.py`, `test_left_hand.py`,
`test_new_gestures.py`, `test_click_latency.py`, `test_v3.py`,
`test_retrain_smoke.py`.

### Benchmark de precisão — fechado na Onda 0

A lacuna estrutural que esta secção registava ("testes *unitários de
detectores*, não *benchmarks de precisão*") está fechada:

* **Gravar** — `main.py --record <ficheiro.npz>` (com `--record-max-frames`,
  `--frame-width/height`) guarda landmarks **e** o rótulo que o utilizador
  Estava a fazer em cada frame. Corre em todo o pipeline, sem câmaras
  adicionais.
* **Reproduzir** — `main.py --replay <ficheiro.npz>` corre o classificador
  real sobre as landmarks gravadas e imprime o relatório. Sem câmara, sem rato,
  sem interface, sem licença — corre em qualquer máquina de CI.
* **Medir** — `tools/eval_recognition.py`: precisão/recall/F1 macro por
  gesto, matriz de confusão, **cliques fantasma por hora** e latência de
  reação em ms.
* **Travar** — `tests/test_corpus_fixture.py` compara
  `tests/fixtures/corpus_regressao_v1.npz` com
  `corpus_regressao_v1.baseline.json`. É o pytest que reprova se um gesto,
  uma métrica ou um limiar se mexer. O passo de CI separado imprime o
  relatório, mas **não reprova**: `--gate` é opt-in, porque o alvo F1 ≥ 0.97
  ainda não é atingido e um job permanentemente vermelho deixa de ser lido.

⚠️ **O corpus de regressão é sintético.** É gerado por
`tools/make_corpus_fixture.py` a partir da cinemática de
`tools/train_gesture_ai.py` (as constantes anatómicas), mas com as poses
definidas localmente — se o gerador de treino mudar, o baseline não se move
sozinho. Trava contra *regressão*, não prova *qualidade*. Gravações com mãos
reais não são versionadas (tamanho e privacidade); para medir qualidade real
é preciso um corpus real, que é objectivo da **Onda 3 §3.1**.

Números actuais (baseline comitado, `python main.py --replay
tests/fixtures/corpus_regressao_v1.npz`):

| Métrica | Valor |
|---|---|
| Frames / frames com mão | 193 / 168 |
| Duração | 6.3 s |
| Exactidão | 1.0000 |
| **F1 macro** | **1.0000** |
| Cliques / cliques fantasma | 3 / **0** |
| Confusão | **nenhuma** |

Os 12 gestos com P = R = F1 = 1.0. Antes da correcção do SHAKA (Onda 1 §1.3) o
baseline era 0.8958 com a confusão única `SHAKA → PINKY` (8/8) e `PINKY` com
P = 0.600 — ver limitação 11.

> **Isto não é um número de marketing.** A fixture é sintética e paramétrica:
> com F1 = 1.0 ela deixa de provar qualidade e passa a provar **regressão** — que
> é para isso que existe. A qualidade em mãos reais continua por medir (Onda 3
> §3.1).

## 1.16 Limitações conhecidas

Documentadas em `HARDWARE/PROBLEMAS_KNOWN.md` e confirmadas no código:

| # | Limitação | Evidência |
|---|---|---|
| 1 | **CPU sem GPU → 12–15 fps**, inferência 48–79 ms | `PROBLEMAS_KNOWN.md` §1.1 — 14.6 fps / 48.3 ms, re-teste 11.9 fps / 78.5 ms |
| 2 | **`--gpu` inoperante** em iGPU antigas (`NotImplementedError`), sem ganho | §1.3 — 13.4 fps com `--gpu` |
| 3 | **Label de handedness instável** — obriga à seleção por X | `engine.py:46-58`, `twohand.py:223` |
| 4 | **`commands_ok` sem teste de integração** no engine | spec 2026-09-06 |
| 5 | `HandLock` — continuidade de mão implementada mas não ligada | `hand_lock.py:19` |
| 6 | `MultiClapDetector` / `DualWaveDetector` implementados mas não instanciados | `twohand.py:408`, `:475` |
| 7 | Rótulos do enum `Gesture` desactualizados face ao comportamento real | `gestures.py:18-19` |
| 8 | Confiança de detecção do MediaPipe **descartada** | `tracker.py:89-99` |
| 9 | Jitter das landmarks dos dedos **não filtrado** | `engine.py:427` filtra só a palma |
| 10 | ~~CLI não tem modo de gravação/replay~~ — **fechado na Onda 0** | `main.py --record` / `--replay`, `core/corpus.py` |
| 11 | ~~**`SHAKA` (Ctrl+V) é praticamente inalcançável**~~ — **fechado na Onda 1 §1.3** (2026-09-28). O `thumb_out` media a ponta do polegar contra o seu próprio IP (`landmark 3`) e exigia `dx > 0.30 × escala`: geometricamente impossível, porque a falange distal mede ~0.28. Mede anatomia, não intenção. Passou a medir a distância da ponta do polegar à **base do indicador (`landmark 5`)**, normalizada pela escala (~1.23 para o lado, ~0.85 recolhido, corte em 1.05). **Na fixture: `SHAKA` F1 0.0 → 1.0, `PINKY` P 0.600 → 1.0, zero confusões, F1 macro 1.0000.** Por confirmar em mãos reais. | `core/gestures.py` (`thumb_out`), `tests/test_corpus_fixture.py::TestShakaIsRecognised`, `tests/test_shaka_thumb_out.py`, `PROBLEMAS_KNOWN.md` §1.4 |

---

# Parte 2 — Lacunas face à Meta Quest

## 2.1 Como a Meta faz

Síntese de [MEgATrack (Meta AI Research, 2020)](https://ai.meta.com/research/publications/megatrack-monochrome-egocentric-articulated-hand-tracking-for-virtual-reality/),
[Hand tracking DNN (FRL, 2019)](https://ai.meta.com/blog/hand-tracking-deep-neural-networks/)
e da documentação do [Horizon Interaction SDK](https://developers.meta.com/horizon/documentation/unity/unity-isdk-hand-pose-detection/).

**Pipeline de multi-stage:**

1. **Detector de mãos** — rede dedicada, robusta a ambientes variados. Roda
   **infrequentemente**.
2. **Estimador de keypoints que usa o histórico de tracking** — produz poses
   *espacial e temporalmente consistentes*. É isto que elimina o jitter.
3. **Model-based tracking (IK)** — reconstrói uma **pose de 26 graus de
   liberdade** e um modelo 3D da mão com geometria de superfície.
4. **Detecção-by-tracking** — entre passagens do detector, as keypoints são
   propagadas frame a frame. Resultado: **60 Hz em PC, 30 Hz em processador
   móvel**, com custo computacional reduzido.
5. **NN quantizada** para correr no mobile sem competir com a app.

**Features contínuas, não booleanas** — o SDK expõe:

| Feature | Descrição |
|---|---|
| `curl` | quanto as duas falanges distais estão dobradas; 3 estados (aberto/neutro/fechado) por limiares em **graus** |
| `flexion` | quanto o MCP está dobrado **relativamente à palma**; fiável nos 4 dedos, pode dar falso-positivo no polegar |
| `abduction` | ângulo entre dedos adjacentes na base |
| `opposition` | estado do polegar |
| `pinch strength` | **contínuo 0..1** — 0 com a ponta longe do polegar, 1 com a ponta a tocar |
| `GetFingerIsHighConfidence()` | confiança **por dedo** |
| `IsHighConfidence` · `IsTrackedDataValid` | confiança ao nível da mão |

**Orientação no mundo** — o tracking expõe 9 transformadores booleanos
comparados contra a pose: `WristUp`, `WristDown`, `PalmDown`, `PalmUp`,
`PalmTowardsFace`, `PalmAwayFromFace`, `FingersUp`, `FingersDown`, `PinchClear`.

**Detecção de poses declarativa e composável** — uma pose é um conjunto de
*shapes* (requisitos de estado de dedos) **+** um *transform* (orientação).
Reconhecimento de **forma** (estático) é separado de reconhecimento de
**velocidade/rotação** (dinâmico), com `JointDeltaProvider` a cachear deltas
entre frames. Todos os limiares vivem em `ScriptableObject`s separados do
código, com **`MinTimeInState`** (tempo mínimo num estado antes de transicionar)
e buffering de mudanças de estado para impedir oscilação rápida.

**Wrist space** — todas as mãos têm o mesmo tamanho em espaço de pulso; o
tamanho real é um `Scale` separado. Normalização por tamanho de mão, por
construção.

**WMM (Wide Motion Mode)** — com **Inside Out Body Tracking**, mantém poses
plausíveis quando as mãos saem do campo de visão do headset.

**Calibração** — o dispositivo mede distâncias entre pontos específicos para fixar
a escala da mão.

**Dataset** — treinado explicitamente sobre diversidade de **condições de
iluminação, formas de mão, tons de pele, distâncias, poses e orientações**
(confirmado em [hands-technology](https://developers.meta.com/horizon/design/hands-technology/)).

**Erro medido**: ~9.6° de erro angular médio (SD 6.2°) contra ground-truth
óptico, com erro a **crescer com a velocidade** na articulação MCP — atribuído a
auto-oclusão.

## 2.2 Tabela comparativa

| Dimensão | Mãouse hoje | Meta Quest / MEgATrack | Gap |
|---|---|---|---|
| **Câmaras** | 1, RGB, 640×480 | 4, monocromáticas, *fisheye* | 🔴 irredutível no desktop |
| **Frames de saída** | 12–30 Hz | 60 Hz (PC) / 30 Hz (mobile) | 🔴 |
| **Keypoints** | 21 | 26 DoF + modelo 3D da mão | 🟠 |
| **Consistência temporal** | One Euro **só na palma** | modelo usa histórico de tracking | 🔴 |
| **Confiança** | **descartada** | por mão + **por dedo** | 🟡 |
| **Pinça** | Schmitt booleano (on/off) | `pinch strength` contínuo 0..1 | 🟡 |
| **Curl** | binário + histerese (razão dist) | 3 estados por **ângulos em graus** | 🟠 |
| **Flexion / Abduction / Opposition** | ❌ inexistente | features de primeira classe | 🔴 |
| **Orientação** | ❌ inexistente | 9 transformadores no mundo | 🔴 |
| **Pinza de mão** | posição X (heurística) | ID por tracking | 🟠 |
| **Detector** | MediaPipe empacotado (caixa preta) | detector dedicado infrequente + det. por tracking | 🟠 |
| **Detecção de pose** | `if/elif` com limiares em código | declarativa, shapes + transform, `MinTimeInState` | 🟠 |
| **Occlusão** | colapsa a razão 2D | reconstrução via IK do modelo | 🔴 |
| **Sai do campo de visão** | perde tudo | WMM + IOBT | 🟠 (relevância menor no desktop) |
| **Escala de mão** | `dist(pulso, lm9)` por frame | wrist space + `Scale` calibrado | 🟡 |
| **Dados de treino** | maioritariamente **sintéticos** | diverso e anotado | 🔴 |
| **Benchmark** | corpus sintético versionado + checklist manual | corpus real anotado vs mocap | 🟠 |
| **Calibração** | ❌ | medição de escala por pessoa | 🟡 |

🔴 Crítico · 🟠 alto · 🟡 médio

## 2.3 As 6 lacunas estruturais

### 1. Não existe medição de precisão 🔴 → ✅ fechada na Onda 0

**Esta é a lacuna raiz — as outras cinco só são visíveis porque esta falta.**

Um sistema de 13 gestos num único sentido não pode ser "nível Meta" sem se saber
a taxa de falso-positivo. Para um rato, um clique fantasma é um evento
destrutivo: abre a janela errada, fecha um separador, perde trabalho. O
critério correcto não é "o gesto é detectado?" mas **"qual é a taxa de
activação espúria por hora de utilização?"**

> **Fechado na Onda 0.** A métrica existe: `tools/eval_recognition.py` mede
> cliques fantasma por hora e latência de reação sobre um corpus gravado com
> `main.py --record`, e `tests/test_corpus_fixture.py` fixa os números num
> baseline que o CI reprova. Estado actual: **F1 macro 0.8958, 0 cliques
> fantasma em 3 cliques, latência medida**. Ver §1.15.
>
> O que a Onda 0 **não** fecha: o corpus versionado é sintético. A medição de
> qualidade com mãos reais é a **Onda 3 §3.1**.

Os testes existentes verificam que *um detector, dado um input sintético, devolve
o esperado*. Não verificam que o sistema *no hardware real* acerta. Não há
corpus, nem matriz de confusão, nem p99 de latência.

### 2. Features binárias em vez de contínuas 🟠

O `Gesture` é um enum de 13 valores discretos, decidido por limiares. A Meta
expõe curl/flexion/abduction/opposition/strength contínuos e deixa a *decisão*
para a aplicação.

A consequência prática: entre "PEACE" e "THREE" há um caminho em que o anelar
passa a dobrar. O sistema tem de escolher um lado de um limiar, e quem escolhe
perde informação. Pior, a decisão é tomada num frame e **descartada** — não há
memória do trajeto.

### 3. Ângulos em vez de distâncias 🟠

O Mãouse decide dobrado/esticado por `dist(tip,pulso) / dist(pip,pulso)`. Essa
razão é função **da posição e da orientação da mão**, não só da articulação: com
a mão rodada, o mesmo dedo dobrado dá razões diferentes. É por isso que a folga
de histerese tem de ser tão generosa (1.06/0.94) — está a compensar a
dependência da pose, não apenas o ruído.

A anatomia correcto é o **ângulo acumulado das falanges** — MCP, PIP, DIP em
graus, invariante a rotação e à escala por construção. É exactamente o que a
Meta usa e o que o SDK descreve como `curl` e `flexion`.

### 4. Jitter não filtrado nas landmarks 🟠

Só a palma passa pelo One Euro (`engine.py:427`). As 20 landmarks restantes são
consumidas cruas pelo `GestureEngine`. Logo, **todo o reconhecimento de dedos
opera sobre a entrada mais ruidosa do sistema**, enquanto a maior parte do
esforço de suavização está concentrada no output (a palma, para o cursor).

A Meta inverte isto: a consistência temporal é um problema do **estimador**,
resolvido com histórico dentro do modelo, não com um filtro à saída.

### 5. Confiança ignorada 🟡

`core/tracker.py:89-99` lê apenas `category_name`. O MediaPipe devolve o score de
handedness e tem limiares de presença — mas nada disto chega ao `GestureEngine`.
Consequência: um frame em que o tracker "vê uma mão" a 51% de confiança é tratado
exactamente como um a 99%, e um gesto pode disparar sobre ruído.

A Meta expõe `IsHighConfidence` **e** `GetFingerIsHighConfidence` — por dedo. O
conceito de "o anelar está a ser rastreado com fraca confiança" é inexistente no
Mãouse.

### 6. Treino em dados sintéticos 🔴

`tools/train_gesture_ai.py` constrói o dataset por `synthesize()` — uma cadeia
cinemática paramétrica. É útil para bootstrap e para cobrir o espaço de
configurações, mas um modelo geométrico perfeito não ensina ao classificador o
que falhará em câmaras reais: **pele com brilho especular, iluminação de ecrã,
ângulos de câmara baixos, mãos maiores, oclusão de dedos por sobreposição**.

A Meta treina sobre diversidade explícita de tom de pele, iluminação, forma de
mão, distância, pose e orientação. É exactamente a lista de eixos em que
`PROBLEMAS_KNOWN.md` regista variação de performance (48.3 ms vs 78.5 ms entre
manhã e noite).

---

# Parte 3 — Plano para nível profissional

## 3.0 Princípio: medir antes de optimizar

O plano **começa** pela Onda 0, não pela Onda 1. Sem métricas, cada alteração
é uma aposta, e um sistema com 13 gestos tem uma superfície de erro tão grande
que "parece melhor" não é evidência.

Critério de sucesso a fixar **antes** de escrever código: definir o que é
"nível profissional" em números. Proposta em [3.8](#38-métricas-de-aceitação).

## 3.1 Onda 0 — Instrumentação e métricas

**Objectivo: conseguir medir a qualidade do reconhecimento em CI.**

> ### Estado: entregue
>
> A Onda 0 está implementada e verde. O que ficou feito, e o que ficou por
> fazer, para não haver dúvida sobre a posição actual.
>
> | Item | Estado | Onde |
> |---|---|---|
> | 0.1 Gravar (`--record`) e reproduzir (`--replay`) | feito | `core/corpus.py`, `main.py` |
> | 0.3 Métricas: F1 por gesto, confusão, cliques fantasma/hora, latência | feito | `tools/eval_recognition.py` |
> | 0.4 CI: baseline de regressão que reprova | feito | `tests/test_corpus_fixture.py`, `.github/workflows/ci.yml` |
> | 0.2 Corpus etiquetado **real** (200–500 clips, diversidade) | **falta** | Onda 3 §3.1 |
> | 0.3 Jitter em repouso, continuidade de tracking, estratificação demográfica | **falta** | precisa de corpus real |
>
> **Medido na entrega da Onda 0** (`main.py --replay
> tests/fixtures/corpus_regressao_v1.npz`): F1 macro **0.8958**, exactidão 0.9310,
> **0 cliques fantasma** em 3 cliques, confusão única `SHAKA → PINKY` 8/8, 11/12
> gestos perfeitos. O alvo F1 ≥ 0.97 **não era atingido** — e a Onda 1 existe
> exactamente para isso.
>
> **Medido hoje, depois da Onda 1 §1.3** (mesmo comando): F1 macro **1.0000**,
> exactidão 1.0000, 12/12 gestos perfeitos, **zero confusões**, 0 cliques
> fantasma, `ACEITE: todos os alvos cumpridos`. A confusão que existia era uma
> só e está fechada.
>
> **Duas decisões que valem registo:**
>
> 1. **O CI não reprova pela métrica.** O `pytest` reprova pela comparação com
>    o baseline (regressão = mau); o passo de relatório imprime os números sem
>    falhar, porque um job vermelho permanente deixa de ser lido. `--gate` /
>    `--replay-gate` existem para quando o alvo for atingido — activá-los é uma
>    linha em `ci.yml`.
> 2. **Rótulo `SETTLE`.** Um corpus anotado tem de marcar os primeiros frames de
>    cada segmento (o gesto destino já começou, mas o debounce ainda não
>    fechou). Sem essa distinção, o F1 mede *quantos segmentos o corpus tem* em
>    vez da qualidade do classificador. `SETTLE` fica fora da matriz de F1 e
>    entra apenas na latência, onde o atraso é visível ao utilizador.
>
> **Limite explícito:** o corpus versionado é sintético e determinístico
> (`tools/make_corpus_fixture.py`). Trava contra regressão; não prova qualidade.
> Gravações com mãos reais não são versionadas — é a Onda 3 que as traz.

### 0.1 Gravar e reproduzir

- **Modo de captura** no CLI: `--record PATH` grava as landmarks que o tracker
  produziu **e** o rótulo do gesto que o utilizador estava a fazer, frame a
  frame, num `.npz` (`core/corpus.py`). Com `--record-max-frames`,
  `--frame-width/height`.
- **Modo de replay** `--replay PATH` que percorre o mesmo classificador sobre as
  landmarks gravadas, **sem câmara e sem escrever no rato** (dry-run). O replay
  corre *antes* de licença, câmara, rato e motor — é o que torna isto usável em
  CI. Permite: testes de regressão de reconhecimento, testes de performance
  (medir o custo do reconhecimento isolado do ruído da câmara) e — crucially —
  determinismo total. Um bug de gesto passa a ser reproduzível.

### 0.2 Corpus etiquetado

- 200–500 clips de 5–15 s, anotados com a sequência de gestos **e** as
  **transições** (o que interessa é a borda, não o estado estável).
- Diversidade intencional, na lista da Meta: **tons de pele variados,
  iluminação (natural/artificial/escura), distâncias, ângulos de rotação, mãos
  pequenas/grandes, e presença de messiness**. Incluir deliberadamente os
  casos em que **não há gesto nenhum** (palmas em repouso) — é onde vivem os
  falsos positivos.
- 20% de clips **out-of-distribution** para medir a degradação honesta.

### 0.3 Métricas

| Métrica | Como | Alvo | Estado |
|---|---|---|---|
| Matriz de confusão por gesto | replay vs. anotação | — | feito |
| F1 / precision / recall por gesto | idem | ≥ 0.97 | feito (0.8958 — abaixo do alvo) |
| **Falso-positivo por hora** | clips "sem gesto" × FP / duração | 0 | feito (0 em 3 cliques) |
| Latência de clique (p50/p95/p99) | replay | p95 < 80 ms | feito |
| **Jitter em repouso** (RMS da palma, mão estática) | replay | < 0.5 px | falta |
| Continuidade de tracking | % frames com mão válida estando visível | ≥ 99% | falta |
| Desempenho por demografia | estratificar por tom de pele, iluminação, ângulo | sem classe > 5 pp abaixo da média | falta |
| Custo de inferência | ms/frame por hardware | ver matriz | falta (precisa de câmara) |

### 0.4 Integração CI

- `pytest` corre o replay de um subconjunto de clips a cada PR — em CI, o
  corpus sintético de `tests/fixtures/`.
- Falha de recall num gesto bloqueia o merge; a matriz completa corre nightly.
- Passo adicional "Recognition report" imprime o relatório **sem** reprovar
  (ver a decisão acima).

**Entregável:** um comando — `python tools/eval_recognition.py` — que produz
um relatório com todas as métricas. Nada na Onda 1 começa sem ele.

## 3.2 Onda 1 — Correções de alto ROI, sem ML

Nesta onda o custo é baixo, o risco é baixo, e o efeito é imediatamente
mensurável com o que a Onda 0 construiu.

### 1.1 Filtrar as landmarks, não só a palma ⚠️ maior ganho isolado

`OneEuroFilter` por coordenada × 21 landmarks × 2 mãos. O filtro já existe e
está testado (`core/filters.py`); é instanciá-lo.

- **Cuidado**: filtrar suaviza o jitter mas **adiciona latência**. O `beta` do
  One Euro existe precisamente para isto — cortar mais quando é rápido. Começar
  com `min_cutoff` mais alto que o da palma e calibrar contra o alvo de latência
  de clique.
- **Não** filtrar a decisão de pinça já Schmitt-triggered: a histerese já faz
  esse trabalho e filtrar aqui só adiciona atraso ao clique.
- Reset do filtro quando a mão é perdida, coerente com o `HandPool`.

*Impacto esperado:* menos falsos positivos e menos "gesto a tremer" sem
qualquer modelo novo.

### 1.2 Propagar a confiança do tracker

- Ler `handedness[0].score` em `core/tracker.py:89` e, se disponível, o score de
  presença.
- Propagar para `HandFrame` (campo novo, p. ex. `detect_conf`).
- Usar em **três** sítios:
  1. **Abstenção** — abaixo de um limiar, `Gesture.NONE` em vez de arriscar
     classificar. A Meta chama a isto `IsHighConfidence`.
  2. **Peso no gate da IA** — um frame de baixa confiança **não** pode confirmar
     um gesto; só pode ser neutro.
  3. **Feedback ao utilizador** — mostrar o anel de tracking a degradar. O
     overlay já sabe desenhar o esqueleto. O utilizador reage antes de o rato
     correr sozinho.

### 1.3 Rever a cadeia de limiares com dados

Com a Onda 0 a dar a matriz de confusão, os limiares deixam de ser herança e
passam a ser **ajustados ao maior off-diagonal**.

> **✅ Feito (2026-09-28, Onda 1 §1.3, branch `fix/onda1-shaka`).** O maior
> off-diagonal do baseline era `SHAKA → PINKY`, 8 em 8, e não era um limiar mal
> afinado: era um limiar **física e geometricamente impossível**. O `thumb_out`
> media o deslocamento da ponta do polegar em relação à IP (`landmark 3`) e
> exigia `dx > 0.30 × scale`. A falange distal é ~0.28 de uma escala de 1.10 —
> em mãos reais, ~30 mm contra ~95 mm de palma. A condição horizontal **nunca
> podia ser satisfeita por nenhuma mão**; a vertical deixava uma janela de ~11°
> em torno da vertical, ou seja o polegar tinha de apontar quase exactamente para
> cima. O predicado media **anatomia**, não intenção, e o resultado variava por
> utilizador.
>
> Efeito prático antes da correcção: **SHAKA (Ctrl+V) nunca chegava ao
> utilizador** — cada tentativa saía como PINKY, ou seja Ctrl+C. Um comando
> não-reversível entregue ao sítio errado.
>
> **A correcção trocou a medida em vez de mexer no número**, exactamente como
> diagnosticado: `thumb_out` passou a medir a distância da ponta do polegar à
> **base do indicador (`landmark 5`)**, normalizada pela escala (pulso →
> `landmark 9`). Medido na fixture: ~1.23 com o polegar para o lado, ~0.85
> recolhido sobre a palma — o corte em 1.05 separa os dois gestos. É a mesma
> medida do `thumb_out` da Meta e a que o `core/gesture_ai.py` já usava.
>
> Commit próprio com corpus antes e depois, como manda a regra: F1 macro
> 0.8958 → **1.0000**, `SHAKA` F1 0.0 → 1.0, `PINKY` precisão 0.600 → 1.0,
> confusões **zero**, `ACEITE: todos os alvos cumpridos`. O portão ficou em
> `tests/test_corpus_fixture.py::TestShakaIsRecognised` (SHAKA F1 ≥ 0.9, a
> condição que §1.4 exigia antes de anunciar) e o predicado isolado está em
> `tests/test_shaka_thumb_out.py`.
>
> **O que fica por provar:** tudo isto é fixture sintética. Falta o SHAKA no
> hardware, à mesma luz que a limitação 11 sempre teve. É exactamente o que a
> Onda 3 §3.1 tem de medir.

### 1.4 Corrigir os rótulos ⚠️ barato

Renomear `Gesture.FIST` de `"arrastar"` para `"scroll"` e `PEACE` de `"scroll"`
para o que realmente faz, para o overlay deixar de mentir. Mudança puramente
textual, zero risco, remove uma fonte de confusão para o utilizador.

### 1.5 Ligar o `HandLock` ⚠️ com cautela

`core/hand_lock.py:19` existe e está testado. **Não ligar directamente**: a
seleção por X foi deliberada e está documentada como mais fiável que o label
nesta câmara. O `HandLock` resolve a **troca de mão**, não o **lado**.

O que faz sentido é um **híbrido**: decidir o *lado* por X (como hoje) e usar o
`HandLock` para decidir **qual mão** dentro do lado, quando há ambiguidade (duas
detecções à esquerda). Ganho marginal, mas é código já escrito e testado.

## 3.3 Onda 2 — Arquitectura de features à Meta

O salto qualitativo. Substituir a taxonomia ad-hoc por **features contínuas
anatómicas**, e deixar a decisão para cima.

### 2.1 Ângulos de falange

Calcular, por dedo e por mão, os ângulos **DIP, PIP, MCP** em graus a partir das
landmarks, e a soma acumulada. Resultado invariante a rotação, escala e
distância.

### 2.2 Referencial canónico (`wrist space`)

Construir um referencial por mão: origem no pulso, `y` ao longo de
pulso→landmark 9, `x` no plano da palma, `z` = normal da palma. Projectar todos
os 21 pontos nesse referencial e normalizar pelo tamanho da mão.

Custo: uma matriz de rotação 3×3 por mão, feita uma vez por frame, a partir de 3
pontos. Trivial. Benefício: **todas** as features seguintes ficam
gratuitamente invariantes a rotação e escala.

### 2.3 As features da Meta

| Feature | Cálculo | Estado |
|---|---|---|
| `curl[i]` | soma dos ângulos DIP+PIP, em graus | 3 estados (aberto/neutro/fechado) por limiar |
| `flexion[i]` | ângulo MCP relativo ao plano da palma | contínuo |
| `abduction[i]` | ângulo entre bases de dedos adjacentes | contínuo |
| `opposition` | posição do polegar no referencial | contínuo |
| `pinch_strength` | 1 − dist(polegar, ponta) normalizada pela mão | **contínuo 0..1** |
| `palm_normal` | produto vectorial de dois eixos da palma | orientação 3D |
| `hand_roll`, `hand_pitch` | Euler do referencial | orientação |

### 2.4 Os 9 transformadores de orientação

Da documentação do SDK, directamente aplicáveis: `PalmUp`, `PalmDown`,
`WristUp`, `WristDown`, `FingersUp`, `FingersDown`, `PalmTowardsFace`,
`PalmAwayFromFace`, `PinchClear`.

Isto desbloqueia gestos **inteiramente novos** que hoje são impossíveis porque
não há noção de orientação: "palma para cima" como gesto de avanço, "palma contra
o ecrã" como push. E, criticamente, permite **condicionar gestos existentes**: o
`thumb_up` deixa de ser "polegar acima dos MCPs" (que falha quando a mão está de
lado) e passa a ser "polegar estendido **e** punho **e** `FingersDown` relativo ao
mundo".

### 2.5 `pinch_strength` contínuo — clique analógico

`pinch_strength` em vez do Schmitt booleano habilita:

- **Clique analógico** — `strength` controla o cursor durante o arraste (rasto
  suave vs. preciso). Primeira vez que a interacção sente o rato físico.
- **Arrastar com pressão** — comprometer o arraste só acima de um limiar, em vez
  de no primeiro frame de contacto.
- **Detecção de pinça mais robusta** — a cruza os limiares em vez de bater neles,
  que é onde o ruído mora.

O Schmitt **não desaparece**: passa a hysterese sobre o sinal contínuo, o que o
torna mais robusto do que a razão actual.

### 2.6 Detector de poses declarativo

Substituir o `if/elif` de `core/gestures.py:230-256` por uma **tabela de
requisitos**, no espírito do `ShapeRecognizer` do SDK:

```python
Pose("scroll_up",
     shapes=[curl(THUMB, OPEN), curl(INDEX, OPEN), curl(MIDDLE, OPEN),
             curl(RING, CLOSED), curl(PINKY, CLOSED)],
     transform=FingersUp,
     min_time_s=0.12)
```

Vantagens concretas:

- **Inspecionável** — o conteúdo de um gesto é dado declarativo, testável sem
  landmark sintética.
- **Editável pelo utilizador** — a mesma estrutura pode alimentar um ecrã de
  configuração de gestos, o que resolve a fragilidade do *pipeline* de
  reconfiguração.
- **Uniforme** — a mesma maquinaria serve para 1 mão, mão esquerda e 2 mãos, o
  que hoje são três sistemas separados.
- **`MinTimeInState`** — a mesma protecção que a histerese, mas no domínio do
  tempo, e em **todos** os gestos, não só nos que têm Schmitt manual.

### 2.7 Separar forma de dinâmica

A Meta distingue reconhecimento de **forma** (estático: "a mão está em
thumbs-up") de **velocidade/rotação** (dinâmico: "a mão está a subir em
thumbs-up"). O Mãouse mistura os dois no mesmo detector com limiares
sobrepostos.

Um `JointDeltaProvider` (cache de deltas entre frames, como no SDK) permite que
`FistCycleDetector`, `WaveDetector` e o swipe da mão esquerda passem a operar
sobre **velocidades articulares** em vez de **posição de palma** — mais robusto
a câmaras lentas, onde um deslocamento por frame é um evento raro e ruidoso em
vez de um evento normal.

## 3.4 Onda 3 — ML real

### 3.1 Corpus de treino real

O objectivo não é "mais dados" mas **os eixos que a Meta nomeia**:

| Eixo | Porquê |
|---|---|
| **Tom de pele** | O erro de landmark é sistematicamente maior em pele escura sob luz fraca; a cor da pele muda a textura que o detector usa |
| **Iluminação** | 3 níveis: natural, artificial, escura. Já sabemos que o desempenho muda (48.3 → 78.5 ms) |
| **Ângulo de câmara** | lateral, de cima, de baixo — o `z` do MediaPipe degrada com obliquidade |
| **Distância** | perto (só a palma entra no crop) a longe (mão pequena, perto do `min_hand_scale_px`) |
| **Forma de mão** | pequenas e grandes; o ratio de falanges varia muito |
| **Nível de "bagunça"** | gestos a meio, dedos em transição — é onde vivem as confusões |

Ferramenta: `tools/collect_gestures.py` já existe; extender para gravar vídeo +
landmarks + **classe**, e a etiqueta vem da anotação humana, não do
gesto que o sistema em anotção própria.

### 3.2 Retreinar com dados reais

- `real_copies` subir de 4 para muito mais, e `load_real()` deixar de ser
  opcional.
- Manter a síntese **apenas como augmentação**, nunca como fonte dominante.
- **Crítico**: añadir uma classe `REJECT` (abstenção). O classificador deve poder
  dizer "não sei" e o sistema faz `Gesture.NONE`. Hoje não tem essa saída — tem
  de escolher uma das 9.

### 3.3 Modelo temporal em vez de média

O feature actual é 60 dims da frame actual + 60 da **média** da janela de 5
(`core/gesture_ai.py:61-71`). Uma média não distingue dois gestos que passam
pelo mesmo ponto intermédio.

Substituir por features de **primeira e segunda ordem**:

- posição actual, já normalizada
- **velocidade** de cada junta (Δ / Δt, com `dt` real do `dt_ema` do engine)
- **aceleração**
- **ângulos** das falanges (da Onda 2)
- delimitadores: mão a entrar/sair, junção de mãos

Isto é barato e ataca directamente os confusos `FIST↔THUMB_UP` e `PEACE↔THREE`,
que são **transições**, não estados.

Se os limites forem atingidos, evoluir para umaTCN/GRU pequeno sobre a sequência
de juntas — é o que a Meta faz com o keypoint estimator a usar histórico.

### 3.4 Especialistas em vez de um classificador único

O classificador único de 9 classes tem de decidir "isto é pinça ou mão aberta?".
Separar:

- **Detector de pinça** dedicado, a sair `pinch_strength` (Onda 2). Mais
  fiável porque é binário e mede-se directamente.
- **Classificador de forma** para os gestos de dedos, sobre os ângulos.
- **Classificador de orientação** para os 9 transformadores.

Cada especialista tem o seu ground truth, é mais fácil de afinar e um erro num
não propaga aos outros. É a mesma divisão que o SDK expõe
(`GetFingerIsPinching` vs. `FingerFeatureStateProvider`).

## 3.5 Onda 4 — Identidade, oclusão e continuidade

### 4.1 Tracking com identidade

Hoje as mãos são escolhidas por X (`core/engine.py:45-108`). Funciona, mas é
uma heurística. Duas mãos que se cruzam trocam de identidade e o engine faz
reset de filtros — o cursor dá um salto.

Replicar o **detection-by-tracking** da Meta: IDs estáveis,reatribuição por
distância prevista, e o detector pesado só de N em N frames quando a confiança
cai. O ganho é duplo: menos custo de inferência (mais fps em CPU fraca, o que
ataca a limitação #1) e sem trocas de identidade.

O `HandLock` já é um rascunho disto — a Onda 1.5 é o passo demeasurable.

### 4.2 Oclusão

Quando os dedos dobram, a razão 2D colapsa e o `pinch_mid_ratio` tem de ir
buscar o 3D — que é exactamente o bug que o comentário em
`core/gestures.py:112-114` descreve a evitar. A resolução da Meta é **não
estimar a junta oculta**: reconstrói a mão de um modelo e resolve a
cinemática inversa com as juntas visíveis como restrições.

Para o Mãouse, uma versão barata: ajustar um modelo paramétrico de mão (falanges
de comprimento fixo) às 21 landmarks por mínimos quadrados, e usar o modelo
como **estado de verdade** para as juntas pouco confiáveis. É um problema de
otimização pequeno e bem definido.

### 4.3 Loss of tracking

A Meta mantém poses plausíveis fora do campo de visão (WMM + IOBT). Para um rato
isto tem valor limitado — não se clica no que não se vê — mas tem um valor
concreto: **evitar tempestade de re-disparos**. Se o gesto foi `PINCH` e a mão
sai, o `left_up` dispara e o `left_down` volta quando ela regressa. Um estado
`TRACKING_LOST` com decaimento de confiança permitiria suprimir isso.

`left_hand_lost_grace_s = 0.3` já é um passo nessa direcção, mas só para a mão de
comandos. Generalizar.

## 3.6 Onda 5 — Redução do conjunto de gestos

A observação mais desconfortável de toda a análise, e talvez a de maior
impacto.

O sistema tem **13 gestos de uma mão + 6 comandos da mão esquerda + 6 gestos de
duas mãos = 25 combinações**. Numa câmara a 12–15 fps, com mãos de tamanho
variável e iluminação imperfeita.

Cada gesto adicional multiplica a superfície de erro. A Meta não tem 25 gestos:
tem **poucas primitivas muito fiáveis** — *pinch*, *point*, *grab*, *palm-up* —
e deixa a aplicação compor. Um SDK com 4 primitivas relics pode suportar
qualquer número de comandos de alto nível com **zero** custo de reconhecimento
adicional.

O mesmo se aplica aqui. `Ctrl+C` e `Ctrl+V` via `PINKY` e `SHAKA` são
convenientes, mas custam dois gestos de baixa frequência, e baixa frequéncia é
exactamente onde a taxa de erro mais dói. Deviam ser:

- **configuráveis** (ver 2.6 — com o detector declarativo, isso é um ecrã de
  settings, não um fork do código), e
- **opcionais** — desligados por omissão para o utilizador que só quer cursor e
  clique.

O objectivo da Onda 5 não é "acrescentar gestos". É **manter o mesmo
vocabulário útil com muito menos primitivas de alto risco**, movendo o risco
para a camada de composição.

## 3.7 Roadmap

| Onda | Âmbito | Esforço | Dependência |
|---|---|---|---|
| **0** ✅ | `--record`/`--replay`, corpus etiquetado, `eval_recognition.py`, CI | feito | — |
| **1** 🔶 | ~~SHAKA→PINKY (defeito medido)~~ **feito** · filtrar landmarks · propagate confiança · rótulos | 1 semana | 0 |
| **2** | wrist space · ângulos de falange · features contínuas · 9 transformadores · detector declarativo · clique analógico | 4–6 semanas | 0, 1 |
| **3** | Corpus real por demografia · `REJECT` · features de velocidade · especialistas | 3–4 semanas | 0, 2 |
| **4** | Identidade por tracking · modelo de mão para oclusão · `TRACKING_LOST` | 3–4 semanas | 2 |
| **5** | Composições configuráveis · reduzir primitivas de alto risco | 2 semanas | 2, 3 |

**Sequenciamento recomendado**: 0 → 1 → 2 → 3 → 4 → 5.

A Onda 1 sozinha já justifica o seu custo (é o maior ganho isolado do plano) e
a Onda 2 é onde o sistema passa de "bons limiares" a "arquitectura correcta". A
Onda 0 não é opcional: é o que torna todo o resto verificável — e sem ela a
Onda 1 seria uma aposta. Agora que existe, a Onda 1 começou por um defeito
**medido** e não por uma intuição, e o primeiro item (§1.3, SHAKA→PINKY) está
**fechado** — a fixture passou de 0.8958 para 1.0000 com zero confusões.

O resto da Onda 1 (filtrar landmarks das pontas dos dedos, propagar a confiança
do MediaPipe, corrigir os rótulos do enum) continua por fazer. A filtragem
ganhou prioridade nova: com a confusão PINKY/SHAKA fechada, o próximo
off-diagonal **não é conhecido** — só aparece quando houver corpus real.

## 3.8 Métricas de aceitação

Definição operacional de "nível profissional" para o Mãouse. Números explícitos
para que a afirmação seja verificável:

| Métrica | Alvo | Actual | Nota |
|---|---|---|---|
| **Cliques fantasma** | **0 por hora** de uso contínuo | **0/h** (sintético) | A métrica mais importante. Destrutiva quando falha. |
| F1 por gesto | ≥ 0.97, sem gesto abaixo de 0.95 | **1.0000** macro (sintético) | Cumprido na fixture depois da Onda 1 §1.3. **Não é evidência de qualidade** — falta o corpus real (Onda 3 §3.1) |
| Recall do cursor (`OPEN`/`ONE`) | ≥ 0.995 | 1.000 | É a função primária; quase nunca pode falhar |
| Precisão do clique (`PINCH`) | ≥ 0.99 | 1.000 | Falso positivo aqui é o pior caso |
| Latência de clique p95 | < 80 ms | medido | Alvo já em `HARDWARE/LAB.md` |
| Jitter em repouso (RMS) | < 0.5 px | por medir | Medido por replay |
| Continuidade de tracking | ≥ 99% dos frames com mão visível | |
| Paridade demográfica | máx. 5 pp abaixo da média por tom de pele | Requisito de MARKETING e de investigação |
| Cobertura de testes do engine | hold→Alt+F4 e `commands_ok` com teste | Fecha o gap registado em 2026-09-06 |
| Desempenho | ≥ 25 fps em desktop com GPU dedicada | Categoria ✅ para marketing (`HARDWARE/LAB.md` risco 1) |

## 3.9 Riscos e não-objetivos

### O gap de frames é irredutível

A diferença de 12 Hz vem de **4 câmaras *fisheye* monocromáticas** num headset
com GPUs dedicate. Numa webcam desktop esse gap não se fecha, e nenhum modelo de
gestos o fecha. É por isso que o alvo da secção anterior é **precisão e
robustez** — jitter, falsos positivos, latência, continuidade — e não taxa de
frames. Prometer paridade com o Quest em fps seria prometer o que a
*plataforma* não permite.

### Não-objetivos

- **Não** perseguir um classificador único end-to-end (Mão → acção). A
  decomposição em features contínuas + composição é mais robusta **e** mais
  depurável.
- **Não** usar modelos de linguagem/vision para classificar gestos em tempo
  real. A latência e o determinismo não o permitem; e o LLM do `core/llm.py`
  já existe para a parte de *voz*, que é assíncrona por natureza.
- **Não** prometer desempenho idêntico ao Quest em condições de oclusão
  extremas. A literatura regista que o erro angular cresce com a velocidade
  mesmo no Quest (11.5° a 80 bpm, 16.7° a 160 bpm na articulação MCP).
- **Não** ligar `HandLock` sem o corpus. A selecção por X é feia mas é
  **medida**; trocá-la por intuição já foi tentado e piorou.

### Riscos

| Risco | Mitigação |
|---|---|
| A Onda 2 é um reescrito grande do cérebro de gestos | Manter o `Gesture` enum como interface pública; mudar só a implementação por trás. Replay da Onda 0 garante que a refactorização não regride nada. |
| Filtrar landmarks aumenta a latência do clique | `beta` do One Euro existe para isto; calibrar contra o alvo de p95, não "a olho". |
| O corpus etiquetado é caro de produzir | Começar por 50 clips nos eixos de maior risco (pele escura, luz fraca, ângulo lateral); crescer só onde a matriz mostrar confusão. |
| Recurso de dados de utilizadores reais | Por enquanto só dados do próprio equipa. Antes de qualquer colecta de terceiros, é obrigatório revisão de RGPD/privacidade e consentimento explícito. |
| Métricasrapper para marketing sem evidência | `HARDWARE/PROBLEMAS_KNOWN.md` é a norma do projecto. Qualquer número mostrado a terceiros tem de sair do `eval_recognition.py`, não de impressão. |

---

## Referências externas

- [MEgATrack: Monochrome Egocentric Articulated Hand-Tracking for VR](https://ai.meta.com/research/publications/megatrack-monochrome-egocentric-articulated-hand-tracking-for-virtual-reality/) — Meta AI Research, 2020
- [Using deep neural networks for accurate hand-tracking on Oculus Quest](https://ai.meta.com/blog/hand-tracking-deep-neural-networks/) — Facebook Reality Labs, 2019
- [Hand tracking technology (design)](https://developers.meta.com/horizon/design/hands-technology/) — Meta Horizon
- [Hand pose detection (Unity SDK)](https://developers.meta.com/horizon/documentation/unity/unity-isdk-hand-pose-detection/) — `curl`, `flexion`, `abduction`, `opposition`, `ShapeRecognizer`, `MinTimeInState`
- [IHand interface](https://beta.developers.meta.com/horizon/reference/interaction/v201/interface_oculus_interaction_input_i_hand/) — `pinch strength`, `IsHighConfidence`, wrist space
- [On-Device, Real-Time Hand Tracking with MediaPipe](https://research.google/blog/on-device-real-time-hand-tracking-with-mediapipe/) — Google Research, 2019 — BlazePalm + landmark + gesture
