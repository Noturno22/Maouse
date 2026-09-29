# Histórico de trabalho — Mãouse

Registo cronológico de tudo o que o agente fez no projeto.
Cada tarefa nova entra no topo, com data/hora, o que foi feito, ficheiros
tocados e como verificar.

Formato de uma entrada:

```
## [AAAA-MM-DD HH:MM] Título curto
- **Objetivo:** ...
- **Alterações:** `ficheiro:linha` — descrição
- **Verificação:** comando executado + resultado
- **Estado:** OK | Parcial | Falhou | Em curso
```

---

## ONDE RETOMAR (2026-09-27 23:15) — o PC foi desligado aqui

**Estado:** o clique está corrigido e confirmado no aparelho real. Nada
pendente de código. A única coisa em aberto é uma medição de confirmação.

**Primeiro, arrancar os serviços** (o PC reinicia e perde os três):
```bash
cd /home/fortuna/Desktop/Maouse-main/license-server && set -a && . ../.env && set +a && \
  setsid nohup ../.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8899 \
  > /tmp/maouse-ls.log 2>&1 < /dev/null &
cd /home/fortuna/Desktop/Maouse-main/mobile/airmouse-mobile && \
  setsid nohup npx expo start --host lan --port 8081 > logs/expo-dev.log 2>&1 < /dev/null &
cd /home/fortuna/Desktop/Maouse-main && \
  AIRMOUSE_TRACE=1 setsid nohup .venv/bin/python main.py > /tmp/maouse-run.log 2>&1 < /dev/null &
```
- Token do remoto: `a693…` (o valor completo está em `settings.json`, que é
  gitignored — não o repetir aqui).
- O trace vai para `logs/airmouse.log`; o arranque vai para `/tmp/maouse-run.log`.
- O `AIRMOUSE_TRACE=1` é só diagnóstico — sem ele o log é limpo e o código
  corre exactamente igual (`core/log.py:trace`).
- Confirmação de que a sessão é X11: `echo $XDG_SESSION_TYPE` → tem de dar
  `x11`. Em Wayland o `pynput` **não** mexe no cursor virtual e nada disto
  se mede.

**A medição que fica em aberto.** Falta comparar o clique píxel a píxel contra
um alvo calibrado. O trace já prova que o `move_to` vai para as coordenadas
certas e que o clique segue no mesmo comando — o que falta é a confirmação de
que o ponto que o utilizador *tocou* corresponde mesmo ao ponto que *vê* no
ecrã. Como o touchpad tem 328 px de largura e o ecrã 1366, qualquer erro de
origem/dimensão do pad (`RemoteScreen.tsx:measurePad`, `PadRect`) é
exactamente o que aparece aqui.
Como fazer, sem instrumentação nova:
1. No telemóvel, carregar em 4 pontos, incluindo por cima do texto de dica e do
   distintivo do ecrã (os dois que já causaram o `locationX` relativo à vista
   errada, entrada das 23:02 de 26-09).
2. Cada clique deixa no trace `REMOTE move_to (x,y) -> (px,py)`, que é o pixel
   exacto. Comparar esse pixel com o ponto que se vê no ecrã depois do clique.
   Desvio 0 px nos quatro = fechado.
Se não quiseres comparar visualmente, diz e faço um teste com um alvo
calibrado no ecrã.

**Estado da árvore de trabalho** (nada disto foi commitado — o trabalho das
02:50 e o de hoje estão todos por commitar):
```
 M HISTORICO.md
 M config.py                              remote_move_gain novo (3.0)
 M core/log.py                            trace() novo, atrás de AIRMOUSE_TRACE
 M core/remote.py                         árbitro begin/end, _move_rel com ganho
 M main.py                                liga on_command_begin/end ao árbitro
 M ui/settings_dlg.py                     slider do ganho remoto
 M tests/test_remote.py                   +5 testes (TestToqueAbsoluto, ganho 1x)
 M mobile/.../RemoteScreen.tsx            toque absoluto reposto
 M mobile/.../remoteClient.ts             flushMoves antes de cada comando; sem ganho
?? logs/                                  logs de diagnóstico, gitignored
```
Para commitar: `git add -A ':!logs'` e depois `git commit`.

**Última suíte:** `302 passed`, `ruff` limpo, `tsc --noEmit` exit 0.

---

## [2026-09-27 03:20] O clique no telefone continuava a saltar: eram três defeitos, um deles de ordem

- **Objetivo:** o utilizador voltou a dizer que o clique no telefone salta,
  depois de três entradas seguidas a tentar corrigir o mesmo sintoma. A
  entrada das 02:50 ficou **Parcial** à espera de confirmação no aparelho.
  Antes de mexer em código, li o que estava por commitar — e havia uma
  inversão de design e dois bugs por detrás.

- **Defeito 1 — o toque tinha passado a relativo, contra a decisão tomada.**
  A entrada das 02:50 regista que o utilizador escolheu explicitamente o
  comportamento **absoluto** ("clicar onde toca no touchpad"). A alteração por
  commitar inverteu isso: o toque passou a mandar `gesture tap` **sem
  coordenadas**, e apagou o `PadRect`/`measureInWindow` que convertia o toque
  em coordenadas absolutas. Com o toque relativo, acertar o ponto passa a
  depender de acertar o **ganho** — e um erro no ganho deixa de se ver como
  "o rato é rápido" e passa a ver-se como "o clique saltou". Confirmado com
  o utilizador: escolhe o **híbrido** (toque absoluto, arrasto relativo).
  Reposto o tap absoluto, mantendo o arrasto relativo.

- **Defeito 2 — o ganho era aplicado duas vezes.** `remoteClient.ts` tinha
  `MOVE_GAIN = 1.8` desde o commit original (`7079103`), e a alteração por
  commitar acrescenta `remote_move_gain = 3.0` no PC. Os dois multiplicam:
  **efectivo 5,4x**. Com o touchpad a medir 328 px (`tx/ty/px/pw` medidos) e o
  ecrã a 1366, uma varredura do dedo na largura do pad atirava o cursor
  **1780 px** — mais do que a largura do ecrã, ou seja, batia sempre no
  limite. O toque seguinte clicava onde o cursor tinha ficado em vez de onde o
  dedo parou. Os testes não apanhavam isto: `tests/test_remote.py` exercita
  `_move_rel` isolado, e o `1.8` vive em TypeScript, onde este projeto não
  tem framework de teste.
  **Decisão:** o ganho fica num sítio só, no PC (`remote_move_gain`), que é
  afinável no ecrã das definições sem recompilar a app. Removido o `1.8` do
  telefone; `pendingDx`/`pendingDy` passaram a acumular em vírgula flutuante
  (o `Math.round` por evento perdia meio píxel de cada vez).

- **Defeito 3 — a ordem de envio estava trocada, e é o que mais explica
  "salta".** `move` era acumulado e enviado de 24 em 24 ms, mas
  `gesture`/`click`/`press` iam **imediatos**. O servidor executa um comando
  de cada vez, pela ordem de chegada: ao carregar havia até 24 ms de
  movimentos do dedo por aplicar, que ficavam **para trás** do clique. O
  clique assentava no sítio antigo e o cursor só avançava **depois** — o
  inverso do que o dedo queria dizer, e a origem mais provável do termo
  "salta".

