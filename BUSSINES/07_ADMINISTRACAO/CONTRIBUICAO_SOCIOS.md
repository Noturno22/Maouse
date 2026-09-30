# Contribuição de Sócio — Fortuna (domínio mobile · remote · Linux · CI)

> Área de **análise de contribuição de sócio-função**. Documento irmão de
> `ESTRUTURA_DA_EMPRESA.md` (§2 e §4 do registo administrativo). Consolida as
> entregas verificáveis de um sócio no seu domínio de responsabilidade e avalia-as
> face ao acordo de sociedade, para servir conversas de cap table e vesting.
> Autor de registo: Luar Studio Angola · Última atualização: **2026-09-30** · Confidencial.

> 🟢 **Actualização de 2026-09-30 — o 🔴 de §4.5 e o 🟡 de §5.3 estão RESOLVIDOS.**
> Verificado no repositório: o `user.email` foi corrigido e há **21 commits de
> 2026-09-29 em `origin/main` com `josefortunafortuna54@gmail.com`** — o sócio é
> agora *atribuível* no GitHub. Os "0 commits" e o "14 dias sem trabalho" que
> este documento registava estavam certos a 2026-09-28 e deixaram de estar. Ver
> §4.5, §5.1, §5.3 e §6.

---

## 1. Ficha do sócio

| Campo | Valor |
|---|---|
| Nome | **Fortuna** — José Fortuna |
| GitHub | `josefortunafortuna54-byte` (colaborador no `Noturno22/Maouse`) |
| Email | `josefortunafortuna54@gmail.com` (GitHub) · git config: **corrigido** 🟢 — os 6 commits de 14–15/set ficaram com o placeholder `teu-email-do-github`, os **21 de 29/set já saem com o email certo** (ver §4.5) |
| Papel | Sócio-função — mobile, remote, Linux, CI |
| Participação | **4% com vesting** (plano, a formalizar em contrato) |
| Capital investido | €0 (sócio-função) |
| Início da colaboração | 2026-09-14 (primeiro commit) |
| Estado | ✅ Ativo |

---

## 2. Método de medição

Só contam como contribuição **artefactos verificáveis** no repositório:

| Fonte | Verificação |
|---|---|
| Commits em `main` | `git log --author="josefortunafortuna54"` |
| Ficheiros entregues/alterados | diff de cada commit |
| Documentação de domínio | `docs/` produzidos para o domínio do sócio |
| Testes/CI | estado do pipeline no momento de cada entrega |

> ⚠️ **Esta tabela mede o repositório, não o GitHub — e as duas coisas voltaram a
> coincidir a 2026-09-30.** Até 28/set o GitHub não atribuía um único commit a este
> sócio, por causa do email `teu-email-do-github` (§4.5). Corrigido: os 21 commits
> de 29/set já são atribuídos. **Os 6 commits antigos de 14–15/set continuam
> invisíveis no GitHub** — e, por §5.1 item 2, não se reescreve o histórico para
> os reatribuir. Onde os dois ainda discordarem, o GitHub é o número que um
> investidor ou um auditor vê.

> **Honestidade metodológica.** As entregas de código são do sócio e verificáveis.
> As **análises/documentos técnicos** do domínio são produzidas pelo **pipeline de
> agentes de IA** da empresa (modelo "empresa nativa de IA", cf.
> `ESTRUTURA_DA_EMPRESA.md` §2) sob **responsabilidade de domínio** do sócio — ou
> seja, o sócio é *accountable* pelo resultado do domínio, não autor de cada linha
> dos documentos. Esta distinção está registada em
> `docs/RECONHECIMENTO_REMOTE.md` (§cabeçalho) e deve ser mantida em qualquer
> apresentação interna ou a investidores.

---

## 3. Registo de entregas verificáveis

Todos os commits de autor `josefortunafortuna54-byte` até 2026-09-28:

