# Mãouse — Estado do Projeto

> **Continuar daqui mais tarde.** Este ficheiro guarda tudo o que foi decidido e feito, e o que falta.

## Estado atual (2026-09-30) — Sprint 2: produto vendável / 1.ª venda

> Posição no `PLANO_DE_EXECUCAO_90_DIAS.md`: **Sprint 2 (dias 31–60)**. Execução comercial em
> curso; trabalho em aberto nos 3 bloqueadores da `PRONTIDAO_PARA_VENDA.md` (§4).

> ⚠️ **A secção "Feito recentemente" abaixo está congelada em 22/set** e não foi
> reconstruída — ler como histórico, não como estado actual. O que aconteceu depois:
>
> - **29/set** — o sócio-função Fortuna entregou **21 commits** em `origin/main`
>   (mobile, remote, discovery, licença, CI Android) e o `user.email` deixou de ser
>   o placeholder. Ver `BUSSINES/07_ADMINISTRACAO/CONTRIBUICAO_SOCIOS.md`.
> - **30/set** — Onda 1 §1.1 (`LandmarkFilterBank`, `fbff50d`) e §1.2 (`class_conf`,
>   `b5fae4e`) fechadas e com baseline comitado; a guarda do `HandLock` foi
>   corrigida (`e457c8b`). Detalhe em `docs/RECONHECIMENTO_MAOS.md`.
> - **30/set** — 🔴 o branch `instrumentacao-corpus-real` **divergiu** de
>   `origin/main` (12 à frente, 21 atrás). Nenhum dos dois trabalhos está no `main`.
> - **01/out** — 🟢 essa divergência **está resolvida**: merge local `--no-ff`
>   `8a24d0d` (0 atrás, 14 à frente; `origin/main` é ancestral; backup do
>   pré-merge em `backup/pre-merge-76c32a0`). No mesmo dia o mobile ganhou
>   **18 testes Jest** do protocolo remoto, o desktop ganhou **28 testes de
>   contrato** do mesmo protocolo (`tests/test_remote_protocol_contract.py`, que
>   travam a simetria PC↔mobile sem precisar de toolchain TS), e foi corrigido um
>   bug real de lock
>   da licença no Windows (`core/license_store_lock.py` lia o byte do lock antes
>   de o trancar; o segundo processo rebentava com `PermissionError`, deixando
>   o anti-replay por proteger). Publicado no branch e no `origin/main` no dia
>   seguinte.
> - **02/out** — 🟢 os dois achados 🔴/🟠 que o `docs/RECONHECIMENTO_REMOTE.md`
>   dava por abertos no remoto foram **corrigidos e publicados**
>   (`origin/main` em `514335e`). O **achado #2 (multi-monitor sem origem)**: o
>   clamp do rato e o `move_to` do servidor assumiam que o desktop virtual
>   começava em 0, mas o Windows põe a origem negativa quando há um ecrã à
>   esquerda ou acima do principal — metade do desktop ficava fora do clamp e o
>   cursor saltava para o monitor principal (`69b15fe`, 17 testes, 8 deles falham
>   sem a correcção). O **achado #10 (`press`/`release` sem estado de arrasto)**:
>   o `press` não guardava estado e o `left_down` punha `_drag` a `True` sem nada
>   a limpar, pelo que perder a rede a meio de um arrasto deixava o botão
>   premido no PC — o `_combo` já fazia esta limpeza para as teclas
>   (`10b3b5c`, 14 testes, 6 falham sem a correcção). Ficou também
>   hermético o `_ctl()` de `tests/test_move_gesture.py`, que passou a herdar a
>   origem do ecrã real de quem corresse a suite (`51f7012`).
> - **02/out** — 🟡 `npm audit fix` no mobile: saiu o único aviso **alto** com
>   correcção limpa (`brace-expansion`, `1f7553c`). O que resta é dívida
>   upstream sem versão corrigida — a advisory do `node-forge` afecta **todas** as
>   versões, e a "solução" que o npm propõe é um downgrade a `expo@44.0.6`, três
>   majors atrás. Está escrito no `mobile/maouse-mobile/README.md` para ninguém
>   correr `--force` e partir o Expo (`b7efe06`).
> - **02/out** — 🔴 **P0 de licenciamento, encontrado e corrigido** (`5a8a936`): a
>   chave pública embebida no PC (`core/licensing_public_key.pem`) e a privada do
>   license-server (`license-server/private.pem`) **não eram o mesmo par**. Um lease
>   comprado e assinado pelo servidor era rejeitado pelo PC com
>   `InvalidSignatureError`, ou seja, a venda estava impossível e o e2e não o apanhava:
>   cada lado testava contra a sua própria chave. Gerou-se um par novo, a pública
>   passou a ser versionada (`license-server/public.pem`, com excepção no `.gitignore`
>   para não a ignorar) e a privada continuou de fora. O guard está em
>   `tests/test_license_signature_e2e.py` — 5 testes, um dos quais falha exactamente
>   no estado anterior.
> - **02/out** — 🟢 **achado #5 (bypass do gate Pro) corrigido e publicado**
>   (`a590d81`): o `auth` do `RemoteServer` só exigia o token de emparelhamento, que é
>   igual para toda a gente, por isso qualquer telemóvel na mesma rede controlava o
>   rato e o teclado do PC sem comprar. O token foi mantido (é o segredo de
>   emparelhamento) e passou a exigir-se também a **lease** que o license-server emite
>   para o telemóvel: o PC verifica a assinatura ES256 com a chave pública embebida
>   (`core/licensing.py::verify_remote_entitlement`), só aceita os tiers pagos e
>   recusa a ligação com `pro_required`. Deliberadamente **não** amarra ao machine id
>   do desktop, porque o lease mobile é emitido com o `device_id` do telemóvel e
>   exigir o do PC rejeitaria uma compra legítima. 6 testes novos no contrato Python
>   e 3 no Jest. O telemóvel guarda a lease em `AsyncStorage` e recusa ligar sem ela.
> - **Bloqueios que continuam abertos:** os achados #3 (sem TLS), #4 (sem rate
>   limit) e #8 (bypass do toggle de pausa) do mesmo documento. TLS e o URL real do
>   license-server dependem de certificado e de decisão do dono.
> - **O que a assinatura não resolve (registado para não dar falsa confiança):** o
>   verificador do PC checa assinatura, tier e `exp` — e nada mais. O lease traz
>   `revocation_nonce` e `use_seq`, mas o PC não consulta estado de revogação, logo
>   uma lease emitida não pode ser revogada antes de expirar; e sendo um bearer token
>   em `AsyncStorage`, pode ser copiada para outro dispositivo durante a validade.
>   `expo-secure-store` fica pendente, tal como o TLS.
> - **Bloqueio actual da Onda 1:** a §1.5 (ligar o `HandLock`) e a calibração do
>   `min_class_conf` esperam as **mãos reais** (Onda 3 §3.1). Não é um problema
>   de código.

### ✅ Feito recentemente (14–22 set)

1. **`maouse.app` ao vivo** — domínio comprado (Cloudflare, US$14.34/ano) + DNS/HTTPS ativos
   (CNAME → Vercel, 2026-09-22) · landing premium a servir em `https://maouse.app`.
2. **Landing premium** — redesign glow/glass/spotlight, wordmark com logo, contacto +
   painel de progresso público (`/api/progress` com updatedAt + marcos) e admin.
3. **Pipeline de assinatura de código pronto** (`build.bat` + `upload_installer.ps1` +
   `web/scripts/upload.mjs`): assina `.exe`/instalador via **eSigner/thumbprint** e faz
   **upload do instalador para o Vercel Blob** (5be39c1).
4. **Certificado SSL.com IV** — pago (US$129) e **VALIDADO** (ref `co-3c1laihs7ca`);
   ordem aprovada pela SSL.com (2026-09-23, ticket `#133702727`). Falta **ativar o eSigner**
   e desbloquear o enroll para o `.exe` sair assinado (Passo 4 do `SSLCOM_VALIDACAO.md`).
5. **Mobile dev** — `conectar.bat` (firewall Metro/Expo) + `@expo/ngrok` para ligação dev.
6. **Fortuna** registado como **2.º sócio-função** (4% vesting: mobile/remote/Linux/CI).
   **Actualizado a 2026-09-30:** o `user.email` foi corrigido e o sócio passou a ser
   *atribuível* no GitHub — **21 commits de 29/set** em `origin/main`
   (+11810 −876, 79 ficheiros, 21 ficheiros de teste), onde em 28/set a auditoria
   contava "0 contributions" e "14 dias sem trabalho". Entregas em mobile, remote,
   discovery, licença, CI Android e manifests. Do portefólio a cobrar, 1 de 3
    entregue.
🟢 **2026-10-01:** a divergência do branch **foi fundida** (merge `8a24d0d`,
     0 atrás / 14 à frente de `origin/main`), o mobile **ganhou 18 testes** Jest do
     protocolo remoto e o desktop **ganhou 28 testes de contrato** do mesmo
     protocolo (`tests/test_remote_protocol_contract.py`), que travam a simetria
     PC↔mobile sem toolchain TS. A integração é local e **ainda não foi enviada** — o
     `origin/main` remoto continua em `e4da026`.
    Detalhe em `BUSSINES/07_ADMINISTRACAO/CONTRIBUICAO_SOCIOS.md` §4.5–§7.
7. **render.yaml movido para a raiz** (Blueprint do Render) + registo SSL.com/domínio.
   *Nota: foi tentada uma subscrição Pro na landing (€4,99/mês) e **removida por decisão** — modelo restante é only lifetime/família/acesso.*
8. **Design de gestos profissionais Meta Glass/Quest** — especificações detalhadas para 5 novos gestos de produtividade (zoom suave, rotação 3D, menu radial, swipe three fingers, modo anotar) criadas em `.superpawers\specs\2026-09-28-meta-glass-gestos-pro-design.md`.
9. **Plano de implementação de gestos profissionais** — roteiro detalhado por semanas para desenvolvimento, testes e integração dos novos gestos criado em `.superpawers\plans\2026-09-28-implementacao-gestos-meta-glass-pro.md`.
10. **Onda 0 do reconhecimento de mãos — instrumentação e métricas** (`docs/RECONHECIMENTO_MAOS.md`).
    O que estava em falta há mais tempo do que devia: **não havia forma de medir se o
    classificador de gestos melhorava ou piorava.** Tudo era impressão. Agora existe:
    * `--record PATH` grava as landmarks que o tracker produziu **e** o rótulo do gesto
      em cada frame (`core/corpus.py`, `main.py`).
    * `--replay PATH` corre o classificador real sobre o corpus gravado **sem câmara, sem
      rato, sem licença** — corre em qualquer máquina de CI.
    * `tools/eval_recognition.py` dá F1 por gesto, matriz de confusão, cliques fantasma
      por hora e latência de clique.
    * `tests/test_corpus_fixture.py` fixa os números num baseline comitado; mexer num
      limiar passa a reprovar o CI em vez de aparecer no hardware de um utilizador.
    * **Medido** (`main.py --replay tests/fixtures/corpus_regressao_v1.npz`): F1 macro
      **0.8958**, exactidão 0.9310, **0 cliques fantasma** em 3 cliques, latência p50/p95
      0 ms. 11 de 12 gestos perfeitos. O alvo F1 ≥ 0.97 **não é atingido** — e a Onda 1
      existe para isso.
    * **Limite honesto**: o corpus versionado é sintético e determinístico. Trava contra
      *regressão*, não prova *qualidade*. Gravações com mãos reais não são versionadas;
      o corpus real por demografia é a Onda 3.
11. **✅ Defeito da Onda 0 corrigido na Onda 1 §1.3: `SHAKA` (Ctrl+V) acontecia
    como Ctrl+C.** O `thumb_out` media o deslocamento da ponta do polegar contra
    o seu próprio `landmark 3` e exigia `dx > 0.30 × escala` — a falange distal
    mede ~0.28, portanto a condição era **geometricamente impossível** por
    construção. Medido na Onda 0: **8 de 8 `SHAKA` → `PINKY`**.
    **Correcção** (`core/gestures.py`, branch `fix/onda1-shaka`): medir a
    distância da ponta do polegar à **base do indicador (`landmark 5`)**,
    normalizada pela escala (~1.23 para o lado, ~0.85 recolhido, corte em 1.05) —
    a mesma medida do `thumb_out` da Meta.
    **Depois** (mesma fixture): F1 macro **0.8958 → 1.0000**, `SHAKA` F1
    **0.0 → 1.0**, `PINKY` precisão 0.600 → 1.0, **zero confusões**,
    `ACEITE: todos os alvos cumpridos` (min_f1 0.97). Portão em
    `tests/test_corpus_fixture.py::TestShakaIsRecognised` + predicado isolado em
    `tests/test_shaka_thumb_out.py`. Ver `HARDWARE/PROBLEMAS_KNOWN.md` §1.4.
    **Falta**: provar em mãos reais (Onda 3 §3.1) — a fixture é sintética.
