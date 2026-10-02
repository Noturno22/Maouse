"""Tests end-to-end da assinatura: a chave EMBUTIDA no PC tem de ser a
contraparte da que o license-server assina.

Este ficheiro existe porque os testes de lease anteriores injectavam sempre um
par novo via ``public_key=pub``: provavam que a *logica* de verificacao
funciona, mas nunca que a chave *realmente embarcada* em
``core/licensing_public_key.pem`` corresponde à do servidor. Quando as duas
divergiram, o desktop passou a rejeitar todas as leases sem que um teste
ficasse vermelho.
"""
import os

import pytest
from cryptography.hazmat.primitives import serialization as ser
from cryptography.hazmat.primitives.asymmetric import ec

import core.licensing as lic

_SERVER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "license-server")
_SERVER_PUBLIC = os.path.join(_SERVER_DIR, "public.pem")
_SERVER_PRIVATE = os.path.join(_SERVER_DIR, "private.pem")
_BAKED_PUBLIC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "core", "licensing_public_key.pem")


def _public_numbers(path):
    with open(path, "rb") as fh:
        key = ser.load_pem_public_key(fh.read())
    return key.public_numbers()


def _sign(payload, private_key):
    import jwt
    return jwt.encode(payload, private_key, algorithm="ES256")


def _payload(machine_id, **over):
    import time
    now = int(time.time())
    base = {
        "sub": f"machine:{machine_id}",
        "key_hash": "abc",
        "tier": "pro",
        "exp": now + 7 * 24 * 3600,
        "iat": now,
        "revocation_nonce": 0,
        "use_seq": 1,
        "session_id": "s",
        "server_time": now,
    }
    base.update(over)
    return base


# ── Invariante que o CI pode sempre correr (nenhum segredo involved) ──

def test_baked_public_key_is_the_server_public_key():
    """A chave embebida no PC e a publica do servidor sao o mesmo par.

    Este e' o guard que fecha o buraco: uma rotacao de chaves feita so de
    um dos lados passa a ser vermelha no CI, sem nunca tocar na privada.
    """
    assert os.path.isfile(_SERVER_PUBLIC), (
        "license-server/public.pem nao esta versionado. A publica nao e "
        "segredo e e o unico lado que o CI consegue comparar com a chave do "
        "PC sem acesso ao segredo."
    )
    assert os.path.isfile(_BAKED_PUBLIC), (
        "core/licensing_public_key.pem desapareceu: sem a publica o PC nao "
        "valida nenhuma lease."
    )
    assert _public_numbers(_BAKED_PUBLIC) == _public_numbers(_SERVER_PUBLIC), (
        "A chave publica do PC NAO e a do license-server. O desktop vai "
        "rejeitar todas as leases do servidor (InvalidSignatureError) e a "
        "licenca Pro nunca activa. Roda o par todo de uma vez."
    )


# ── O caminho completo, com a chave privada real ──

@pytest.mark.skipif(not os.path.isfile(_SERVER_PRIVATE),
                    reason="a privada nao esta no repo (correto); corre localmente")
def test_pc_validates_a_lease_signed_by_the_server_private_key():
    with open(_SERVER_PRIVATE, "rb") as fh:
        priv = ser.load_pem_private_key(fh.read(), password=None)

    lm = lic.LicenseManager(store_path=":memory:", trial_seconds=60)
    lm.lease = _sign(_payload(lm._machine), priv)
    lm.tier = lic.Tier.PRO

    assert lm.is_pro_offline_valid(), (
        "Uma lease assinada pela privada REAL do servidor foi rejeitada pela "
        "chave real do PC. As chaves divergiram."
    )
    assert not lm.is_blocked()


@pytest.mark.skipif(not os.path.isfile(_SERVER_PRIVATE),
                    reason="a privada nao esta no repo (correto); corre localmente")
def test_mobile_pro_lease_also_passes_local_validation():
    with open(_SERVER_PRIVATE, "rb") as fh:
        priv = ser.load_pem_private_key(fh.read(), password=None)

    lm = lic.LicenseManager(store_path=":memory:", trial_seconds=60)
    lm.lease = _sign(_payload(lm._machine, tier="mobile_pro"), priv)
    lm.tier = lic.Tier.PRO

    assert lm.is_pro_offline_valid(), (
        "O lease mobile_pro tem de passar a mesma verificacao — e' o mesmo "
        "formato, so muda o tier."
    )


# ── Prova de que o guard tem dentes ──

def test_lease_signed_by_a_foreign_key_is_rejected():
    """Se isto passasse, o guard acima seria vacuo: qualquer chave serviria.

    O bug original era um guard que nunca correu; um guard que nunca falha
    seria o mesmo erro pelo lado oposto.
    """
    foreign = ec.generate_private_key(ec.SECP256R1())
    lm = lic.LicenseManager(store_path=":memory:", trial_seconds=60)
    lm.lease = _sign(_payload(lm._machine), foreign)
    lm.tier = lic.Tier.PRO

    assert not lm.is_pro_offline_valid(), (
        "Uma lease assinada por uma chave que nao e a do servidor foi aceite. "
        "A verificacao de assinatura nao esta a funcionar."
    )
    assert lm.is_blocked()


@pytest.mark.skipif(not os.path.isfile(_SERVER_PRIVATE),
                    reason="a privada nao esta no repo (correto); corre localmente")
def test_expired_lease_from_the_real_pair_is_rejected():
    with open(_SERVER_PRIVATE, "rb") as fh:
        priv = ser.load_pem_private_key(fh.read(), password=None)

    lm = lic.LicenseManager(store_path=":memory:", trial_seconds=60)
    lm.lease = _sign(_payload(lm._machine, exp=0), priv)
    lm.tier = lic.Tier.PRO

    assert not lm.is_pro_offline_valid(), "Uma lease expirada foi aceite."
