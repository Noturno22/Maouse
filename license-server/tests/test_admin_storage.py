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