- **Alterações:**
  - `remoteClient.ts:29` — `MOVE_GAIN` removido; o ganho passa a ser só o do
    PC. Comentário a explicar porque é que não pode voltar a haver ganho
    nos dois lados.
  - `remoteClient.ts:112` — `move()` acumula em vírgula flutuante, sem ganho.
  - `remoteClient.ts:180` — `sendRaw()` passou a fazer `flushMoves()` antes de
    enviar. Todos os comandos discretos passam por ela, portanto a ordem de
    escrita no WebSocket passa a ser a ordem em que o utilizador fez as
    coisas. `flushMoves()` usa `rawSend` (não `sendRaw`) para não se chamar a
    si próprio indefinidamente.
  - `RemoteScreen.tsx` — reposto o `PadRect`/`padRef`/`measurePad()` e o
    `ref`/`onLayout` no touchpad; o toque volta a converter `pageX`/`pageY`
    em normalizados e a mandar `gesture('tap', x, y)`. `measurePad()` corre no
    `onLayout` e a cada `onPanResponderGrant` (o teclado abrir/fechar muda a
    posição do pad sem mudar o tamanho). `accessibilityHint` e o texto de dica
    voltaram ao "toque clica no ponto tocado".
  - `core/remote.py:1` — docstring do protocolo: `gesture tap` com x/y é o
    caminho normal; o caminho sem x/y fica documentado como o que preferem os
    clientes que usam o rato como alvo.
  - `tests/test_remote.py` — `FakeMouse` passou a registar `click_at`, a
    posição do cursor no instante exato de cada clique. Sem isso não dava para
    provar nada: o `move_to` e o `left_click` acontecem no mesmo comando e a
    posição final é a mesma nos dois casos.
  - `tests/test_remote.py:TestToqueAbsoluto` (novo, 4 testes) — o clique cai
    no ponto tocado; cai no ponto tocado com movimento relativo pendente;
    acerta nos quatro cantos; e com o ganho no extremo (1.0, 3.0, 8.0) o
    ponto tocado dá sempre a mesma coordenada.
  - `tests/test_remote.py:test_ganho_aplicado_so_pelo_pc` (novo) — uma
    varredura do pad tem de dar `pad_w x ganho` e não atravessar o ecrã, para
    a regressão do ganho duplicado ser óbvia.
  - `tests/test_remote.py:TestTouchpadRelativo` — o docstring dizia que
    misturar relativo e absoluto era o bug. Passou a descrever o híbrido, e o
    teste do `gesture tap` sem coordenadas foi requalificado (o servidor
    continua a aceitá-lo; o app é que já não o usa).

- **Verificação:**
  - `pytest tests/ --ignore=tests/test_voice_direct.py` → **302 passed**
    (baseline 297; +5).
  - `ruff check core/ tests/ main.py ui/` → limpo.
  - `npx tsc --noEmit` (em `mobile/airmouse-mobile`) → exit 0.
  - `test_toque_cai_no_ponto_tocado_mesmo_com_movimento_relativo_pendente`
    fixa a ordem: com 20 `move` de 1 px e ganho 3.0, o cursor estava em
    (160, 100) e o clique assentou no ponto tocado — nem no sítio anterior
    nem a meio caminho entre os dois.

- **Verificação no aparelho (feita, com o telemóvel do utilizador):**
  Serviços arrancados — o PC tinha reiniciado às 21:04 e não havia nada a
  correr: license-server em `127.0.0.1:8899` (`/health` → `{"status":"ok"}`),
  Metro em `*:8081`, e `main.py` com `AIRMOUSE_TRACE=1` (sessão **X11**, o que
  importa: em Wayland o `pynput` não mexe no cursor virtual).
  - **O bundle que o Metro serve já tem as três correções**, lido do bundle
    real (`curl index.bundle?platform=android&dev=true`, 7.5 MB):
    `pendingDx += dx` (sem `Math.round(MOVE_GAIN * dx)`);
    `sendRaw(cmd){ if(!this.ready) return; this.flushMoves(); this.rawSend(cmd); }`;
    e `gesture('tap', x, y)`.
  - **Um toque real do aparelho, no trace:**
    ```
    7608.234  REMOTE recv {"cmd":"gesture","event":"tap","x":0.6189,"y":0.5308}
    7608.236  ARBITER toma o rato por 1.50s (pausa a camara)
    7608.242  REMOTE move_to (0.6189,0.5308) -> (844,407)
    7608.247  REMOTE done  gesture -> TAP (espera 14 ms)
    7609.820  ARBITER devolve o rato a camara
    ```
    Ou seja: o toque chega **absoluto** (prova de que o aparelho recarregou e
    apanhou o bundle novo), a câmara é silenciada 2 ms **antes** do salto, o
    `move_to` e o clique seguem no mesmo comando com **14 ms** de latência (a
    corrida de GIL das 02:50 não se repetiu), e **não entra um único `move`
    depois do clique**. A janela de 1,5 s cumpre-se a partir do fim.
  - **Dois arrastos reais, com a câmara a ver:** 49 e 32 `move`, e
    **0 decisões da câmara** em ambos. O árbitro segura durante o arrasto.
  - **O telefone envia o dedo a 1:1 — medido na distribuição dos deltas.** Dos
    1026 componentes de `move` no trace, **54,5% são de 1 px**. Com o
    `MOVE_GAIN = 1.8` isso era aritmeticamente impossível (`round(1.8 × 1) = 2`:
    nunca sairia 1). Prova directa de que o ganho duplicado desapareceu.
  - `remote_move_gain` em runtime = **3.0**, vindo do omisso: a chave não
    existe no `settings.json`, logo não há segundo ganho a somar. E o
    `test_ganho_aplicado_so_pelo_pc` fixa `pad_w × ganho` sem atravessar o ecrã.

- **Armadilha da medição (registada porque quase deu um falso "OK"):** a
  primeira tentativa de medir o ganho no rato real deu 0.42. A causa foi o
  utilizador estar a mexer no touchpad ao mesmo tempo — os comandos que o
  trace atribuí ao script eram do dedo dele. Só se mede o ganho com o
  telemóvel quieto, ou pelo trace (que é imune a quem mexe no rato).

- **Nota:** o `remote_move_gain` a 3.0 é o valor por omisso com a calibragem
  assumida (pad 328 px, ecrã 1366 px) e é afinável em Definições. Só afecta o
  **arrasto**, agora que o toque é absoluto.
- **Estado:** OK — corrigido, coberto por testes e confirmado no aparelho real
  (bundle, toque absoluto, ordem, arrasto com a câmara activa, ganho 1:1).
  Fica por medir o **ponto exato** do clique contra um alvo conhecido: o trace
  prova o `move_to` e que o clique seguiu no mesmo comando, mas eu não tinha
  um alvo calibrado para comparar píxel a píxel.

## [2026-09-27 02:50] O clique do telemóvel caía no sítio errado: a janela de silêncio expirava a meio do comando

- **Objetivo:** o utilizador passou a dizer que não era um salto depois de
  clicar, mas que **o clique caía no sítio errado**. Decidiu manter o
  comportamento **absoluto** (clicar onde toca no touchpad).
- **As coordenadas estavam certas.** Com instrumentação no telefone
  (payload `d` com `tx/ty/px/py/pw/ph`) e no PC, um toque no centro do pad deu
  `tx=180`, rect `px=16 pw=328` → `x = (180-16)/328 = 0.5000` exacto, e o
  cursor foi para o centro do ecrã, (682, 361). Um segundo toque deu
  `tx=44 ty=128.5` → `x=0.0854 y=0.0650` → (116, 49). A aritmética do touchpad
  está certa.
- **A pista anterior dos "656" era um erro meu.** Impus que `pageX` fosse
  inteiro e exigi que `x·w` desse inteiro; como o telefone devolve meio
  píxel (`ty=128.5`), concluí falsamente que a largura era o dobro. Com
  `w=328` todos os valores anteriores são plausíveis. O rect nunca mudou.
- **A causa real era uma corrida no árbitro.** O trace mostrou o comando a
  *chegar* e a *executar* 2,02 s depois:
  `REMOTE recv` às 4351.034 → `ARBITER devolve o rato a camara` às 4352.544 →
  `REMOTE move_to` às 4352.829 → clique às 4353.057. A janela de silêncio de
  1,5 s arrancava na **recepção** e expirava **durante a execução**; a câmara
  reabria o rato e o clique aterrava onde ela tivesse deixado o cursor. O
  comando demora porque a inferência MediaPipe segura a GIL — é intermitente, o
  toque seguinte demorou 2 ms.
