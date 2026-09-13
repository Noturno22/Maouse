# Design — Painel Administrativo Mãouse (Web)

> Área administrativa web para controlo total e transparente da empresa (pré-fundada) —
> dentro do license-server existente (FastAPI + SQLite + Render), custo de infra ~0.
> **Data:** 2026-09-13 · Autor: Luar Studio Angola · Estado: **aprovado pelo fundador**.

---

## 1. Objetivo

Dashboard consultável e editável pelo fundador (login único) para gerir toda a estrutura da
empresa num só lado web: sócios, investidores, funcionários, fases, marcos/comemorações, metas
/próximos investimentos, finanças/caixa, chat privado e envio de email aos sócios. Deve
espelhar/controlar o que hoje está em `BUSSINES/07_ADMINISTRACAO/` (ESTRUTURA + HISTORICO).

## 2. Âmbito

IN:
- Login único por senha de administração (`AIRMOUSE_LS_ADMIN_TOKEN` — já existe).
- CRUD simples (consultar/criar/editar/estado) para: sócios, investidores, funcionários, fases,
  marcos, metas, movimentos de caixa.
- Chat privado (só o fundador; histórico persistido; auto-refresh por polling ~3 s).
- Envio de email aos sócios via SMTP existente (`emailer.py`) + histórico de envios.
- Dashboard com KPIs: nº sócios, nº investidores, total investido, caixa atual, utilizadores
  pagos / máquinas ativas (from tabelas `purchases`/`machines` existentes), fases concluídas.
- Autenticação protegendo `/admin/*` e `/api/admin/*`; sem login → redireciona para `/admin/login`.

OUT:
- Sem contas por sócio (só o fundador usa o painel).
- Sem websockets (chat via polling).
- Sem build step / Node (páginas Jinja2 + JS leve fetch).
- Não altera endpoints públicos existentes (`/api/v1/*`, webhooks) — compatível.

## 3. Arquitetura

### 3.1 Stack
- FastAPI (existente) + Jinja2 (novo) + SQLite (tabelas novas em `license.db`).
- Templates em `license-server/templates/`, estáticos (CSS/JS) em `license-server/admin_static/`.
- Sessão: cookie assinado com `secrets` HMAC (`AIRMOUSE_LS_ADMIN_SESSION_SECRET`; fallback dev).

### 3.2 Componentes

| Módulo | Ficheiro | Responsabilidade |
|---|---|---|
| Rotas páginas | `license-server/admin_pages.py` | `GET /admin/login`, `POST /admin/login`, `GET /admin` e subpáginas; proteção por middleware |
| Rotas API | `license-server/admin_api.py` | CRUD JSON `/api/admin/*` (cada recurso) |
| Armazenamento admin | `license-server/admin_storage.py` | Tabelas novas + helpers CRUD/um-só-lugar SQL |
| Sessão | `license-server/admin_auth.py` | login/logout, cookie assinado, dependência `require_admin` |
| Email genérico | `emailer.py` (extendido) | `send_generic_email(to, subject, body)` reutilizando SMTP |
| Templates | `license-server/templates/*.html` | Jinja2 pages |
| Estáticos | `license-server/admin_static/*` | `admin.css`, `admin.js` |

### 3.3 Schema (novas tabelas — `admin_storage.py`, criadas no `init_db`)

```
socios(id PK, nome, papel, participacao REAL, capital_investido TEXT,
       capital_moeda TEXT, estado TEXT, notas TEXT, created_at, updated_at)
investidores(id PK, nome, local TEXT, valor TEXT, moeda TEXT, equity TEXT,
             acordo TEXT, fase TEXT, estado TEXT, data_contacto TEXT,
             notas TEXT, created_at, updated_at)
funcionarios(id PK, nome, funcao, tipo TEXT, regime TEXT, estado TEXT,
             salario TEXT, notas TEXT, created_at, updated_at)
fases(id PK, nome, fase TEXT, estado TEXT, data_inicio TEXT, data_fim TEXT,
      notas TEXT, created_at, updated_at)
marcos(id PK, data TEXT, titulo, tipo TEXT, descricao TEXT, created_at, updated_at)
metas(id PK, titulo, descricao, valor TEXT, moeda TEXT, prazo TEXT, estado TEXT,
      prioridade TEXT, created_at, updated_at)
movimentos_caixa(id PK, data TEXT, tipo TEXT, descricao, valor REAL, moeda TEXT,
                 categoria TEXT, criado_em)
chat(id PK, autor TEXT, mensagem, created_at)
emails_enviados(id PK, para TEXT, assunto, corpo TEXT, estado TEXT, erro TEXT, created_at)
```

Notas:
- Todos os campos monetários guardados como **texto + moeda** (ex. `"260.000"` + `"Kz"`, `"222"` + `"USD"`) para
  não inventar câmbio; exibição documenta ambos quando existirem.
