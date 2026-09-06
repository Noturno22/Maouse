"""Splash de arranque do Mãouse: mostra o logo (splash.svg) antes da UI.

Renderizado a partir do SVG da marca (``assets/brand/splash/splash.svg``) via
``QSvgRenderer`` — sem dependências extra. Tudo é best-effort: se algo falhar
(asset ausente, QtSvg indisponível), devolve ``None`` e a UI abre normalmente.
"""

import os
import sys

from PySide6.QtCore import QElapsedTimer, QRectF, Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication, QSplashScreen


def splash_path():
    """Resolve o caminho do splash.svg (source, exe congelado ou cwd)."""
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [os.path.join(here, "assets", "brand", "splash", "splash.svg")]
    if getattr(sys, "frozen", False):
        candidates.insert(
            0,
            os.path.join(
                os.path.dirname(sys.executable), "assets", "brand", "splash", "splash.svg"
            ),
        )
        candidates.insert(
            1,
            os.path.join(
                os.path.dirname(sys.executable),
                "_internal",
                "assets",
                "brand",
                "splash",
                "splash.svg",
            ),
        )
    candidates.append(os.path.join(os.getcwd(), "assets", "brand", "splash", "splash.svg"))
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def render_splash(size=460):
    """Devolve um QPixmap com o logo renderizado, ou None se falhar."""
    path = splash_path()
    if not path:
        return None
    try:
        renderer = QSvgRenderer(path)
        if not renderer.isValid():
            return None
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter, QRectF(0, 0, size, size))
        painter.end()
        return pixmap
    except Exception:
        return None


def show_splash(ms=480):
    """Mostra o splash centrado no ecrã principal.

    Bloqueia o thread durante ``ms`` (processando eventos para pintar) e
    devolve o ``QSplashScreen`` para o chamador terminar com ``finish()``.
    Devolve ``None`` se o asset/QtSvg estiver indisponível — nesse caso o
    chamador deve abrir a UI normalmente.
    """
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