- **Alterações:**
  - `core/remote.py:140` — `RemoteArbiter.begin_command()` / `end_command()`:
    mantêm a câmara calada durante toda a execução do comando, por mais tempo
    que a GIL o segure, e re-armam os 1,5 s a contar do fim (quando o clique
    já aconteceu).
  - `core/remote.py:193` — `tick()` deixa de devolver o rato à câmara enquanto
    há comando em voo.
  - `core/remote.py:418` — o ciclo de comando passou a envolver
    `_handle()` em `begin`/`end`, com `finally` para não deixar o rato preso
    se o comando lançar excepção. `trace` passou a registar a latência
    `recv → done` em ms.
  - `core/remote.py:244` — `_begin_command()` / `_end_command()` no servidor,
    com degradação segura para `_note_activity()`.
  - `main.py:380` — liga os dois callbacks novos ao árbitro.
  - `tests/test_remote.py:307` — teste de regressão com relógio controlado.
- **Verificação:**
  - `pytest tests/ --ignore=tests/test_voice_direct.py` → **290 passed**;
    `ruff check core/ tests/ main.py` → limpo; license-server → **72 passed**.
  - O teste de regressão **falha sem a correcção** (`False != True`) e passa
    com ela — verificado por reversão temporária.
  - `/tmp/opencode/e2e_gil.py` (novo, ponta a ponta com X11 real): com comando
    atrasado 2,5 s, o clique sai **7 px fora do alvo** sem a correcção e
    **2 px** (só arredondamento do `move_to`) com ela, e o rato fica parado no
    alvo durante a execução.
  - `/tmp/opencode/diag_drag.py`: durante um arrasto de 3 s, **0** decisões da
    câmara com o árbitro a segurar, em 8/8 execuções.
  - Corrigido o artefacto de medição do `/tmp/opencode/e2e_click.py`: o
    sampler começava antes do handshake e contava como falha a janela em que
    ainda não tinha chegado comando nenhum.
- **Resta por verificar no aparelho real:** com a mão à frente da câmara, o
  clique tem de cair no ponto tocado mesmo que a latência seja de segundos.
- **Nota de ambiente (não resolvido):** a latência de 2 s vem da inferência da
  câmara a segurar a GIL. A correcção garante que o clique é correcto, mas o
  atraso em si é um problema de performance à parte.
- **Estado:** Parcial — código corrigido e coberto por testes; falta confirmar
  no aparelho com a mão em cena.

## [2026-09-27 01:25] Verificação do clique do telemóvel finally fechada (o X11 deixou de estar congelado)

- **Objetivo:** retomar a entrada das 00:46, que ficou **Parcial** por causa da
  nota de ambiente: o ponteiro do X11 estava congelado no centro do ecrã e
  bloqueava a verificação ponta a ponta do clique.
- **Estado do ambiente ao arrancar:** nenhum processo vivo (o PC voltou a
  reiniciar) e a árvore de trabalho limpa — o código do árbitro já estava
  commitado em `caddd76`.
- **O bloqueio do X11 já não existe.** Medi antes de mexer em nada:
  `pynput.Controller().position` respondeu a quatro `warp` seguidos para
  (100,100), (1200,700), (683,384) e (300,500), ficando em cada um, e um clique
  real foi aceite. A janela 1366x768 está presente. Podia-se, portanto, medir.
- **Nenhuma alteração a código nesta entrada.** O que segue é a verificação que
  faltava, feita com a máquina real e só a mão simulada.
- **Verificação 1 — teste ponta a ponta com tudo real** (`/tmp/opencode/e2e_click.py`):
  servidor `RemoteServer` real, `MouseCtl` real sobre X11, `SmoothEmitter` real
  a 180 Hz, `RemoteArbiter` real, e uma frame loop que reproduz o que
  `core/engine.py:212` faz a cada frame (`arbiter.tick()` e o gate de
  `state["paused"]`). Só a mão é simulada — empurra 7 px por frame a ~20 Hz.
  - base, sem telemóvel: a câmara mexe o rato (123 px em 0,6 s);
  - 6 cliques absolutos (cantos, centro e intermédios): todos exactamente no
    sítio, com a mão a competir;
  - arrasto de 3 s a 30 Hz (o que o app envia): **0** decisões da câmara, contra
    ~60 esperadas sem telemóvel; árbitro a segurar 60 das 61 amostras;
  - clique em (0,72; 0,31) com a sessão viva: **desvio 0 px** em 26 amostras de
    1,2 s — o clique não é arrastado;
  - passado 1,5 s de silêncio: a câmara retoma, `holding` falso, `paused` limpo.
- **Verificação 2 — contra o processo real em produção** (`main.py` a correr com
  a câmara ligada, porta 8765): 4 cliques em (0,25;0,4), (0,7;0,6), (0,5;0,85) e
  (0,05;0,95). Todos assentam no alvo em **30–40 ms** e ficam **imóveis, desvio
  0 px**, em ~36 amostras de 1,2 s cada.
- **Suítes:** `289` testes desktop e `72` server verdes; `ruff` limpo.
- **Nota (não é bug):** o `ping` é tratado com `continue` **antes** de
  `_note_activity()` (`core/remote.py:344`), logo o keepalive do telemóvel não
  re-arma o árbitro. É inofensivo: `PING_INTERVAL_MS = 15000`
  (`remoteClient.ts:29`) contra uma janela de 1,5 s — o ping nunca cairia no
  prazo de qualquer forma, e o silêncio é precisamente o sinal para devolver o
  rato à câmara.
- **Duas armadilhas da própria harness, ambas minhas, ambas por premissa errada**
  (registadas porque só uma delas dava um falso "OK"):
  1. o `arbiter.tick()` só é chamado pelo `process_frame` do engine. Sem frame
     loop, `paused` ficava preso a `True` e os testes de clique passavam **sem
     competição nenhuma** — verde falso;
  2. o servidor responde a cada comando; um cliente simulado que não leia as
     respostas trava o `send` do servidor e os comandos deixam de chegar, o que
     fez o teste "a câmara cala-se" falhar com 171 decisões em 3 s. O cliente
     real do app lê as respostas.
- **Por confirmar no aparelho:** o clique no touchpad, com a câmara a ver uma
  mão. As medições acima usam uma mão simulada porque não há mão à frente da
  câmara a esta hora; a câmara real não detetou nada
  (`(1234,129)` → `(1234,129)` em 1,5 s).
- **Serviços arrancados** (o PC tinha reiniciado e perdera todos):
  - license-server em `127.0.0.1:8899` (`/health` → `{"status":"ok"}`);
  - Metro em `*:8081` (log em `mobile/airmouse-mobile/logs/expo-dev4.log`);
  - `main.py` → `License: PRO`, `Camera 0 ativa`, `Controlo remoto ativo em
    0.0.0.0:8765`, token `a693…`.
- **Estado:** OK no código e na verificação medida; falta só a confirmação com
  a mão real à frente da câmara.

---


- **Objetivo:** com o `locationX` e a dead zone já corrigidos, o toque chegava ao
  PC com as coordenadas certas mas o clique continuava a saltar — "os comandos
  funcionam, menos o clique".
- **Diagnóstico (medição, não leitura):** amostrei a posição do rato durante
  12 s **sem nenhum comando do telemóvel**. Mexeu sozinho, e muito:
  `(-431, +26)`, `(+169, -12)`, `(-420, +37)`. Não era o telemóvel: era o motor
  de rastreamento da mão, que também mexe no rato (`mao aberta/1 dedo=mover`),
  ativo com a câmara ligada.
- **Causa raiz:** os dois mexem no mesmo rato e não havia coordenação nenhuma.
  `state["paused"]` (barra de espaço) era o único gate e nunca era ligado pelo
  telemóvel. Cada `gesture tap` fazia `move_to` + `left_click` no sítio certo e
  a câmara arrastava o cursor de imediato a seguir.
