# Painel Administrativo Mãouse (Web) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpawers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Painel administrativo web dentro do license-server (FastAPI + SQLite + Render) para controlo total e transparente da empresa: sócios, investidores, funcionários, fases, marcos, metas, caixa, chat privado e email aos sócios.

**Architecture:** FastAPI serve páginas Jinja2 (`/admin/*`) e API JSON autenticada (`/api/admin/*`) num único servidor, com novas tabelas no `license.db` e sessão via cookie HMAC. Sem Node/build step; chat por polling.

**Tech Stack:** FastAPI (0.141, existente), starlette Jinja2Templates, SQLite (stdlib), HMAC sessions (stdlib), pytest (existente).

**Spec:** `.superpawers/specs/2026-09-13-admin-panel-web-design.md`

---

## File Structure

| Ficheiro | Ação | Responsabilidade |
|---|---|---|
| `license-server/requirements.txt` | Modify | + `jinja2` |
| `license-server/admin_storage.py` | Create | Tabelas novas + CRUD genérico + chat + emails + KPIs |
| `license-server/admin_auth.py` | Create | Cookie de sessão HMAC + `require_admin` |
| `license-server/emailer.py` | Modify | + `send_generic_email` |
| `license-server/admin_api.py` | Create | Router `/api/admin/*` (CRUD, chat, dashboard, emails) |
| `license-server/admin_pages.py` | Create | Router `/admin/*` (páginas Jinja2) |
| `license-server/templates/_base.html` | Create | Layout + sidebar |
| `license-server/templates/login.html` | Create | Login |
| `license-server/templates/crud.html` | Create | Página CRUD genérica |
| `license-server/templates/dashboard.html` | Create | Dashboard KPIs |
| `license-server/templates/chat.html` | Create | Chat privado |
| `license-server/templates/emails.html` | Create | Email aos sócios |
| `license-server/admin_static/admin.css` | Create | Estilos dark Mãouse |
| `license-server/admin_static/admin.js` | Create | Crud genérico + utils |
| `license-server/admin_static/chat.js` | Create | Polling chat |
| `license-server/admin_static/emails.js` | Create | Envio emails |
| `license-server/admin_static/dashboard.js` | Create | KPIs |
| `license-server/app.py` | Modify | incluir routers + static |
| `license-server/Dockerfile` | Modify | `COPY license-server /app` |
| `license-server/render.yaml` | Modify | + `AIRMOUSE_LS_ADMIN_SESSION_SECRET` |

Testes novos em `license-server/tests/`: `test_admin_storage.py`, `test_admin_auth.py`, `test_admin_api.py`, `test_admin_pages.py`.

---

## Task 1: Dependência Jinja2

**Files:** `license-server/requirements.txt`

- [ ] **Step 1:** Adicionar `jinja2>=3.1` ao `license-server/requirements.txt` (última linha)

- [ ] **Step 2:** Instalar e verificar

Run: `.\.venv\Scripts\python.exe -m pip install -r license-server/requirements.txt`
Run: `.\.venv\Scripts\python.exe -c "import jinja2; print(jinja2.__version__)"`
Expected: imprime versão (ex. `3.1.x`)

- [ ] **Step 3:** Commit

```bash
git add license-server/requirements.txt
git commit -m "chore: add jinja2 dependency for admin panel"
```

---

## Task 2: admin_storage.py (tabelas + CRUD + chat + KPIs) + testes

**Files:**
- Create: `license-server/admin_storage.py`
- Test: `license-server/tests/test_admin_storage.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for admin_storage (tabelas novas, CRUD genérico, chat, KPIs)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import admin_storage
from storage import connect, init_db

RES = "socios"
ROW = {"nome": "Luar Studio", "papel": "fundador", "participacao": "100",
       "capital_investido": "0", "capital_moeda": "EUR", "estado": "ativo",
       "notas": "raiz"}


def _db(tmp_path):
    os.environ["AIRMOUSE_LS_DB"] = str(tmp_path / "ad.db")
    conn = connect()
    init_db(conn)
    return conn


def test_create_and_list_row(tmp_path):
    conn = _db(tmp_path)
    row_id = admin_storage.create_row(conn, RES, ROW)
    rows = admin_storage.list_rows(conn, RES)
    assert len(rows) == 1
    assert rows[0]["id"] == row_id
    assert rows[0]["nome"] == "Luar Studio"


def test_update_and_get_row(tmp_path):
    conn = _db(tmp_path)
    row_id = admin_storage.create_row(conn, RES, ROW)
    ok = admin_storage.update_row(conn, RES, row_id, {"estado": "inativo"})
    assert ok is True
    row = admin_storage.get_row(conn, RES, row_id)
    assert row["estado"] == "inativo"


def test_update_ignores_unknown_columns(tmp_path):
    conn = _db(tmp_path)
    row_id = admin_storage.create_row(conn, RES, ROW)
    ok = admin_storage.update_row(conn, RES, row_id, {"hacker": "x"})
    assert ok is True
    row = admin_storage.get_row(conn, RES, row_id)
    assert "hacker" not in dict(row)


def test_delete_row(tmp_path):
    conn = _db(tmp_path)
    row_id = admin_storage.create_row(conn, RES, ROW)
    assert admin_storage.delete_row(conn, RES, row_id) is True
    assert admin_storage.get_row(conn, RES, row_id) is None
    assert admin_storage.delete_row(conn, RES, row_id) is False


def test_all_resources_have_common_id_column(tmp_path):
    conn = _db(tmp_path)
    for resource in admin_storage.RESOURCES:
        row_id = admin_storage.create_row(conn, resource, {})
        assert row_id > 0
        admin_storage.delete_row(conn, resource, row_id)


def test_chat_add_and_after(tmp_path):
    conn = _db(tmp_path)
    id1 = admin_storage.add_chat(conn, "fundador", "primeira")
    id2 = admin_storage.add_chat(conn, "fundador", "segunda")
    after = admin_storage.chat_after(conn, after_id=id1)
    assert [m["mensagem"] for m in after] == ["segunda"]


def test_record_and_list_emails(tmp_path):
    conn = _db(tmp_path)
    admin_storage.record_email(conn, "socio@x.com", "Evento", "Olá", "enviado")
    rows = admin_storage.list_emails(conn)
    assert rows[0]["para"] == "socio@x.com"


def test_dashboard_kpis(tmp_path):
    conn = _db(tmp_path)
    admin_storage.create_row(conn, "socios", ROW)
    admin_storage.create_row(conn, "investidores",
                             {"nome": "Roberto", "estado": "recebido"})
    admin_storage.create_row(conn, "fases", {"nome": "B", "estado": "concluida"})
    kpi = admin_storage.dashboard_kpis(conn)
    assert kpi["socios"] == 1
    assert kpi["investidores"] == 1
    assert kpi["fases_concluidas"] == 1
```

