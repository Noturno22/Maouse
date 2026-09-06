"""Splash de arranque do Mãouse: mostra o logo (logo.png) antes da UI.

Usa ``assets/brand/logo.png`` (logo com fundo escuro, 1254x1254) redimensionado
para o ecrã do splash — sem composição extra. Tudo é best-effort: se algo
falhar, devolve ``None`` e a UI abre normalmente.

No Windows o splash está desligado (o arranque é melhor sem ele).
"""

import os
import sys

from PySide6.QtCore import QElapsedTimer, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen


def splash_enabled():
    """True fora do Windows; no Windows o splash é desligado."""
    return not sys.platform.startswith("win")


def splash_path():
    """Resolve o caminho do logo.png (source, exe congelado ou cwd)."""
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [os.path.join(here, "assets", "brand", "logo.png")]
    if getattr(sys, "frozen", False):
        candidates.insert(
            0,
            os.path.join(os.path.dirname(sys.executable), "assets", "brand", "logo.png"),
        )
        candidates.insert(
            1,
            os.path.join(
                os.path.dirname(sys.executable),
                "_internal",
                "assets",
                "brand",
                "logo.png",
            ),
        )
    candidates.append(os.path.join(os.getcwd(), "assets", "brand", "logo.png"))
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def render_splash(size=460):
    """Devolve um QPixmap com o logo redimensionado, ou None se falhar."""
    path = splash_path()
    if not path:
        return None
    try:
        logo = QPixmap(path)
        if logo.isNull():
            return None
        return logo.scaled(
            size,
            size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    except Exception:
        return None


def show_splash(ms=480, force=False):
    """Mostra o splash centrado no ecrã principal.

    No Windows devolve ``None`` (splash desligado) a menos que ``force`` seja
    True (usado nos testes). Bloqueia o thread durante ``ms`` (processando
    eventos para pintar) e devolve o ``QSplashScreen`` para o chamador
    terminar com ``finish()``. Devolve ``None`` também se o asset estiver
    indisponível — nesse caso o chamador deve abrir a UI normalmente.
    """
    if not splash_enabled() and not force:
        return None
    pixmap = render_splash()
    if pixmap is None:
        return None
    app = QApplication.instance()
    splash = QSplashScreen(pixmap)
    if app is not None and app.primaryScreen() is not None:
        geo = app.primaryScreen().geometry()
        splash.move(geo.center() - splash.rect().center())
    splash.setEnabled(False)
    splash.show()
    splash.repaint()
    if ms and ms > 0:
        timer = QElapsedTimer()
        timer.start()
        while timer.elapsed() < ms:
            QApplication.processEvents()
    return splash
