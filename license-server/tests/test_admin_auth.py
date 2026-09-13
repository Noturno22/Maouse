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