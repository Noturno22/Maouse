# Mãouse — Estado do Projeto

> **Continuar daqui mais tarde.** Este ficheiro guarda tudo o que foi decidido e feito, e o que falta.

## Estado atual (2026-09-22) — Sprint 2: produto vendável / 1.ª venda

> Posição no `PLANO_DE_EXECUCAO_90_DIAS.md`: **Sprint 2 (dias 31–60)**. Execução comercial em
> curso; trabalho em aberto nos 3 bloqueadores da `PRONTIDAO_PARA_VENDA.md` (§4).

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
6. **Fortuna** registado como **2.º sócio-função** (4% vesting: mobile/remote/Linux).
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
    *Não é hipotético.* O `wmic` foi descontinuado e já não vem no Windows 11
    recente: `core/fingerprint.py:_wmic` volta `""` para os dois números de
    série. Falta só o acesso ao registo (`MachineGuid`) também falhar — e esse
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

### 🔴 Bloqueadores em aberto (Sprint 2 → 1.ª venda paga)

| # | Bloqueador | Estado |
|---|---|---|
| 0 | **Renomear as 16 variáveis no painel do Render** — `AIRMOUSE_*` → `MAOUSE_*`, **antes do próximo deploy**. O `render.yaml` versionado já está no prefixo novo; as do painel não se renomeiam sozinhas (`sync: false`, e o Render nunca as mostra). Chegam como string vazia: o `mobile/entitle` deixa de validar compras, o admin recusa o login, o SMTP cala-se — sem erro nenhum. Passo a passo em `license-server/DEPLOY_RENDER.md` | 🔴 antes de qualquer deploy |
| 1 | **Assinatura digital do `.exe`** — pipeline pronto; certificado SSL.com **VALIDADO**; falta **enroll/ativação do eSigner** | 🟡 eSigner por ativar |
| 2 | **Store listing mobile (Play Console)** — IAP code ✅; falta prebuild/upload/listing. O package agora é `com.maouse.mobile` e o app **ainda não foi submetido**, portanto o rename não custou nada aqui — mas também não há volta: depois do primeiro upload o package é imutável | 🔴 |
| 3 | **LAB de compatibilidade** — matriz ≥5 dispositivos por categoria    | 🟡 1 🟡 (HP i3-5005U 14.6 fps) |
| 4 | **Corpus de mãos reais** — a instrumentação está pronta (item 19), mas `--record` e `collect_gestures.py` nunca produziram um ficheiro: o tool estava partido. Recolher é ~20 min por gesto e não se repete; a partir de agora cada recolha grava a confiança e a proveniência | 🔴 precisa de mãos reais — **caminho corrigido (itens 21–22), falta gravar** |
| 5 | **`machine_id` degenerado é partilhado entre máquinas** — se nenhuma componente de hardware for lida, o `machine_id` é o sha256 de uma string constante e `core/licensing.py:163` valida a licença por ele: a licença de uma máquina passa a funcionar noutra. Plausível agora, porque o `wmic` já não vem no Windows 11 recente e basta o acesso ao registo falhar. O teste que deveria apanhar isto era `assert comps`, que passa com as três componentes vazias. **Aberto de propósito:** fechar exige que `machine_id()` recuse e que `licensing.py` decida o que fazer sem identidade estável — e essa decisão é do dono do produto (item 22) | 🔴 decisão do dono do produto |

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
    > **A ordem dentro de cada segmento decide se os 20 minutos servem:** premir a
    > tecla **antes** de adoptar a pose. A etiqueta vale a partir do momento da
    > tecla; se adoptares a pose e só depois premires, os primeiros frames ficam
    > com a etiqueta anterior — e esse erro fica gravado para sempre.

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
3. Testes `tools/test_hand_lock.py`: **13/13 PASS** (inclui caso apanhado pelo teste:
   unica mao intrusa respeita a graca antes de assumir).

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
