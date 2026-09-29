"""ES256 JWT lease: assinatura assimétrica + revocation_nonce + server_time.

O servidor assina com chave PRIVADA EC; o cliente verifica com a PÚBLICA.
A secret simétrica NUNCA sai do servidor (spec V3).
"""
import os
import time

import jwt
from cryptography.hazmat.primitives import serialization

LEASE_TTL_SECONDS = 7 * 24 * 3600
CLOCK_SKEW_TOLERANCE = 600


def _private_key_path() -> str:
    """Caminho OU conteudo PEM da chave privada (ver `_load_private_key`).

    O `os.getenv(nome, default)` e um buraco: devolve `""` quando a variavel
    **esta definida e vazia**, e so usa o default quando ela nao existe. No
    Render, onde o `private.pem` do repositorio nao esta, a diferenca entre
    "renomeei a variavel e deixei-a vazia" e "a variavel nao existe" e a
    diferenca entre um `open("")` a rebentar na primeira activacao e um erro
    que diz o que falta. Ver DEPLOY_RENDER.md.
    """
    valor = os.getenv("MAOUSE_LS_PRIVATE_KEY")
    if valor is not None and not valor.strip():
        raise RuntimeError(
            "MAOUSE_LS_PRIVATE_KEY esta definida mas vazia. No Render a variavel "
            "tem de conter o PEM inteiro (ver DEPLOY_RENDER.md 2), ou entao "
            "apaga a variavel para o servidor usar o private.pem ao lado."
        )
    if valor is None:
        return os.path.join(os.path.dirname(__file__), "private.pem")
    return valor


def _load_private_key():
    """Aceita MAOUSE_LS_PRIVATE_KEY como caminho OU conteúdo PEM (Render)."""
    p = _private_key_path()
    if p.lstrip().startswith("-----BEGIN"):
        return serialization.load_pem_private_key(p.encode(), password=None)
    with open(p, "rb") as fh:
        return serialization.load_pem_private_key(fh.read(), password=None)


def _load_public_key_embedded():
    """Lê public.pem ao lado de private.pem (chave emparelhada do servidor)."""
    from cryptography.hazmat.primitives import serialization as _ser
    priv_dir = os.path.dirname(_private_key_path())
    pub_f = os.path.join(priv_dir, "public.pem")
    try:
        with open(pub_f, "rb") as fh:
            return _ser.load_pem_public_key(fh.read())
    except OSError as exc:
        raise RuntimeError(
            f"sem chave publica para verificar as leases: nem MAOUSE_LS_PUBLIC_KEY "
            f"esta definida nem ha um public.pem ao lado da privada (procurado em "
            f"{pub_f!r}). No Render define MAOUSE_LS_PUBLIC_KEY com o PEM inteiro."
        ) from exc


def _load_public_key():
    """Prefere env MAOUSE_LS_PUBLIC_KEY (caminho para public.pem ou PEM);
    senão lê public.pem emparelhado ao lado de private.pem."""
    pub_pem = os.getenv("MAOUSE_LS_PUBLIC_KEY", "")
    if pub_pem:
        if os.path.isfile(pub_pem):
            with open(pub_pem, "rb") as fh:
                return serialization.load_pem_public_key(fh.read())
        return serialization.load_pem_public_key(pub_pem.encode())
    return _load_public_key_embedded()


def sign(claims: dict) -> str:
    """Assina um dict de claims e devolve o JWT ES256."""
    key = _load_private_key()
    return jwt.encode(claims, key, algorithm="ES256")


def issue_lease(machine_id: str, key_hash: str, revocation_nonce: int,
                session_id: str, use_seq: int, tier: str = "pro") -> str:
    now = int(time.time())
    claims = {
        "sub": f"machine:{machine_id}",
        "key_hash": key_hash,
        "tier": tier,
        "session_id": session_id,
        "use_seq": use_seq,
        "revocation_nonce": revocation_nonce,
        "iat": now,
        "nbf": now - CLOCK_SKEW_TOLERANCE,
        "exp": now + LEASE_TTL_SECONDS,
        "server_time": now,
    }
    return sign(claims)


def decode_jwt(token: str) -> dict:
    """Decodifica + verifica a assinatura ES256 usando a chave pública
    (não confia em 'alg:none')."""
    key = _load_public_key()
    return jwt.decode(token, key, algorithms=["ES256"])
