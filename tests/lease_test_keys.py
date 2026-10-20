"""Par de chaves e leases de teste para o gate de entitlement do `RemoteServer`.

O `auth` exige um lease assinado. Estes testes exercitam o protocolo, não a
chave de produção, e a privada do license-server não está no repo (nem deve
estar) — por isso injectamos um par de chaves descartável.

Vive num módulo próprio, e não no `conftest.py`, por uma razão concreta: sem
`__init__.py`, o pytest importa `conftest.py` com o nome `conftest`, enquanto
`from tests.conftest import ...` importa-o com o nome `tests.conftest`. São
duas instâncias distintas, cada uma com a sua `TEST_SIGNING_KEY` gerada à
partida — a fixture assinava com uma chave e o teste usava a outra, e tudo
falhava com `assinatura_invalida`.
"""
import time

import jwt
from cryptography.hazmat.primitives.asymmetric import ec

TEST_SIGNING_KEY = ec.generate_private_key(ec.SECP256R1())


def make_test_lease(tier="mobile_pro", exp_delta=7 * 24 * 3600, key=None):
    now = int(time.time())
    return jwt.encode(
        {
            "sub": "machine:telemovel",
            "tier": tier,
            "exp": now + exp_delta,
            "iat": now,
            "revocation_nonce": 0,
            "use_seq": 1,
        },
        key or TEST_SIGNING_KEY,
        algorithm="ES256",
    )


VALID_LEASE = make_test_lease()
