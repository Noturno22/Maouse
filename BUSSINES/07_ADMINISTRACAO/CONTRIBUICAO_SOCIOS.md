# Contribuição de Sócio — Fortuna (domínio mobile · remote · Linux · CI)

> Área de **análise de contribuição de sócio-função**. Documento irmão de
> `ESTRUTURA_DA_EMPRESA.md` (§2 e §4 do registo administrativo). Consolida as
> entregas verificáveis de um sócio no seu domínio de responsabilidade e avalia-as
> face ao acordo de sociedade, para servir conversas de cap table e vesting.
> Autor de registo: Luar Studio Angola · Última atualização: **2026-09-28** · Confidencial.

---

## 1. Ficha do sócio

| Campo | Valor |
|---|---|
| Nome | **Fortuna** — José Fortuna |
| GitHub | `josefortunafortuna54-byte` (colaborador no `Noturno22/Maouse`) |
| Email | `josefortunafortuna54@gmail.com` (GitHub) · git config actual: **`teu-email-do-github`** 🔴 ver §4.5 e §5.1 |
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

> ⚠️ **Esta tabela mede o repositório, não o GitHub — e as duas coisas já não
> coincidem.** Ver §4.5: o GitHub não atribui um único commit a este sócio. Onde
> os dois discordarem, o GitHub é o número que um investidor ou um auditor vê.

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
path `mobile/airmouse-mobile/` (os outros 4 são no core/desktop).

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
| 🟠 | Zero testes no mobile (sem `test` script, sem jest) | `mobile/airmouse-mobile/package.json` |
| ~~🟠~~ | ~~`pyproject.toml` sem as dependências reais~~ **feito pelo fundador** 2026-09-28 | `pyproject.toml`, `tests/test_manifests.py` |
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
- **A propriedade do mobile é na prática do fundador.** `mobile/airmouse-mobile/`
  tem 30 commits do `Noturno22` vs 2 do Fortuna. O domínio "mobile" do papel do
  sócio está, na prática, entregue acima de 90% pelo fundador.
- **Contribuição invisível para o GitHub** — 🔴 ver §4.5. Não é tracking fraco: é
  contributação a **zero** no perfil.
- **Nenhuma contribuição em testes do remote** — o item 🔴 do cap §4.2.

### 4.5 🔴 A contribuição não aparece no GitHub (verificado 2026-09-28)

Isto não estava no registo e é o achado mais consequente desta revisão. Verificado
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
feito pelo fundador, e no caminho encontrou um 🔴 que é anterior ao sócio e de um
domínio diferente: o `cryptography` faltava aos dois manifestos e
`main.py:35` importa `core.licensing` ao nível do módulo, ou seja, o `setup.bat`
instalava uma aplicação que não arrancava. Detalhe em
`RECONHECIMENTO_REMOTE.md` §1.14.2.

---

## 5. Recomendações

### 5.1 Higiene imediata (15 minutos)

1. **Corrigir o `user.email`/`user.name` do git do Fortuna** para
   `josefortunafortuna54@gmail.com` / `José Fortuna` — 🔴 **é a prioridade
   máxima desta lista**, porque hoje a contribuição dele é **invisível no
   GitHub** (§4.5). Sem isto, qualquer leitura externa do repositório atribui ao
   fundador trabalho que o sócio fez. Na máquina dele:

   ```bash
   git config --global user.name  "José Fortuna"
   git config --global user.email "josefortunafortuna54@gmail.com"
   ```

   Confirmar com `git log -1 --format='%an <%ae>'` a dar o email certo.
2. **Não reescrever o histórico.** Os 6 commits são públicos; `filter-branch` ou
   force-push para os reatribuir destrói o histórico partilhado por um ganho
   estético. A atribuição correcta do passado é a tabela de §3.
3. **Esclarecer onde está o trabalho recente** (ver §5.3) — há divergência entre
   o que o sócio refere e o que o repositório e o GitHub mostram.
4. Definir o critério formal de vesting (o que conta para os 4%: commits?
   PRs? marcos?) e registar em `ESTRUTURA_DA_EMPRESA.md`.

### 5.2 Portefólio a cobrar no próximo passo do sócio

Prioridade segundo o plano em `docs/RECONHECIMENTO_REMOTE.md` Parte 3:

1. Teste de origem virtual + correcção do multi-monitor — 🔴, é a falha que o
   utilizador sente.
2. Testes mínimos no mobile (o vazio total é inaceitável para um sócio que
   responde pelo domínio mobile).
3. Respect dos gates de pausa e licença no canal remoto.