| Commit | Data | Entrega | Impacto no domínio remote |
|---|---|---|---|
| `af01a82` | 2026-09-14 | **feat(linux): porting do Maouse para Linux** | 🟢 Habilita o requisito "Linux" do papel do sócio |
| `a9e0892` | 2026-09-14 | merge de `origin/main` em `clean` | 🟡 higiene de base |
| `dfd218b` | 2026-09-14 | **fix(remote): resposta de auth com `cmd`, setas `arrow_*`, `lan_ips` Linux, media sem `media_stop`** | 🟢 **Corrige directamente o protocolo remoto** — a resposta `auth` passa a incluir `cmd` (o cliente exige-o), adiciona os aliases `arrow_*` ao mapa de teclas, torna `lan_ips` funcional em Linux, e remove o media_stop inexistente no pynput 1.8 |
| `3990e69` | 2026-09-14 | **fix(ui): abrir definições sem áudio; import `sounddevice` protegido** | 🟡 robustez do arranque (import lazy) |
| `79cafa2` | 2026-09-15 | **fix(lint): remover `sys` não usado e quebrar linha longa (ruff F401/E501)** | 🟡 CI ficou verde |
| `d9def7d` | 2026-09-15 | **fix(ci): CI headless verde — pynput/tray lazy, libs Qt+Xvfb e teste snap multiplataforma** | 🟢 **Infraestrutura de CI** — torna o pipeline headless e multiplataforma, desbloqueia a automatização da qualidade |

**Totais:** 6 commits (5 substantivos + 1 merge). Domínio mobile: 2 commits no
path `mobile/maouse-mobile/` (os outros 4 são no core/desktop).

---

## 4. Análise da contribuição

### 4.1 O que a contribuição faz pelo produto

1. **`dfd218b` é a intervenção mais relevante no remote.** A resposta de `auth` do
   servidor passou a ter o campo `cmd` — que o `RemoteClient` do telemóvel **exige**
   para confirmar a ligação (`remoteClient.ts:177-205` processa `auth` com `cmd`).
   Sem este fix, o telemóvel nunca completava o handshake contra o servidor
   actualizado. Os aliases `arrow_*` cobrem exactamente o que a UI mobile envia
   (`RemoteScreen.tsx` usa `arrow_up`/`arrow_down`), e `media` passou a funcionar no
   pynput 1.8. **É fixes de protocolo entre dois ecossistemas (TS ↔ Python) que só
   alguém com visão dos dois lados detecta.**
2. **O porting Linux** (`af01a82`) executa o eixo "Linux" do papel do sócio. O
   estado actual do manuseamento de Linux é por confirmar (a injecção pynput via XTest
   não tem verificação automatizada em hardware), mas o suporte declarado existe.
3. **CI headless verde** (`d9def7d`) é a fundação operacional: é o que permite a
   cada PR detectar regressões. Sem ele, o `tests/test_remote.py` que existe nem
   correria de forma fiável.

### 4.2 O que está **por fazer** no domínio (evidência da auditoria)

A auditoria profunda (`docs/RECONHECIMENTO_REMOTE.md` §1.11) identifica **24
limitações**. As atribuíveis ao domínio do sócio:

| Gravidade | Item | Referência |
|---|---|---|
| ~~🔴~~ | ~~`websockets>=13.0` inválido — rebenta instalações limpas da EAS~~ **RETRACTADO**: premissa falsa, ver §4.6 | — |
| 🔴 | Multi-monitor sem origem virtual (cursor encurralado) | `core/mouse_ctl.py:127-143,186-189` |
| 🔴 | Sem TLS + cliente remove `wss://` | `core/remote.py:227-231`, `remoteClient.ts:33-41` |
| 🔴 | Sem rate limit / lockout / allowlist | `core/remote.py:250` |
| 🔴 | Bypass do gate Pro no remote | ausência em `core/remote.py` |
| 🟠 | Zero testes no mobile (sem `test` script, sem jest) | `mobile/maouse-mobile/package.json` |
| ⚪ **Sem impacto** | ~~`pyproject.toml` sem as dependências reais~~ — **premissa errada, e anterior ao sócio**: o projecto não é distribuído por pip, logo o item não era bug. Limpo pelo fundador a 2026-09-28 | `pyproject.toml` (secções mortas removidas) |
| 🟠 | Bypass do toggle de pausa | ausência em `core/remote.py` |
| 🟠 | Sem auto-reconnect / AppState / fila no mobile | `src/services/remoteClient.ts` |
| 🟠 | Condição de corrida no `MouseCtl` partilhado | `main.py:310-313` |