12. **O `--replay-gate` passou a valer no CI.** Com a confusão PINKY/SHAKA
    fechada, o alvo `min_f1 = 0.97` passou a ser medível: antes falhava por
    construção, não por qualidade. O step de reconhecimento do `ci.yml` passou a
    correr **com gate** (F1 macro ≥ 0.97, precisão do PINCH ≥ 0.99, 0 cliques
    fantasma/h). O portão contra *regressão* continua a ser
    `tests/test_corpus_fixture.py`, que compara com o baseline commitado — são
    perguntas diferentes e as duas vigiam.
    **Limite honesto**: o gate mede a fixture **sintética**. Trava contra piora de
    medição, não prova qualidade em mãos reais (Onda 3 §3.1).
13. **Um 🔴 de instalação encontrado e corrigido.** O `cryptography` **não
    estava em nenhum manifesto de runtime**, sendo importado por
    `core/licensing.py` e por `main.py:35` ao nível do módulo — logo o
    `setup.bat` instalava uma aplicação que **não arrancava**. Provado por
    resolução limpa (o manifesto antigo resolvia 59 pacotes; `cryptography`
    ausente, nada o traz transitivamente). O CI não o via porque
    `cryptography` chegava pelo manifesto do license-server, por uma porta
    das traseiras: todos desenvolvem e testam num ambiente onde o bug não
    existe. Corrigido, e trancado com `tests/test_manifests.py` (7 testes que
    comparam os manifestos com os imports reais do código, falhando nos dois
    sentidos) + o CI a instalar `requirements-linux.txt`, que ninguém instalava.
    Ver `RECONHECIMENTO_REMOTE.md` §1.14.2.
14. **Um 🔴 de documentação retractado, e uma lição de método.** Três documentos
    afirmavam que `websockets>=13.0` "rebentava o build da EAS". Era falso nos
    dois pontos: o namespace `websockets.asyncio` existe desde a **13.0**, e a EAS
    compila React Native com npm e nunca lê `requirements.txt`. O erro nasceu de
    se confirmar a *string* no ficheiro e assumir a *consequência* — regra que
    ficou escrita: ler a linha não é verificar a consequência. Ver
    `RECONHECIMENTO_REMOTE.md` §1.14.1 e `CONTRIBUICAO_SOCIOS.md` §4.6.

15. **Duas premissas minhas que eram falsas, e o que sobreviveu delas.** O
    `pyproject.toml` não era o problema do manifesto: o projecto **não é
    distribuído por pip** (nada no repositório faz `pip install .`; o produto sai
    por PyInstaller e as dependências vêm do `setup.bat`). Ao
    “corrigi-lo” criei uma **segunda lista de dependências** — que é exactamente o
    mecanismo que escondia o `cryptography`. As secções mortas foram apagadas e
    **5 dos 12 testes cortados**, por medirem algo que não existe. Regra: um teste
    que impõe uma ficção é pior do que nenhum teste, porque faz a config morta
    parecer necessária. Ver `RECONHECIMENTO_REMOTE.md` §1.14.3.

16. **Rename `AirMouse` → `Maouse` feito e commitado (`4c4c43d`, 139 ficheiros).**
    O produto chamava-se AirMouse desde o início; o nome certo estava no README
    enquanto o código, o manifesto, o package Android e as variáveis de ambiente
    diziam outra coisa. Além do rename entraram as **guardas** que faltavam —
    `tests/test_naming.py`, 7 testes que comparam o package Android, o product id
    e o conjunto de variáveis com **o sítio onde cada um é mesmo declarado**
    (servidor, `render.yaml`, `app.json`, Kotlin) e falham nos dois sentidos.
    Não repetem a constante, que é o que fazia `test_mobile_entitle.py` passar
    sempre. A segunda lista de dependências que escondeu o `cryptography` foi
    exactamente um valor que divergia em silêncio — a mesma classe de bug.
    *Verificado*: ruff limpo, **442** testes do cliente, **70** do license-server,
    `--replay-gate` com F1 macro 1.0000, `expo config` a resolver com
    `com.maouse.mobile` nas três chaves. O 1.0000 é o gate sobre o corpus
    **sintético** e não diz nada sobre mãos reais — ver o limite honesto acima,
    item 12; aqui está porque o gate passou, não porque a qualidade esteja
    demonstrada.
    *Duas coisas que o rename **não** toca, de propósito*: a URL do modelo em
    `core/gesture_ai.py` (`airmouse-ai` é um org GitHub de terceiros) e as
    entradas antigas em `IDENTIDADE_VISUAL.md`, que listam o que não se escreve.
    *Sem alias de compatibilidade* — seguro porque ainda não há utilizadores
    para perder (instalador por assinar, listing por criar).

17. **Três coisas que o rename destapou, nenhuma delas óbvia.**
    *O job `mobile` do CI era cego para a config da app.* Corria só
    `npm run typecheck`, que só olha para TypeScript. Medido: com o directório
    do config plugin movido e o `app.json` desatualizado, o `typecheck` dá
    **exit 0** — o prebuild é que rebentaria, no EAS, com a loja à espera.
    Entrou `npx expo config --type public` como passo próprio; com o plugin
    quebrado dá exit 1. É o mesmo buraco do `cryptography`: uma configuração que
    ninguém valida parece viva porque ninguém a exercise.
    *Uma variável definida e vazia não é uma variável ausente.* `os.getenv(nome,
    default)` só usa o `default` quando a variável **não existe**; se existe e
    está vazia devolve `""`. `security.py` abria `""` e rebentava com
    `FileNotFoundError: No such file or directory: ''` — na **primeira
    activação**, porque `/health` é um `return {"status": "ok"}` estático: os
    health checks passavam, a landing servia, e ninguém activava o Pro. É
    exactamente o que o Render entrega se as chaves não forem renomeadas. Agora
    o erro diz qual variável falta; 3 testes, mutation-tested.
    *O nome da tarefa de arranque automático também envelheceu.* "AirMouse
    JARVIS" passou a "Maouse JARVIS", e esse nome não vive no código: vive em
    dois `.bat` que o git trata como texto e que ninguém abre depois de os
    escrever. O `uninstall` apagava só o nome novo — que não existe para quem
    instalou antes — e imprimia *"Arranque automatico removido."* na mesma, e o
    `install` não limpava o legado nenhum. Ficava a tarefa antiga em ONLOGON, e
    o `echo` era a razão de ninguém reparar: já tinha dito que estava resolvido.
    *A consequência que escrevi primeiro era falsa, e corrigi-a antes de a
    deixar:* "a aplicação arranca duas vezes" era conta emocional, não
    medição. Não arranca: `acquire_single_instance()` (`main.py:151`) faz o
    segundo processo sair com código 1 e `log.info("Mãouse ja esta em
    execucao.")`, desde que as duas tarefas apontem para o mesmo `main.py` — que
    é o caso normal. Só haveria dois arranques a sério se a tarefa antiga
    apontasse para outra pasta, e isso exige a versão antiga numa pasta e a nova
    noutra, num produto que ainda não foi entregue a ninguém (item 16: sem alias
    de compatibilidade porque ainda não há utilizadores para perder).
    *O que fica de pé é mais pequeno e mais feio:* duas entradas no Agendador
    de Tarefas, das quais o utilizador não sabe qual tirar, e — se a tarefa
    órfã apontar para uma pasta que já não existe — um arranque que falha em
    silêncio a cada sessão, com `pythonw` e sem janela. É o `echo` de sucesso a
    impedir a reparação.
    Agora os dois scripts conhecem os dois nomes, o `install` limpa antes de
    criar, e o `uninstall` só diz *"removido"* se removeu mesmo alguma coisa.
    *Verificado* nesta máquina, que não tinha tarefa nenhuma: o
    `uninstall_startup.bat` real imprime agora *"Nao havia tarefa de arranque
    automatico com estes nomes."* — a frase antiga diria o contrário.
    `tests/test_startup_task.py`, 5 testes, **mutation-tested** (cada um dos
    dois lados do bug foi reintroduzido à mão e os testes falharam). Total:
    **447** testes do cliente.

18. **Onda 1 §1.4 fechada — e a prescrição partia o enum.** O item era
    "renomear `Gesture.FIST` de `arrastar` para `scroll`", descrito como
    *"mudança puramente textual, zero risco"*. Feito à letra, era um bug.
    *Um `Enum` do Python com dois membros de valor igual não tem dois membros:
    o segundo vira **alias** do primeiro.* Com o `PEACE = "scroll"` que já lá
    estava, `FIST = "scroll"` apaga o **PEACE**: `Gesture.PEACE is Gesture.FIST`,
    o membro some de `list(Gesture)`, `PEACE.name` passa a devolver `"FIST"`, e
    os 7 sítios que comparam `Gesture.PEACE` passam a comparar FIST — o brilho
    de `engine.py:428` incluído. Medido, não suposto, e sem uma única excepção:
    a mesma classe de silêncio do `cryptography` e da variável vazia.
    *E o motivo do item era falso.* Dizia ser "para o overlay deixar de
    mentir"; o overlay nunca mentiu — `core/overlay.py:BADGES` e
    `ui/theme.py:GESTURE_LABELS` já diziam `FIST → "SCROLL"` e
    `PEACE → "DOIS DEDOS"`, e ninguém lê o `value` do enum. A mentira era para
    quem lê o **código**. Por isso mexeu nos **dois** valores: `FIST = "scroll"`,
    `PEACE = "dois dedos"`.
    *O guard que faltava* está em `tests/test_gesture_labels.py` (5 testes):
    unicidade dos valores, `.name` de cada membro, e concordância entre o
    `value` e o rótulo do badge. Escrito com `Gesture.__members__` e **não** com
    a iteração — a primeira versão passava com o bug presente, porque a
    iteração não vê aliases, e foi reescrita depois de isso acontecer. É a
    segunda vez nesta sessão que um teste meu passava com o bug dentro; a regra
    que daqui sai é que um guard que não consegue falhar não é um guard.
    *Verificado*: ruff limpo, **452** testes do cliente, 70 do license-server,
    `--replay-gate` F1 macro 1.0000 e 0 cliques fantasma, mutation-tested (com
    `PEACE = "scroll"`, 4 dos 5 testes falham).