> ✅ **Feito pelo fundador, não fica a dívida do sócio** (2026-09-28): o
> `pyproject.toml` alinhado, `cryptography` acrescentado aos dois manifestos,
> `comtypes` removido, `tests/test_manifests.py` com 12 testes a trancar a
> divergência, e o CI a instalar `requirements-linux.txt`. Detalhe em
> `RECONHECIMENTO_REMOTE.md` §1.14.2.

> ❌ **Retirado do topo desta lista:** `websockets>=14.0`, que estava classificado
> como bloqueador de build da EAS. A premissa era falsa (§4.6) — não é trabalho
> que se possa cobrar a ninguém.

### 5.3 Trabalho recente: divergência a esclarecer 🟡

Verificado a 2026-09-28: **o GitHub não regista commits deste sócio desde
2026-09-15** (14 dias), e o único PR seu (#1, `fix(lint)`) foi **merged hoje**,
mas é o commit de duas semanas — a branch `feature/touch` continua no mesmo SHA
de 15/set. O repositório local confirma: zero commits de terceiros desde 16/set.

O sócio refere ter trabalhado recentemente. **Perguntas directas a fazer:**

- Onde exactamente está o trabalho — outro repositório, branch local não
  partilhada, ou trabalho ainda não commitado?
- Se for noutro sítio, porque não foi trazido para `Noturno22/Maouse`? Sem isso
  o domínio do papel não é auditável e, por definição, não conta para vesting.
- O PR #1, merged hoje, conta como entrega?

**Não registar como entrega até haver commit verificável.** A regra do projecto
(§2) só conta artefactos verificáveis; um "fiz trabalho" sem diff não entra no
cap table.

---

## 6. Estado da partnership

| Indicador | Valor |
|---|---|
| Equity (plano) | 4% com vesting |
| Entregas verificáveis | 6 commits (5 substantivos), **todos de 14–15/set** |
| Commits registados pelo **GitHub** em nome do sócio | **0** 🔴 (§4.5) |
| Último commit do sócio | **2026-09-15** — há 14 dias |
| Trabalho recente declarado, não encontrado no repositório | 🟡 por esclarecer (§5.3) |
| Documentação de domínio | `docs/RECONHECIMENTO_REMOTE.md` (ca. 1110 linhas, 3 partes) |
| Domínio no papel vs. na prática | papel: mobile/remote/Linux/CI · prática: core desktop/CI mixes |
| Bloqueadores de build atribuíveis ao domínio | **0** — o alegado foi retractado (§4.6) |
| Limitações 🔴 reais no domínio (4, todas pré-existentes) | multi-monitor · sem TLS · sem rate limit · bypass Pro |
| Testes no mobile | **0** |

---

| Versão | Data | O quê mudou | Quem |
|---|---|---|---|
| 1.0 | 2026-09-28 | Criação da área de análise de contribuição; consolidação das entregas verificáveis do sócio-função Fortuna; registo das 24 limitações do domínio remote (auditoria) | Luar Studio Angola |
| 1.1 | 2026-09-28 | **Verificação por API do GitHub**: a contribuição do sócio é **invisível** (0 commits atribuídos, `author: null`, 1 contributor no repo) por causa do email `teu-email-do-github` — nova §4.5, 🔴. Confirmado que **não há trabalho novo desde 15/set** (repo local e GitHub); o PR #1 merged hoje é o commit de duas semanas — nova §5.3, 🟡, com a pergunta directa a fazer | Luar Studio Angola |
| 1.2 | 2026-09-28 | **Retractada a acusação de 2 bloqueadores 🔴 de build** (nova §4.6, ⚪). Verificado antes de alterar: `websockets.asyncio` existe desde a **13.0** (o floor de `requirements.txt:5` está correcto) e a EAS nunca lê `requirements.txt`. Bloqueadores de build: **zero**. Corrigidos §4.2, §4.4, §5.2, §6, e a versão 1.6 de `ESTRUTURA_DA_EMPRESA.md` | Luar Studio Angola |
| 1.3 | 2026-09-28 | Ao verificar o ponto anterior, **encontrado um 🔴 real e mais grave**: `cryptography` faltava a `requirements.txt` e `requirements-linux.txt`, sendo importado por `core/licensing.py` ao nível do módulo — logo o `setup.bat` instalava uma aplicação que não arrancava. Corrigido, com `pyproject.toml` alinhado e `tests/test_manifests.py` (12 testes) a trancar a divergência entre manifestos. Detalhe em `RECONHECIMENTO_REMOTE.md` §1.14.2 | Luar Studio Angola |

---

*Documento de registo — Luar Studio Angola · 2026-09-28 · Confidencial. Fonte interna para
cap table, vesting e avaliação de sócio-função, até formalização legal.*