### 4.3 Pontos fortes

- **Conhece os dois lados do protocolo** — os fixes de `dfd218b` exigiam ler o
  TS do telemóvel *e* o Python do desktop. Raro e valioso.
- **Entrega CI que fica verde** — um sócio que deixa o pipeline verde deixa a
  casa arrumada; os restantes ~200 commits do repo dependem disso.
- **Iniciou rapidamente** — 5 commits substantivos nos primeiros 2 dias.

### 4.4 Pontos fracos / risco

- **Volume muito baixo.** 6 commits em 14 dias de colaboração, num domínio com 24
  limitações auditadas, das quais **4 🔴 reais** — e que bloqueiam a
  funcionalidade central em multi-monitor. (O alegado bloqueador de build da EAS
  foi retractado em §4.6: **zero bloqueadores de build**.)
- **A propriedade do mobile é na prática do fundador.** `mobile/maouse-mobile/`
  tem 30 commits do `Noturno22` vs 2 do Fortuna. O domínio "mobile" do papel do
  sócio está, na prática, entregue acima de 90% pelo fundador.
- **Contribuição invisível para o GitHub** — 🔴 ver §4.5. Não é tracking fraco: é
  contributação a **zero** no perfil.
- **Nenhuma contribuição em testes do remote** — o item 🔴 do cap §4.2.

### 4.5 🟢 RESOLVIDO (2026-09-30) — a contribuição já aparece no GitHub

> **O que se registou a 2026-09-28 estava certo na altura e deixou de estar.** O
> email foi corrigido e o sócio é agora atribuível. Evidência verificada no
> repositório, não por impressão:
>
> | Verificação | 2026-09-28 | 2026-09-30 |
> |---|---|---|
> | Commits do sócio em `origin/main` | 6 (todos com email placeholder) | **27** |
> | Commits com `josefortunafortuna54@gmail.com` | **0** | **21** (todos de 29/set) |
> | Commits com `teu-email-do-github` | 6 | 6 (histórico, não se reescreve) |
> | Atribuível no GitHub | ❌ não | 🟢 **sim**, nos 21 commits novos |
>
> Os 6 commits antigos (14–15/set) continuam sem dono no GitHub, por §5.1 item 2.
> O que se recuperou é o **futuro** da atribuição; para o passado, a atribuição
> correcta é a tabela de §3, verificável por qualquer pessoa pelo diff.

Isto não estava no registo e foi o achado mais consequente desta revisão. Verificado
por API, não por impressão:

| Consulta | Resultado |
|---|---|
| `GET /repos/Noturno22/Maouse/contributors` | **1 entrada só: `Noturno22` (198 commits no GitHub).** O Fortuna não consta. |
| `GET .../commits?author=josefortunafortuna54-byte` | **`[]`** — vazio |
| `GET .../commits/d9def7d…` | `"author": null` — o commit existe, mas **sem dono** |

Nota de contagem: o GitHub diz 198 commits para o fundador; o repositório local
tem 205 seus + 6 do Fortuna = 211. A diferença é o delay entre o push e o
recálculo de atribuição do GitHub — os 6 commits do sócio nunca entrarão nessa
conta enquanto o email não for corrigido.

**Causa.** Os commits foram feitos com `user.email = teu-email-do-github`, que não
corresponde a nenhum email verificado da conta `josefortunafortuna54-byte`. O GitHub
associa um commit a uma conta **pelo email**, não pelo `user.name` — e `git config
user.name` está correcto (`josefortunafortuna54-byte`), o que torna a falha
invisível a quem olha o `git log` local.

**Consequência.** Não é "tracking mais fraco", como dizia §5.1 antes desta revisão:
é **contribuição a zero** para fora do projecto. Não aparece no perfil do sócio,
nem no Insights → Contributors, nem em nenhum número que se possa citar numa
conversa de cap table ou num diligence de investidor. A lista que um terceiro
veria é "1 contributor, 198 commits" — o que, pior, atribui ao fundador o
trabalho que o sócio fez.

**Gravidade.** 🔴 — e o custo de corrigir é de minutos, não de semanas. Um
cap table é uma conversa sobre evidência; evidência que não aparece não conta.

