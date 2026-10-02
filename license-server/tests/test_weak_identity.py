"""A identidade fraca da máquina: registada, não bloqueada.

O buraco que esta série fecha era o `machine_id` degenerado ser **a mesma
constante em todas as máquinas** sem hardware, e o `licensing.py:163` validar a
licença por ele. Fechou-se no cliente: o id degradado deriva de um sal por
máquina, e duas máquinas dão ids diferentes.

O que fica aqui em cima é a outra metade, e é a que interessa ao dono: mesmo
com ids separados, uma identidade que não vem de hardware não é prova de nada,
e o servidor tem de saber quais são para poder olhar para elas. Não para
bloquear — bloquear quem pagou por causa de uma máquina esquisita seria
trocar receita por uma garantia que ninguém pediu.
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import storage
from app import create_app
from fastapi.testclient import TestClient


def _client():
    return TestClient(create_app())


def _issue(client, email="tester@example.com"):
    resp = client.post("/admin/keys", json={
        "email": email, "admin_token": "dev-admin-token"})
    assert resp.status_code == 200
    return resp.json()["key"]


def test_uma_maquina_fraca_fica_marcada_e_nao_bloqueada(tmp_path, monkeypatch):
    """A Identidade fraca não impede a activação. Só fica registada."""
    monkeypatch.setenv("MAOUSE_LS_DB", str(tmp_path / "lic.db"))
    client = _client()
    resp = client.post("/api/v1/activate", json={
        "key": _issue(client), "machine_id": "MAQ-SEM-HARDWARE",
        "machine_weak": True})
    assert resp.status_code == 200, (
        "a activação foi recusada. A decisão tomada foi avisar e funcionar: "
        f"recusar transformava uma máquina esquisita num ticket de suporte para "
        f"quem já pagou. Resposta: {resp.status_code} {resp.text}"
    )
    assert resp.json()["tier"] == "pro"


def test_um_cliente_antigo_que_nao_manda_o_campo_continua_a_ser_aceite(tmp_path, monkeypatch):
    """A ausência do campo tem de ser aceitável, e guardada como não-marcada.

    Um cliente velho não manda `machine_weak`. Recusá-lo seria rebentar a
   (product de quem actualiza o cliente antes do servidor. E guardar a ausência
    como "forte" seria a mentira pelo outro lado: `weak_identity=0` diz "não foi
    marcado", e o painel tem de o ler assim.
    """
    monkeypatch.setenv("MAOUSE_LS_DB", str(tmp_path / "lic.db"))
    client = _client()
    resp = client.post("/api/v1/activate", json={
        "key": _issue(client), "machine_id": "MAQ-VELHA"})
    assert resp.status_code == 200, resp.text

    conn = storage.connect()
    try:
        assert storage.machine_is_weak(conn, "MAQ-VELHA") is False
    finally:
        conn.close()


def test_as_duas_maquinas_fracas_aparecem_na_lista_do_dono(tmp_path, monkeypatch):
    monkeypatch.setenv("MAOUSE_LS_DB", str(tmp_path / "lic.db"))
    client = _client()
    for i, maq in enumerate(("MAQ-FRACA-1", "MAQ-FRACA-2")):
        resp = client.post("/api/v1/activate", json={
            "key": _issue(client, f"pessoa{i}@x.com"), "machine_id": maq,
            "machine_weak": True})
        assert resp.status_code == 200, resp.text
    resp = client.post("/api/v1/activate", json={
        "key": _issue(client, "forte@x.com"), "machine_id": "MAQ-FORTE"})
    assert resp.status_code == 200, resp.text

    conn = storage.connect()
    try:
        fracas = {m["machine_id"] for m in storage.weak_machines(conn)}
    finally:
        conn.close()
    assert fracas == {"MAQ-FRACA-1", "MAQ-FRACA-2"}, (
        f"a lista de identidades fracas está errada: {fracas}. A máquina com "
        f"hardware não pode aparecer, e as duas sem hardware têm de aparecer — "
        f"é a lista que o dono olha para decidir o que fazer."
    )


def test_a_migracao_acrescenta_a_coluna_a_uma_base_ja_existente(tmp_path, monkeypatch):
    """O `CREATE TABLE IF NOT EXISTS` não chega, e este teste diz porquê.

    Numa base de produção a tabela `machines` já existe, e a forma antiga não
    tem `weak_identity`. Se a migração não correr, a activação passa a rebentar
    com um `OperationalError: no such column` — na produção, no momento em que
    alguém paga. Este teste constrói a base na forma **antiga** à mão e
    verifica que a migração a traz para a nova, sem perder o que lá estava.
    """
    caminho = tmp_path / "velha.db"
    conn = sqlite3.connect(caminho)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript("""
            CREATE TABLE machines (
                machine_id TEXT PRIMARY KEY,
                key_hash TEXT NOT NULL,
                activated_at INTEGER NOT NULL,
                last_use_seq INTEGER NOT NULL DEFAULT 0,
                last_seen INTEGER NOT NULL DEFAULT 0
            );
        """)
        conn.execute(
            "INSERT INTO machines(machine_id, key_hash, activated_at)"
            " VALUES('MAQ-ANTIGA','HASH',100)")
        conn.commit()
        cols_antes = {r["name"] for r in conn.execute("PRAGMA table_info(machines)")}
        assert "weak_identity" not in cols_antes, "sanity: a base ja estava nova"

        storage.init_db(conn)          # o arranque normal
        cols_depois = {r["name"] for r in conn.execute("PRAGMA table_info(machines)")}
        assert "weak_identity" in cols_depois, (
            "a migracao nao acrescenta a coluna a uma base existente. Em "
            "producao isto rebenta na activacao, com 'no such column'."
        )
        # A máquina que já lá estava continua lá, e não foi marcada como forte.
        row = conn.execute(
            "SELECT machine_id, weak_identity FROM machines").fetchone()
        assert row["machine_id"] == "MAQ-ANTIGA", "a migracao perdeu uma maquina"
        assert row["weak_identity"] == 0, (
            "a migracao marcou uma maquina antiga como identidade forte. "
            "Desconhecida nao e forte: o DEFAULT tem de ser 0."
        )
    finally:
        conn.close()

    # Idempotente: `init_db` corre a cada arranque, e na segunda vez nao pode
    # rebentar com "duplicate column name".
    conn = sqlite3.connect(caminho)
    conn.row_factory = sqlite3.Row
    try:
        storage.init_db(conn)
        storage.init_db(conn)
    finally:
        conn.close()


def test_machine_is_weak_diz_nao_sei_a_quem_nao_esta_na_base(tmp_path, monkeypatch):
    """`None` e não `False` para uma máquina que ninguém activou.

    Uma máquina ausente da base ainda não disse nada sobre a sua identidade.
    Devolver `False` — "forte" — seria a mesma mentira que a migração evita,
    outra vez e pelo caminho mais discreto: um `if machine_is_weak(...)` que
    deixa passar tudo.
    """
    monkeypatch.setenv("MAOUSE_LS_DB", str(tmp_path / "lic.db"))
    conn = storage.connect()
    try:
        storage.init_db(conn)   # `connect()` so abre: a base nasce no arranque
        assert storage.machine_is_weak(conn, "MAQ-NAO-ACTIVADA") is None, (
            "uma maquina que ninguem activou voltou como 'forte'. Tem de ser "
            "None: ausente nao e forte."
        )
    finally:
        conn.close()
