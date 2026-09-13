"""Tests para a API JSON /api/admin/* (CRUD, chat, dashboard, email)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from admin_auth import COOKIE_NAME, make_session
from app import create_app
from fastapi.testclient import TestClient


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
    for key in ("socios", "investidores", "pagantes", "maquinas_ativas",
                "fases_concluidas", "metas_abertas", "marcos"):
        assert key in kpi


def test_email_send_records_history_when_smtp_disabled():
    client = _client()
    socio_id = client.post("/api/admin/socios",
                           json={"nome": "S1", "estado": "ativo",
                                 "email": "socio@maouse.test"}).json()["id"]
    resp = client.post("/api/admin/emails/send",
                       json={"socio_ids": [socio_id], "assunto": "A",
                             "corpo": "B"})
    assert resp.status_code == 200
    entries = client.get("/api/admin/emails").json()["items"]
    assert entries[0]["assunto"] == "A"
