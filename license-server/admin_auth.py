"""Sessão de administrador: cookie assinado HMAC (sem lib externa).

O cookie transporta apenas timestamp + nonce, assinado com HMAC-SHA256 usando
AIRMOUSE_LS_ADMIN_SESSION_SECRET. A senha do login compara com
AIRMOUSE_LS_ADMIN_TOKEN (todo-poderoso do painel).
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time

COOKIE_NAME = "maouse_admin"
MAX_AGE = 7 * 24 * 3600
_DEV_SECRET = "dev-session-secret"


def _secret() -> str:
    return os.getenv("AIRMOUSE_LS_ADMIN_SESSION_SECRET", _DEV_SECRET)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def _sign(body: str) -> str:
    return hmac.new(_secret().encode(), body.encode(), hashlib.sha256).hexdigest()


def make_session() -> str:
    payload = json.dumps({"t": int(time.time()),
                          "n": secrets.token_hex(8)},
                         separators=(",", ":")).encode()
    body = _b64(payload)
    return f"{body}.{_sign(body)}"


def verify_session(cookie: str) -> bool:
    try:
        body, _, sig = cookie.partition(".")
        if not body or not sig:
            return False
        if not hmac.compare_digest(_sign(body), sig):
            return False
        payload = json.loads(_unb64(body.decode() if isinstance(body, bytes) else body))
        if int(payload["t"]) + MAX_AGE < time.time():
            return False
        return True
    except Exception:
        return False


def verify_password(password: str) -> bool:
    expected = os.getenv("AIRMOUSE_LS_ADMIN_TOKEN", "dev-admin-token")
    return hmac.compare_digest(password, expected)


def require_admin(request) -> None:
    """Dependency FastAPI: rejeita com 401 se a sessão não for válida."""
    from fastapi import HTTPException
    cookie = request.cookies.get(COOKIE_NAME, "")
    if not verify_session(cookie):
        raise HTTPException(status_code=401, detail="nao_autenticado")