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
            "estado", "email", "notas",
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
        "socios": f"CREATE TABLE IF NOT EXISTS socios (" f"{_COMMON_COLS}," " nome TEXT, papel TEXT, participacao TEXT, capital_investido TEXT, capital_moeda TEXT, estado TEXT, email TEXT, notas TEXT);",
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