- [ ] **Step 2: Run to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest license-server/tests/test_admin_storage.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'admin_storage'`

- [ ] **Step 3: Write implementation** (`license-server/admin_storage.py`)

```python
"""Armazenamento administrativo: tabelas novas no license.db + CRUD genérico.

Estrutura de recursos replicada do design: cada recurso tem uma tabela nova,
colunas editáveis e estados livres (texto curto). Valores monetários guardados
como texto + coluna de moeda (sem câmbio no servidor).
"""
from storage import connect, init_db

RESOURCES: dict[str, dict] = {
    "socios": {
        "cols": [
            "nome", "papel", "participacao", "capital_investido", "capital_moeda",
            "estado", "notas",
        ],
    },
    "investidores": {
        "cols": [
            "nome", "local", "valor", "moeda", "equity", "acordo", "fase",
            "estado", "data_contacto", "notas",
        ],
    },
    "funcionarios": {
        "cols": ["nome", "funcao", "tipo", "regime", "estado", "salario", "notas"],
    },
    "fases": {
        "cols": ["nome", "fase", "estado", "data_inicio", "data_fim", "notas"],
    },
    "marcos": {
        "cols": ["data", "titulo", "tipo", "descricao"],
    },
    "metas": {
        "cols": ["titulo", "descricao", "valor", "moeda", "prazo", "estado",
                 "prioridade"],
    },
    "movimentos_caixa": {
        "cols": ["data", "tipo", "descricao", "valor", "moeda", "categoria"],
    },
}

_COMMON_COLS = "id INTEGER PRIMARY KEY AUTOINCREMENT, created_at INTEGER NOT NULL DEFAULT 0"
_ADMIN_TABLES: dict[str, str] = {
    key: " ".join(
        [f"{col} TEXT" for col in info["cols"]]
    )
    for key, info in RESOURCES.items()
}


def init_admin_tables(conn) -> None:
    """Cria as tabelas administrativas (idempotente). Chamar a seguir a init_db."""
    _DDL = {
        "socios": f"CREATE TABLE IF NOT EXISTS socios (" f"{_COMMON_COLS}," " nome TEXT, papel TEXT, participacao TEXT, capital_investido TEXT, capital_moeda TEXT, estado TEXT, notas TEXT);",
        "investidores": f"CREATE TABLE IF NOT EXISTS investidores (" f"{_COMMON_COLS}," " nome TEXT, local TEXT, valor TEXT, moeda TEXT, equity TEXT, acordo TEXT, fase TEXT, estado TEXT, data_contacto TEXT, notas TEXT);",
        "funcionarios": f"CREATE TABLE IF NOT EXISTS funcionarios (" f"{_COMMON_COLS}," " nome TEXT, funcao TEXT, tipo TEXT, regime TEXT, estado TEXT, salario TEXT, notas TEXT);",
        "fases": f"CREATE TABLE IF NOT EXISTS fases (" f"{_COMMON_COLS}," " nome TEXT, fase TEXT, estado TEXT, data_inicio TEXT, data_fim TEXT, notas TEXT);",
        "marcos": f"CREATE TABLE IF NOT EXISTS marcos (" f"{_COMMON_COLS}," " data TEXT, titulo TEXT, tipo TEXT, descricao TEXT);",
        "metas": f"CREATE TABLE IF NOT EXISTS metas (" f"{_COMMON_COLS}," " titulo TEXT, descricao TEXT, valor TEXT, moeda TEXT, prazo TEXT, estado TEXT, prioridade TEXT);",
        "movimentos_caixa": f"CREATE TABLE IF NOT EXISTS movimentos_caixa (" f"{_COMMON_COLS}," " data TEXT, tipo TEXT, descricao TEXT, valor TEXT, moeda TEXT, categoria TEXT);",
        "chat": "CREATE TABLE IF NOT EXISTS chat ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "autor TEXT NOT NULL, mensagem TEXT NOT NULL, created_at INTEGER NOT NULL);",
        "emails_enviados": "CREATE TABLE IF NOT EXISTS emails_enviados ("
                           "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                           "para TEXT NOT NULL, assunto TEXT NOT NULL, corpo TEXT,"
                           "estado TEXT NOT NULL, erro TEXT, created_at INTEGER NOT NULL);",
    }
    for ddl in _DDL.values():
        conn.execute(ddl)
    conn.commit()


def _table(resource: str) -> str:
    if resource not in RESOURCES:
        raise ValueError(f"recurso_inexistente: {resource}")
    return resource


def _cols(resource: str) -> list[str]:
    return RESOURCES[resource]["cols"]


def _filtered(data: dict, resource: str) -> dict:
    allowed = set(_cols(resource))
    return {k: v for k, v in data.items() if k in allowed}


def list_rows(conn, resource: str, order: str = "id") -> list[dict]:
    table = _table(resource)
    rows = conn.execute(f"SELECT * FROM {table} ORDER BY {order}").fetchall()
    return [dict(r) for r in rows]


def get_row(conn, resource: str, row_id: int) -> dict | None:
    table = _table(resource)
    row = conn.execute(f"SELECT * FROM {table} WHERE id=?", (row_id,)).fetchone()
    return dict(row) if row else None


def create_row(conn, resource: str, data: dict) -> int:
    import time
    table = _table(resource)
    clean = _filtered(data, resource)
    cols = list(clean.keys())
    vals = list(clean.values())
    cols.append("created_at")
    vals.append(int(time.time()))
    placeholders = ",".join("?" for _ in vals)
    cur = conn.execute(
        f"INSERT INTO {table}({','.join(cols)}) VALUES({placeholders})", vals)
    conn.commit()
    return cur.lastrowid


def update_row(conn, resource: str, row_id: int, data: dict) -> bool:
    table = _table(resource)
    if get_row(conn, resource, row_id) is None:
        return False
    clean = _filtered(data, resource)
    if clean:
        set_clause = ",".join(f"{k}=?" for k in clean)
        conn.execute(f"UPDATE {table} SET {set_clause} WHERE id=?",
                     list(clean.values()) + [row_id])
        conn.commit()
    return True


def delete_row(conn, resource: str, row_id: int) -> bool:
    table = _table(resource)
    if get_row(conn, resource, row_id) is None:
        return False
    conn.execute(f"DELETE FROM {table} WHERE id=?", (row_id,))
    conn.commit()
    return True


def add_chat(conn, autor: str, mensagem: str) -> int:
    import time
    cur = conn.execute(
        "INSERT INTO chat(autor, mensagem, created_at) VALUES(?,?,?)",
        (autor, mensagem, int(time.time())))
    conn.commit()
    return cur.lastrowid


