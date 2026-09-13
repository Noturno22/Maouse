"""Tests para as páginas /admin/* (login, proteção por sessão)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from admin_auth import COOKIE_NAME, make_session
from app import create_app
from fastapi.testclient import TestClient


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


def test_all_admin_pages_200_with_session():
    client = TestClient(create_app())
    client.cookies.set(COOKIE_NAME, make_session())
    for path in ("/admin", "/admin/socios", "/admin/investidores",
                 "/admin/funcionarios", "/admin/fases", "/admin/marcos",
                 "/admin/metas", "/admin/caixa", "/admin/chat", "/admin/emails"):
        assert client.get(path).status_code == 200, path