- Estados usam valores de texto curto (`ativo`, `em_discussao`, `concluida`, `em_curso`, `pendente`) — livre.

## 4. Autenticação

- `POST /admin/login` (form) → compara senha com `^AIRMOUSE_LS_ADMIN_TOKEN` (constante tempo) →
  set cookie `maouse_admin` = `payload.b64 + "." + HMAC(payload, session_secret)`.
- Middleware/rota wrapper: sem cookie válido → 307 para `/admin/login` (páginas) e 401 (API).
- `POST /admin/logout` limpa o cookie.
- `AIRMOUSE_LS_ADMIN_SESSION_SECRET` em `render.yaml` (sync:false); fallback dev = valor fixo apenas
  se não definido (warning no arranque).

## 5. Páginas

| Rota | Template | Conteúdo |
|---|---|---|
| `/admin` | `dashboard.html` | KPIs (sócios, investidores, total investido, caixa, pagantes, máquinas, fases/marcos/metas) |
| `/admin/socios` | `socios.html` | Lista + form CRUD |
| `/admin/investidores` | `investidores.html` | Lista + form CRUD |
| `/admin/funcionarios` | `funcionarios.html` | Lista + form CRUD |
| `/admin/fases` | `fases.html` | Lista + form CRUD |
| `/admin/marcos` | `marcos.html` | Comemorações & marcos |
| `/admin/metas` | `metas.html` | Próximos investimentos e metas |
| `/admin/caixa` | `caixa.html` | Movimentos + saldo |
| `/admin/chat` | `chat.html` | Chat privado (polling 3 s) |
| `/admin/emails` | `emails.html` | Enviar email a sócio(s) + histórico |

Design: CSS simples dark (coerente com branding Mãouse), sidebar fixa, tabelas + forms inline.

## 6. API (JSON)

Rotas CRUD genéricas por recurso, autenticadas:
- `GET/POST /api/admin/<recurso>` — listar/criar
- `PATCH/DELETE /api/admin/<recurso>/<id>` — editar/eliminar (estado via PATCH)
- `POST /api/admin/chat` — nova mensagem; `GET /api/admin/chat?after_id=N` — mensagens novas (polling)
- `GET /api/admin/dashboard` — KPIs agregados
- `POST /api/admin/emails/send` — corpo `{para: [ids_socios], assunto, corpo}` → `send_generic_email` por sócio + regista em `emails_enviados`
- `GET /api/admin/emails` — histórico

Recursos: `socios`, `investidores`, `funcionarios`, `fases`, `marcos`, `metas`, `movimentos_caixa`.

## 7. Fluxo de dados e erros

- Páginas carregam dados via fetch para `/api/admin/*` (JS) — mesmo contrato da API (evolui para SPA depois).
- Erros: `{error: "msg"}` com 400/404/401; chat retorna `{messages: [...], next_id}`.
- Email: estado por envio (`enviado`/`falhou` + erro); nunca quebra a UI.

## 8. Segurança

- Sessão assinada (HMAC), `HttpOnly`, `SameSite=Lax`.
- Sem dados sensíveis expostos em público: `/admin/*` e `/api/admin/*` sempre atrás de auth.
- CSS/JS estáticos públicos (sem dados).
- Email: sem logs das credenciais SMTP.

## 9. Testes

- `license-server/tests/test_admin_auth.py` — login ok/falha, cookie inválido, páginas 307, API 401.
- `license-server/tests/test_admin_crud.py` — CRUD por recurso (criar/listar/patch/delete) com auth.
- `license-server/tests/test_admin_dashboard.py` — KPIs agregados (incl. contagens de `purchases`/`machines`).
- `license-server/tests/test_admin_chat.py` — POST/GET com `after_id` e ordenação.
- `license-server/tests/test_admin_emails.py` — send com `AIRMOUSE_SMTP_ENABLED=0` (não fire) e registo.
- `license-server/tests/test_admin_pages.py` — 200 das páginas autenticadas; 307 sem sessão.

Runner: `.venv\Scripts\python -m pytest license-server/tests -q` (mesma suíte; sem quebrar os 40 existentes).

## 10. Deploy

- Render blueprint: `render.yaml` ganha `AIRMOUSE_LS_ADMIN_SESSION_SECRET` (sync:false).
- Dockerfile inalterado (templates/estáticos copiados por `COPY license-server/* /app/*` já cobre
  pastas? → ajustar para `COPY license-server /app` simples).
- Health check `/health` inalterado.

## 11. Decisões assumidas

- Um só `license.db` (backups simples).
- Moeda: valor+moeda (texto), sem conversão automática.
- Só fundador. Chat polling. Sem websockets/build.