def chat_after(conn, after_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM chat WHERE id>? ORDER BY id ASC", (after_id,)).fetchall()
    return [dict(r) for r in rows]


def record_email(conn, para: str, assunto: str, corpo: str, estado: str,
                 erro: str = "") -> int:
    import time
    cur = conn.execute(
        "INSERT INTO emails_enviados(para, assunto, corpo, estado, erro, created_at)"
        " VALUES(?,?,?,?,?,?)",
        (para, assunto, corpo, estado, erro, int(time.time())))
    conn.commit()
    return cur.lastrowid


def list_emails(conn, limit: int = 100) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM emails_enviados ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def dashboard_kpis(conn) -> dict:
    def count(table: str, where: str = "", args: tuple = ()) -> int:
        q = f"SELECT COUNT(*) AS c FROM {table}"
        if where:
            q += " WHERE " + where
        row = conn.execute(q, args).fetchone()
        return int(row["c"])

    pagantes = count("purchases") + count("mobile_purchases")
    maquinas = count("machines")
    socios = count("socios")
    investidores = count("investidores")
    funcionarios = count("funcionarios")
    fases_concluidas = count("fases", "estado=?", ("concluida",))
    metas_abertas = count("metas", "estado!=? OR estado IS NULL", ("concluida",))
    marcos = count("marcos")
    chat_msgs = count("chat")
    return {
        "socios": socios,
        "investidores": investidores,
        "funcionarios": funcionarios,
        "pagantes": pagantes,
        "maquinas_ativas": maquinas,
        "fases_concluidas": fases_concluidas,
        "metas_abertas": metas_abertas,
        "marcos": marcos,
        "chat_mensagens": chat_msgs,
    }
```

- [ ] **Step 4: Update `storage.init_db`** to call admin init. Modify `license-server/storage.py` end of `init_db`:

```python
        """
    )
    # tabelas administrativas (painel web)
    from admin_storage import init_admin_tables
    init_admin_tables(conn)
    cur = conn.execute("SELECT v FROM config WHERE k='revocation_nonce'")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.\.venv\Scripts\python.exe -m pytest license-server/tests/test_admin_storage.py -q`
Expected: PASS (9 passed)

- [ ] **Step 6: Run the existing suite to ensure no regression**

Run: `.\.venv\Scripts\python.exe -m pytest license-server/tests -q --no-header --disable-warnings 2>&1 | Select-String "passed|failed"`
Expected: all previously passing still pass (the known 1 failure may remain)

- [ ] **Step 7: Commit**

```bash
git add license-server/admin_storage.py license-server/tests/test_admin_storage.py license-server/storage.py
git commit -m "feat: admin_storage CRUD, chat, emails, KPIs"
```

---

## Task 3: admin_auth.py + testes

**Files:**
- Create: `license-server/admin_auth.py`
- Test: `license-server/tests/test_admin_auth.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for admin_auth (sessão HMAC + require_admin)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import admin_auth


def test_verify_password_ok(monkeypatch):
    monkeypatch.setenv("AIRMOUSE_LS_ADMIN_TOKEN", "segredo")
    assert admin_auth.verify_password("segredo") is True
    assert admin_auth.verify_password("errado") is False


def test_session_roundtrip():
    cookie = admin_auth.make_session()
    assert admin_auth.verify_session(cookie) is True


def test_tampered_session_rejected():
    cookie = admin_auth.make_session()
    bad = cookie[:-1] + ("B" if cookie[-1] != "B" else "C")
    assert admin_auth.verify_session(bad) is False


def test_garbage_session_rejected():
    assert admin_auth.verify_session("not-a-cookie") is False
```

- [ ] **Step 2: Run to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest license-server/tests/test_admin_auth.py -q`
Expected: FAIL — module not found

- [ ] **Step 3: Write implementation** (`license-server/admin_auth.py`)

```python
"""Sessão de administrador: cookie assinado HMAC (sem lib externa).

O cookie transporta apenas timestamp + nonce, assinado com HMAC-SHA256 usando
AIRMOUSE_LS_ADMIN_SESSION_SECRET. A senha do login compara com
AIRMOUSE_LS_ADMIN_TOKEN (todo-poderoso do painel).
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time

COOKIE_NAME = "maouse_admin"
MAX_AGE = 7 * 24 * 3600
_DEV_SECRET = "dev-session-secret"


def _secret() -> str:
    return os.getenv("AIRMOUSE_LS_ADMIN_SESSION_SECRET", _DEV_SECRET)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def _sign(body: str) -> str:
    return hmac.new(_secret().encode(), body.encode(), hashlib.sha256).hexdigest()


def make_session() -> str:
    payload = json.dumps({"t": int(time.time()),
                          "n": secrets.token_hex(8)},
                         separators=(",", ":")).encode()
    body = _b64(payload)
    return f"{body}.{_sign(body)}"


def verify_session(cookie: str) -> bool:
    try:
        body, _, sig = cookie.partition(".")
        if not body or not sig:
            return False
        if not hmac.compare_digest(_sign(body), sig):
            return False
        payload = json.loads(_unb64(body.decode() if isinstance(body, bytes) else body))
        if int(payload["t"]) + MAX_AGE < time.time():
            return False
        return True
    except Exception:
        return False


def verify_password(password: str) -> bool:
    expected = os.getenv("AIRMOUSE_LS_ADMIN_TOKEN", "dev-admin-token")
    return hmac.compare_digest(password, expected)


def require_admin(request) -> None:
    """Dependency FastAPI: rejeita com 401 se a sessão não for válida."""
    from fastapi import HTTPException
    cookie = request.cookies.get(COOKIE_NAME, "")
    if not verify_session(cookie):
        raise HTTPException(status_code=401, detail="nao_autenticado")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.\.venv\Scripts\python.exe -m pytest license-server/tests/test_admin_auth.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add license-server/admin_auth.py license-server/tests/test_admin_auth.py
git commit -m "feat: admin_auth sessao HMAC"
```

---

## Task 4: emailer.send_generic_email + teste

**Files:**
- Modify: `license-server/emailer.py`
- Test: `license-server/tests/test_emailer.py` (modify — adicionar teste)

- [ ] **Step 1: Add the failing test** (apêndice em `test_emailer.py`)

```python
from emailer import send_generic_email


def test_generic_email_disabled_returns_noop(monkeypatch):
    monkeypatch.setenv("AIRMOUSE_SMTP_ENABLED", "0")
    result = send_generic_email("a@b.c", "Assunto", "Corpo")
    assert result.fired is False
    assert result.error == ""
```

- [ ] **Step 2: Run to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest license-server/tests/test_emailer.py -q`
Expected: FAIL — `AttributeError: 'module' object has no attribute 'send_generic_email'`

- [ ] **Step 3: Implement** — adicionar ao fim de `emailer.py`:

```python
def build_generic_email(to_email: str, subject: str, body: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = _cfg()["from"]
    msg["To"] = to_email
    msg.set_content(body)
    return msg


def send_generic_email(to_email: str, subject: str, body: str) -> Result:
    cfg = _cfg()
    if not cfg["enabled"]:
        return Result(fired=False, error="")
    try:
        msg = build_generic_email(to_email, subject, body)
        with smtplib.SMTP(cfg["host"], cfg["port"]) as srv:
            srv.starttls()
            srv.login(cfg["user"], cfg["password"])
            srv.sendmail(cfg["from"], [to_email], msg.as_string())
        return Result(fired=True, error="")
    except Exception as exc:  # noqa: BLE001
        return Result(fired=False, error=str(exc))
```

- [ ] **Step 4: Run to verify passes**

Run: `.\.venv\Scripts\python.exe -m pytest license-server/tests/test_emailer.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add license-server/emailer.py license-server/tests/test_emailer.py
git commit -m "feat: send_generic_email para o painel admin"
```

---

## Task 5: admin_api.py + testes

**Files:**
- Create: `license-server/admin_api.py`
- Test: `license-server/tests/test_admin_api.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests para a API JSON /api/admin/* (CRUD, chat, dashboard, email)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from admin_auth import COOKIE_NAME, make_session
from app import create_app


def _client():
    client = TestClient(create_app())
    client.cookies.set(COOKIE_NAME, make_session())
    return client


def test_api_requires_auth():
    client = TestClient(create_app())
    resp = client.get("/api/admin/socios")
    assert resp.status_code == 401


def test_crud_create_and_list():
    client = _client()
    resp = client.post("/api/admin/socios", json={"nome": "X", "papel": "socio"})
    assert resp.status_code == 200
    row_id = resp.json()["id"]
    rows = client.get("/api/admin/socios").json()["items"]
    assert any(r["id"] == row_id and r["nome"] == "X" for r in rows)


def test_crud_patch_and_delete():
    client = _client()
    row_id = client.post("/api/admin/metas", json={"titulo": "meta1"}).json()["id"]
    patch = client.patch(f"/api/admin/metas/{row_id}", json={"estado": "concluida"})
    assert patch.status_code == 200
    row = next(r for r in client.get("/api/admin/metas").json()["items"]
               if r["id"] == row_id)
    assert row["estado"] == "concluida"
    assert client.delete(f"/api/admin/metas/{row_id}").status_code == 200
    assert client.delete(f"/api/admin/metas/{row_id}").status_code == 404


def test_unknown_resource_404():
    client = _client()
    assert client.get("/api/admin/naoexiste").status_code == 404


def test_chat_post_and_poll():
    client = _client()
    r1 = client.post("/api/admin/chat", json={"mensagem": "ola"})
    assert r1.status_code == 200
    first_id = r1.json()["id"]
    client.post("/api/admin/chat", json={"mensagem": "mundo"})
    poll = client.get(f"/api/admin/chat?after_id={first_id}").json()
    assert [m["mensagem"] for m in poll["messages"]] == ["mundo"]
    assert poll["next_id"] > first_id


def test_dashboard_returns_kpis():
    client = _client()
    kpi = client.get("/api/admin/dashboard").json()
    for key in ("socios", "investidores", "pagantes", "machines_ativas",
                "fases_concluidas", "metas_abertas", "marcos"):
        assert key in kpi


def test_email_send_records_history_when_smtp_disabled():
    client = _client()
    socio_id = client.post("/api/admin/socios",
                           json={"nome": "S1", "estado": "ativo",
                                 "email": ""}).json()["id"]
    # repositório: testa o fluxo com smtp off -> regista estado nao_fire
    resp = client.post("/api/admin/emails/send",
                       json={"socio_ids": [socio_id], "assunto": "A",
                             "corpo": "B"})
    assert resp.status_code == 200
    entries = client.get("/api/admin/emails").json()["items"]
    assert entries[0]["assunto"] == "A"
```

- [ ] **Step 2: Run to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest license-server/tests/test_admin_api.py -q`
Expected: FAIL — module not found

- [ ] **Step 3: Write implementation** (`license-server/admin_api.py`)

```python
"""API JSON /api/admin/* — autenticada por sessão HMAC.

CRUD genérico para os recursos de RESOURCES, chat, dashboard e envio de email
aos sócios (reutiliza send_generic_email).
"""
import os

from fastapi import APIRouter, Depends, HTTPException, Request

import admin_storage
from admin_auth import require_admin
from emailer import send_generic_email
from storage import connect, init_db

router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_admin)])


