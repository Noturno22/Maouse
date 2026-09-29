"""Structured logging for Maouse.

Single logger tree (``maouse``) with console + rotating file output.
The file lands in ``%LOCALAPPDATA%\\Maouse\\logs\\maouse.log`` on Windows
(or ``./logs`` when LOCALAPPDATA is unavailable), which survives across
runs and keeps the console clean.
"""
import logging
import os
import time
from logging.handlers import RotatingFileHandler

LOGGER_NAME = "maouse"
DEFAULT_LEVEL = logging.INFO

log = logging.getLogger(LOGGER_NAME)

# RastreioVerbose de quem mexe no rato (camara vs telemovel). Diagnostico:
# AIRMOUSE_TRACE=1 no arranque. Silencioso por omissao.
TRACE = os.environ.get("AIRMOUSE_TRACE", "").strip() not in ("", "0", "false")

_FMT = "%(asctime)s %(levelname)-5s %(name)s: %(message)s"


def _log_dir():
    base = os.environ.get("LOCALAPPDATA")
    if base:
        path = os.path.join(base, "Maouse", "logs")
    else:
        path = os.path.join(".", "logs")
    try:
        os.makedirs(path, exist_ok=True)
        return path
    except OSError:
        return "."


def setup_logging(level=DEFAULT_LEVEL, console=True, log_file=None):
    """Configura handlers do logger raiz ``maouse``. Idempotente."""
    log.setLevel(level)
    for h in list(log.handlers):
        log.removeHandler(h)
    log.propagate = False

    fmt = logging.Formatter(_FMT, datefmt="%Y-%m-%d %H:%M:%S")
    if console:
        ch = logging.StreamHandler()
        ch.setLevel(level)
        ch.setFormatter(fmt)
        log.addHandler(ch)
    if log_file is None:
        log_file = os.path.join(_log_dir(), "maouse.log")
    fh = RotatingFileHandler(
        log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8",
    )
    fh.setLevel(level)
    fh.setFormatter(fmt)
    log.addHandler(fh)
    return log


def get_logger(name=""):
    if name:
        return logging.getLogger(f"{LOGGER_NAME}.{name}")
    return log


def trace(msg, *args):
    """Rastreio de quem mexe no rato, com tempo monotónico de alta resolução.

    O formato do log tem resolução de 1 s e o emissor corre a 180 Hz: sem o
    ``monotonic`` não dava para intercalar a câmara e o telemóvel.
    """
    if TRACE:
        log.info("[%9.3f] " + msg, time.monotonic(), *args)