- **Alterações:**
  - `core/remote.py`: `RemoteArbiter`. Cada comando de um telemóvel
    autenticado silencia a câmara durante `hold_s` (1,5 s); passado esse tempo
    sem comandos, o rato volta para a câmara. Se o utilizador tinha pausado por
    si, o árbitro não toca nesse estado. `RemoteServer` ganhou `on_activity`,
    chamado no auth e em cada comando.
  - esvaziar a fila do `SmoothEmitter`: pausar a câmara só impede que ela
    decida mais movimentos, mas o emissor continua a despejar a ~180 Hz o que já
    estava enfileirado (até `max_pending_px` = 600 px). Sem esvaziar, o rato
    continuava a andar durante o silêncio do telemóvel.
  - `core/engine.py`: `tick()` do árbitro em `process_frame`, a par do
    `UsageWatchdog`, para devolver o rato à câmara assim que o telemóvel cala.
  - `ui/main_window.py` + `main.py`: a `MainWindow` era construída **sem**
    `state` e criava o seu próprio dicionário, pelo que `state["paused"]` e
    `state["emitter"]` que o `main.py` escrevia nunca chegavam à janela. Passa
    a partilhar o mesmo `state`.
- **Verificação:**
  - `289` testes desktop e `72` server verdes; `ruff` limpo; 8 testes novos para
    o árbitro (pausa no comando, janela estendida por comandos sucessivos,
    devolução ao silêncio, não toca na pausa do utilizador, `on_activity`).
  - **End-to-end, cliente WebSocket simulado:** 200 comandos `move` em ~4 s com
    soma de deltas `(600, 120)` → posição obtida `(599, 121)`, desvio de 1 px
    (o acumulador fracionário do `move_by`). **Antes do fix o mesmo teste dava
    `(359, 171)`.**
  - Cliques absolutos verificados nos 4 cantos, no centro e em pontos
    intermédios: todos exactamente no sítio.
  - **Por confirmar no aparelho:** com a câmara a ver uma mão, o rato tem de
    calar-se durante o uso do telemóvel e voltar depois de 1,5 s de silêncio.
- **Nota de ambiente:** durante esta sessão o ponteiro do X11 ficou congelado no
  centro do ecrã (`(682, 383)`) para **todos** os clientes — `pynput`,
  `XWarpPointer`, `XTestFakeMotionEvent` e `XAllowEvents` — com a aplicação
  parada, sem grab de servidor, e sem ecrã táctil/tablet em modo absoluto. Não é
  do código (reproduz-se com o `main.py` parado) e bloqueia a verificação do
  clique ponta a ponta até o input do X11 ser reposto.
- **Estado:** Parcial — o código está testado e o conflito está medido e
  corrigido; falta confirmar no aparelho com a câmara ativa.

---

## [2026-09-27 00:05] Mobile: o cursor saltava com a tremedeira do dedo no toque

- **Objetivo:** o `locationX` já estava corrigido e as coordenadas do toque
  chegavam certas ao PC, mas o cursor continuava a saltar — muitos toques nem
  sequer carregavam.
- **Diagnóstico (por medição, não por leitura):** log temporário de todos os
  comandos recebidos do telemóvel. As coordenadas do toque estavam **certas** em
  todos os quadrantes (0,131/0,148 → (178,113) num ecrã 1366x768, etc.), logo o
  `pageX` do fix anterior estava bem. O que aparecia era **36 `move` para 6
  toques**: a tremedeira do dedo gerava um `move` relativo por evento, e o
  cursor paseava-se antes de o clique o reposicionar. Noutra ronda chegaram
  36 `move` e **zero** toques.
- **Causa raiz:** a distinção toque/arrasto media o deslocamento **entre dois
  eventos** e ligava aos 2 px, e o toque tinha um limite de 260 ms. Uma
  tremedeira normal de 3 px já marcava o gesto como arrasto (descartando o
  clique) e um toque deliberado de 300 ms não contava como toque. Em ambos os
  casos só ficavam os `move` relativos — que é o "salto" que se via.
- **Alterações** (`mobile/airmouse-mobile/src/components/RemoteScreen.tsx`):
  - `TAP_SLOP_PX = 12`: o limiar passa a medir o deslocamento **total** desde o
    `onPanResponderGrant` (`startX`/`startY` no `touchState`), e não o delta
    entre eventos;
  - **dead zone**: `remote.move` só é enviado quando `ts.dragging || ts.moved`.
    A tremedeira deixa de mexer no cursor, e como `ts.last` é reancorado a cada
    evento, a travessia do limiar não dá um salto;
  - **sem limite de tempo** no toque: um toque lento e deliberado também conta;
  - **arrasto em duas fases** (`holdArmed`): passar `DRAG_HOLD_MS` sem sair do
    limiar *arma* o gesto, mas o botão só carrega quando o dedo começa a mexer.
    Sem isto, um toque parado de mais de 380 ms fazia `press`+`release` e
    carregava na posição em que o cursor por acaso estava em vez do ponto
    tocado; e exigir movimento para armar faria qualquer arrasto normal com mais
    de 380 ms carregar o botão.
- **Verificação:**
  - `npx tsc --noEmit` → limpo; fix confirmado no bundle servido pelo Metro
    (`Math.hypot`, dead zone, `holdArmed`).
  - **Medição no aparelho**, por blocos de comandos recebidos:
    - 4 toques em quadrantes distintos → **0 `move`** antes de cada `gesture tap`,
      coordenadas corretas;
    - arrasto rápido (32 `move`) → **nenhum** `press`/`click`, só mexe o cursor;
    - parar ~1 s e mexer (90 e 62 `move`) → `press` → arrastar → `release`;
    - toque lento de ~1 s → `gesture tap (0.540, 0.559)` com 0 `move` e **sem
      `press`**;
    - 2 dedos a mexer → `scroll`; 2 dedos parados → `click(right)`.
  - Regressão apanhada nesta mesma ronda e corrigida: a primeira versão do fix
    exigia `moved` para carregar o botão, o que fazia *todo* arrasto com mais de
    380 ms clicar. Daí o `holdArmed` acima.
  - `281` testes desktop e `72` testes server verdes; `ruff` limpo.
  - `main.py` reiniciado com o código final (sem os logs de diagnóstico):
    `License: PRO`, controlo remoto ativo em `0.0.0.0:8765`.
- **Fora deste fix:** a sensibilidade do movimento relativo continua 1:1 px, ou
  seja num touchpad de ~400 px só se cobre 400 px de um ecrã de 1366 px.
- **Estado:** OK — medido no aparelho.

---

## [2026-09-26 23:02] Mobile: o toque/clique mandava o cursor para outra direção

- **Objetivo:** no telemóvel, arrastar funcionava mas o toque (clique) colocava
  o cursor no sítio errado.
- **Causa raiz:** o `onPanResponderRelease` convervia o toque com
  `touch.locationX / layoutRef.current.w`. Em React Native o `locationX` é
  relativo **à vista que recebeu o toque**, não à vista que tem o
  `PanResponder`. O touchpad tem dois filhos por cima dele:
  `touchpadHint` (um `Text` centrado, que ocupa a maior parte da área) e
  `screenPill` (`position: absolute`, canto superior direito). Tocar em cima de
  qualquer um dos dois dava coordenadas relativas ao `Text`/ao `pill`, ou seja
  quase (0,0) — e o cursor saltava para o canto, noutra direção.
  O pan não tinha o problema porque usa `pageX`/`pageY` (absolutos) para os
  deltas.
- **Alterações:**
  - `mobile/airmouse-mobile/src/components/RemoteScreen.tsx`:
    - `PadRect` (w, h, pageX, pageY) + `padRef` e `measurePad()`, que usa
      `measureInWindow` para saber onde está o touchpad na janela;
    - o toque passa a usar `pageX`/`pageY` menos a origem do pad, com clamp a
      0..1 — coerente com o pan e independente de qual vista foi tocada;
    - `measurePad()` corre no `onLayout` **e** a cada `onPanResponderGrant`:
      abrir/fechar o teclado ou rodar o telefone muda a posição do pad sem
      necessariamente mudar o tamanho, e o `onLayout` só dispara quando o
      tamanho muda.
