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
- **Problema 4 —上没有 `.env`:** nada no repo lia o `.env` para estas vars, e o
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
