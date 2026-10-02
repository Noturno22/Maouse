"""Fixture partilhada pelos testes que falam com o `RemoteServer`.

O `auth` passou a exigir um lease assinado. Estes testes exercitam o
protocolo, não a chave de produção, e a privada do license-server não está no
repo (nem deve estar) — por isso injectamos um par de chaves de teste.

O par e as leases vivem em `tests/lease_test_keys.py`; aqui fica só a fixture
que faz o `core.licensing` aceitar essa chave. Use
`pytestmark = pytest.mark.usefixtures("patched_public_key")` no módulo.
"""
import pytest

from tests.lease_test_keys import TEST_SIGNING_KEY


@pytest.fixture
def patched_public_key(monkeypatch):
    import core.licensing as lic

    monkeypatch.setattr(lic, "_load_public_key", lambda: TEST_SIGNING_KEY.public_key())