- **Verificação:**
  - `npx tsc --noEmit` → limpo (confirma também que `measureInWindow` existe
    com esta assinatura no RN 0.86 do Expo SDK 57; é API do React Native core,
    sem página própria na doc do Expo).
  - `curl "http://127.0.0.1:8081/index.bundle?platform=android&dev=true"` →
    HTTP 200, e o fix está no bundle servido (`touch.pageX - pad.pageX`).
  - **Por confirmar no aparelho:** não há framework de teste no projeto mobile
    (sem jest), logo a verificação do comportamento é manual — recarregar a app
    e tocar em quatro pontos do touchpad, incluindo por cima do texto de dica e
    do distintivo do ecrã.
- **Estado:** Parcial — código e build verificados, falta confirmar no
  telemóvel.

---

## [2026-09-26 22:31] Licença: recuperação de lease divergente (409 + chave persistente + lock)

- **Objetivo:** resolver os três pontos pedidos para o `seq_repetido` que
  deixava o Pro sem renovação: (1) o servidor distinguir "cliente atrasado" de
  replay, (2) o cliente guardar a chave para se auto-reativar, (3) serializar o
  ciclo ler → servidor → gravar com lock de ficheiro.
- **Diagnóstico:**
  - O `license.json` tinha `use_seq=1790435341750`; a BD do servidor tinha
    `last_use_seq=1790435341751`. O lease do cliente estava **um atrás**.
  - `revalidate()` fazia `new_seq = use_seq + 1` e rejeitava com 403
    `seq_repetido` porque `new_seq <= last_seq`. O cliente ficava preso para
    sempre: sem 409, sem chave guardada, sem forma de recuperar.
  - Causa possível do desvio: `main.py` e uma ferramenta de linha de comandos
    partilham `~/AirMouse/license.json`; ambos reliam o ficheiro **fora** de
    qualquer lock e ambos gravavam, pelo que um write perdia o `use_seq` do
    outro.
  - Agravante: em `revalidate()` a atualização dos contadores monotónicos
    (`last_use_seq`) só acontecia mais tarde, num `is_blocked()`; o `_save()`
    intermediate gravava o lease novo com os contadores **velhos**, mantendo o
    store atrás do servidor mesmo sem corrida.
- **Alterações:**
  - `license-server/service.py` — nova `LeaseConflict`; `revalidate()` levanta-a
    quando `claims.use_seq < last_seq` (cliente atrasado). `use_seq == last_seq`
    continua a ser a renovação normal; `use_seq > last_seq` (BD do servidor
    reposta para trás) passa a ser aceite e reaparelha o contador. Removido um
    `if new_seq <= last_seq` que era código morto.
  - `license-server/app.py` — `LeaseConflict` → HTTP `409`
    `{"error": "seq_repetido", "recovery": "reativar"}`. Um 403 continua sem
    `recovery` (revogação não se resolve a reativar).
  - `core/license_client.py` — `LicenseError` transporta `status`, `payload`,
    `recovery` e `needs_reactivation`. Acrescentado também um
    `except LicenseError: raise` antes do `except Exception` genérico: um 4xx
    devolvido sem levantar `HTTPError` caía nesse genérico e aparecia como
    `sem_servidor_reachavel`, o que tornava o 409 indistinguível de uma falha de
    rede.
  - `core/license_store_lock.py` (novo) — lock de ficheiro POSIX/Windows com
    profundidade **por thread** e `RLock` de guarda. A primeira versão partilhava
    a profundidade entre threads e por isso uma segunda thread entrava na secção
    crítica **sem** `flock` (pega por um teste novo, ver abaixo).
  - `core/licensing.py` — `key` no store (só aceite se `machine_id` bater);
    `_reload()`/`_save()` sem lock, para uso dentro de `with store_lock(...)`;
    `activate()`, `revalidate()`, `deactivate()`, `report_usage()` e
    `reconcile_trial()` tomam o lock no ciclo completo; `revalidate()` valida o
    lease **antes** de gravar (avança os contadores) e, num 409, reativa
    automaticamente com a chave guardada; propriedade `needs_reactivation`.
  - `ui/license_dlg.py` + `i18n.py` — texto próprio para "a licença precisa de
    ser reativada", em vez do genérico "chave inválida".
- **Verificação:**
  - `pytest tests/ --ignore=tests/test_voice_direct.py` → **281 passed**
    (eram 257; +24 em `tests/test_license_recovery.py`).
  - `pytest license-server/tests/` → **72 passed** (eram 67; +5 em
    `test_revalidate.py`: 409 com `recovery`, renovação repetida do lease atual,
    `use_seq > last_seq` a resincronizar, ciclo 409 → reativar → funciona, e
    revogação a continuar 403).
  - `ruff check core/ license-server/ tests/ ui/` → limpo.
  - **Ponta a ponta contra o servidor local real** (`127.0.0.1:8899`):
    - `revalidate` com o lease atrasado → `HTTP 409
      {"error":"seq_repetido","recovery":"reativar"}`;
    - `LicenseManager().revalidate()` numa store **sem** chave (versão antiga) →
      `False`, `needs_reactivation=True`, `last_error="reativacao_necessaria"`
      (diz o que fazer em vez de falhar calado);
    - depois de `activate(key)`, recuando o servidor 5 `use_seq`: `revalidate()`
      → `True`, reativou sozinho com a chave guardada, `needs_reactivation`
      limpo, e o `revalidate()` seguinte renova normalmente.
  - Dois bugs apanhados pelos testes novos e corrigidos pelo caminho:
    - o `store_lock` partilhava a profundidade entre threads, e uma segunda
      thread entrava na secção crítica **sem** `flock` (agora: profundidade por
      thread + `RLock`);
    - `os.makedirs(os.path.dirname(path))` rebentava com um path relativo
      (`makedirs("")`), e o `except OSError` engolia-o — o store nunca era
      gravado, em silêncio (agora `or "."`).
- **Estado:** OK (código, testes e verificação manual). A app `main.py` que
  estava a correr foi reiniciada no fim (`kill` + `setsid nohup`, o mesmo
  padrão de sempre) para passar a correr o código novo: arranque limpo com
  `License: PRO`, sem `seq_repetido` no log, controlo remoto de volta em 8765.

---

## [2026-09-26 15:20] UFW: abrir 8765 e recuperar o trabalho por commitar

- **Objetivo:** o PC desligou às ~15:05. Retomar a sessão de ontem
  (14:50) e fechar o commit do trabalho que ficou por registar.
- **Diagnóstico do estado ao arrancar:**
  - `logs/maouse-run.log` (15:05:34) mostra `main.py` a correr com
    `Controlo remoto ativo em 0.0.0.0:8765` — ou seja, **a correção do UFW
    funcionou e o ecrã Remote chegou a ligar**. A entrada das 14:50 ficou
    desatualizada quanto ao resultado.
  - `mobile/airmouse-mobile/logs/expo-dev2.log` → `Android Bundled 40041ms
    index.ts (1162 modules)` — o telefone carregou o bundle do Metro.
  - Após o reinício: nada a escutar em 8081 nem 8765 (servidores perdidos).
- **Causa raiz restante (encontrada agora):** o UFW tinha **só** a porta 8081
  aberta. A 8765 (controlo remoto) continuava bloqueada — o `ufw allow 8765/tcp`
  que a entrada das 14:50 sugeria nunca chegou a ser corrido.
- **Alterações:**
  - `sudo ufw allow 8765/tcp comment 'Maouse remote control'` → regra 3 (v4)
    e 6 (v6). Estado final: 3000, 8081, 8765 todas ALLOW.
  - `HISTORICO.md` — esta entrada.
  - Nenhuma alteração a código neste momento (o código foi apenas commitado).
- **Verificação:**
  - `ufw status numbered` → `8081/tcp ALLOW` + `8765/tcp ALLOW` (v4 e v6)
  - `cd mobile/airmouse-mobile && npx tsc --noEmit` → exit 0
