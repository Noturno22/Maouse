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
| Email | `josefortunafortuna54@gmail.com` (GitHub) · git config actual: **`teu-email-do-github`** ⚠️ ver §5.1 |
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
| 🔴 | `websockets>=13.0` inválido (importa o namespace que só existe na 14.0) — rebenta instalações limpas da EAS | `requirements.txt:5`, `core/remote.py:223` |
| 🔴 | Multi-monitor sem origem virtual (cursor encurralado) | `core/mouse_ctl.py:127-143,186-189` |
| 🔴 | Sem TLS + cliente remove `wss://` | `core/remote.py:227-231`, `remoteClient.ts:33-41` |
| 🔴 | Sem rate limit / lockout / allowlist | `core/remote.py:250` |
| 🔴 | Bypass do gate Pro no remote | ausência em `core/remote.py` |
| 🟠 | Zero testes no mobile (sem `test` script, sem jest) | `mobile/airmouse-mobile/package.json` |
| 🟠 | `pyproject.toml` sem as dependências reais | `pyproject.toml:10-12` |
| 🟠 | Bypass do toggle de pausa | ausência em `core/remote.py` |
| 🟠 | Sem auto-reconnect / AppState / fila no mobile | `src/services/remoteClient.ts` |
| 🟠 | Condição de corrida no `MouseCtl` partilhado | `main.py:310-313` |

### 4.3 Pontos fortes

- **Conhece os dois lados do protocolo** — os fixes de `dfd218b` exigiam ler o
  TS do telemóvel *e* o Python do desktop. Raro e valioso.
- **Entrega CI que fica verde** — um sócio que deixa o pipeline verde deixa a
  casa arrumada; os restantes 197 commits do repo dependem disso.
- **Iniciou rapidamente** — 5 commits substantivos nos primeiros 2 dias.

### 4.4 Pontos fracos / risco

- **Volume muito baixo.** 6 commits em 14 dias de colaboração, num domínio com 24
  limitações conhecidas e 2 bugs 🔴 que **bloqueiam o build da EAS hoje**
  (`websockets>=13.0`) e **bloqueiam a funcionalidade central em multi-monitor**.
- **A propriedade do mobile é na prática do fundador.** `mobile/airmouse-mobile/`
  tem 30 commits do `Noturno22` vs 2 do Fortuna. O domínio "mobile" do papel do
  sócio está, na prática, entregue acima de 90% pelo fundador.
- **Email de git por preencher** (`teu-email-do-github`) — invisível para
  ferramentas de atribuição de contribuição.
- **Nenhuma contribuição em testes do remote** — o item 🔴 do cap §4.2.

---

## 5. Recomendações

### 5.1 Higiene imediata (15 minutos)

1. Corrigir o `user.email`/`user.name` do git do Fortuna para
   `josefortunafortuna54@gmail.com` / `José Fortuna` — sem isso, o GitHub não
   atribui os commits e o *tracking* de contribuição fica mais fraco.
2. Definir o critério formal de vesting (o que conta para os 4%: commits?
   PRs? marcos?) e registar em `ESTRUTURA_DA_EMPRESA.md`.

### 5.2 Portefólio a cobrar no próximo passo do sócio

Prioridade segundo o plano em `docs/RECONHECIMENTO_REMOTE.md` Parte 3:

1. `websockets>=14.0` — **bloqueia o build da EAS** (não é opcional).
2. Teste de origem virtual + correcção do multi-monitor.
3. Testes mínimos no mobile (o vazio total é inaceitável para um sócio que
   responde pelo domínio mobile).
4. Respect dos gates de pausa e licença no canal remoto.

---

## 6. Estado da partnership

| Indicador | Valor |
|---|---|
| Equity (plano) | 4% com vesting |
| Entregas verificáveis | 6 commits (5 substantivos) |
| Documentação de domínio | `docs/RECONHECIMENTO_REMOTE.md` (ca. 1110 linhas, 3 partes) |
| Domínio no papel vs. na prática | papel: mobile/remote/Linux/CI · prática: core desktop/CI mixes |
| Bloqueadores do build atribuíveis ao domínio | **2 🔴** (`websockets>=13.0`) |
| Testes no mobile | **0** |

---

| Versão | Data | O quê mudou | Quem |
|---|---|---|---|
| 1.0 | 2026-09-28 | Criação da área de análise de contribuição; consolidação das entregas verificáveis do sócio-função Fortuna; registo das 24 limitações do domínio remote (auditoria) | Luar Studio Angola |

---

*Documento de registo — Luar Studio Angola · 2026-09-28 · Confidencial. Fonte interna para
cap table, vesting e avaliação de sócio-função, até formalização legal.*