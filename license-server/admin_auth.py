"""Sessão de administrador: cookie assinado HMAC (sem lib externa).

O cookie transporta apenas timestamp + nonce, assinado com HMAC-SHA256 usando
AIRMOUSE_LS_ADMIN_SESSION_SECRET. A senha do login compara com
AIRMOUSE_LS_ADMIN_TOKEN (todo-poderoso do painel).
"""
import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time

from fastapi import Request

COOKIE_NAME = "maouse_admin"
MAX_AGE = 7 * 24 * 3600
_DEV_SECRET = "dev-session-secret"
_DEV_TOKEN = "dev-admin-token"

_logger = logging.getLogger("maouse.admin")
_dev_secret_warned = [False]
_dev_token_warned = [False]


def _warn_once(flag: list, message: str) -> None:
    if flag[0]:
        return
    flag[0] = True
    _logger.warning(message)


def _secret() -> str:
    value = os.getenv("AIRMOUSE_LS_ADMIN_SESSION_SECRET")
    if value is None:
        _warn_once(_dev_secret_warned,
                   "AIRMOUSE_LS_ADMIN_SESSION_SECRET nao definido; a usar segredo "
                   "de desenvolvimento (inseguro em producao)")
        return _DEV_SECRET
    return value


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
    expected = os.getenv("AIRMOUSE_LS_ADMIN_TOKEN")
    if expected is None:
        _warn_once(_dev_token_warned,
                   "AIRMOUSE_LS_ADMIN_TOKEN nao definido; a usar senha de "
                   "desenvolvimento (inseguro em producao)")
        expected = _DEV_TOKEN
    return hmac.compare_digest(password, expected)


def require_admin(request: Request) -> None:
    """Dependency FastAPI: rejeita com 401 se a sessão não for válida."""
    from fastapi import HTTPException
    cookie = request.cookies.get(COOKIE_NAME, "")
    if not verify_session(cookie):
        raise HTTPException(status_code=401, detail="nao_autenticado")