- **Trabalho incluido no commit (nunca registado no histórico):**
  - `AirMouseAccessibilityService.kt` — drag contínuo com a API de
    continuação de strokes (`StrokeDescription willContinue` +
    `continueStroke`), todo o estado do drag confinado à thread main com
    `Handler(Looper.getMainLooper())`. Antes, cada `dragMove` levantava o
    dedo (`dispatchGesture` só corre um gesto de cada vez).
  - `App.tsx` — banner de aviso + botão **ATIVAR** quando o serviço de
    Acessibilidade está desligado; botão de teclado no top bar; filtro de
    movimento mínimo no arrasto (>= 6px) para reduzir backlog de gestos;
    `accessibilityLabel`/`accessibilityRole` nos botões; cores de texto
    corrigidas (`#FFF` -> `#003049` sobre fundo escuro/claro).
  - `src/hooks/useAccessibilityStatus.ts` (novo) — polling de 3s do estado
    do serviço + atalho para as Definições.
  - `SystemControllerModule.kt` — `openAccessibilitySettings()`.
  - `remoteClient.ts` — `rawSend()` para o `auth`: o `sendRaw` antigo
    descartava a mensagem porque `ready` só fica true *depois* do ok do
    servidor, o que produzia um falso "erro de login" no ecrã Remote.
  - `core/licensing_public_key.pem` — chave pública de licenciamento
    atualizada.
  - `.github/workflows/build-android.yml` (novo) — build de APK via GitHub
    Actions (`workflow_dispatch`, perfis `preview`/`development`, artifact).
- **Estado:** OK.
- **Reiniciar a sessão (2 comandos):**
  ```bash
  cd mobile/airmouse-mobile && npx expo start --host lan --port 8081
  python3 main.py     # token a693…, telefone 192.168.0.189, porta 8765
  ```

---

## [2026-09-26 21:57] Gap de produção do license-server — URL deixa de falhar em silêncio

- **Objetivo:** fechar o gap de produção documentado em
  `docs/DESKTOP_LICENSE_URL.md` (descoberto em 2026-09-04): sem um endpoint real
  embebido no build, a ativação de chaves Pro num `.exe` distribuído falha sem
  o utilizador perceber porquê.
- **O que NÃO se pode fazer aqui:** inventar o URL de produção nem o
  `vendor_id` do Paddle. Continuam a precisar de uma conta Render e de uma
  conta Paddle. O que ficou feito é **tornar o placeholder visível** e
  **criar o mecanismo para o URL real entrar no binário**.
- **Problema 1 — o placeholder era silencioso:**
  - `core/licensing.py` ganhou `LICENSE_URL_NOT_CONFIGURED`,
    `license_server_configured()` e `license_server_status()`.
  - `LicenseManager.__init__` faz `log.warning` no arranque quando o endpoint
    é o placeholder → aparece no log em vez de falhar em silêncio.
  - `activate()` recusa com `last_error == "servidor_nao_configurado"` em vez
    de gastar 8 s por endpoint a resolver um domínio inexistente. A UI passou a
    distinguir "chave errada" de "servidor não configurado" (chave de i18n
    `license.server_not_configured`, 7 línguas).
  - `open_checkout()` já não abre `checkout.paddle.com/0?…` no browser do
    utilizador: sem `vendor_id` e sem URL de produto, recusa com aviso. O
    botão "comprar" do Trading Master deixou de ser um no-op silencioso
    (`ui/settings_dlg.py:_buy_trading_master`).
- **Problema 2 — REGRESSÃO encontrada e corrigida:** `activate()` punha
  `_blocked = True` quando a ativação falhava. Uma chave com um typo deixava o
  utilizador **sem poder usar nem o Free**. Agora só regista o motivo em
  `last_error` e não bloqueia. Coberto por
  `test_failed_activation_does_not_block_free`.
- **Problema 3 — a env var não sobrevivia ao build:** num bundle PyInstaller não
  existem env vars de compilação em runtime, portanto
  `AIRMOUSE_LICENSE_SERVER_URL` por si só nunca chegaria ao `.exe`. Solução:
  - `tools/gen_license_endpoint.py` gera `core/_license_endpoint.py` (gitignored)
    a partir da env var ou de um argumento.
  - `core/licensing.py:_baked_endpoint()` lê esse módulo — é agora o passo 3 da
    resolução, acima da constante.
  - `build.bat` chama o gerador no passo **4/7** (passos renumerados).
  - `airmouse.spec` lista `core._license_endpoint` em `hiddenimports` — sem isto
    o módulo não entra no binário, porque o import é feito dentro de uma função
    e a análise estática do PyInstaller não o vê.
- **Problema 4 — não havia `.env`:** nada no repo lia o `.env` para estas vars, e o
  `.env.example` existia sem consumidor para o licensing. Novo `core/envcfg.py`
  (`env_value` / `env_int`, sem dependências) é agora usado por
  `core/licensing.py` e `ui/license_dlg.py`. Ordem: env var > `.env` (cwd, depois
  raiz do projeto). Criado um `.env` local (gitignored) com
  `AIRMOUSE_LICENSE_URLS=http://127.0.0.1:8899` — já não é preciso exportar nada
  no shell a cada arranque.
- **Resolução final do endpoint (fonte única, `core/licensing.py`):**
  1. `AIRMOUSE_LICENSE_URLS` (env) — override, QA/dev, CSV = failover
  2. `.env` do utilizador — mesmo override
  3. `core/_license_endpoint.py` — **URL real embebido no build**
  4. `PROD_LICENSE_SERVER_URL` — constante; tem de ser o URL real
- **Verificação:**
  - `tests/test_license_server_url.py` — 31 testes novos (deteção do
    placeholder, ordem de resolução, embebido vs env, `activate` sem bloquear,
    `open_checkout`, leitor de `.env`, gerador)
  - `pytest tests/ --ignore=tests/test_voice_direct.py` → **257 passed**
  - `tests/test_voice_direct.py` falha por `PortAudio library not found` —
    **pré-existente**, confirmado com `git stash` no baseline; nada a ver com
    estas alterações
  - `ruff check core/ ui/ tests/ tools/ main.py` → All checks passed
  - Fluxo do gerador verificado end-to-end: sem gerar → placeholder detectado;
    com `AIRMOUSE_LICENSE_SERVER_URL=https://exemplo.onrender.com` → cliente
    passa a `license_server_configured() == True`
  - `main.py` reiniciado com o código novo → `License: PRO`, remoto em 8765
    (PID 839909), **sem** o warning de placeholder
- **Alterações:** `core/licensing.py`, `core/envcfg.py` (novo),
  `ui/license_dlg.py`, `ui/settings_dlg.py`, `i18n.py`, `build.bat`,
  `airmouse.spec`, `tools/gen_license_endpoint.py` (novo),
  `tests/test_license_server_url.py` (novo), `.gitignore`, `.env.example`,
  `docs/DESKTOP_LICENSE_URL.md`, `license-server/DEPLOY_RENDER.md`.
- **Estado:** Parcial — o mecanismo está pronto e testado, mas **falta o URL real
  e o vendor_id do Paddle**, que só o dono com as contas pode fornecer. Passos
  restantes em `license-server/DEPLOY_RENDER.md` §6 e
  `docs/DESKTOP_LICENSE_URL.md`.
- **BUG em aberto (NÃO corrigido aqui, precisa de decisão):** `revalidate()`
  está a devolver `seq_repetido` permanentemente. Ver entrada seguinte.

---

## [2026-09-26 21:40] BUG: revalidate() preso em "seq_repetido" sem auto-recuperação

- **Sintoma:** com o lease ainda válido, `LicenseManager.revalidate()` devolve
  `False` com `LicenseError: seq_repetido` — e vai devolver sempre.
- **Causa:** o `use_seq` do lease guardado no cliente ficou **um passo atrás** do
  `last_use_seq` que o servidor tem em `machines`:
  ```
  lease do cliente (~/AirMouse/license.json)  use_seq = 1790435341750
  last_use_seq no servidor (license.db)                = 1790435341751
  revalidate calcula new_seq = 1790435341751; servidor exige > 1790435341751 -> rejeita
  ```
