"""Tests for the production license-server URL wiring.

Cobre o gap documentado em docs/DESKTOP_LICENSE_URL.md: sem um endpoint real
embutido no build, a ativação de chaves Pro falha em silêncio. Estes testes
travam esse comportamento para não voltar.
"""
import os

import pytest

import core.envcfg
import core.licensing as lic
from core.envcfg import env_int, env_value


@pytest.fixture(autouse=True)
def _sem_override(monkeypatch):
    """Isola dos overrides reais do ambiente e do `.env` da máquina de teste."""
    monkeypatch.delenv("MAOUSE_LICENSE_URLS", raising=False)
    monkeypatch.delenv("MAOUSE_LICENSE_SERVER_URL", raising=False)
    monkeypatch.setattr(core.envcfg, "_CANDIDATES", ())


# ── Deteção do placeholder ────────────────────────────────────────────

def test_placeholder_url_is_detected(monkeypatch):
    monkeypatch.setattr(lic, "PROD_LICENSE_SERVER_URL", lic.LICENSE_URL_NOT_CONFIGURED)
    assert lic.license_server_configured() is False


def test_real_prod_url_counts_as_configured(monkeypatch):
    monkeypatch.setattr(lic, "PROD_LICENSE_SERVER_URL", "https://abc.onrender.com")
    assert lic.license_server_configured() is True


def test_override_url_counts_as_configured(monkeypatch):
    monkeypatch.setenv("MAOUSE_LICENSE_URLS", "http://127.0.0.1:8899")
    assert lic.license_server_configured() is True


def test_status_message_empty_when_configured(monkeypatch):
    monkeypatch.setenv("MAOUSE_LICENSE_URLS", "http://127.0.0.1:8899")
    assert lic.license_server_status() == ""


def test_status_message_explains_the_gap(monkeypatch):
    monkeypatch.setattr(lic, "PROD_LICENSE_SERVER_URL", lic.LICENSE_URL_NOT_CONFIGURED)
    msg = lic.license_server_status()
    assert lic.LICENSE_URL_NOT_CONFIGURED in msg
    assert "MAOUSE_LICENSE_URLS" in msg


def test_endpoints_never_empty(monkeypatch):
    """Mesmo sem override, tem de haver sempre um endpoint (mesmo que errado)."""
    assert lic.LicenseManager(store_path=":memory:")._endpoints


def test_endpoints_comma_separated_and_stripped(monkeypatch):
    monkeypatch.setenv("MAOUSE_LICENSE_URLS", " http://a.test/ , http://b.test ")
    assert lic.LicenseManager(store_path=":memory:")._endpoints == [
        "http://a.test", "http://b.test",
    ]


# ── Endpoint EMBUTIDO no build (core/_license_endpoint.py) ───────────

def test_baked_endpoint_absent_is_empty(monkeypatch):
    """Sem o módulo gerado (dev), não inventa endpoint."""
    monkeypatch.setattr(lic, "_baked_endpoint", lambda: "")
    assert lic.LicenseManager(store_path=":memory:")._endpoints == [
        lic.LICENSE_URL_NOT_CONFIGURED,
    ]


def test_baked_endpoint_is_used(monkeypatch):
    monkeypatch.setattr(lic, "_baked_endpoint", lambda: "https://baked.onrender.com")
    assert lic.license_server_configured() is True
    assert lic.LicenseManager(store_path=":memory:")._endpoints == [
        "https://baked.onrender.com",
    ]


def test_baked_endpoint_loses_to_env_override(monkeypatch):
    """O endpoint embebido é o default; MAOUSE_LICENSE_URLS manda."""
    monkeypatch.setattr(lic, "_baked_endpoint", lambda: "https://baked.onrender.com")
    monkeypatch.setenv("MAOUSE_LICENSE_URLS", "http://127.0.0.1:8899")
    assert lic.LicenseManager(store_path=":memory:")._endpoints == [
        "http://127.0.0.1:8899",
    ]


def test_baked_endpoint_loses_to_env_server_url(monkeypatch):
    monkeypatch.setattr(lic, "_baked_endpoint", lambda: "https://baked.onrender.com")
    monkeypatch.setenv("MAOUSE_LICENSE_SERVER_URL", "https://build-time.test")
    assert lic.LicenseManager(store_path=":memory:")._endpoints == [
        "https://build-time.test",
    ]


def test_baked_endpoint_empty_falls_back_to_placeholder(monkeypatch):
    """Um módulo gerado com URL vazio NÃO pode parecer 'configurado'."""
    monkeypatch.setattr(lic, "_baked_endpoint", lambda: "")
    monkeypatch.setattr(lic, "PROD_LICENSE_SERVER_URL", lic.LICENSE_URL_NOT_CONFIGURED)
    assert lic.license_server_configured() is False


# ── tools/gen_license_endpoint.py ─────────────────────────────────────