**Correcção** (do lado do sócio, precisa da sua máquina): ver §5.1. Nota: os 6
commits já são públicos e não se reescrevem sem `filter-branch`/force-push, que
**não** é recomendado. O que se recupera a partir de agora é o FUTUREIRO da
atribuição; para o passado, a atribuição correcta é a tabela de §3, que é
verificável por qualquer pessoa pelo diff.

### 4.6 ⚪ Retractado: o bloqueador de build da EAS nunca existiu

A versão 1.0 deste documento afirmava, com base na auditoria
`docs/RECONHECIMENTO_REMOTE.md` §1.11, que o domínio do sócio entregava **2 bugs
🔴 que bloqueavam o build da EAS** — um deles `websockets>=13.0` em
`requirements.txt:5`. Fui verificar antes de fazer a alteração, e **a premissa
era falsa em ambos os pontos.**

**Premissa 1 — o floor do `websockets` é inválido.** Falso. O namespace
`websockets.asyncio` foi introduzido na **13.0**, não na 14.0: o changelog
upstream da 13.0 diz *"introduces a new asyncio implementation"*, e a 14.0 foi
apenas o que a tornou default. O ficheiro `websockets/asyncio/server.py` existe
na tag `13.0` do GitHub. O `core/remote.py:223` importa o caminho explícito, que
é justamente a forma que não depende do default. `requirements.txt:5` está
correcto tal como está.

**Premissa 2 — isso "rebenta instalações limpas da EAS".** Falso. A EAS compila o
app React Native com npm. O `mobile/` não referencia `requirements.txt`, `pip`,
`expo-build-hook` nem `buildHook`; o `eas.json` só tem perfis de build, sem hooks;
e o `package.json` do telemóvel não tem dependências Python. Os únicos consumidores
de `requirements.txt` são o `ci.yml:18` e o `setup.bat:12` — ambos do desktop.
A EAS nunca vê este ficheiro.

**Porque isto importa mais do que a correcção técnica.** "Entregou 2 bloqueadores
🔴" é uma afirmação sobre o desempenho de uma pessoa, e estava a assentar numa
inferência nunca verificada: a auditoria tinha confirmado que a *string*
`websockets>=13.0` estava no ficheiro, e saltou daí para "logo este floor está
partido". O `ci.yml` está verde no mesmo commit que tem esse manifesto — já era
evidência suficiente de que a premissa não se aguentava, e não foi lida.

**Estado corrigido.** Bloqueadores de build do domínio: **zero**. As 4 limitações
🔴 que restam (multi-monitor, sem TLS, sem rate limit, bypass do gate Pro) são
reais, mas são **pré-existentes** — foram encontradas pela auditoria, não
introduzidas pelo sócio, e nenhuma delas o impede de entregar trabalho.

**O que fica a dever, e é real** (§5.2): teste de origem virtual + multi-monitor,
testes no mobile, e os gates de pausa/licença. O `pyproject.toml` foi entretanto
limpo pelo fundador — e o resultado foi `⚪ sem impacto`, não um bug corrigido:
o projecto não é distribuído por pip. O que apareceu no caminho, e é 🔴 de
domínio diferente, foi o `cryptography` a faltar aos dois manifestos, com
`main.py:35` a importar `core.licensing` ao nível do módulo — ou seja, o
`setup.bat` instalava uma aplicação que não arrancava. Detalhe em
`RECONHECIMENTO_REMOTE.md` §1.14.2 e §1.14.3.

---

## 5. Recomendações

### 5.1 Higiene imediata (15 minutos)

1. ✅ **FEITO (2026-09-30)** — `user.email` corrigido. Os 21 commits de 29/set já
   saem com `josefortunafortuna54@gmail.com` e são atribuídos no GitHub (§4.5).
   Era a **prioridade máxima** desta lista, porque a contribuição dele era
   **invisível no GitHub** e qualquer leitura externa do repositório atribuía ao
   fundador trabalho que o sócio fez.
   *Resta um cosmeticamente menor:* o `user.name` continua a ser o handle
   `josefortunafortuna54-byte` e não `José Fortuna`. O GitHub associa por **email**,
   por isso a atribuição está garantida — mas o nome legível no commit é o handle.
   Para o limpar:
   ```bash
   git config --global user.name "José Fortuna"
   ```
   Confirmar com `git log -1 --format='%an <%ae>'`.
