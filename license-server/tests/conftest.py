import pytest


@pytest.fixture(autouse=True)
def _test_env(tmp_path, monkeypatch):
    monkeypatch.setenv("MAOUSE_LS_DB", str(tmp_path / "ls.db"))
    monkeypatch.setenv("MAOUSE_LS_SECRET", "test-jwt-secret")
    monkeypatch.setenv("MAOUSE_LS_ADMIN_TOKEN", "dev-admin-token")
    monkeypatch.setenv("MAOUSE_PADDLE_WEBHOOK_SECRET", "pdl_test_secret")
    from keys import ensure_test_keypair
    ensure_test_keypair(tmp_path)