def get_db():
    conn = connect()
    init_db(conn)
    try:
        yield conn
    finally:
        conn.close()


def _register_crud(resource: str):
    uid = resource.replace("_", "")
    table = resource

    @router.get(f"/{resource}",
                operation_id=f"list_{uid}", response_model=dict)
    def _list(db=Depends(get_db)):
        return {"items": admin_storage.list_rows(db, table)}

    @router.post(f"/{resource}",
                 operation_id=f"create_{uid}", response_model=dict)
    def _create(payload: dict, db=Depends(get_db)):
        row_id = admin_storage.create_row(db, table, payload)
        return {"id": row_id}

    @router.patch(f"/{resource}/{{row_id}}",
                  operation_id=f"patch_{uid}", response_model=dict)
    def _patch(row_id: int, payload: dict, db=Depends(get_db)):
        if admin_storage.get_row(db, table, row_id) is None:
            raise HTTPException(status_code=404, detail="nao_encontrado")
        admin_storage.update_row(db, table, row_id, payload)
        return {"ok": True}

    @router.delete(f"/{resource}/{{row_id}}",
                   operation_id=f"delete_{uid}", response_model=dict)
    def _delete(row_id: int, db=Depends(get_db)):
        if admin_storage.get_row(db, table, row_id) is None:
            raise HTTPException(status_code=404, detail="nao_encontrado")
        admin_storage.delete_row(db, table, row_id)
        return {"ok": True}


for _resource in admin_storage.RESOURCES:
    _register_crud(_resource)


@router.get("/chat", operation_id="chat_list", response_model=dict)
def chat_get(after_id: int = 0, db=Depends(get_db)):
    messages = admin_storage.chat_after(db, after_id)
    next_id = messages[-1]["id"] if messages else after_id
    return {"messages": messages, "next_id": next_id}