2. **Não reescrever o histórico.** Os 6 commits são públicos; `filter-branch` ou
   force-push para os reatribuir destrói o histórico partilhado por um ganho
   estético. A atribuição correcta do passado é a tabela de §3.
3. **Esclarecer onde está o trabalho recente** (ver §5.3) — há divergência entre
   o que o sócio refere e o que o repositório e o GitHub mostram.
4. Definir o critério formal de vesting (o que conta para os 4%: commits?
   PRs? marcos?) e registar em `ESTRUTURA_DA_EMPRESA.md`.

### 5.2 Portefólio a cobrar no próximo passo do sócio

Prioridade segundo o plano em `docs/RECONHECIMENTO_REMOTE.md` Parte 3. **Situação
verificada a 2026-09-30** contra os 21 commits de 29/set:

| # | Item | Estado | Evidência |
|---|---|---|---|
| 1 | Teste de origem virtual + correcção do multi-monitor | 🟡 **por entregar** | nenhum commit dedicada; há fixes de *clique a saltar* no remote/desktop (`f77e8d6`, `e16ed49`) mas não o teste de origem virtual |
| 2 | Testes mínimos no mobile | 🔴 **por entregar** | **zero** ficheiros de teste em `mobile/` — 14 ficheiros de app tocados, 0 testes |
| 3 | Gates de pausa e licença no canal remoto | ✅ **entregue** | `license-server/tests/` (2 ficheiros), `test_license_gate`, `test_license_recovery`, `test_license_server_url`, `mobile/.../ProGate.tsx`, e os commits `afc375e` (lease divergente) e `cc31736` (URL de produção) |

> **Leitura honesta.** O item 3 é o mais difícil dos três (é o caminho que o
> utilizador percorre todos os dias) e está feito, com testes. O item 2 é o mais
> visível num diligence: um sócio que responde pelo domínio mobile sem um único
> teste no mobile. Não é trabalho que não se possa entregar — é trabalho que não
> foi entregue.

> ✅ **Feito pelo fundador, não fica a dívida do sócio** (2026-09-28): o
> `cryptography` acrescentado aos dois manifestos (o 🔴 real), `comtypes`
> removido, `tests/test_manifests.py` com 7 testes a comparar os manifestos com
> os imports do código, e o CI a instalar `requirements-linux.txt`. Detalhe em
> `RECONHECIMENTO_REMOTE.md` §1.14.2 e §1.14.3.

> ❌ **Retirado do topo desta lista:** `websockets>=14.0`, que estava classificado
> como bloqueador de build da EAS. A premissa era falsa (§4.6) — não é trabalho
> que se possa cobrar a ninguém.

### 5.3 ✅ Esclarecido (2026-09-30): o trabalho está no `main`

A pergunta feita a 2026-09-28 — *"onde exactamente está o trabalho recente?"* —
tem resposta, e é verificável. **O trabalho está em `origin/main`: 21 commits de
2026-09-29, +11810 −876 em 79 ficheiros.** Não é branch local não partilhada, nem
outro repositório, nem trabalho sem commit. É o mais fácil de auditar que pode
existir.

> A divergência desapareceu porque o email deixou de ser o placeholder: sem ele
> os commits *existiam* mas o GitHub não os atribuía, e uma leitura externa
> concluía que não havia trabalho. A regra de §2 — *"não registar como entrega até
> haver commit verificável"* — manteve-se firme ao longo do caminho, e foi ela que
> obrigou a ir procurar o diff em vez de aceitar a palavra. Os commits apareceram.

Entregas verificadas no `origin/main` (2026-09-29):