19. **Instrumentação do corpus de mãos reais — e a razão de nunca ter havido
    um corpus de mãos reais.** Quatro commits em `instrumentacao-corpus-real`.
    *O que faltava ao formato v1* eram duas coisas, e as duas custam caro
    quando faltam. **A confiança**: `core/tracker.py` lia
    `handedness[0].category_name` e deitava fora `handedness[0].score`, e um
    corpus gravado sem ela fica sem ela **para sempre** — mãos reais não se
    recolhem duas vezes. **A origem**: "sintético" era uma nota de rodapé em
    três sítios do `PROGRESSO.md`, e o `--replay-gate` anunciava F1 macro 1.0000
    sem dizer de que dados. Agora `meta["source"]` é um dado e o relatório
    imprime-o na segunda linha; por omissão é `"unknown"`, **não** `"synthetic"`
    — "não sei" é o que deixa o gate recusar-se a anunciar qualidade em vez de a
    inventar. `FORMAT_VERSION` = 2, com `conf` (F,2) float32 a `NaN` nos slots
    vazios (nunca `0.0`, que faria um limiar de abstenção descartar tudo sem
    ninguém saber porquê) e `meta` em JSON, nunca pickle. O loader continua a ler
    a v1 — a fixture do CI já existia em v1 — e um v3 continua a ser erro alto.
    `replay()` **não** mudou de forma: há ~20 sítios que o descompactam em 5
    valores e essa forma não é o que se quer mexer; quem precisa da confiança usa
    `replay_with_conf()`.
    *A confiança tem o nome que tem*: é o score da **classificação** da mão
    (esquerda/direita), não a de detecção — a API Python do `HandLandmarker` não
    a expõe, só os limiares `min_*_confidence`, que são um limiar e não uma
    medida. Chamar-lhe "detection confidence" seria um over-claim.
    *E o que apareceu pelo caminho.* `tools/collect_gestures.py` — o tool que
    recolhe mãos reais — **nunca foi executado**: fazia `hands =
    tracker.process(...)` e depois `hands[0]`, que levanta `ValueError`, porque
    o `process()` devolve uma tupla desde o primeiro commit (`3a5c67b`). **É
    provavelmente a razão de o modelo nunca ter visto mãos reais.** A terceira
    tabela divergida do repo, com a mesma classe de silêncio das outras duas.
    E nele: as classes e as teclas eram escritas à mão e já divergiam do seu par
    — o `--record` usa 0-9 + `d`/`c`/`g` e `x` para limpar; este usava 1-9 e
    `c` para limpar. `c` com dois sentidos opostos conforme o `if` que o apanhe,
    e errar a tecla **não dá erro**: grava o gesto errado, que é a forma mais
    cara de errar sobre mãos reais. Passou a importar `LABEL_KEY_CHOICES`.
    *A premessa do plano ("estender o tool às 13 classes") estava errada, e
    verifiquei antes de implementar.* O tool alimenta `train_gesture_ai.py`, não
    o `Corpus`, e o que o treinador lê são as 9 `CLASSES` de `core/gesture_ai.py`.
    Estender rebenta o `load_real` com `ValueError: zip() argument 2 is longer
    than argument 1` (reproduzi antes de afirmar) e, pior, os pesos que o
    produto distribui são um **modelo de 9 classes de um org de terceiros** —
    alterar `N_CLASSES` sem retreinar faz o modelo distribuído mentir. **Decisão
    de retraining, do dono do produto.** O que ficou feito sem a tomar: o tool
    passa a recolher as 12 classes do enum (incluindo `PINKY`, com tecla), as de
    fora do modelo marcadas a amarelo e com aviso no `save`; e o `load_real` falha
    com uma frase que **nomeia a classe** e diz as duas saídas possíveis, em vez
    de um sintoma de zip. `PINKY` era metade da confusão PINKY/SHAKA e **não tinha
    tecla nenhuma** — essa confusão não se resolvia a recolher mais dados,
    porque os dados de um dos lados não se podiam recolher.
    *Verificado*: ruff limpo, **516** testes do cliente, 70 do license-server,
    `--replay-gate` ACEITE com a origem impressa, fixture regenerada com métricas
    idênticas, e 8 mutações testadas (as que não podiam falhar foram reescritas
    até poderem: uma escrevia a lista de classes à mão e passava na igualdade;
    a do `zip` só "morreu" por erro de sintaxe e foi repetida como mutação válida).

20. **A ajuda dizia atalhos que o programa não prime — e ninguém comparava a
    ajuda com o código.** Quarta tabela escrita à mão que divergiu do seu par, e
    a única em que a divergência é visível para quem paga.
    O banner de arranque (`main.py:540-541`, lido em **cada** execução)
    anunciava `fechar/abrir punho x2=Ctrl+D` e `bye bye=Ctrl+E`. O motor prima
    `win+d` (`engine.py:618`) e `win+down` (`:623`). Quem seguisse a instrução
    carregava Ctrl+D — que no Excel duplica a linha e no Explorer não faz nada —
    e a janela não minimizava. **O programa não dá erro nenhum:** funciona, e a
    instrução é que mente. O cliente conclui que o software é que é, e tem
    razão do ponto de vista dele.
    *As outras duas estavam certas*, o que prova que se sabe ler o código para
    conferir o que se escreve: o painel do preview (`core/overlay.py:168-169`) e
    a ajuda da janela PySide em 7 línguas (`i18n.py`, `help.g.wind`/`help.g.min`)
    dizem `Win+D` e `minimizar (Win+↓)`. Só o banner ficou para trás — quase de
    certeza quando alguém mudou o código de `ctrl+d` para `win+d` para o atalho
    passar a funcionar no Windows, e não actualizou a linha de baixo.
    *O guard* (`tests/test_help_truthfulness.py`, 4 testes) compara a ajuda com
    o que o motor realmente prima, **lido do `core/engine.py` por AST** — pela
    mesma razão que o guard anterior: uma lista escrita à mão seria a mesma
    tabela outra vez. Inclui um teste de que essa lista de atalhos ainda existe,
    porque `Alt+Tab` e `Alt+Shift+Tab` não passam por `_keyboard_shortcut` (vão
    por `Key.tab`/`Key.shift_l`, em `core/hotkeys.py`) e a guarda tem de cobrir a
    metade do código onde não os vê — cada entrada declarando de onde vem, para
    que ninguém a acrescente por adivinhação.
    *Quatro guardas nasceram erradas nesta guarda*, e vale a pena registá-las
    porque são o erro de sempre: **um guard que não pode falhar não é um
    guard.** (1) Filtrar as strings por nome de variável (`show_help`,
    `log.info`) — um rename deixava a lista vazia e o teste *verde a não
    verificar nada*; trocado por "todas as strings do ficheiro", que é o que a
    AST dá de graça. (2) `\S+` no padrão do atalho agarrava o fecho de
    parênteses: `(Win+↓)` dava `win+)` e `Ctrl+C / Ctrl+V` dava um atalho só.
    (3) O normalizador partia por `+` **e** pelas setas, o que deitava fora a
    própria seta em vez de a converter: `"Win+↓"` dava `["win", "", ""]`. (4) O
    padrão não encadeava modificadores, e `"Alt+Shift+Tab"` era lido
    `"Alt+Shift"` — um atalho que o motor não prime, ou seja, um erro
    inventado. Nenhuma delas era o bug; todas teriam feito desligar o teste
    quem encontrasse a primeira. E o teste do i18n acusou a **tradução
    francesa** de mentir por causa de `Alt+Maj` — o `Maj` do teclado francês. A
    tradução estava certa; a guarda é que não conhecia o teclado alheio.
    *Verificado*: ruff limpo, **568** testes do cliente, `--replay-gate` ACEITE,
    2 mutações testadas (mudar o atalho no motor, e esvaziar a lista de
    atalhos do painel).

21. **Gravar um corpus tinha efeitos colaterais na máquina de quem grava.** O
    `mouse = MouseCtl()` e o `SmoothEmitter` eram construídos e corriam sempre, e
    o recorder é puramente passivo — portanto, durante a recolha, o cursor
    movia-se, cada PINCH clicava a sério no que estivesse por baixo, e cada
    PINKY/SHAKA soltava `Ctrl+C`/`Ctrl+V` **na janela que estivesse em foco**.
    Quem grava ficava a mirar ao que davam os gestos. O comentário em
    `main.py` dizia que o `--record` "nunca toca no rato": era verdade sobre as
    teclas de etiqueta e falso sobre o rato, e foi essa frase que fez o defeito
    passar por característica.
    *Não é um mau hábito do operador, é uma propriedade da ferramenta* — por isso
    que o silêncio é o **predefinido** e `--record-live` é que o desliga.
    `MuteMouse` substitui o rato e **conta** o que engoliu: o fim da sessão
    imprime o que ficou calado, e um `0x0` porque o código está errado não
    provaria nada. O toast continua a falar — é ele que diz ao operador o que
    foi reconhecido, que é a única informação de que precisa para etiquetar.
    *Três garantias*, porque silenciar a saída podia estragar a gravação: a mão do
    cursor é escolhida pela palma filtrada (`_active_hand_index`), não pela
    posição do rato do sistema; o emissor corre igual, porque é a aritmética dos
    acumuladores que fixa o ritmo a que cada frame é processado; e o brilho
    também é mudado, por ser a única saída que corromperia o próprio ficheiro — a
    câmara vê o ecrã, e se a aplicação escurece o ambiente a meio da recolha a
    luz muda sem ninguém mexer em nada.
    `tests/test_mute_output.py`, 13 testes.

22. **Um corpus de mãos reais não conseguia levar o rótulo `SETTLE`** — e sem ele
    o primeiro F1 real sairia mais baixo do que é, por uma razão que não é
    má qualidade do classificador. `LABEL_KEY_CHOICES` não tem SETTLE, e não tem
    porquê: SETTLE não é um gesto e o operador não tem quando o aplicar. Só a
    fixture sintética o produz. O que sobra num corpus real é a verdade
    desconfortável de que a etiqueta muda no instante da tecla e a mão só chega à
    pose uns centimos de segundo depois — e sem uma janela, **todo** início de
    segmento contaria como erro, medindo a velocidade da mão humana em vez da
    qualidade do classificador.
    `settle_frames()` deriva a janela da **mudança de etiqueta**, que é a única
    coisa que um corpus real tem para dizer "aqui começou um segmento": por
    definição, um frame cujo ground truth difere do anterior é um frame de
    transição. Duas decisões que os testes trancam:
    * A janela é um intervalo de **tempo**, não uma contagem de frames. O mesmo
      corpus lido a 14,6 fps (HP i3-5005U) e a 30 fps tem de dar a mesma resposta
      ao mesmo intervalo em ms; uma guarda em frames mediria coisas diferentes em
      máquinas diferentes e o "F1" deixaria de ser comparável entre corpora.
    * A janela é um **diagnóstico ao lado** do F1, nunca a sua substituta. O gate
      avalia sempre `macro_f1`; se fosse o outro caminho, a janela passava a ser
      um parâmetro de afinação do alvo e 0,97 deixaria de valer alguma coisa.
    `--replay-settle-guard-ms`, fechada por omissão: o baseline do CI não se move,
    e há teste a assegurar que `macro_f1` e `passed` são idênticos com e sem
    guarda. *Um caso que o relatório precisou de aprender a dizer*: com uma janela
    maior que um segmento não sobra nada para avaliar, e imprimir `F1 0.0000`
    manda quem lê concluir que o classificador está partido — acontece a justo a
    este corpus, feito de segmentos de 6 frames (~200 ms). A linha diz que não há
    F1, há zero frames, e o F1 principal continua impresso em cima.
    `tests/test_settle_guard.py`, 18 testes.

21. **O ecrã dizia "SEM MÃO" com a mão no enquadramento.** Quinta tabela
    divergida, e a única que chega ao utilizador a cada frame.
    O `BADGES` de `core/overlay.py` tem 11 entradas; o `Gesture` tem 13 membros.
    Faltam **`THUMB_DOWN` e `ROCK`**, e os dois são produzidos:
    `core/gestures.py:248` devolve `THUMB_DOWN` pelo caminho geométrico, `:260`
    devolve `ROCK`, e `:297` deixa a IA confirmá-lo. O `draw_overlay` procurava
    o rótulo com `BADGES.get(hf.gesture, BADGES[Gesture.NONE])`, e para esses
    dois o fallback é o de `NONE`: o overlay desenhava **"SEM MAO"** a
    cinzento, com a mão no enquadramento.
    *O que torna isto pior do que um rótulo em falta é o sítio.* O badge é a
    única resposta que o utilizador tem em tempo real sobre o que o reconhecedor
    achou que ele fez. Se faz o gesto, o classificador concorda, e o ecrã diz
    que não há mão, a conclusão é "isto não funciona" — e repetir o gesto é a
    tentativa cansativa que este projecto existe para tirar. Não há excepção, não
    há log, e ninguém repara sem ter a mão à frente.
    **Não se inventou o rótulo.** A palavra que o utilizador deve ler para estes
    dois é decisão do dono do produto e continua por decidir (o badge do
    `THUMB_DOWN` já foi recusado). O overlay mostra o `name` do enum, a
    cinzento-claro — feio e honesto. Escolher a palavra aqui, dentro de um bug de
    ecrã, era tomá-la sem o dono do produto dar por isso. A cor também não é a
    de nenhum outro estado, porque o esqueleto da mão é desenhado com ela, e dois
    estados que se vêem iguais não são estados que se consiga ler.
    *O guard* (`tests/test_overlay_badge_honesty.py`, 8 testes) percorre
    `Gesture.__members__` e **não** uma lista escrita à mão — pela mesma razão
    que o `test_gesture_labels.py`: a iteração sobre o `Enum` não vê aliases, e
    o `PEACE` apagado em silêncio passou justamente numa verificação feita com
    ela. Os gestos que o motor produz são lidos do `core/gestures.py` por AST,
    com um mínimo que falha se a extracção esvaziar.
    *Duas guardas nasceram erradas aqui também.* Uma contava quantas vezes o
    overlay citava `Gesture.` acima de um limite — contava também o que está
    nos *docstrings*, que é onde a correcção se descreve, e o número não
    significa nada; trocada por uma afirmação de sanidade sobre o que
    interessa. E a outra comparava `cor == COLOR_SEM_ROTULO`, **o módulo
    consigo próprio**: mudar a constante deixava o teste verde, porque importa
    a mesma constante que mudou. Quinta vez nesta série que um guard meu não
    conseguia falhar. Trocada pela propriedade — a cor tem de ser diferente da
    de todos os estados já decididos, incluindo o de "sem mão". As duas
    mutações morrem; a anterior não.
    *Verificado*: ruff limpo, **560** testes do cliente, `--replay-gate` ACEITE,
    3 mutações testadas.