@router.post("/chat", operation_id="chat_add", response_model=dict)
def chat_post(payload: dict, db=Depends(get_db)):
    mensagem = str(payload.get("mensagem", "")).strip()
    if not mensagem:
        raise HTTPException(status_code=400, detail="mensagem_vazia")
    msg_id = admin_storage.add_chat(db, "fundador", mensagem)
    return {"id": msg_id}


@router.get("/dashboard", operation_id="dashboard_get", response_model=dict)
def dashboard(db=Depends(get_db)):
    return admin_storage.dashboard_kpis(db)


@router.get("/emails", operation_id="emails_list", response_model=dict)
def emails_list(db=Depends(get_db)):
    return {"items": admin_storage.list_emails(db)}


@router.post("/emails/send", operation_id="emails_send", response_model=dict)
def emails_send(payload: dict, db=Depends(get_db)):
    socio_ids = [int(i) for i in payload.get("socio_ids", [])]
    assunto = str(payload.get("assunto", "")).strip()
    corpo = str(payload.get("corpo", "")).strip()
    if not assunto or not corpo:
        raise HTTPException(status_code=400, detail="campos_em_falta")
    sent, failed = [], []
    for sid in socio_ids:
        socio = admin_storage.get_row(db, "socios", sid)
        if socio is None:
            continue
        email = (socio.get("email") or "").strip()
        if not email:
            failed.append({"id": sid, "erro": "sem_email"})
            continue
        result = send_generic_email(email, assunto, corpo)
        estado = "enviado" if result.fired else "nao_fire"
        admin_storage.record_email(db, email, assunto, corpo, estado, result.error)
        if result.fired:
            sent.append(sid)
        else:
            failed.append({"id": sid, "erro": "smtp_desligado"})
    return {"sent": sent, "failed": failed}
```

**Nota:** a coluna `email` não está em `RESOURCES["socios"]`; para suportar `socio.email`, adicionar `"email"` a `RESOURCES["socios"]["cols"]` em `admin_storage.py` e à lista de cols do ddl de `socios` em `init_admin_tables` (string do CREATE TABLE). Atualizar também o teste de recurso se necessário (o teste `test_all_resources_have_common_id_column` continua válido).

- [ ] **Step 4: Update `admin_storage.py`** — adicionar `"email"` ao recurso `socios`:

Em `RESOURCES`:
```python
    "socios": {
        "cols": [
            "nome", "papel", "participacao", "capital_investido", "capital_moeda",
            "estado", "email", "notas",
        ],
    },