| Domínio | Commits |
|---|---|
| mobile | `fix(mobile): o toque ia para outra direção por causa do locationX` · `fix(mobile): a tremedeira no toque saltava o cursor e descartava o clique` · `feat(mobile): drag continuo com strokes, aviso de acessibilidade e auth do remote` |
| remote | `fix(remote): o clique no telefone saltava por causa da ordem e do ganho duplicado` · `fix(desktop): a camara disputava o rato ao telemovel e o clique saltava` |
| discovery | `feat(discovery): anunciar o PC em _maouse._tcp, com o token fora dos TXT` |
| licença | `fix(license): recuperar lease divergente com chave persistente e lock` · `fix(license): URL de producao deixa de falhar em silencio e passa a entrar no build` |
| CI / manifests | `fix(ci): build-android.yml apontava para mobile/airmouse-mobile` · `fix(manifests): requirements-linux.txt nao terminava em newline` · `fix(lint): E501 nas mensagens de licenca do i18n` |
| env / fusão | `refactor(env): unificar prefixo de env vars em MAOUSE_ apos merge (AIRMOUSE_->MAOUSE_)` · `Merge branch 'instrumentacao-corpus-real'` · `Merge branch 'feature/touch'` |

**21 ficheiros de teste** tocados, incluindo `tests/test_remote.py`,
`tests/test_license_server_url.py` e `license-server/tests/test_revalidate.py`.

**O PR #1, merged a 2026-09-28, conta como entrega** — mas contava antes: o que
não contava era o trabalho que ele dizia ter feito e que não aparecia. Agora
aparece.

---

## 6. Estado da partnership

| Indicador | Valor |
|---|---|
| Equity (plano) | 4% com vesting |
| Entregas verificáveis | **27 commits** — 6 de 14–15/set + **21 de 29/set** (+11810 −876, 79 ficheiros) |
| Commits registados pelo **GitHub** em nome do sócio | **21** 🟢 (§4.5) — os 6 antigos continuam sem dono, por decisão de não reescrever o histórico |
| Último commit do sócio | **2026-09-29** (ontem) |
| Trabalho recente declarado, não encontrado no repositório | ✅ **esclarecido** — está no `origin/main` (§5.3) |
| Documentação de domínio | `docs/RECONHECIMENTO_REMOTE.md` (ca. 1110 linhas, 3 partes) |
| Domínio no papel vs. na prática | papel: mobile/remote/Linux/CI · **prática: mobile · remote · CI · licença · discovery** — o desvio do papel era *infra* Windows, e foi por isso que o trabalho real foi ignorado |
| Bloqueadores de build atribuíveis ao domínio | **0** — o alegado foi retractado (§4.6) |
| Limitações 🔴 reais no domínio (4, todas pré-existentes) | multi-monitor · sem TLS · sem rate limit · bypass Pro |
| Testes no mobile | **0** 🔴 — 14 ficheiros de app tocados, nenhum teste (§5.2 item 2) |
| Portefólio §5.2 | 1 de 3 entregue (gates de licença ✅); origem virtual + multi-monitor e testes mobile por entregar |
| Ficheiros de teste tocados (21 commits) | **21** — incluindo `tests/test_remote.py`, `tests/test_license_server_url.py`, `license-server/tests/test_revalidate.py` |
| **Risco operacional aberto** | 🔴 o branch `instrumentacao-corpus-real` **divergiu** de `origin/main`: 12 commits à frente, **21 atrás**. O trabalho dos dois existe e nenhum está no `main`. Ver §7 |

---

## 7. 🔴 Risco operacional: o branch divergiu de `origin/main`

Descoberto a 2026-09-30 ao verificar as entregas do sócio. Não é um problema de
gestão de sócios nem de qualidade do domínio: é o facto de que **nenhum dos dois
trabalhos está no `main`**, e um lançamento feito a partir do `main` hoje não
levaria nenhum deles.

| | commits |
|---|---|
| `instrumentacao-corpus-real` (branch actual) à frente de `origin/main` | **12** |
| `instrumentacao-corpus-real` atrás de `origin/main` | **21** |

Os 21 de trás são as entregas do sócio (§5.3). Os 12 da frente incluem os 3
commits do fundador de 2026-09-30 — `fbff50d` (§1.1 LandmarkFilterBank),
`b5fae4e` (§1.2 `class_conf`) e `e457c8b` (guarda do `HandLock`) — **nenhum dos
três está no `main`**.

**Estado de fusão.** O `origin/main` já contém `54df3c5` "Merge branch
'instrumentacao-corpus-real'" (o sócio fundiu o branch do corpus a 29/set), por
isso o `main` tem o corpus até esse ponto. O que falta é trazer de volta o que o
branch ganhou depois, e o que o branch não tem do `main`.

