"""Guarda de build: impede distribuir .exe com o placeholder do license-server.

Cobre tools/check_prod_license_url.py — `url_is_ready` e o comportamento do main.
"""
import tools.check_prod_license_url as guard


def test_placeholder_rejected():
    assert not guard.url_is_ready("https://licenses.maouse.example.com")


def test_empty_rejected():
    assert not guard.url_is_ready("")


def test_http_rejected():
    assert not guard.url_is_ready("http://licenses.maouse.app")


def test_template_rejected():
    assert not guard.url_is_ready("https://<service>.onrender.com")


def test_real_https_accepted():
    assert guard.url_is_ready("https://maouse-license-server.onrender.com")


def test_trailing_slash_normalized():
    assert guard.url_is_ready("https://maouse-license-server.onrender.com/")