```
E no `_DDL` de `socios` acrescentar `, email TEXT` antes de `notas TEXT`.

- [ ] **Step 5: Run tests**

Run: `.\.venv\Scripts\python.exe -m pytest license-server/tests/test_admin_api.py license-server/tests/test_admin_storage.py -q`
Expected: PASS (todos)

- [ ] **Step 6: Commit**

```bash
git add license-server/admin_api.py license-server/tests/test_admin_api.py license-server/admin_storage.py
git commit -m "feat: API /api/admin (CRUD, chat, dashboard, email)"
```

---

## Task 6: admin_pages.py + templates base/login + estáticos + testes

**Files:**
- Create: `license-server/admin_pages.py`
- Create: `license-server/templates/_base.html`
- Create: `license-server/templates/login.html`
- Create: `license-server/admin_static/admin.css`
- Modify: `license-server/app.py`
- Modify: `license-server/Dockerfile`
- Test: `license-server/tests/test_admin_pages.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests para as páginas /admin/* (login, proteção por sessão)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from admin_auth import COOKIE_NAME, make_session
from app import create_app


def test_login_page_200():
    client = TestClient(create_app())
    assert client.get("/admin/login").status_code == 200


def test_admin_pages_redirect_without_session():
    client = TestClient(create_app())
    for path in ("/admin", "/admin/socios", "/admin/investidores",
                 "/admin/funcionarios", "/admin/fases", "/admin/marcos",
                 "/admin/metas", "/admin/caixa", "/admin/chat", "/admin/emails"):
        resp = client.get(path, follow_redirects=False)
        assert resp.status_code in (302, 303), path


def test_admin_pages_200_with_session():
    client = TestClient(create_app())
    client.cookies.set(COOKIE_NAME, make_session())
    for path in ("/admin", "/admin/socios", "/admin/chat", "/admin/emails"):
        assert client.get(path).status_code == 200, path


def test_login_ok_sets_cookie_and_redirects():
    client = TestClient(create_app())
    resp = client.post("/admin/login", data={"password": "dev-admin-token"},
                       follow_redirects=False)
    assert resp.status_code in (302, 303)
    assert COOKIE_NAME in resp.headers.get("set-cookie", "")


def test_login_bad_password_no_cookie():
    client = TestClient(create_app())
    resp = client.post("/admin/login", data={"password": "errada"},
                       follow_redirects=False)
    assert resp.status_code == 200
    assert COOKIE_NAME not in resp.headers.get("set-cookie", "")
```

- [ ] **Step 2: Run to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest license-server/tests/test_admin_pages.py -q`
Expected: FAIL — module not found

- [ ] **Step 3: Write `admin_pages.py`**

```python
"""Páginas /admin/* (Jinja2) do painel administrativo."""
import os

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

import admin_storage
from admin_auth import COOKIE_NAME, make_session, verify_password, verify_session

router = APIRouter()

_templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "templates")
templates = Jinja2Templates(directory=_templates_dir)


def _authed(request: Request) -> bool:
    cookie = request.cookies.get(COOKIE_NAME, "")
    return bool(verify_session(cookie))


def _render(request: Request, template: str, page: str, **ctx):
    if not _authed(request):
        return RedirectResponse("/admin/login", status_code=302)
    return templates.TemplateResponse(template, {
        "request": request, "page": page, "title": page.title(), **ctx})


@router.get("/admin/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {
        "request": request, "page": "login", "error": ""})


@router.post("/admin/login")
def login_post(request: Request, password: str = Form("")):
    if verify_password(password):
        resp = RedirectResponse("/admin", status_code=302)
        resp.set_cookie(COOKIE_NAME, make_session(), httponly=True,
                        samesite="lax", max_age=7 * 24 * 3600)
        return resp
    return templates.TemplateResponse("login.html", {
        "request": request, "page": "login", "error": "Senha inválida."}, status_code=401)


@router.get("/admin/logout")
def logout():
    resp = RedirectResponse("/admin/login", status_code=302)
    resp.delete_cookie(COOKIE_NAME)
    return resp


def _crud_ctx(request: Request, page: str, resource: str):
    fields = admin_storage.RESOURCES[resource]["cols"]
    return _render(request, "crud.html", page, resource=resource,
                   fields=fields)


@router.get("/admin")
def dashboard(request: Request):
    return _render(request, "dashboard.html", "dashboard")


@router.get("/admin/socios")
def socios(request: Request):
    return _crud_ctx(request, "sócios", "socios")


@router.get("/admin/investidores")
def investidores(request: Request):
    return _crud_ctx(request, "investidores", "investidores")


@router.get("/admin/funcionarios")
def funcionarios(request: Request):
    return _crud_ctx(request, "funcionários", "funcionarios")


@router.get("/admin/fases")
def fases(request: Request):
    return _crud_ctx(request, "fases", "fases")


@router.get("/admin/marcos")
def marcos(request: Request):
    return _crud_ctx(request, "marcos", "marcos")


@router.get("/admin/metas")
def metas(request: Request):
    return _crud_ctx(request, "metas", "metas")


@router.get("/admin/caixa")
def caixa(request: Request):
    return _crud_ctx(request, "caixa", "movimentos_caixa")


@router.get("/admin/chat")
def chat(request: Request):
    return _render(request, "chat.html", "chat")


@router.get("/admin/emails")
def emails(request: Request):
    return _render(request, "emails.html", "emails")
```

- [ ] **Step 4: Write templates**

`license-server/templates/_base.html`:

```html
<!doctype html>
<html lang="pt">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mãouse Admin — {{ title }}</title>
<link rel="stylesheet" href="/admin_static/admin.css">
</head>
<body>
<header class="topbar">
  <div class="brand">🐭 Mãouse <span>Admin</span></div>
  <a href="/admin/logout" class="ghost">Sair</a>
</header>
<div class="layout">
  <nav class="sidebar">
    <a href="/admin" class="{% if page=='dashboard' %}active{% endif %}">Dashboard</a>
    <a href="/admin/socios" class="{% if page=='sócios' %}active{% endif %}">Sócios</a>
    <a href="/admin/investidores" class="{% if page=='investidores' %}active{% endif %}">Investidores</a>
    <a href="/admin/funcionarios" class="{% if page=='funcionários' %}active{% endif %}">Funcionários</a>
    <a href="/admin/fases" class="{% if page=='fases' %}active{% endif %}">Fases</a>
    <a href="/admin/marcos" class="{% if page=='marcos' %}active{% endif %}">Marcos</a>
    <a href="/admin/metas" class="{% if page=='metas' %}active{% endif %}">Metas</a>
    <a href="/admin/caixa" class="{% if page=='caixa' %}active{% endif %}">Caixa</a>
    <a href="/admin/chat" class="{% if page=='chat' %}active{% endif %}">Chat</a>
    <a href="/admin/emails" class="{% if page=='emails' %}active{% endif %}">Emails</a>
  </nav>
  <main class="content">
    {% block content %}{% endblock %}
  </main>
</div>
</body>
</html>
```

`license-server/templates/login.html`:

```html
<!doctype html>
<html lang="pt">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mãouse Admin — Login</title>
<link rel="stylesheet" href="/admin_static/admin.css">
</head>
<body class="login-body">
  <form class="login-card" method="post" action="/admin/login">
    <div class="brand">🐭 Mãouse <span>Admin</span></div>
    <h1>Acesso restrito</h1>
    <label>Senha de administração
      <input type="password" name="password" autofocus required>
    </label>
    {% if error %}<p class="error">{{ error }}</p>{% endif %}
    <button type="submit">Entrar</button>
  </form>
</body>
</html>
```

`license-server/admin_static/admin.css`:

```css
:root { --bg:#0b0f14; --panel:#11161d; --line:#1f2731; --text:#e6edf3;
        --muted:#8b98a5; --accent:#4cc2ff; --ok:#3ddc84; --err:#ff6b6b; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--text);
       font-family: "Segoe UI", system-ui, sans-serif; }
.topbar { display:flex; justify-content:space-between; align-items:center;
          padding:12px 20px; background:var(--panel); border-bottom:1px solid var(--line); }
.brand { font-weight:700; letter-spacing:.5px; }
.brand span { color:var(--accent); }
.layout { display:flex; min-height:calc(100vh - 54px); }
.sidebar { width:200px; background:var(--panel); border-right:1px solid var(--line);
           padding:12px 8px; display:flex; flex-direction:column; gap:2px; }
.sidebar a { color:var(--text); text-decoration:none; padding:9px 12px; border-radius:8px;
             font-size:14px; }
.sidebar a:hover { background:var(--line); }
.sidebar a.active { background:#1b2530; color:var(--accent); }
.content { flex:1; padding:22px 26px; max-width:1100px; }
h1 { font-size:20px; margin:0 0 16px; }
table { width:100%; border-collapse:collapse; background:var(--panel);
        border:1px solid var(--line); border-radius:10px; overflow:hidden; }
th, td { text-align:left; padding:9px 12px; border-bottom:1px solid var(--line);
         font-size:13px; vertical-align:top; }
th { background:#151c24; color:var(--muted); text-transform:uppercase; font-size:11px; }
tr:last-child td { border-bottom:none; }
.card { background:var(--panel); border:1px solid var(--line); border-radius:12px;
        padding:16px 18px; }
.grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:12px; }
.kpi .v { font-size:26px; font-weight:700; color:var(--accent); }
.kpi .l { font-size:12px; color:var(--muted); }
form .row { margin-bottom:12px; }
label { display:block; font-size:12px; color:var(--muted); margin-bottom:4px; }
input, select, textarea { width:100%; padding:9px 11px; background:#0d1219;
        border:1px solid var(--line); border-radius:8px; color:var(--text); font-size:14px; }
textarea { min-height:80px; resize:vertical; }
button { background:var(--accent); color:#06121c; border:none; border-radius:8px;
         padding:10px 16px; font-weight:600; cursor:pointer; font-size:14px; }
button.ghost, a.ghost { background:transparent; color:var(--muted); border:1px solid var(--line);
                        padding:6px 12px; border-radius:8px; text-decoration:none; font-size:13px; }
button.danger { background:var(--err); color:#fff; }
.error { color:var(--err); }
.login-body { display:grid; place-items:center; min-height:100vh; }
.login-card { width:340px; background:var(--panel); border:1px solid var(--line);
              border-radius:14px; padding:28px; display:flex; flex-direction:column; gap:14px; }
.login-card h1 { font-size:18px; }
.panel { background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:16px; margin-top:16px; }
.chat-box { height:340px; overflow-y:auto; display:flex; flex-direction:column; gap:8px;
            background:#0d1219; border:1px solid var(--line); border-radius:10px; padding:12px; }
.msg { background:var(--line); border-radius:10px; padding:8px 12px; max-width:75%; }
.msg .meta { font-size:11px; color:var(--muted); }
.muted { color:var(--muted); }
```

`license-server/Dockerfile` — substituir `COPY license-server/*.py /app/` por:

```dockerfile
COPY license-server /app
```

`license-server/app.py` — adicionar no fim, antes do `return app`, dentro de `create_app()`:

```python
    # Painel administrativo (páginas + API + estáticos)
    from admin_api import router as admin_api_router
    from admin_pages import router as admin_pages_router
    from fastapi.staticfiles import StaticFiles
    admin_static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "admin_static")
    app.mount("/admin_static",
              StaticFiles(directory=admin_static_dir), name="admin_static")
    app.include_router(admin_pages_router)
    app.include_router(admin_api_router)
```

Também importar `os` no topo de `app.py` (já existe: `import os` na linha 2). Confirmar.

- [ ] **Step 5: Run test — create `admin_static/` and `templates/` first**

Run: `.\.venv\Scripts\python.exe -m pytest license-server/tests/test_admin_pages.py -q`
Expected: PASS (5 passed)

- [ ] **Step 6: Run whole license-server suite**

Run: `.\.venv\Scripts\python.exe -m pytest license-server/tests -q --no-header --disable-warnings 2>&1 | Select-String "passed|failed"`
Expected: existing passes intact (only pre-existing known failure may remain)

- [ ] **Step 7: Commit**

```bash
git add license-server/admin_pages.py license-server/templates license-server/admin_static/admin.css license-server/app.py license-server/Dockerfile license-server/tests/test_admin_pages.py
git commit -m "feat: paginas admin (login, dashboard, base) + static + wiring"
```

---

## Task 7: restantes templates/JS (dashboard, chat, emails, crud) + testes de regressão

**Files (create):**
- `license-server/templates/crud.html`
- `license-server/templates/dashboard.html`
- `license-server/templates/chat.html`
- `license-server/templates/emails.html`
- `license-server/admin_static/admin.js`
- `license-server/admin_static/chat.js`
- `license-server/admin_static/emails.js`
- `license-server/admin_static/dashboard.js`

- [ ] **Step 1: Write templates**

`license-server/templates/crud.html`:

```html
{% extends "_base.html" %}
{% block content %}
<h1>{{ title }}</h1>
<div class="panel">
  <form id="entry-form" class="form-grid">
    {% for field in fields %}
    {% if field == 'notas' or field == 'descricao' or field == 'corpo' %}
    <div class="row" style="grid-column:1/-1">
      <label>{{ field.replace('_',' ').title() }}</label>
      <textarea name="{{ field }}" placeholder="{{ field }}"></textarea>
    </div>
    {% else %}
    <div class="row">
      <label>{{ field.replace('_',' ').title() }}</label>
      <input name="{{ field }}" placeholder="{{ field }}">
    </div>
    {% endif %}
    {% endfor %}
    <div class="row" style="grid-column:1/-1">
      <button type="submit" id="save-btn">Adicionar</button>
    </div>
  </form>
</div>
<div class="panel">
  <table id="items-table">
    <thead><tr id="items-head"></tr></thead>
    <tbody id="items-body"></tbody>
  </table>
</div>
<script>
window.ADMIN_RESOURCE = "{{ resource }}";
const ADMIN_FIELDS = {{ fields | tojson }};
</script>
<script src="/admin_static/admin.js"></script>
{% endblock %}
```

`license-server/templates/dashboard.html`:

```html
{% extends "_base.html" %}
{% block content %}
<h1>Dashboard</h1>
<div class="grid" id="kpis"></div>
<script src="/admin_static/dashboard.js"></script>
{% endblock %}
```

`license-server/templates/chat.html`:

```html
{% extends "_base.html" %}
{% block content %}
<h1>Chat privado</h1>
<div class="chat-box" id="chat-box"></div>
<form id="chat-form" class="row" style="margin-top:12px">
  <textarea id="chat-input" placeholder="Escreve uma mensagem..." required></textarea>
  <button type="submit">Enviar</button>
</form>
<script src="/admin_static/chat.js"></script>
{% endblock %}
```

`license-server/templates/emails.html`:

```html
{% extends "_base.html" %}
{% block content %}
<h1>Enviar email aos sócios</h1>
<div class="panel">
  <form id="email-form">
    <div class="row"><label>Destinatários (sócios)</label><div id="socios-list"></div></div>
    <div class="row"><label>Assunto</label><input name="assunto" required></div>
    <div class="row"><label>Corpo</label><textarea name="corpo" required></textarea></div>
    <button type="submit">Enviar</button>
    <p id="email-result" class="muted"></p>
  </form>
</div>
<h1>Histórico</h1>
<div class="panel"><table id="emails-history">
  <thead><tr><th>Para</th><th>Assunto</th><th>Estado</th><th>Erro</th></tr></thead>
  <tbody></tbody>
</table></div>
<script src="/admin_static/emails.js"></script>
{% endblock %}
```

- [ ] **Step 2: Write JS**

`license-server/admin_static/admin.js`:

```js
const RES = window.ADMIN_RESOURCE;
const FIELDS = window.ADMIN_FIELDS;

async function j(url, opts) {
  const r = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!r.ok && r.status !== 404) throw new Error(await r.text());
  try { return await r.json(); } catch { return {}; }
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

async function load() {
  const data = await j(`/api/admin/${RES}`);
  const thead = document.getElementById("items-head");
  const tbody = document.getElementById("items-body");
  thead.innerHTML = "<th>#</th>" + FIELDS.map(f => `<th>${esc(f).replace(/_/g, " ")}</th>`).join("")
    + "<th></th>";
  tbody.innerHTML = (data.items || []).map(item => {
    const tds = FIELDS.map(f => `<td>${esc(item[f])}</td>`).join("");
    return `<tr><td>${item.id}</td>${tds}
      <td>
        <button class="ghost" onclick="editItem(${item.id})">Editar</button>
        <button class="ghost danger" onclick="delItem(${item.id})">Eliminar</button>
      </td></tr>`;
  }).join("");
  window._items = data.items || [];
}

window.editItem = function (id) {
  const item = window._items.find(x => String(x.id) === String(id));
  if (!item) return;
  document.querySelectorAll("#entry-form input, #entry-form textarea")
    .forEach(el => { el.value = item[el.name] ?? ""; });
  const btn = document.getElementById("save-btn");
  btn.textContent = "Guardar";
  btn.dataset.id = id;
};

async function delItem(id) {
  if (!confirm("Eliminar registo?")) return;
  await j(`/api/admin/${RES}/${id}`, { method: "DELETE" });
  await load();
}
window.delItem = delItem;

document.getElementById("entry-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {};
  document.querySelectorAll("#entry-form input, #entry-form textarea")
    .forEach(el => { payload[el.name] = el.value.trim(); });
  const btn = document.getElementById("save-btn");
  if (btn.dataset.id) {
    await j(`/api/admin/${RES}/${btn.dataset.id}`, {
      method: "PATCH", body: JSON.stringify(payload),
    });
    delete btn.dataset.id;
  } else {
    await j(`/api/admin/${RES}`, { method: "POST", body: JSON.stringify(payload) });
  }
  btn.textContent = "Adicionar";
  document.getElementById("entry-form").reset();
  await load();
});

load().catch(console.error);
```

`license-server/admin_static/dashboard.js`:

```js
const LABELS = {
  socios: "Sócios", investidores: "Investidores", funcionarios: "Funcionários",
  pagantes: "Pagantes", maquinas_ativas: "Máquinas ativas",
  fases_concluidas: "Fases concluídas", metas_abertas: "Metas em aberto",
  marcos: "Marcos", chat_mensagens: "Mensagens no chat",
};
fetch("/api/admin/dashboard")
  .then(r => r.json())
  .then(kpi => {
    document.getElementById("kpis").innerHTML = Object.entries(LABELS)
      .map(([k, l]) => `<div class="card kpi">
          <div class="v">${kpi[k] ?? 0}</div><div class="l">${l}</div></div>`)
      .join("");
  })
  .catch(console.error);
```

`license-server/admin_static/chat.js`:

```js
const box = document.getElementById("chat-box");
let afterId = 0;

async function pollNow() {
  try {
    const r = await fetch(`/api/admin/chat?after_id=${afterId}`);
    const data = await r.json();
    (data.messages || []).forEach(m => {
      const div = document.createElement("div");
      div.className = "msg";
      div.innerHTML = `<div class="meta">${new Date(m.created_at * 1000).toLocaleString()}</div>${m.mensagem}</div>`;
      box.appendChild(div);
      afterId = m.id;
    });
    box.scrollTop = box.scrollHeight;
  } catch (e) { /* ignore */ }
}
setInterval(pollNow, 3000);
pollNow();