def _load_gen_module():
    import importlib.util
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "tools", "gen_license_endpoint.py")
    spec = importlib.util.spec_from_file_location("gen_license_endpoint", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_gen_prefers_argv_over_env(monkeypatch):
    monkeypatch.setenv("MAOUSE_LICENSE_SERVER_URL", "https://da-env.test")
    assert _load_gen_module().resolve_url(["x", "https://do-argv.test/"]) == \
        "https://do-argv.test"


def test_gen_falls_back_to_env(monkeypatch):
    monkeypatch.setenv("MAOUSE_LICENSE_SERVER_URL", "https://da-env.test/")
    assert _load_gen_module().resolve_url(["x"]) == "https://da-env.test"


def test_gen_empty_when_nothing_set(monkeypatch):
    monkeypatch.delenv("MAOUSE_LICENSE_SERVER_URL", raising=False)
    assert _load_gen_module().resolve_url(["x"]) == ""


def test_gen_writes_importable_module(monkeypatch, tmp_path):
    mod = _load_gen_module()
    out = tmp_path / "_license_endpoint.py"
    monkeypatch.setattr(mod, "OUT_PATH", str(out))
    mod.main(["x", "https://gerado.test"])
    ns = {}
    exec(compile(out.read_text(encoding="utf-8"), str(out), "exec"), ns)
    assert ns["LICENSE_SERVER_URL"] == "https://gerado.test"


def test_gen_empty_url_stays_detectable_as_placeholder(monkeypatch, tmp_path):
    """Gerado sem URL tem de dar o placeholder — o binário avisa em vez de
    parecer configurado."""
    mod = _load_gen_module()
    out = tmp_path / "_license_endpoint.py"
    monkeypatch.setattr(mod, "OUT_PATH", str(out))
    monkeypatch.delenv("MAOUSE_LICENSE_SERVER_URL", raising=False)
    mod.main(["x"])
    ns = {}
    exec(compile(out.read_text(encoding="utf-8"), str(out), "exec"), ns)
    assert ns["LICENSE_SERVER_URL"] == ""


# ── Ativação com o servidor por configurar ────────────────────────────

def test_activate_refuses_when_server_unconfigured(monkeypatch):
    monkeypatch.setattr(lic, "PROD_LICENSE_SERVER_URL", lic.LICENSE_URL_NOT_CONFIGURED)
    lm = lic.LicenseManager(store_path=":memory:")
    assert lm.activate("MAO-TESTE-12345") is False
    assert lm.last_error == "servidor_nao_configurado"


def test_failed_activation_does_not_block_free(monkeypatch):
    """Regressão: ativar com chave errada deixava o utilizador sem Free."""
    monkeypatch.setattr(lic, "PROD_LICENSE_SERVER_URL", "https://x.test")
    monkeypatch.setattr(lic.LicenseClient, "activate",
                        lambda self, key, mid, weak=False: (_ for _ in ()).throw(
                            lic.LicenseError("chave_invalida")))
    lm = lic.LicenseManager(store_path=":memory:", trial_seconds=300)
    assert lm.activate("MAO-ERRADA") is False
    assert lm.last_error == "chave_invalida"
    assert lm.is_blocked() is False
    assert lm.tier is lic.Tier.FREE


def test_empty_key_rejected_without_network():
    lm = lic.LicenseManager(store_path=":memory:")
    assert lm.activate("   ") is False
    assert lm.last_error == "chave_vazia"


# ── Checkout do Paddle ────────────────────────────────────────────────

def test_open_checkout_refuses_without_vendor_id(monkeypatch):
    """Sem vendor_id e sem URL de produto, não abrir o browser numa página de erro."""
    opened = []
    monkeypatch.setattr(lic.webbrowser, "open", lambda url, new=0: opened.append(url))
    monkeypatch.setitem(lic.PADDLE_PRODUCT_URLS, "lifetime", "")
    lm = lic.LicenseManager(store_path=":memory:")
    assert lm.open_checkout("lifetime", 0) is False
    assert opened == []


def test_open_checkout_allows_configured_product_url(monkeypatch):
    opened = []
    monkeypatch.setattr(lic.webbrowser, "open", lambda url, new=0: opened.append(url) or True)
    monkeypatch.setitem(lic.PADDLE_PRODUCT_URLS, "lifetime",
                        "https://buy.paddle.com/x/12345")
    lm = lic.LicenseManager(store_path=":memory:")
    assert lm.open_checkout("lifetime", 0) is True
    assert opened == ["https://buy.paddle.com/x/12345"]


# ── Leitor de .env ────────────────────────────────────────────────────

def test_env_value_prefers_real_env(monkeypatch, tmp_path):
    f = tmp_path / ".env"
    f.write_text("X_TEST_TOKEN=do_ficheiro\n", encoding="utf-8")
    monkeypatch.setenv("X_TEST_TOKEN", "da_env_var")
    assert env_value("X_TEST_TOKEN", files=[str(f)]) == "da_env_var"


def test_env_value_falls_back_to_env_file(monkeypatch, tmp_path):
    monkeypatch.delenv("X_TEST_TOKEN", raising=False)
    f = tmp_path / ".env"
    f.write_text('# comentario\n\nX_TEST_TOKEN="do_ficheiro"\nOUTRA=1\n', encoding="utf-8")
    assert env_value("X_TEST_TOKEN", files=[str(f)]) == "do_ficheiro"


def test_env_value_missing_returns_empty(tmp_path):
    assert env_value("X_NAO_EXISTE", files=[str(tmp_path / ".env")]) == ""


def test_env_value_ignores_unreadable_file(tmp_path):
    assert env_value("X", files=[str(tmp_path / "sub" / ".env")]) == ""


@pytest.mark.parametrize("raw,expected", [("42", 42), ("0", 0), ("", 7), ("abc", 7)])
def test_env_int(monkeypatch, tmp_path, raw, expected):
    monkeypatch.delenv("X_TEST_NUM", raising=False)
    f = tmp_path / ".env"
    f.write_text(f"X_TEST_NUM={raw}\n", encoding="utf-8")
    assert env_int("X_TEST_NUM", default=7, files=[str(f)]) == expected


def test_env_int_missing_returns_default(tmp_path):
    assert env_int("X_NAO_EXISTE", default=7, files=[str(tmp_path / ".env")]) == 7