22. **Um teste chamado "nonempty" que não verificava se algum valor tinha
    conteúdo — e estava a proteger a identidade de licenciamento.**
    `tests/test_fingerprint.py` tinha `assert comps`, e `collect_components()`
    devolve sempre um dicionário com três chaves. Passava **com as três
    componentes vazias**.
    `machine_id()` é o sha256 de `"board_uuid=…|disk_serial=…|machine_guid=…"`.
    Com as três vazias, esse sha256 é uma **constante** —
    `751f034653eeaa33…`, o mesmo em todas as máquinas degradadas. E
    `core/licensing.py:163` valida a licença por `machine_id`, ou seja: a
    licença de uma máquina funciona noutra. Num produto pago, isso é receita
    que sai sem dar erro a ninguém.
    *Não é hipotético.* O `wmic` foi removido de vez no Windows 11 24H2+
    (ver o item 24 para a medida): `core/fingerprint.py:_wmic` volta `""` para
    os dois números de série. Falta só o acesso ao registo (`MachineGuid`)
    também falhar — e esse
    `except` era `except Exception: pass`, que não distingue um `PermissionError`
    de um `ImportError`, que são problemas de conserto completamente
    diferentes. Este ficou estreito (`OSError`, `ImportError`) e passa a registar
    a falha em `debug`. Um `except: pass` indistinguível de não ter o bloco
    custa um dia inteiro a um suporte quando a activação falha.
    *O `test_machine_id_deterministic` passa neste estado*, porque `a == b` é
    verdadeiro tanto para uma identidade boa como para uma partilhada. O
    determinismo é a única propriedade garantida, e ela não distingue as duas.
    **Nada na suite apanhava isto.**
    *O que mudou*: `core/fingerprint.py::degenerate()` dá nome à condição (uma
    função, e não uma comparação espalhada — é o nome que permite escrever um
    teste), `machine_id()` deixa de falar em silêncio, e
    `test_a_maquina_tem_pelo_menos_uma_componente_real` falha **de propósito**
    numa máquina sem identidade, com a mensagem a explicar porquê.
    *O buraco fica aberto de propósito.* `test_o_machine_id_degradado_e_partilhado_entre_maquinas`
    fixa a constante para que ela não desapareça em silêncio — mas fechá-lo
    exige que `machine_id()` recuse e que `licensing.py` decida o que fazer sem
    identidade estável, e recusa a activação é decisão do dono do produto, não
    um efeito colateral de um teste. Registado como bloqueador #5.
    *Verificado*: ruff limpo, 2 mutações testadas — degradar a máquina (o
    teste antigo passava, o novo morre) e `degenerate()` a devolver sempre
    `False`.

23. **Varredura `grep Error` — o resto.** Concluída a classe "código escrito e
    nunca exercitado" nos três sítios onde ela aparece: tabelas escritas à mão
    (itens 18, 20, 21), `except` que engole, e código ao topo do módulo.
    *Os `except` que engole* — 18 no código do cliente, **15 sem justificação
    escrita**. Perolhamente legíveis:
    | Sítio | Veredicto |
    |---|---|
    | `main.py:617` `remote.stop()` | correcto — melhor esforço no fecho |
    | `core/gesture_ai.py:148` | correcto — `continue` para o URL seguinte |
    | `core/remote.py` ×4 | correcto — limpeza de rede |
    | `core/tts.py`, `core/media_ctl.py`, `core/voice.py` | periférico, isolado |
    | `config.py:253,365` | correcta a leer, a justificação é que falta |
    | **`core/fingerprint.py:13`** | **corrigido — o item 22** |

    Os que ficaram por justificar são todos de periférico ou de fecho, e
    nenhum está no caminho de um clique. Não foram tocados: mexer neles sem
    caminho é um risco sem recompensa, e vale a mesma regra que o resto — não
    mexer no que não está partido.
    *O código ao topo do módulo* que executa no `import` só existe em
    `tools/test_*.py` e `tools/debug_*.py`, que são *scripts* com
    `if __name__ == "__main__"`, e em `license-server/admin_api.py:56`, que é
    um servidor feito para se executar. Nenhum deles é importado por outro
    módulo, que é o que tornaria a execução no `import` um efeito secundário
    em vez do ponto do ficheiro.
    *Falso alarme que vale registar*: `temp_baseline_ref.py`, na raiz, **não é
    UTF-8** — é UTF-16. O Python lê `.py` como UTF-8, portanto o ficheiro não
    importa, e `ast.parse` nem sequer o abre. Está no `.gitignore`, é rascunho
    de alguém, e não é achado.