document.getElementById("chat-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = document.getElementById("chat-input");
  const msg = input.value.trim();
  if (!msg) return;
  await fetch("/api/admin/chat", { method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mensagem: msg }) });
  input.value = "";
  pollNow();
});
```

`license-server/admin_static/emails.js`:

```js
async function loadSocios() {
  const r = await fetch("/api/admin/socios");
  const data = await r.json();
  document.getElementById("socios-list").innerHTML = (data.items || [])
    .map(s => `<label style="display:flex;align-items:center;gap:6px">
      <input type="checkbox" value="${s.id}"> ${s.nome}${s.email ? ` — ${s.email}` : ""}</label>`)
    .join("") || '<span class="muted">Sem sócios registados.</span>';
}

document.getElementById("email-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const ids = [...document.querySelectorAll("#socios-list input:checked")]
    .map(cb => Number(cb.value));
  const assunto = document.querySelector('[name="assunto"]').value.trim();
  const corpo = document.querySelector('[name="corpo"]').value.trim();
  const out = document.getElementById("email-result");
  if (!ids.length) { out.textContent = "Escolhe pelo menos um sócio."; return; }
  const r = await fetch("/api/admin/emails/send", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ socio_ids: ids, assunto, corpo }) });
  const data = await r.json();
  out.textContent = `Enviados: ${data.sent.length} · Sem envio: ${data.failed.length}`;
  loadHistory();
});