- **Como se dessincronizou:** dois processos a partilhar o mesmo
  `~/AirMouse/license.json` sem locking. O `acquire_single_instance()` do
  `main.py` só corre na `main.py:227` — **depois** de `LicenseManager()` (`:209`)
  e das ações de licença (`:215-225`), e não protege ferramentas separadas. O
  `revalidate()` que corri à mão e o `maybe_revalidate()` do `main.py` que já
  estava a correr gravaram o mesmo ficheiro; o último a escrever deixou o
  cliente atrás do servidor.
- **Impacto:** o lease atual é válido até **2026-10-03**, por isso nada quebra
  hoje. Mas nesse dia a renovação falha e o PC volta a Free/bloqueado. **Não há
  caminho de recuperação**: o servidor rejeita, e o cliente não tem a chave
  guardada (`save()` em `core/licensing.py` persiste lease/email/machine_id/
  trial_used/last_nonce/last_use_seq, **não** `key`), logo o utilizador teria de
  voltar a escrever a chave `MAO-…` à mão.
- **Causa de raiz (design):** `seq_repetido` é usado tanto para "replay malicioso"
  como para "cliente que reverteu o estado" — casos diferentes com o mesmo 403,
  e o cliente não tem como distinguir nem recuperar.
- **Correções possíveis (preciso de decisão — uma delas mexe em segredos em disco):**
  1. Servidor: responder a `seq_repetido` de forma distinta (ex.: `409` + código
     `reativar`) para o cliente se poder auto-reparar.
  2. Cliente: persistir a `key` no store para permitir re-ativação sem o
     utilizador digitar nada — **guardar a chave em disco é uma decisão de
     segurança, não minha**.
  3. Cliente: acquiring de ficheiro em `save()`/`load()` para impedir a corrida
     entre processos.
- **Estado:** Em curso — reportado, nada alterado. À espera da decisão do dono.

---

## [2026-09-26 16:10] Licença PRO restaurada — license-server local

- **Objetivo:** o utilizador reportou que o PC estava a pedir para activar o
  plano Pro. Diagnóstico e correção.
- **Diagnóstico (não era pedido de compra — era bloqueio):**
  - `~/AirMouse/license.json` tinha `trial_used: 300/300` → `is_blocked()=True`,
    `block_reason=trial_esgotado`. O trial Free de 5 min já estava gasto.
  - Havia um lease Pro guardado, mas **expirado**: `iat` 2026-09-17 19:06,
    `exp` 2026-09-24 19:06 (TTL de 7 dias, `license-server/security.py:12`).
    Em `_validate_local_lease` (`core/licensing.py:212`) o `exp` faz o
    lease ser rejeitado → o cliente volta a FREE → o trial já gasto bloqueia.
    Toast em `core/engine.py:213`.
  - Ativação online não resolvia: `PROD_LICENSE_SERVER_URL` ainda é o
    placeholder `https://licenses.maouse.example.com`
    (`core/licensing.py:25`) e `PADDLE_VENDOR_ID = 0  # TODO`
    (`ui/license_dlg.py:39`).
- **Chave privada — verificada, NÃO está exposta:**
  `license-server/private.pem` casa com `core/licensing_public_key.pem`
  (comparação DER byte a byte: True). O ficheiro está em `.gitignore:39`
  (`license-server/*.pem`), modo `600` e **não** é rastreado pelo git
  (`git ls-files license-server/` não o lista).
- **Correção — license-server local em `127.0.0.1:8899` (caminho real):**
  ```bash
  cd license-server
  AIRMOUSE_LS_DB=/tmp/maouse-license-dev.db \
  AIRMOUSE_LS_ADMIN_TOKEN=dev-local-239898 \
  AIRMOUSE_LS_ADMIN_SESSION_SECRET=dev-local-secret \
  setsid nohup ../.venv/bin/python -m uvicorn app:app \
    --host 127.0.0.1 --port 8899 > /tmp/maouse-ls.log 2>&1 < /dev/null &
  ```
  - `POST /admin/keys` → chave `MAO-PROC7-FFC1B-57B00-14484-1`
    (guardada em `/tmp/maouse-pro-key.txt`)
  - Ativação com o cliente real e `AIRMOUSE_LICENSE_URLS=http://127.0.0.1:8899`:
    ```bash
    AIRMOUSE_LICENSE_URLS=http://127.0.0.1:8899 \
      .venv/bin/python main.py --activate-key MAO-PROC7-FFC1B-57B00-14484-1
    # -> "Licença Pro ATIVADA com sucesso."
    ```
  - `main.py` foi reiniciado **com** `AIRMOUSE_LICENSE_URLS` para que
    `maybe_revalidate()` (`core/licensing.py:255`) consiga renovar o lease
    em vez de cair no URL placeholder.
- **Verificação:**
  - `tier=pro`, `is_pro=True`, `is_blocked()=False`, `block_reason=''`
  - lease novo expira **2026-10-03 16:10** (7 dias)
  - `revalidate()` → `True`, lease renovado, `use_seq` incrementado
  - `main.py` → `License: PRO`, `Camera 0 ativa`, `Controlo remoto ativo em
    0.0.0.0:8765` (PID 575561)
  - `curl http://127.0.0.1:8899/health` → `{"status":"ok"}`
- **Renovar daqui a ~7 dias** (quando `exp` passar):
  ```bash
  cd /home/fortuna/Desktop/Maouse-main
  AIRMOUSE_LICENSE_URLS=http://127.0.0.1:8899 \
    .venv/bin/python -c "from core.licensing import LicenseManager; m=LicenseManager(); print(m.revalidate())"
  ```
  Se o license-server local não estiver a correr, reemitir uma chave nova em
  `/admin/keys` e reativar com `--activate-key`.
- **Não corrigido (TODO de produção, precisa de decisão):**
  `PROD_LICENSE_SERVER_URL` continua placeholder e o vendor Paddle é `0` —
  a ativação online real não funciona até o servidor estar deployed.
- **Alterações:** `HISTORICO.md` — esta entrada. Nenhuma alteração a código.
- **Estado:** OK — Pro ativo e renovável.

---

## [2026-09-26 15:26] Sessão retomada — Metro + main.py a correr

- **Objetivo:** arrancar os dois serviços que o reinício do PC matou.
- **Armadilha encontrada:** `python3 main.py` com o Python do sistema falha
  com `ModuleNotFoundError: No module named 'cv2'`. O projeto tem venv em
  `.venv/` — tem de ser `.venv/bin/python main.py`.
- **Comandos (ambos em background, `setsid nohup`, sem TTY):**
  ```bash
  cd mobile/airmouse-mobile
  setsid nohup npx expo start --host lan --port 8081 > logs/expo-dev3.log 2>&1 < /dev/null &
  cd ../..
  setsid nohup .venv/bin/python main.py > logs/maouse-run.log 2>&1 < /dev/null &
  ```
  O `main.py` não precisa de stdin (as teclas são lidas por um listener
  global do pynput), por isso corre bem desacoplado do terminal.
- **Verificação:**
  - `ss -tlnp | grep 8081` → `LISTEN *:8081` (PID 500315)
  - `curl http://192.168.0.107:8081/` → `200`
  - `ss -tlnp | grep 8765` → `LISTEN 0.0.0.0:8765` (PID 504056)
  - `/dev/tcp/192.168.0.107/8765` → alcançável (a nova regra do UFW funciona)
  - `logs/maouse-run.log` → `License: FREE`, `Camera 0 ativa`,
    `Controlo remoto ativo em 0.0.0.0:8765 (IPs: 192.168.0.107; token: a693…)`
- **No telefone:** ecrã do dev-client → `http://192.168.0.107:8081`;
  no ecrã Remote do app, host `192.168.0.107`, porta `8765`, token
  `a69352f45ba7efc1` (`settings.json` → `remote_token`).
- **Alterações:** `HISTORICO.md` — esta entrada. Nenhuma alteração a código.
- **Estado:** OK — ambos os serviços a correr.

---

## [2026-09-26 14:04] Ligar o app Mãouse (Expo) ao telefone