**Decisão do fundador, não acção automática.** Uma fusão de branches com 12 e 21
commits, em dois blocos de trabalho independentes, pode resolver-se por `merge`,
por `rebase`, ou por reescrita. Cada uma tem custo diferente em risco e é uma
decisão de gestão, não um passo de higiene. Fica registado, não executado.

---

| Versão | Data | O quê mudou | Quem |
|---|---|---|---|
| 1.0 | 2026-09-28 | Criação da área de análise de contribuição; consolidação das entregas verificáveis do sócio-função Fortuna; registo das 24 limitações do domínio remote (auditoria) | Luar Studio Angola |
| 1.1 | 2026-09-28 | **Verificação por API do GitHub**: a contribuição do sócio é **invisível** (0 commits atribuídos, `author: null`, 1 contributor no repo) por causa do email `teu-email-do-github` — nova §4.5, 🔴. Confirmado que **não há trabalho novo desde 15/set** (repo local e GitHub); o PR #1 merged hoje é o commit de duas semanas — nova §5.3, 🟡, com a pergunta directa a fazer | Luar Studio Angola |
| 1.2 | 2026-09-28 | **Retractada a acusação de 2 bloqueadores 🔴 de build** (nova §4.6, ⚪). Verificado antes de alterar: `websockets.asyncio` existe desde a **13.0** (o floor de `requirements.txt:5` está correcto) e a EAS nunca lê `requirements.txt`. Bloqueadores de build: **zero**. Corrigidos §4.2, §4.4, §5.2, §6, e a versão 1.6 de `ESTRUTURA_DA_EMPRESA.md` | Luar Studio Angola |
| 1.3 | 2026-09-28 | Ao verificar o ponto anterior, **encontrado um 🔴 real e mais grave**: `cryptography` faltava a `requirements.txt` e `requirements-linux.txt`, sendo importado por `core/licensing.py` ao nível do módulo — logo o `setup.bat` instalava uma aplicação que não arrancava. Corrigido, com `tests/test_manifests.py` (7 testes) a comparar os manifestos com os imports do código. O `pyproject.toml`, que se supunha estar em causa, deu `⚪ sem impacto`: o projecto não é distribuído por pip | Luar Studio Angola |
| 1.4 | 2026-09-29 | Corrigida a minha própria correcção: ao tentar alinhar o `pyproject.toml` criei uma **segunda** lista de dependências, que é exactamente o mecanismo que escondia o bug do `cryptography`. Secções `[build-system]`/`[project]`/`[tool.setuptools]` apagadas e 5 dos 12 testes cortados por medirem algo que não existe. **Cortar foi a correcção** | Luar Studio Angola |
| 1.5 | 2026-09-30 | **O 🔴 de §4.5 e o 🟡 de §5.3 estão resolvidos** — verificado no repositório: o `user.email` foi corrigido e há **21 commits de 29/set em `origin/main` com `josefortunafortuna54@gmail.com`** (+11810 −876, 79 ficheiros, 21 ficheiros de teste). O sócio passou a ser *atribuível* no GitHub; o "0 contributions" e o "14 dias sem trabalho" eram verdade a 28/set e deixaram de ser. Actualizados §1, §2, §4.5, §5.1, §5.2, §5.3, §6. Corrigida a **contagem do portefólio**: 1 de 3 entregue (gates de licença ✅), **0 testes em `mobile/`** apesar de 14 ficheiros de app tocados, e origem virtual + multi-monitor sem commit — portanto o 🟡 do §5.3 era *onde está o trabalho*, não *se há trabalho*. **Nova §7 🔴**: o branch divergiu de `origin/main` (12 à frente, 21 atrás) e nenhum dos dois trabalhos está no `main` — registado como decisão de gestão, não executado. Apagada a entrada 1.3 duplicada, que contradizia a 1.4 ao dizer que o `pyproject.toml` tinha sido "alinhado" quando foi **removido** | Luar Studio Angola |

---

*Documento de registo — Luar Studio Angola · 2026-09-30 · Confidencial. Fonte interna para
cap table, vesting e avaliação de sócio-função, até formalização legal.*
