"""Tests for revalidate: renew lease, revoke via nonce, anti-replay."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from fastapi.testclient import TestClient


def _client():
    return TestClient(create_app())


def _activate(client, machine="M1"):
    resp = client.post("/admin/keys", json={
        "email": "r@x.com", "admin_token": "dev-admin-token"})
    key = resp.json()["key"]
    r = client.post("/api/v1/activate", json={"key": key, "machine_id": machine})
    return r


def _activate_with_key(client, machine="M1"):
    """Como `_activate`, mas devolve tambem a chave em texto (que a resposta
    de /activate, por seguranca, nao devolve)."""
    resp = client.post("/admin/keys", json={
        "email": "r@x.com", "admin_token": "dev-admin-token"})
    key = resp.json()["key"]
    act = client.post("/api/v1/activate", json={
        "key": key, "machine_id": machine}).json()
    return key, act["lease"]


def test_revalidate_returns_new_lease():
    client = _client()
    act = _activate(client).json()
    resp = client.post("/api/v1/revalidate", json={
        "machine_id": "M1", "old_lease": act["lease"]})
    assert resp.status_code == 200
    assert resp.json()["tier"] == "pro"
    assert resp.json()["lease"]


def test_revalidate_rejects_stale_nonce_after_revoke():
    client = _client()
    act = _activate(client).json()
    r = client.post("/api/v1/revoke", json={
        "machine_id": "M1", "admin_token": "dev-admin-token"})
    assert r.status_code == 200
    resp = client.post("/api/v1/revalidate", json={
        "machine_id": "M1", "old_lease": act["lease"]})
    assert resp.status_code == 403


def test_revalidate_rejects_unknown_machine():
    client = _client()
    resp = client.post("/api/v1/revalidate", json={
        "machine_id": "NOBODY", "old_lease": "garbage"})
    assert resp.status_code == 403


# ── Lease atrasado: 409 + "reativar" (recovery) ───────────────────────

def _use_seq(lease: str) -> int:
    import base64
    import json
    payload = lease.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    return int(json.loads(base64.urlsafe_b64decode(payload))["use_seq"])


def test_revalidate_stale_lease_asks_to_reactivate():
    """O cliente está um lease ATRÁS do servidor: 409 com recovery, não 403
    genérico — é o que permite ao cliente reativar a chave sozinho."""
    client = _client()
    first = _activate(client).json()["lease"]
    # o servidor avança (o cliente renova e grava)
    ok = client.post("/api/v1/revalidate", json={
        "machine_id": "M1", "old_lease": first})
    assert ok.status_code == 200
    assert _use_seq(ok.json()["lease"]) == _use_seq(first) + 1

    # agora volta atrás no tempo e reenvia o lease antigo
    stale = client.post("/api/v1/revalidate", json={
        "machine_id": "M1", "old_lease": first})
    assert stale.status_code == 409
    assert stale.json() == {"error": "seq_repetido", "recovery": "reativar"}


def test_revalidate_current_lease_renews_repeatedly():
    """Renovar o lease ACTUAL várias vezes é legítimo (a app renova a cada ~6d)."""
    client = _client()
    lease = _activate(client).json()["lease"]
    for _ in range(3):
        r = client.post("/api/v1/revalidate", json={
            "machine_id": "M1", "old_lease": lease})
        assert r.status_code == 200
        assert _use_seq(r.json()["lease"]) == _use_seq(lease) + 1
        lease = r.json()["lease"]


def test_revalidate_client_ahead_resyncs_server():
    """A base de dados do servidor foi reposta para trás de um lease já emitido.
    É o espelho do 409: aceita-se e o contador volta a alinhar, em vez de
    bloquear o cliente para sempre."""
    client = _client()
    lease = _activate(client).json()["lease"]
    renewed = client.post("/api/v1/revalidate", json={
        "machine_id": "M1", "old_lease": lease}).json()["lease"]

    # o servidor "esquece-se" do estado: repomos o contador para trás
    from storage import connect, set_last_use_seq
    db = connect()
    try:
        set_last_use_seq(db, "M1", 0)
        db.commit()
    finally:
        db.close()

    r = client.post("/api/v1/revalidate", json={
        "machine_id": "M1", "old_lease": renewed})
    assert r.status_code == 200
    assert _use_seq(r.json()["lease"]) == _use_seq(renewed) + 1


def test_reactivate_after_409_recovers():
    """Fluxo completo do bug: 409 -> o cliente reativa a chave -> volta a
    funcionar sem intervenção do utilizador."""
    client = _client()
    key, first = _activate_with_key(client)
    client.post("/api/v1/revalidate", json={
        "machine_id": "M1", "old_lease": first})
    assert client.post("/api/v1/revalidate", json={
        "machine_id": "M1", "old_lease": first}).status_code == 409

    # o cliente guarda a chave e reativa
    again = client.post("/api/v1/activate", json={
        "key": key, "machine_id": "M1"})
    assert again.status_code == 200
    fresh = again.json()["lease"]
    r = client.post("/api/v1/revalidate", json={
        "machine_id": "M1", "old_lease": fresh})
    assert r.status_code == 200
    assert r.json()["tier"] == "pro"


def test_revoke_still_wins_over_reactivation_path():
    """O 409 é só para estado revertido — um nonce revogado continua 403 e
    NÃO se resolve a reativar."""
    client = _client()
    act = _activate(client).json()
    client.post("/api/v1/revalidate", json={
        "machine_id": "M1", "old_lease": act["lease"]})
    client.post("/api/v1/revoke", json={
        "machine_id": "M1", "admin_token": "dev-admin-token"})

    stale = client.post("/api/v1/revalidate", json={
        "machine_id": "M1", "old_lease": act["lease"]})
    assert stale.status_code == 403
    assert "recovery" not in stale.json()