- **Objetivo:** o telefone abria o ecrã do dev-client ("Start a local development
  server with: npx expo start") sem servidor de desenvolvimento a correr.
  Arranquei o Metro em modo LAN para o telefone se ligar.
- **Alterações:** nenhuma alteração a código.
  - Servidor arrancado em `mobile/airmouse-mobile` com
    `npx expo start --host lan --port 8081` (background, log em
    `mobile/airmouse-mobile/logs/expo-dev.log`).
  - Servidor a escutar em `*:8081` (PID do processo Node).
  - IP do PC na rede local: `192.168.59.153`.
- **Verificação:**
  - `ss -tlnp | grep 8081` → `LISTEN *:8081`
  - `curl http://127.0.0.1:8081/` → `200`
  - `curl http://192.168.59.153:8081/` → `200` (alcançável pela rede local)
- **Como ligar no telefone:**
  - Tocar em **"http: Connect"** no ecrã do dev-client, ou
   - escrever à mão `http://192.168.0.107:8081`, ou
     (IP correto — ver entrada das 14:10; o 192.168.59.153 estava errado)
  - digitalizar o QR code no terminal.
  - Requisito: telefone e PC no mesmo Wi-Fi.
- **Estado:** OK — a aguardar confirmação do utilizador de que o ecrã do
  app já carregou.
- **Seguinte passo previsto:** depois de o bundle carregar, ligar o ecrã
  "Remote" do app ao servidor do PC (`ws://192.168.0.107:8765`, token em
  `settings.json`) e arrancar o `main.py` no PC.

---

## [2026-09-26 14:10] "Erro de login" no telefone — IP errado + diagnóstico

- **Objetivo:** o utilizador não conseguiu a ligação; reportou "erro de login".
- **Causa 1 (encontrada):** dei o IP errado. O IP real do PC na rede Wi-Fi
  é `192.168.0.107/24` em `wlp13s0` (gateway `192.168.0.1`).
  O `192.168.59.153` que indicrei antes era um endereço obsoleto.
- **Causa 2 (a confirmar):** o telefone ainda não chegou a pedir o bundle.
  O log do Metro (`.expo/dev/logs/start.log`) só tem 2 `metro:bundling:started`,
  ambos de ~13:29 e ~13:30 (sessão anterior) — nenhum pedido nesta sessão.
- **Alterações:** `HISTORICO.md` — corrigido o URL para `192.168.0.107`.
  Código do app inalterado.
- **Verificação:**
  - `ip -4 addr show wlp13s0` → `inet 192.168.0.107/24`
  - `ip route` → `default via 192.168.0.1 dev wlp13s0`
  - `curl http://192.168.0.107:8081/` → `200`
  - servidor ainda a escutar em `*:8081`
- **Instrução corrigida para o telefone:** `http://192.168.0.107:8081`
- **Estado:** Em curso — falta o texto exato do erro no ecrã para distinguir
  entre (a) erro de ligação do dev-client, (b) erro de token/auth do ecrã
  Remote, (c) erro de compra/restauração da licença Pro.
- **Nota:** o ecrã Remote do app dá `auth_required` se o token não bater certo
  com o `remote_token` do PC (`settings.json` → `a69352f45ba7efc1`). O token
  é preenchido manualmente no app, por isso é a causa mais provável de um
  erro com cara de "login".

---

## [2026-09-26 14:50] CAUSA RAIZ encontrada — UFW bloqueia a porta 8081

- **Objetivo:** o telefone dava `Failed to connect to /192.168.0.107:8081`.
- **Diagnóstico:** o telefone **chega** ao PC (ping OK), mas a ligação TCP
  é descartada. Evidência no log do kernel:
  ```
  [UFW BLOCK] IN=wlp13s0 SRC=192.168.0.189 DST=192.168.0.107
              PROTO=TCP SPT=35792 DPT=8081 SYN
  ```
  (repetido às 14:47:32, :33, :35, :39, :47, e 14:48:03, :37)
- **Confirmações:**
  - `/etc/default/ufw` → `DEFAULT_INPUT_POLICY="DROP"`
  - `systemctl is-active ufw` → `active`
  - telefone = `192.168.0.189` (vizinho ARP, `96:00:12:fe:c5:d0`, ping 0% loss)
  - Metro a escutar em `*:8081` (PID 417987) — o servidor está bem
  - manifesto servia corretamente com `192.168.0.107` no `launchAsset.url`
- **Correção necessária (comando para o utilizador, requer sudo):**
  ```bash
  sudo ufw allow 8081/tcp comment 'Mãouse Expo dev server'
  ```
  (adicionar também `sudo ufw allow 8765/tcp` quando o ecrã Remote for usado)
- **Alternativa sem root:** `npx expo start --tunnel` (liga por
  ngrok/túnel, sem abrir portas) ou `adb reverse tcp:8081 tcp:8081` com o
  telefone ligado por USB.
- **Alterações de código:** nenhuma.
- **Estado:** Em curso — à espera de o utilizador correr o comando `ufw`
  e voltar a tentar.

---

## [2026-09-26 14:20] Investigação do "erro de login" no ecrã do dev-client

- **Objetivo:** o erro aparecia no ecrã de arranque do `expo-dev-client`,
  não dentro do app. Investigar o código do launcher para saber o que
  provoca um erro de login nessa fase.
- **Constatação:** o `expo-dev-launcher` 57.0.19 tem um ecrã de login
  (`compose/routes/Profile.kt:124` — *"Log in or create an account to view
  local development servers and more"*). Em algumas versões/estados o
  launcher exige sessão Expo iniciada para **listar servidores de
  desenvolvimento discovery**; sem isso, o botão de descoberta falha.
  O HomeScreen (`compose/screens/HomeScreen.kt:131`) mostra sempre a
  secção `DevelopmentSessionSection` com 3 caminhos:
  1. campo de URL manual (`ServerUrlInput.kt`) — **não exige login**;
  2. "Fetch development servers" — descoberta de rede;
  3. scan de QR code.
- **Caminho sem login:** o campo de URL manual é sempre disponível.
  Se o login é o bloqueio, usar o campo de URL ou o QR code evita o
  problema na totalidade.
- **QR code gerado** para `http://192.168.0.107:8081` (ASCII no terminal,
  via `qrcode` instalado em `/tmp`; sem alterações ao projeto).
- **Reinício do servidor:** o processo anterior foi terminado e o Metro
  arrancou de novo com `setsid` + `nohup` (a sessão de shell anterior
  bloqueava). A escutar em `*:8081` (PID 417987), log em
  `mobile/airmouse-mobile/logs/expo-dev2.log`.
- **Verificação:**
  - `curl http://192.168.0.107:8081/?expo-platform=android` → `200`
  - manifesto servido com `launchAsset.url` correto:
    `http://192.168.0.107:8081/index.ts.bundle?platform=android&dev=true...`
    (o IP certo é propagado no manifesto quando o pedido vem pelo IP LAN —
     confirmado por comparação com `127.0.0.1`, que devolve `127.0.0.1`)
  - `runtimeVersion: exposdk:57.0.0` — compatível com o build instalado
- **Alterações de código:** nenhuma.
- **Estado:** Em curso — instrução dada ao utilizador: usar o campo de URL
  manual com `http://192.168.0.107:8081` (ou o QR code) em vez do botão
  que exige login.
- **Plano B se o campo manual também falhar:** o build instalado no
  telefone é de *development* (tem dev-client). Se for um build EAS
  `preview`/`production`, o ecrã de arranque é esperado e a ligação tem de
  ser feita ao dev server; se o tokenizer divergir, reinstalar com
  `npx expo run:android` (USB) ou `eas build --profile development
  --local`.

---

## [2026-09-26 14:05] Criado este ficheiro de histórico

- **Objetivo:** ficheiro de registo pedidos pelo utilizador, para registar
  tudo o que o agente faz a partir de agora.
- **Alterações:** criado `HISTORICO.md` na raiz do repositório.
- **Verificação:** ficheiro existe na raiz do projeto.
- **Estado:** OK