24. **A margem do buraco #5, medida em vez de estimada.** Escrevi no
    bloqueador que o buraco abria "basta o acesso ao registo falhar". Isso era
    uma afirmação; agora é uma medição, e é **menos largo do que parecia**.
    O `wmic` foi **removido de vez** no Windows 11 24H2+ — não é um FoD, foi
    reformado e o FoD desaparece em 2026 (Microsoft, "WMIC removal from
    Windows"). Portanto nessas máquinas `_wmic` volta `""` para os dois números de
    série, e a fingerprint fica a **1 componente de 3**:
    | Máquina | Componentes com conteúdo | `degenerate()` |
    |---|---|---|
    | esta (Win 10 22H2, tem `wmic.exe`) | 3 de 3 | não |
    | Win 11 24H2+ | **1 de 3** | não |
    | Win 11 24H2+ **e** registo indisponível | 0 de 3 | **sim** |
    *O que muda:* o `MachineGuid` do registo passou a ser **a única coisa** que
    sustenta a identidade. Confirmado: dois `MachineGuid` diferentes dão
    `machine_id` diferentes, o que é o que se quer — o problema nunca foi a
    força do hash, foi haver uma só fonte.
    *Isto torna o bloqueador menos urgente e mais frágil.* Menos urgente porque
    é preciso o registo falhar, e ele só falha por `PermissionError` ou chave
    corrompida. Mais frágil porque **deixou de haver redundância**: antes havia
    três independentes, e a queda de uma não apoderia nada. Uma política de
    empresa que negue a leitura do registo é plausível, e o `except` estreito do
    item 22 agora diz qual foi a razão.
    *Onde é que isto se decide:* fechar o buraco **não** é uma alteração de
    produto disfarçada de correcção. Faz `machine_id()` recusar, obriga a
    `licensing.py` a decidir o que fazer sem identidade estável, e essa decisão
    (recusar a activação? avisar e continuar com um id derivado do que houver?
    pedir uma confirmação ao utilizador?) muda o que o produto faz a quem paga.
    Fica como bloqueador #5, **com a dimensão agora medida** para a decisão ser
    tomada com números em vez de com um "isto pode ser grave".

25. **O sal de máquina apareceu no `git status` — e não era um ficheiro para
    commitar.** `core/fingerprint.py::_fallback_salt()` gravava `machine_salt.txt`
    em `user_data_dir()`. Esse fallback tinha um pormenor que só apareceu em dev:
    quando o `LOCALAPPDATA` não era gravável, `config.user_data_dir()` devolvia
    **o directório do pacote** (para não cair a usar `Program Files` com permissões
    de admin). Em dev esse diretório é a **raiz do repositório**, logo o sal era
    escrito em `maouse/machine_salt.txt` e aparecia na árvore como um ficheiro não
    rastreado, a um `git add .` de distância de ser comittado (um segredo por
    máquina). Num install portátil também seria partilhado por todos os
    utilizadores, e o sal é o que separa as máquinas — o que teria voltado a
    partilhar a identidade que o buraco #5 acabou de fechar.
    *Correção:* `core/fingerprint.py::_salt_dir()` recusa o diretório do pacote
    (com comparação **sem distinção de maiúsculas** — o bug original foi comparar
    strings cruamente, e `...\DEV\maouse` vs `...\DEV\Maouse` nunca davam iguais
    no Windows). Quando o fallback do `user_data_dir()` aponta para o pacote, não se
    grava nada, `degraded` continua verdadeiro e `machine_identity()` deriva só do
    hostname — honesto, não mentiroso. Acrescentei `machine_salt.txt` ao
    `.gitignore`, limpei o ficheiro que tinha nascido na raiz e acrescentei um teste
    (`test_o_sal_nunca_vai_para_o_directorio_do_pacote`) que força a caixa trocada
    para não deixar o guard adormecer outra vez. 3 mutações confirmam que ele apanha
    o caso (inclusive a comparação sem `normcase`). (`core/fingerprint.py`,
    `tests/test_fingerprint.py`, `.gitignore`)

26. **A gravação dizia a etiqueta uma vez e desaparecia — e a tecla errada é
    permanente.** A ajuda que dei para gravar dependia de duas coisas que não
    se defendem: o operador decorar `d PINKY` / `c SHAKA` / `g ROCK`, e
    apanhar o toast de 1,3 s que confirmava a etiqueta. As duas falhavam em
    silêncio, e o custo não era um ficheiro meio estragado: `x` limpa a
    sessão **inteira**, portanto um engano no minuto 4 obriga a refazer tudo,
    com a mão já cansada e a luz já diferente.
    *O que mudou:* com `--record`, o preview passa a ter uma **faixa
    permanente** com a etiqueta corrente, a tecla que a repete, os frames do
    segmento e do total, e o **fps medido** (`--`, enquanto não há dois
    frames) — e um **rodapé com a tabela de teclas inteira**, sempre visível.
    A barra de `ganho`/`suavidade` dá lugar ao rodapé durante a recolha, e o
    `fps` sobe para a faixa. Se aparecer **duas mãos no ecrã**, a faixa avisa
    em rosa: só a mão do cursor é gravada, e uma tecla só não descreve duas
    mãos. O `h` ganhou as três regras (tecla **antes** da pose, mão única,
    `x` limpa tudo) e desce para `y=140` para não ficar por baixo da faixa.
    *Duas decisões que valem registar:*
    - A tabela de teclas **não é escrita no texto do preview**. Sai de
      `core.corpus.LABEL_KEY_CHOICES` via `ui["record"]["keys"]`, e a quebra
      de linhas mede o texto com `getTextSize` — um `len()` fixo dava uma
      tabela truncada, e `THUMB_D` a meio de uma recolha é pior do que não
      mostrar nada. `tests/test_record_hud.py` fixa a ordem, a integridade e a
      largura em píxeis a 640/800/1280/480.
    - **`_record_hud` não levanta.** Um painel que uma excepção mate no meio
      de uma recolha de minutos acaba a sessão sem ninguém saber porquê — o
      mesmo argumento que `CorpusRecorder.observe` dá para o descasamento de
      `confs`. O que o gravador não sabe lê-se `?` / `--`, nunca um número.
      Foi isto que apareceu: o spy de `tests/test_recorder_provenance.py` só
      implementa `observe`, e o painel deixou-o de fora antes de o segundo
      teste o dizer.
    `tests/test_record_hud.py`, 30 testes. `main.py --replay` sobre a fixture
    continua em **F1 macro 1.0000** e `--replay-gate` continua a sair 0 — o
    painel só existe com `ui["record"]`, que só existe com `--record`.

27. **O portão de regressão não via a IA — e foi medido, não suposto.** O
    `--replay-gate` tem saído verde em todos os commits desta série, e a
    razão pela qual isso não significava nada foi descoberta agora: com
    `--no-ai` a saída é **idêntica linha a linha**. Num corpus sintético as
    regras geométricas resolvem os 193 frames antes de o modelo ser
    consultado, portanto o portão que íamos usar para validar o retreino
    para 13 classes **aceitaria pesos inúteis com o mesmo conforto de
    antes**. A red de segurança de que a decisão 2 dependia não existia.
    *O que mede o modelo, sozinho:*

    | | N | taxa |
    |---|---|---|
    | as 9 classes que o modelo tem | 92 | **1.00** |
    | as 3 que não tem (`PINKY`, `ONE`, `THUMB_DOWN`) | 24 | **0.00** |
    | total | 116 | 0.7931 |

    E o défice não é ruído, é coerente: `PINKY → SHAKA` 12/12, `ONE → ROCK`
    6/8, `THUMB_DOWN → FIST` 4/4. Cada gesto cai na classe mais próxima
    **que existe**. Isto converte a frase "a `PINKY` é metade da confusão
    PINKY/SHAKA", que era uma estimativa, em 12/12 medidos — e diz que o
    estrangulamento é a **lista de classes**, não os pesos. Alargar para 13
    deixa de ser especulação.
    *O que este número não diz:* mede a lista, não a qualidade. Dizer que o
    modelo está "bom" a partir de esqueletos canónicos seria ler uma
    distribuição sintética como se fossem mãos reais. `tests/test_ai_standalone.py`
    fixa essa distinção na docstring **e** em código: se algum dia a fixture
    deixar de ser sintética, o teste falha a dizer que a afirmação tem de ser
    reescrita, e não a deixar passar em silêncio.
    `tests/test_ai_standalone.py`, 3 testes. A regra fixada é só esta: cada
    gesto **que o modelo consegue representar** tem de ser classificado
    certo, e os que não consegue são contados em vez de falhados. Quando o
    retreino trouxer `PINKY`/`ONE`/`THUMB_DOWN` para dentro de `CLASSES`, o
    teste começa a exigir também esses sem ninguém lhe tocar — **fica mais
    forte sozinho**, que é o único sítio onde isso acontece.
    *Prova de que o teste parte* (mutações em cópia temporária, modelo do repo
    intocado): permutar as 9 classes → **parte**; `PINCH ↔ FIST` → **parte**;
    `THUMB_UP ↔ THREE ↔ PEACE` → **parte**; `w3` a zero → **parte**. É
    exactamente o estrago que um retreino introduz em silêncio — o modelo
    carrega, o `shape` bate certo, o `GestureAI` inicializa, o portão dá
    1.0000, e cada gesto real recebe o nome do vizinho. Duas mutações **não**
    partiram, e não deviam: `pesos 100x` não muda o `argmax` por construção,
    e 5% de ruído em esqueletos canónicos também não. Nenhuma das duas é
    defeito de modelo; registo-as para que ninguém as conte como falha.

28. **A caixa de diálogo nova estava invisível — e a causa era código morto,
    não um limiar mal afinado (30 set).** `ui/modern_messagebox.py` foi escrito
    para substituir o `QMessageBox` em todo o diálogo de licença, e a caixa
    ficava a **opacidade 0.0**: não aparecia. Sem excepção, sem log, sem nada —
    só faltava aparecer. A causa está medida: a classe tinha *duas*
    `QPropertyAnimation` na mesma property (`windowOpacity`) dentro de um
    `QParallelAnimationGroup`, e o grupo deixava o valor no `startValue`.
    **Medido: animação solitária 1.0 · grupo com duas 0.0 · grupo com uma 1.0.**
    Havia ainda dois defeitos no caminho de fecho: um `TypeError` (o `finished`
    de uma animação chama o slot sem argumentos, e o `done(self, result)` não
    tinha valor por omissão) e um `event.ignore()` sem event loop, que deixava
    a janela visível para sempre em vez de a fechar.
    *O que ficou*: uma animação só, com pai explícito — a assinatura é
    `QPropertyAnimation(target, propertyName, parent=None)`, o primeiro
    argumento é o *alvo* e não o pai, e sem pai de QObject a animação não
    aparece em `findChildren`, o que impedia sequer de verificar que havia uma
    só. E o `finished` reforça o `1.0`, para a janela ficar visível mesmo que
    a animação seja interrompida a meio. As animações de saída foram
    **removidas** em vez de arranjadas: eram código morto ao serviço de uma
    animação de entrada que não funcionava.
    *Os guards* (`tests/test_modern_messagebox.py`, **15 testes**). O que fixou
    a caixa foi `test_so_ha_uma_animacao`, que diz o *porquê* — o defeito não
    foi um limiar mal afinado, foi uma segunda animação na mesma property — e
    não `test_a_opacidade_chega_a_um`, que só via o sintoma.
    *Um teste-guarda que era ele próprio um defeito:* a espera pela animação
    era um `QTimer` de 400 ms para uma animação de 250 ms. Passava sozinho e
    **falhava na suite completa** (opacidade 0.83), porque 400 ms de relógio
    não chegam quando o event loop está atrasado. Passou a esperar pelo sinal
    `finished`. Um guard não pode depender de o CPU estar livre.
    *Mutações* — **24 tentadas, 20 mortas à primeira**; o resto registado em
    vez de arredondado para cima:
    - as duas animações em paralelo, o `closeEvent` a ignorar, o `done()` a
      voltar a ser override, `show_error` a delegar em `warning`, a mensagem a
      deixar de partir, a cor de erro trocada, rejeitar a reportar `Accepted`, e
      a rede de segurança a repor `0.0` em vez de `1.0` — **todas mortas**.
    - **duas não mediam nada**, e foram reescritas até morrerem. Uma inseria
      `self._fade_in = None` a seguir a `setWindowOpacity(0.0)`, que está
      *dentro* de `_setup_animations()` e por isso era sobrescrita duas linhas
      depois — uma no-op. A outra apagava o `show_warning` do checkout e deixava
      o `if` sem corpo, o que dá `IndentationError` na *recolha*; e um harness
      que só lê linhas `FAILED` conta uma recolha falhada como "ninguém
      morreu". **É a mesma armadilha da mutação do `zip` no item 19.**
    - **uma não pode morrer, e não é defeito**: com a animação a ir de `0.0` a
      `0.0`, a rede de segurança continua ligada e repõe o `1.0` quando ela
      acaba — a janela fica visível na mesma. É a redundância deliberada a
      funcionar, como as duas mutações do item 27 que "não deviam" partir.
    - **uma revelou uma lacuna a sério**: não havia nenhum teste para a chave
      **inválida**, que é o caminho que o utilizador encontra quando paga e a
      chave não cola. Sem aviso, ele carrega outra vez e outra vez sem
      perceber porquê que nada muda. Corrigido, com o tier a continuar FREE e
      o diálogo a não fechar como se fosse sucesso.
    *O diálogo de licença* deixou de usar `QMessageBox`: os testes
    `test_license_dialog_free_ui.py` e `test_license_dialog_pro_ui.py` faziam
    patch de `ld.QMessageBox`, que deixou de existir, o que dava 1 FAILED +
    7 ERROR e deixava a suite pendurada em diálogos modais. Passam a gravar
    as chamadas de `show_*` com um spy comum (`tests/_dialog_spies.py`).
    *Verificado*: `ruff` limpo, **suite completa 654 testes, exit 0**.
    `tools/cmd_hand_debug.txt` — dump gerado por `tools/debug_cmd_hand.py` —
    saiu do rastreio do Git (o `*.log` do `.gitignore` não o apanhava por ser
    `.txt`). E o `LicenseAgency` saiu de `core/licensing.py`: código morto,
    nunca instanciado, que estava a pesar no diff do diálogo.

29. **Onda 1 §1.1 fechada — e os dois bugs que só apareceram porque o portão mede
    (30 set).** `LandmarkFilterBank` (`core/filters.py`) põe um `OneEuroFilter`
    em cada coordenada dos 21 landmarks, dentro do `GestureEngine`, **antes de
    qualquer limiar** — escala, rácio de pinça, curl, SHAKA e palma consomem todos
    a lista filtrada. O `reset()` vem do `GestureEngine.reset()`, que o `HandPool`
    já chamava quando a mão desaparece. Fecha a limitação nº 9.
    *Dois defeitos meus, ambos com sintoma medido e não teórico:*
    - **Base temporal errada.** O filtro media `dt` pelo relógio de parede. Numa
      câmara a 30 fps é um detalhe; num `--replay` que despeja o corpus à
      velocidade do processador, `dt` é de microssegundos, `alpha = 1/(1+tau/dt)`
      tende a zero e o filtro **congela**. F1 macro **1.0000 → 0.2787**, e todas as
      confusões seguiam o gesto anterior (`ROCK→PEACE` 8/8, `SHAKA→PINKY` 8/8) —
      a assinatura de um filtro parado, não de limiares partidos. Corrigido passando
      o timestamp do frame (`ts_ms` no runtime, `t_ms` no replay) até ao filtro.
      **Um filtro cuja saída depende da velocidade da máquina não é um filtro** —
      o mesmo princípio do item 28, uma camada abaixo.
    - **`beta` na escala errada.** `beta` foi herdado de `FilterPair2D`, afinado
      sobre a palma em **pixels**, mas as landmarks chegam normalizadas em [0, 1].
      Um salto de 32 px em 33 ms mede `|edx| = 591.7/s` em pixels e `0.925/s`
      normalizado — logo `beta*|edx|` dava 5.92 Hz ou **0.0092 Hz**, 0.3% de um
      cutoff de 3.0. O One Euro degradava-se num low-pass estático, que é
      precisamente o que ele existe para não ser. Sintoma: a pinça não cruzava o
      Schmitt a tempo, F1 macro **0.9098**. Corrigido escalando `beta` pelas
      dimensões do frame (`_apply_scale`); `width`/`height` são argumentos
      **obrigatórios**, porque um default de 1 voltaria a essa falha em silêncio.
    *Medido depois:* F1 macro **1.0000**, 116/116, **0 cliques fantasma**,
    `ACEITE`, `ruff` limpo, suite **654 → 656 testes**, exit 0. Com
    `min_cutoff = 5.0` (acima do 1.4 da palma, como o plano mandava) a banca
    suaviza **1.93x** em repouso contra os 2.57x da palma e arrasta 4.8 px a
    970 px/s. O `min_cutoff = 3.0` era pior **nos dois** eixos (F1 0.9790,
    latência 66 ms) — menos suavização é mais atraso, não menos.
    *O custo, que é real.* **1 frame (33 ms) de latência no clique da pinça**, o
    atraso de grupo do próprio filtro. A baseline foi re-gerada de `latency_p95_ms`
    0.0 para 33.0 **com aval explícito do dono do produto**. O 0.0 anterior **não
    era um alvo de mundo real**: era um zero sintético, porque no corpus a pinça é
    instantânea e o trigger dispara no primeiro frame qualificado — medir o custo de
    um filtro contra esse zero é medir contra nada. **Não há saída gratuita:** a
    latência só volta a 0 ms **acima de 20 Hz**, onde a suavização cai para 1.14x
    e o filtro deixa de filtrar. O `.npz` ficou **byte-idêntico** (só o JSON muda),
    porque `--force` reescreve os dois e o corpus é a entrada fixa do teste.
    *Limite honesto, e é um defeito da fixture, não do filtro.*
    `tools/make_corpus_fixture.py:265-266` sorteia um **centro novo por frame**
    (`cx = 0.5 ± 0.05`), teletransportando a mão ~49 px/frame mesmo numa pose
    supostamente parada; o jitter que o `NOISE_FRAC = 0.008` queria modelar
    (0.96 px) é ~50x menor e fica enterrado. Verifiquei que **não** é a origem do
    custo de 33 ms (remediado o centro, a latência mantém-se), mas significa que
    a fixture **não avalia comportamento temporal com fidelidade** — registado como
    limitação nº 12, correcção é de scope da Onda 3. Tudo isto continua a ser
    fixture sintética: trava contra *regressão*, não prova qualidade em mãos reais.

30. **Onda 1 §1.2 fechada — e o código morto que parecia uma feature (30 set).**
    O `core/tracker.py` já devolvia `handedness[0].score` como terceiro valor
    desde a Onda 0, e o plumbing estava **inteiro**: `engine.py` → `HandPool` →
    `GestureEngine.update(conf=...)`. E aí ficava. Ninguém lia o `conf`. Quatro
    camadas de transporte para um valor que morria à porta — o pior tipo de
    código, porque à leitura parece implementado e tem testes a passar. A §1.2
    foi menos "implementar uma feature" e mais "perguntar a quem já transportava
    isto para que lado vai, e porquê que não vai a lado nenhum".
    *Os três usos, e sobretudo o que cada um não faz:*
    - **Abstenção** (`too_far or low_conf` → `Gesture.NONE`): uma mão que não
      sabemos de que lado é não mexe no rato.
    - **Gate da IA** (`not (too_far or low_conf)`): um frame de baixa confiança
      é **neutro, nunca confirmador**. Consultar um classificador cujas
      entradas não sabemos de que lado estão não é decidir melhor — é fabricar
      autoridade. E a IA fica com `ai_conf = 0.0`, que é o que ela é: não sabe.
    - **Feedback**: badge `MAO ???`. A roadmap pedia "anel de tracking a
      degradar"; escolhi um badge porque um anel a degradar **desenharia uma
      qualidade que o tracker não mediu**. O badge só diz a única coisa verdadeira
      — que o motor não sabe de que lado a mão está.
    *A invariante que sustenta os três:* `None` e `NaN` são **não medido**, e
    não medido **nunca** abstém. Não é um detalhe — o corpus versionado tem
    **todas** as confianças a `NaN` por desenho (grava-se `NaN` em vez de
    inventar um `0.0`). Bastava um `conf < min` sem guarda e a §1.2 silenciava
    a IA em todas as mãos do portão de regressão, e o portão passava a verde
    **por estar mudo**: o pior estado possível para um teste de regressão,
    porque parece proteger-te e não mede nada. O `test_nan_nao_abste` existe
    exactamente para travar essa regressão.
    *Nome deliberadamente diferente do sugerido.* A roadmap propunha
    `detect_conf`; ficou `class_conf`. `handedness[0].score` é a confiança da
    **classificação** (esta mão é esquerda ou direita), não da **detecção** — o
    `HandLandmarker` do MediaPipe não expõe confiança de detecção na API Python,
    só limiares `min_hand_detection_confidence` / `min_hand_presence_confidence`,
    que são limiares e não medidas. O `tests/test_tracker_confidence.py` já
    escrevia isto antes de o código o fazer; chamei-lhe `detect_conf` seria
    contradizer o nosso próprio teste.
    *Duas armadilhas apanhadas pelo caminho.* O `classify()` da IA devolvia a
    confiança em `conf` — **o mesmo nome** do parâmetro da classificação, dois
    sentidos num só âmbito. Não rebentava (a normalização acontece antes), mas
    qualquer código novo depois daquela linha leria a confiança da IA como se
    fosse a da mão. Renomeado `ml_conf`. E a primeira versão do teste do
    badge passava **por estar a medir o badge errado**: o rect "N MAOS" ocupa
    exactamente (522,10)-(628,40), a mesma caixa do badge novo, porque o
    `x_right` só é empurrado se o novo existir. Um teste que verde por razão
    errada é pior do que um teste que falha.
    Verificado: **16 testes novos** (`tests/test_class_conf_abstention.py`),
    suite 656 → **672**, `ruff` limpo, portão de regressão **ACEITE** com F1
    macro 1.0000, 116/116, 0 cliques fantasma e latência p95 33 ms **inalterada**
    — que é a prova de que a abstenção não se auto-silencia no corpus.
    *Limite honesto, e é o principal.* `min_class_conf = 0.5` **não está
    afinado**: não há número com que o afinar, porque o corpus é sintético e
    não tem confiança de classificação. É uma escolha conservadora, não uma
    medição — o que a afina é o corpus de mãos reais (Onda 3 §3.1). A abstenção
    também não diz *qual* dos lados é o incerto, e um badge é mais fraco do que
    a roadmap pedia. E o `min_class_conf` já tinha estado na `config.py` desde a
    sessão anterior sem ninguém o ler: **config morta**, exactamente a mesma
    doença do `LicenseAgency` no item 28. Só passou a existir quando ganhou
    leitura — e foi isso que a §1.2 me obrigou a verificar.

### 🔴 Bloqueadores em aberto (Sprint 2 → 1.ª venda paga)

| # | Bloqueador | Estado |
|---|---|---|
| 0 | **Renomear as 16 variáveis no painel do Render** — `MAOUSE_*` → `MAOUSE_*`, **antes do próximo deploy**. O `render.yaml` versionado já está no prefixo novo; as do painel não se renomeiam sozinhas (`sync: false`, e o Render nunca as mostra). Chegam como string vazia: o `mobile/entitle` deixa de validar compras, o admin recusa o login, o SMTP cala-se — sem erro nenhum. Passo a passo em `license-server/DEPLOY_RENDER.md` | 🔴 antes de qualquer deploy |
| 1 | **Assinatura digital do `.exe`** — pipeline pronto; certificado SSL.com **VALIDADO**; falta **enroll/ativação do eSigner** | 🟡 eSigner por ativar |
| 2 | **Store listing mobile (Play Console)** — IAP code ✅; falta prebuild/upload/listing. O package agora é `com.maouse.mobile` e o app **ainda não foi submetido**, portanto o rename não custou nada aqui — mas também não há volta: depois do primeiro upload o package é imutável | 🔴 |
| 3 | **LAB de compatibilidade** — matriz ≥5 dispositivos por categoria    | 🟡 1 🟡 (HP i3-5005U 14.6 fps) |
| 4 | **Corpus de mãos reais** — a instrumentação está pronta (item 19), mas `--record` e `collect_gestures.py` nunca produziram um ficheiro: o tool estava partido. Recolher é ~3 min por sessão (uma volta dos 13 gestos é ~60 s); a partir de agora cada recolha grava a confiança e a proveniência. **O modelo foi medido sozinho (item 27): 92/92 nas 9 classes que tem, 0/24 nas 3 que não tem** — o estrangulamento é a lista de classes, e o portão de regressão é cego à IA | 🔴 precisa de mãos reais — **caminho corrigido (itens 21–22 e 25), falta gravar** |
| 5 | **`machine_id` degenerado é partilhado entre máquinas** — se nenhuma componente de hardware for lida, o `machine_id` é o sha256 de uma string constante (`751f034653eeaa33…`), o mesmo em todas as máquinas assim, e `core/licensing.py:163` valida a licença por ele: a licença de uma máquina passa a funcionar noutra. **Margem medida (item 24):** no Windows 11 24H2+ o `wmic` foi removido de vez, por isso **1 das 3 componentes** enche; o buraco só abre se o acesso ao registo ao `MachineGuid` falhar também. A defesa do servidor existe (`license-server/service.py:78` recusa quando `claims["sub"] != f"machine:{machine_id}"`) e é exactamente esse valor partilhado que a anula. **Decisão do dono do produto (item 22): avisar forte, mas funcionar.** `machine_identity()` devolve agora o par `(id, degradado)`; o id sai de um sal local por máquina, o servidor regista a identidade fraca e mostra-a, e o cliente **avisa uma vez por sessão** (`toast.weak_identity`, 7 línguas). Não recusa a activação — trocar receita por uma garantia que ninguém pediu. Detalhe em `72ee9eb`, incluindo o bug em que o sal nascia na raiz do repositório | 🟢 **fechado** |

    > **As duas ferramentas não são o mesmo trabalho**, e o bloqueador tratava-as
    > como se fossem. `tools/eval_recognition.py` — e portanto o `--replay` e o
    > `--replay-gate` — consome um `Corpus` **temporal**: frames com timestamp,
    > frames sem mão e a janela `SETTLE`.
    >
    > | Ferramenta | Formato | O que sai daqui |
    > |---|---|---|
    > | `main.py --record FICHEIRO` | `Corpus` temporal | **F1, cliques fantasma/h, latência em mãos reais.** É esta que fecha o bloqueador. |
    > | `tools/collect_gestures.py` | saco de amostras (`X`/`y`/`classes`/`conf`) | **Dados de treino** do MLP. Nada mais. |
    >
    > `collect_gestures.py` por si só **nunca** responde "como é o reconhecimento
    > em mãos reais": produz material de treino, que `train_gesture_ai.py::load_real`
    > consome. É plausível que o "nunca houve um ficheiro" venha de se ter gravado
    > com a ferramenta errada, ou com a ferramenta certa para a pergunta errada.
    >
    > **A ordem dentro de cada segmento decide se os 3 minutos servem:** premir a
    > tecla **antes** de adoptar a pose. A etiqueta vale a partir do momento da
    > tecla; se adoptares a pose e só depois premires, os primeiros frames ficam
    > com a etiqueta anterior — e esse erro fica gravado para sempre.
    >
    > **Onde se retoma.** O procedimento é `HARDWARE/RECOLHA_CORPUS.md` (o
    > `RECONHECIMENTO_MAOS.md` remete para lá). O preview já diz a etiqueta, a
    > tecla e os frames do segmento, portanto não há nada a decorar nem a
    > adivinhar (item 25). **Primeiro passo é um ensaio de 60 s** para
    > `data\smoke.npz`: serve para provar que a máquina grava, e não é
    > medível. A sessão a sério só leva três minutos. Ao gravar, o passo
    > seguinte é `--replay data\sessao1.npz --replay-settle-guard-ms 300`, e a
    > matriz de confusão lê-se antes de acreditar em qualquer F1.

24. **O `main` estava vermelho antes de este trabalho, e duas das armadilhas
    encontradas são do mesmo feitio: uma lista que ninguém confere porque é a
    única fonte.** Fusão dos 12 commits de `instrumentacao-corpus-real` com
    `--no-ff` e **sem** `--reset-author` — a autoria do `Noturno22` é legítima e
    o `--reset-author` de 2026-08-29 foi para identidades erradas, não para
    apagar autoria de quem escreveu o código. **528 → 664 testes.** Conflito
    único, no import de `core.remote`: o ramo partiu de `c1fcac8`, antes do
    árbitro existir, e a resolução é a **união** (`MouseCtl, MuteMouse` +
    `RemoteArbiter, RemoteServer, lan_ips`). Não é escolha: o bloco que liga o
    `RemoteArbiter` ao estado fundeu limpo e referencia o símbolo, e
    `MuteMouse` é construído em `main.py:442`. `--record` passa a calar o rato,
    o teclado e o brilho, **pelo mesmo objecto por onde o telemóvel entra** —
    que era o certo a fazer.
    *`requirements-linux.txt` não terminava em newline.* O `printf '>>'` do
    costume — a forma natural de acrescentar uma dependência a um manifesto —
    colava-a à última linha e produzia `cryptography>=42dbus-next>=0.2.3`. O
    `read_requirements` parte no `>` e lê `cryptography`: **a dependência nova
    desaparece em silêncio**, o `TestImportsEstaoDeclarados` vê a declaração e
    dá-se por satisfeito, e o `setup.bat` instala um ambiente sem ela. Mesmo
    formato de bug do `cryptography` em falta, pelo mesmo caminho. **Não há
    guarda pelo conteúdo que o apanhe**, porque a linha não fica inválida —
    fica válida e errada. Daí os dois testes novos: newline final (a causa) e
    contagem de operadores de versão antes do marker (o sintoma, com linha e
    conteúdo). Ambos provados contra o estado partido antes de passarem a
    verde.
    *`build-android.yml` nunca funcionou.* Apontava para
    `mobile/airmouse-mobile`, que não existe desde 2026-08-29, e como só corre
    por `workflow_dispatch` nunca deu vermelho: o botão é que não fazia nada.
    O `ci.yml` já usava o caminho certo — a cópia que ficou para trás foi esta.
    E o `eas build:list --limit 1 --status=finished` escolhia "o último build
    acabado" da conta inteira: com outro build a terminar ao mesmo tempo
    descarregava o APK errado e subia-o com o nome do perfil pedido, porque o
    nome do artefacto vem do input. O id passa a ser lido da resposta do
    próprio `eas build --json`, e os dois `head -1` silenciosos dão
    `::error::` — sem isso, `apk_path` vazio fazia o `upload-artifact` subir o
    directório de trabalho inteiro com o nome do APK.
    *Um erro de plano que vale registar.* A ideia era declarar `zeroconf` e
    `dbus-next` nos manifestos numa fase de preparação, e escrever o código
    depois. **`TestSemDependenciasFantasmas` reprova isso** — o que é declarado e
    não importado é resíduo, pela mesma razão pela qual `comtypes` saiu do
    manifesto. As dependências têm de entrar **no mesmo commit que o código que
    as importa**, ou seja, a descoberta e o BLE declaram as suas no próprio dia.
    *Ainda por fazer, e não é meu para decidir:* a numeração desta secção tem
    21, 22 e 23 duas vezes (linhas 291, 315 e 344, 385, 422) — os commits mais
    recentes acrescentaram 21–23 sem renumerar os 21–22 que já lá estavam. Não
    renumerei porque as referências cruzadas não resolvem: a da linha 434
    ("o item 22", `core/fingerprint.py:13`) aponta para a série nova, mas a da
    linha 460 (`machine_id`, decisão do dono do produto) não resolve para
    nenhum dos dois "22" — já estava errada antes. Renumerar seria adivinhar
    a intenção de quem escreveu as entradas.
    *Verificado*: ruff limpo, **668** testes do cliente (1 falha
    ambiental pré-existente: `OSError: PortAudio library not found`, a lib do
    sistema não está instalada), 75 do license-server, `--replay-gate` ACEITE
    com F1 1.000 nos 12 gestos e 0 cliques fantasma, CI verde nos dois jobs
    (`ci` e `mobile`) em `5440bd6`, `3791659` e `15be498`.

25. **O Bluetooth estava a bloquear o telemóvel, e a premissa do BLE estava por
    provar: agora está provada.** O adaptador (`hci0`, Realtek
    `30:F7:72:5F:56:4C`) estava `Soft blocked: yes` e `Powered: no`. Com
    `rfkill unblock bluetooth` + `bluetoothctl power on` fica utilizável, e
    o `bluetoothd` responde. A questão seguinte era se o **PC consegue ser
    peripheral** (servidor GATT) **sem root** — de que depende o plano de
    ligar o telemóvel por Bluetooth. Ninguém tinha provado, e a documentação
    do `bluetooth.conf` só diz que qualquer utilizador pode *enviar* a
    `org.bluez`.
    **Duas armadilhas, e ambas parecem outra coisa.** A primeira
    `RegisterApplication` devolveu `NoReply`, que se lê como "a política de
    segurança bloqueou a resposta" — e quase se foi à frente a mexer no
    `/etc/dbus-1/system.d/bluetooth.conf`. **Não era** isso: o default de
    25 s é curto para a primeira chamada, enquanto o daemon inicializa o GATT.
    Com tempo a shades deu `org.bluez.Error.Failed - No object received`, que
    já é o BlueZ a falar — logo **não há barreira de permissões**, é o
    pedido que estava incompleto.
    A segunda custou mais: com os objectos exportados, o daemon respondeu
    `chrc_create() Failed to obtain service path for characteristic` e
    descartou a característica **e o serviço inteiro** — dois sítios de falha
    para uma causa. A propriedade `Service` é um caminho de objecto (`o`);
    passada como `str` o BlueZ lê `s` e não a encontra. Com
    `Variant("o", ...)` dentro de um `a{sv}` o `dbus-next` embrulha o variant
    duas vezes e o daemon continua cego. A forma certa é o decorador
    `@property` do `dbus_next.service`, que gera a interface
    `org.freedesktop.DBus.Properties` com a assinatura certa — e o
    `ObjectManager` devolve os objectos com as propriedades **vazias**, porque
    o BlueZ as lê por `GetAll`. Nada disto se deduz da documentação; só se
    descobre com o daemon em `-d`, e foi assim que se descobriu.
    *Também:* utilizador normal **não** pode ser dono de um nome no bus de
    sistema (só `root`) — e não precisa. O `RegisterApplication` só quer o
    caminho do objecto, e o BlueZ volta a falar por `:1.NNN`, o nome único da
    ligação. Pedir um nome próprio foi o primeiro erro.
    *Verificado*: `RegisterApplication` aceite como `fortuna`, sem sudo, sob o
    `bluetoothd` normal do systemd (não só em modo debug) — `client_ready_cb()
    GATT application registered`. A aplicação GATT de teste tinha um serviço
    e uma característica `write`+`notify`, e desregistou limpa. O `dbus-next`
    ficou instalado no venv **sem** entrar em nenhum manifesto, porque
    `TestSemDependenciasFantasmas` reprova dependência declarada que o código
    não importa: o `dbus-next` entra no commit que trouxer
    `core/remote_ble.py`, e o `zeroconf` no que trouxer `core/discovery.py`.

### Reserva financeira (Pista A)

Gasto **US$168.34** de **US$222** (cert US$129 + domínio US$14.342 + Play US$25) →
**reserva restante ≈ US$53.66** (usa-se só quando os critérios §3 de
`DIRECIONAMENTO_DOS_FUNDOS.md` dispararem).

### Próximo passo recomendado (do próprio plano §7.4)

Escolher UMA via: **(A)** **ativar o eSigner** no portal SSL.com → configurar CodeSignTool/ESIGNER_* no ambiente → `build.bat` assinado e instalador subido ao Blob; **(B)** prebuild/upload/listing do mobile no Play Console; ou
**(C)** testar desktop com GPU para provar 25+ fps.

## O que é

Projeto novo dentro de `DEV\JARVIS\maouse` — controla o rato do PC com a mão via webcam.
Criado porque o barehands parece amador; este usa técnicas profissionais para precisão:

1. **One Euro Filter** — elimina tremor sem lag perceptível
2. **Gesto de ativação** — mão aberta = modo mover; mão longe/ausente = rato físico normal
3. **Histerese na pinça** — dois limiares (liga aos 0.38, desliga aos 0.55) evitam cliques duplos acidentais
4. **Freeze nos cliques** — cursor congelado ~130 ms durante cliques/transições
5. **Controlo relativo tipo touchpad** (não espelho absoluto) — menos cansativo, mais preciso

## Decisões tomadas

| Ponto | Escolha |
|---|---|
| Stack | Python 3.14 + MediaPipe 1.0.1 + OpenCV + pynput |
| Controlo | Relativo (touchpad) com ganho ajustável (`move_gain`) |
| Gestos | Básico: pinça=clique esq., punho=arrastar, 2 dedos (index+médio)=clique dir. |
| Local | `C:\Users\Luar Studio Angola\Desktop\DEV\JARVIS\maouse` |
| Modelo | `hand_landmarker.task` (MediaPipe Tasks API), download automático na 1ª execução |

### Mapeamento de gestos (implementado em `core/gestures.py`)

- Prioridade de classificação: **punho > pinça > 2 dedos > mão aberta**
- Punho = 4 dedos encolhidos (comparação distância ponta-vs-PIP ao pulso, invariante à rotação)
- Pinça = distância polegar-index normalizada pela escala da mão (invariante à distância)
- Gesto precisa estabilizar **3 frames** antes de mudar de estado
- Mão demasiado longe (`min_hand_scale_px = 55`) → gesto NONE → cursor não mexe
- Perder a mão durante arrasto → **solta o botão automaticamente**

## Ficheiros já criados (CÓDIGO COMPLETO)

```
maouse/
├── config.py            ← TODOS os parâmetros de afinação estão aqui
├── main.py              ← loop tempo real, câmara, overlay, voz/IA/auto-afinação, selftest (--frames N)
├── requirements.txt     ← mediapipe==1.0.1, opencv-python, numpy, pynput, vosk, sounddevice
├── setup.bat            ← instalação única (cria .venv + instala deps)
├── start.bat            ← arranque rápido (passa argumentos ao main.py)
├── README.md
├── PROGRESSO.md
├── core/
│   ├── __init__.py
│   ├── filters.py       ← One Euro Filter + FilterPair2D
│   ├── tracker.py       ← HandLandmarker (VIDEO mode) + download modelo
│   ├── gestures.py      ← máquina de estados de gestos + eventos (híbrido com IA)
│   ├── gesture_ai.py    ← MLP numpy de classificação de gestos
│   ├── voice.py         ← Vosk offline PT + wake word + grammar restrita
│   ├── nlu.py           ← intenções em português + fallback Ollama
│   ├── autotune.py      ← auto-afinação adaptativa de filtros/ganho
│   └── mouse_ctl.py     ← pynput + DPI awareness + limites do ecrã
├── tools/
│   └── train_gesture_ai.py  ← gera dados sintéticos, treina e valida o MLP
└── models/              ← hand_landmarker.task ✓ | gesture_mlp.npz ✓ | vosk-model-small-pt-0.3 ✓
```

## ✅ Estado atual (2026-08-25)

### V3 PROFISSIONAL (implementado e testado)
1. **Movimento profissional**: `core/motion.py` — emissor a 180 Hz com acumulador
   sub-pixel + predição lead (`predict_ms=40`) · aceleração exponencial (`accel_expo=1.7`)
   · mouse_ctl com acumuladores fracionários.
2. **Snap magnético**: `core/snap.py` — UI Automation (4 Hz) deteta clicáveis reais;
   atrai o cursor perto de botões/campos; clique assistido usa o ponto exato do alvo.
   Tecla **m** / voz "ativa/desativa o snap".
3. **Duas mãos**: `core/twohand.py` — HandPool (redundância: troca de mão dominante sem
   salto, reset de filtros) · ClapDetector (palmas → abre/fecha assistente 3D barehands,
   Chrome app-mode; fecha por WM_CLOSE) · MagnifierCtl (2 mãos abertas = Lupa do Windows,
   afastar amplia, juntar reduz, sair = tirar mãos, Win+Esc força).
4. **Voz híbrida**: Vosk só wake word ("jarvis"/"jarbas") + **faster-whisper small int8**
   transcreve comandos naturais (lazy load após 1º wake) + NLU estendida
   (assistente/lupa/snap) + respostas faladas.
5. **TTS neural**: `core/tts.py` — Piper pt_BR-faber-medium (~60 MB descarrega na 1ª vez),
   fallback SAPI5; fila de fala.
6. **Arranque automático**: `install_startup.bat`/`uninstall_startup.bat` (schtasks
   ONLOGON, pythonw --tray) + `core/tray.py` (ícone pystray: pausar/voz/preview/sair)
   + mutex single-instance.
7. **Luz baixa**: `core/light.py` histerese <40/>60 → CLAHE LAB no frame +
   tentativa de exposição da câmara.
8. **Gestos novos integrados**: três dedos = volume (media keys), polegar cima =
   play/pausa; IA retrainada para **7 classes** (100% val sintética); config ganhou
   `volume_deadzone_px`.
9. **Testes**: `tools/test_v3.py` **17/17 PASS**. Selftest com câmara pendente
   (câmara indisponível nesta sessão — correr `start.bat` ao vivo).

### TRAVA DE MAO (intent detection lite, estilo AirTouch)
1. **`core/hand_lock.py`** (`HandLock`) — com 2+ maos em cena segue sempre a mao do
   controlador (a mais proxima do ultimo ponto controlado); intrusos longe desse ponto
   nao roubam o controlo; apos `hand_lost_grace_frames` (10) qualquer mao pode adquirir.
   Com 1 mao: comportamento anterior intacto.
2. Tracker agora com `num_hands=2` (config `num_hands`; flag `--single-hand` reverte).
3. Testes: **13/13 PASS** em `tools/test_hand_lock.py` — anotado aqui desde
   antes, mas este número era aparência de cobertura, não cobertura. Corrigido a
   **2026-09-30**: o ficheiro em `tools/` era um script standalone (asserções ao
   nível do módulo, `sys.exit()` no fim) e com `testpaths = ["tests"]` **nunca
   correu na suite** — o "13/13 PASS" vinha de o correr à mão. E o check que
   alegava cobrir *"unica mao intrusa respeita a graca antes de assumir"* era
   `lock2.select([far], W, H) is None or True` — sempre verdadeiro, e colocado
   depois do ciclo de 12 frames, com a graça já expirada. Era exactamente o caso
   que o ponto 1 acima promete. Agora são 12 testes a sério em
   `tests/test_hand_lock.py`, com a garantia afirmada frame a frame
   (`test_intruso_longe_nao_rouba_durante_a_graca` → dez `None`s seguidos),
   verificados por mutação: gracar ao primeiro frame, raio desligado e aquisição
   pela primeira mão **morrem** todas. O `HandLock` **continua desligado** — isto
   só conserta a guarda, não liga o módulo.

### COLETA DE DADOS REAIS + RETREINO DA IA
4. **`tools/collect_gestures.py`** — janela interativa: teclas 1-5 escolhem gesto
   (OPEN/PINCH/PINCH_MID/FIST/PEACE), gravacao por frames com gate de qualidade,
   z/c/s/Q; modo automatico `--frames N --class X --no-preview` para testes.
   Grava `data/real_landmarks.npz` (X=N×21×3 px, y=classe, conf=confiança da
   classificação, meta=proveniência). **Correção (item 19):** este formato
   nunca chegou a ser escrito, porque o `tracker.process` devolvia uma tupla e o
   tool não a descompactava.
5. **`tools/train_gesture_ai.py`** estendido:
   - `--real <npz>` mistura sintetico+reais; split estratificado 85/15;
     validacao REAL reportada epoca a epoca + matriz de confusao real.
   - Backup automatico do modelo anterior → `models/gesture_mlp_prev.npz`
     (reverter = copiar de volta); aviso se acc real <90%.
   - Parametrizado `--per-class/--epochs/--real-copies/--out`.
   - Corrigidos 2 bugs apanhados no smoke test: `epochs` ignorado (hardcoded 24) e
     copia para core/ sobrescrita quando `--out` temporario (agora so na default).
   - Smoke test `tools/test_retrain_smoke.py`: **6/6 PASS** (pipeline completo com
     "reais" falsos: split, treino, backup, inferencia 5/5).

### EXECUTAVEL (.exe)
6. **`build.bat`** + `maouse.spec` + `requirements-build.txt` (PyInstaller onedir).
   - Paths congelados: `_base_dir()/_abs_path()` em main.py — settings.json e modelos
     junto ao exe (dist\Maouse\models copiado pelo build.bat).
   - NOTA: `matplotlib` e dependencia declarada do mediapipe; o primeiro build falhou
     porque a spec a excluia. Ja nao excluida; nada a instalar a mais.
   - Build OK (~395 MB). Exe congelado testado sem camara: importa mediapipe/vosk,
     carrega IA e modelos ao lado do exe, sai com erro limpo de camara
     (camara indisponivel nesta sessao — validar ao vivo com start.bat).

### ROBUSTEZ DO GESTO MOVER (2026-09-05)

- **Validado ao vivo pelo utilizador**: o gesto mover (mão aberta / 1 dedo) está
  perfeito — latência, precisão e suavidade confirmadas.
- **Cobertura de testes dedicada** (`tests/test_move_gesture.py`, **10/10 PASS**):
  1. `GestureEngine` classifica `OPEN` e `ONE` como gestos de movimento (e `PINCH`
     também; gestos não-movimento ficam de fora) — inclui sintetizador de mão ONE.
  2. `SmoothEmitter` conserva pixels: emitido + residuo do acumulador = empurrado,
     nunca duplica por cima, nunca reverte em negativo; `clear()` descarta pendente.
  3. `MouseCtl.move_by` acumula frações corretamente e clampa ao ecrã virtual.
- Sem alterações de comportamento no motor — apenas suíte de regressão para
  proteger o gesto validado.

### CORRECAO ALT+F4 POR PUNHO (2026-09-05)

- **Bug**: a mao esquerda "instavel" fechava janelas com o punho demasiado
  depressa e confundia-se. Causa: bastava **1 frame** de FIST (gesto commitado)
  para disparar Alt+F4 — um punho **transitório** (pinca de clique que curva os
  dedos, ou a mao do cursor a atravessar a metade esquerda do ecra) fechava a janela.
- **Fix**: `core/twohand.py` ganhou `FistHoldDetector` (hold continuo + cooldown +
  exigencia de soltar entre disparos), usado em `core/engine.py`:
  - `left_hand_fist_close_hold_s = 0.8` — o punho (unica mao, lado esquerdo) tem
    de ficar segurado continuamente antes de fechar a janela.
  - `left_hand_fist_close_cooldown_s = 2.5` — sem disparos em rajada; e preciso
    soltar o punho para re-armar.
- Testes: `tests/test_fist_hold.py` **5/5 PASS** (hold curto nao dispara, hold
  completo dispara 1x, segurar 6s nao fecha em rajadas, interrupcao reinicia,
  re-disparo so apos soltar + cooldown). Suíte completa verde (exceto o teste de
  licenca que depende da maquina, pre-existente).

### REDESIGN AREA DE SUBSCRICAO (2026-09-05)

- **Etapa A concluída** — área de subscrição modernizada para **premium minimalista**
  (design em `.superpawers\specs\2026-09-05-license-dialog-modernize-design.md`,
  plano em `.superpawers\plans\2026-09-05-license-dialog-modernize.md`).
- **Etapa C concluída (fontes embebidas)** — `assets\fonts` com **Inter** (corpo/interface),
  **Space Grotesk** (display/títulos) e **JetBrains Mono** (mono/badges/código),
  TTFs variáveis OFL + licenças. `ui/fonts.py` regista-as via `QFontDatabase`
  (`ensure_fonts()` chamado no `run_gui` do `main.py`); `ui/theme.py` antepõe
  estas famílias às de sistema (fallback `Segoe UI`/`Consolas` mantido) através
  de `_bundle_font_families`; `FONT_*` usam as famílias embebidas; `build.bat`
  copia `assets\fonts` para o pacote (instalador inclui via recursive).
  Tests `tests/test_fonts.py` 4/4.
- **Copy confiante e conciso** (`i18n.py`): hero "PRO", sub "Com o PRO sente-se a
  diferença", secção "Tudo incluído no PRO", CTA "ATIVAR PRO"; campo de chave com
  placeholder (`license.key_hint`). Chaves `has_key`/`activate_key` preservadas.
- **Tema** (`ui/theme.py`): tokens novos `StatusChip`, `HeroChip`, `PlanCard`
  (+`[selected="true"]`), `PlanName/Badge/Price/Extra`, `KeyCaption`, `KeyField`,
  `SettingsButtonSecondary`; fonts com fallback (`'Segoe UI Variable Display','Segoe UI'`,
  `'Cascadia Code','Consolas'`); `ProCta` restaurado (CTA dourado); `breathe_glow`
  mantido (usado pelo menu) mas a área de subscrição deixou de pulsar.
- **UI FREE** (`ui/license_dlg.py`): 620px, chip de estado "FREE · 5 MIN DE TESTE"
  sem pulse, hero + benefícios compactos, grelha 2 colunas de cartões de plano
  (seleção via property + repolish, 84px), CTA único dourado sem animação, chave
  secundária discreta (caption + `KeyField` + ativar).
- **UI PRO ativa**: 560×340 sóbrio, remover licença em `SettingsButtonSecondary`
  (vermelho suave, sem destaque dourado).
- **Testes**: `tests/test_theme.py` 5/5, `tests/test_license_dialog_free_ui.py`
  4/4, `tests/test_license_dialog_pro_ui.py` 3/3 — padrão TDD (RED→GREEN);
  suíte completa verde (exceto falha de ambiente pré-existente da licença ativa).
- Commits: `f73506e` (copy) · `4ab2270` (tokens) · `57d0ae5` (UI FREE + ProCta)
  · `8d1f88a` (UI PRO) · `c6e2b21` (Etapa C: fontes embebidas).

## Estado anterior (2026-08-24)

### Motor de precisão V2 + garantia de qualidade por pipeline de agentes
1. **Implementador sénior** construiu o motor V2:
   - **Palm-center** como ponto de controlo (média lm 0,5,9,13,17) — zero saltos ao clicar/arrastar
   - **Curva de aceleração** smoothstep (1.2→3.0 @ 1400 px/s): preciso devagar, rápido a varrer
   - **Pinça index = botão touchpad** (toque=clique · segurar+mover=arrastar); **pinça médio = clique direito**; paz = **scroll** com acumulador fracionário; punho = drag alternativo
   - **Câmara em thread dedicada (MJPG) + sequenciador** — inferência só sobre frames novos
   - **Anti-glitch "modo rápido confirmado"** — rejeita teletransportes sem travar varrimentos
2. **Verificador independente**: 7 verificações → PASS total (settings corrompido tolerado, acumulador de scroll provado conservativo)
3. **Revisor sénior**: encontrou **1 crítico + 4 importantes** — botão preso se pausa durante drag; corrida na thread da câmara; anti-glitch travava varrimentos rápidos; voz dessincronizava drag; frames duplicados processados
4. **Implementador (TDD)**: 16 testes reproduziram os defeitos (RED), corrigiu os 11 pontos, GREEN 16/16
5. Verificação final própria: `--frames 120 --no-preview` → OK · fps honestos pós-dedup · inferência ~39 ms · 0 glitches

### INTEGRAÇÃO IA COMPLETA (100% local/offline)
1. **IA de gestos** (`core/gesture_ai.py` + `tools/train_gesture_ai.py`)
   - MLP numpy (40→96→48→5 softmax, ~35 KB), treino com 30k mãos sintéticas paramétricas
   - Normalização invariante a rotação/escala; augmentação com ruído até σ=0.05 e outliers
   - Validação: **100% accuracy** sintética; integração testada 5/5 gestos com conf 1.000
   - Híbrido: conf < `ai_confidence_min` (0.72) → fallback para regras geométricas
   - Modelo em `models/gesture_mlp.npz` + cópia em `core/`
2. **Comandos de voz offline** (`core/voice.py`) — Vosk small-pt + sounddevice
   - Wake word "jarvis" com alias "jarbas" (jarvis não está no vocabulário do modelo PT!)
   - Grammar restrita (mais preciso); variantes acentuadas incluídas (rápido/botão...)
   - Janela de escuta de 8 s após wake word; tecla V liga/desliga; `--voice-always` opcional
   - Modelo descarregado automaticamente (~49 MB) na 1ª execução
3. **NLU** (`core/nlu.py`) — parser de intenções PT (regex + difflib fuzzy), 11/11 testes
   - Fallback opcional para Ollama local (localhost:11434, `llama3.2:3b`, timeout 2.5 s) — sem dependências novas (urllib)
4. **Auto-afinação adaptativa** (`core/autotune.py`)
   - Observa tremor (EMA velocidade vs jitter) → ajusta `filter_min_cutoff`/`beta` dentro de limites seguros
   - Trim de ganho ±20% baseado em reversões/twitch; tecla A liga/desliga; persiste ao sair
5. **main.py integrado** — overlay mostra IA conf%, estado da voz, toasts de comandos; flags `--no-ai --no-voice --no-autotune --voice-always`

### Testes executados
- Sintaxe OK em todos os ficheiros novos/editados
- NLU: 11/11 intenções corretas (inclui casos negativos)
- Selftest completo: `main.py --frames 90` → 17.3 fps, inferência 53.5 ms, 0 glitches, IA ativa, voz ativa (mic Realtek detetado)
- Integração gestos: 5/5 classes classificadas com conf 1.000; eventos left_down/left_up OK

### Estado anterior (pré-IA)
- Dependências instaladas no `.venv` (Python 3.14.6): mediapipe 1.0.1, opencv 5.0.0.93, numpy 2.5.2, pynput 1.8.2, vosk, sounddevice 0.5.6
- API MediaPipe 1.0 verificada — `HandLandmarker`, `RunningMode.VIDEO`, `detect_for_video` OK
- Thresholds de confiança baixados para 0.5 (mais tolerante a câmaras de má qualidade)

## Falta fazer

1. **Teste real com o utilizador (v3):** `start.bat` — validar: movimento sedoso + snap
   (aproximar cursor de um botão), palmas → assistente 3D, duas mãos abertas → lupa,
   "Jarvis" + comando natural, voz Piper a responder, ícone na bandeja.
2. **Arranque automático:** correr `install_startup.bat` e reiniciar sessão para confirmar.
3. Coletar dados reais + retreinar IA com 7 gestos: `tools\collect_gestures.py`
   (agora suporta 1-7) → `tools\train_gesture_ai.py --real data\real_landmarks.npz`.
4. Testar o exe ao vivo (reconstruir com build.bat para incluir módulos v3).
5. Opcional: instalar Ollama para linguagem natural completa (fallback do NLU).

## Afinação (tudo em `config.py` + hotkeys em tempo real)

| Parâmetro | Default | Efeito |
|---|---|---|
| `move_gain` | 2.0 | ↑ = cursor mais rápido (teclas `[` `]`) |
| `accel_min_gain` / `accel_max_gain` | 1.2 / 3.0 | curva de aceleração (preciso devagar, rápido a varrer) |
| `accel_ref_speed` | 1400 | velocidade da mão (px/s) que atinge ganho máximo |
| `filter_min_cutoff` / `filter_beta` | presets SUAVE/NORMAL/REACTIVO | suavidade (teclas `,` `.`) |
| `pinch_on_ratio` / `pinch_off_ratio` | 0.38 / 0.55 | sensibilidade das pinças |
| `scroll_gain_factor` | 0.06 | velocidade do scroll |
| `deadzone_px` | 1.0 | mata micro-deriva com a mão parada |
| `min_hand_scale_px` | 55.0 | distância mínima da mão à câmara |
| `click_freeze_ms` | 60 | congela cursor durante cliques (baixo: palm-center não salta) |

`s` grava tudo em `settings.json` (auto-carrega no arranque) · auto-afinação adaptativa também ajusta sozinha.

## Comandos úteis

```powershell
.venv\Scripts\python.exe main.py                  # normal (janela de preview)
.venv\Scripts\python.exe main.py --no-preview     # invisível
.venv\Scripts\python.exe main.py --gain 1.6       # cursor mais lento
.venv\Scripts\python.exe main.py --camera 1       # outra câmara
.venv\Scripts\python.exe main.py --frames 90      # teste rápido
.venv\Scripts\python.exe main.py --no-voice       # sem voz/mic
.venv\Scripts\python.exe main.py --no-ai          # só regras geométricas
.venv\Scripts\python.exe main.py --gpu            # tenta GPU no tracker
```

Na janela de preview: **Q/ESC** sai · **espaço** pausa · **[ ]** ganho · **, .** suavidade · **s** grava · **h** ajuda · **v** voz · **a** IA.
Voz: diz **"jarvis"** (ou "jarbas") + pausa/continua/clica/clique direito/scroll cima/scroll baixo.

até mesmo com pouca qualidade de imagem da camera deve funcionar 