async function loadHistory() {
  const r = await fetch("/api/admin/emails");
  const data = await r.json();
  document.querySelector("#emails-history tbody").innerHTML = (data.items || [])
    .map(m => `<tr><td>${m.para}</td><td>${m.assunto}</td><td>${m.estado}</td>
      <td>${m.erro || ""}</td></tr>`).join("");
}

loadSocios();
loadHistory();
```

- [ ] **Step 3: Verify all pages render with session (test já existente cobre as 10 rotas; atualizar teste para incluir todas)** — atualizar `test_admin_pages.py` para verificar 200 em todas as rotas com sessão:

```python
def test_all_admin_pages_200_with_session():
    client = TestClient(create_app())
    client.cookies.set(COOKIE_NAME, make_session())
    for path in ("/admin", "/admin/socios", "/admin/investidores",
                 "/admin/funcionarios", "/admin/fases", "/admin/marcos",
                 "/admin/metas", "/admin/caixa", "/admin/chat", "/admin/emails"):
        assert client.get(path).status_code == 200, path
```

- [ ] **Step 4: Run tests**

Run: `.\.venv\Scripts\python.exe -m pytest license-server/tests -q --no-header --disable-warnings 2>&1 | Select-String "passed|failed"`
Expected: tudo o que passava continua a passar; novos testes passam.

- [ ] **Step 5: Lint (ruff)**

Run: `.\.venv\Scripts\python.exe -m ruff check license-server`
Expected: sem erros (fixar se necessário)

- [ ] **Step 6: Commit**

```bash
git add license-server/templates license-server/admin_static
git add license-server/tests/test_admin_pages.py
git commit -m "feat: templates dashboard/chat/emails/crud + JS"
```

---

## Task 8: render.yaml + verificação final + commit

**Files:**
- Modify: `license-server/render.yaml`

- [ ] **Step 1: Adicionar a env da sessão** a `render.yaml` (junto às outras `sync: false`):

```yaml
      - key: AIRMOUSE_LS_ADMIN_SESSION_SECRET
        sync: false # definir no painel do Render
```

- [ ] **Step 2: Suíte completa + lint**

Run: `.\.venv\Scripts\python.exe -m pytest license-server/tests -q --no-header --disable-warnings 2>&1 | Select-String "passed|failed"`
Run: `.\.venv\Scripts\python.exe -m ruff check license-server`
Expected: suíte verde (excepto a falha pré-existente conhecida de `test_security`); ruff ok.

- [ ] **Step 3: Smoke test local de login + CRUD via TestClient**

Run: `.\.venv\Scripts\python.exe -m pytest license-server/tests/test_admin_pages.py license-server/tests/test_admin_api.py -q`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add license-server/render.yaml
git commit -m "chore: env de sessao admin no render blueprint"
```

---

## Task 9: verificação final (verifier) e resumo

- [ ] **Step 1:** Correr a suíte completa (`license-server/tests`) e `ruff check license-server`.
- [ ] **Step 2:** Confirmar que nenhum endpoint público existente foi quebrado (health, activate, revalidate, webhook, mobile/entitle — cobertos pela suíte).
- [ ] **Step 3:** Resumo final: ficheiros criados/alterados, como fazer login, o que falta no deploy.

---

## Revisão final (reviewer)

Após a tarefa 9, um reviewer verifica: o spec está cumprido (páginas, API, chat, email, KPIs, auth), código limpo (ruff, sem duplicação), testes verdes.