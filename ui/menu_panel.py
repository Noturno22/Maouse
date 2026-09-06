"""Side menu panel: icon+text action buttons, entrance animation and a
language switcher. Uses SVG icons from assets/brand/icons.
"""
from PySide6.QtCore import QEasingCurve, QSize, QVariantAnimation
from PySide6.QtGui import QAction, QColor, QIcon
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from i18n import I18N, tr
from ui.icon_kits import menu_icon
from ui.theme import FONT_HELP, breathe_glow


class MenuButton(QPushButton):
    """PushButton with a left SVG icon and a translated label."""

    ICON_SIZE = QSize(20, 20)

    def __init__(self, key, icon, checkable=False, parent=None):
        super().__init__(parent)
        self._key = key
        self._icon = menu_icon(icon)
        self._locked = False
        self.setObjectName("MenuBtn")
        self.setCheckable(checkable)
        self.setIcon(self._icon)
        self.setIconSize(self.ICON_SIZE)
        self.update_text()
        I18N.language_changed.connect(lambda *_: self.update_text())

    def update_text(self):
        prefix = "  " if not self.icon().isNull() else ""
        self.setText(prefix + tr(self._key))

    def set_key(self, key):
        self._key = key
        self.update_text()

    def set_locked(self, locked: bool):
        """Aspeto 'bloqueado' (cinzento, Pro) mantendo o botão clicável: o clique
        continua a disparar o gate/paywall no handler da janela."""
        locked = bool(locked)
        if locked == self._locked:
            return
        self._locked = locked
        self.setProperty("locked", locked)
        if locked:
            pm = self._icon.pixmap(self.ICON_SIZE, QIcon.Mode.Disabled, QIcon.State.Off)
            self.setIcon(QIcon(pm))
            self.setToolTip("Disponível no Mãouse Pro — upgrade no menu")
        else:
            self.setIcon(self._icon)
            self.setToolTip("")
        self.style().unpolish(self)
        self.style().polish(self)


class LanguageButton(QPushButton):
    """Globe button that opens a menu with the six available languages."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MenuLangBtn")
        self.setIcon(menu_icon("menu-language"))
        self.setIconSize(QSize(16, 16))
        self.update_text()
        I18N.language_changed.connect(lambda *_: self.update_text())
        I18N.language_changed.connect(lambda *_: self._rebuild_menu())
        self._rebuild_menu()

    def _rebuild_menu(self):
        menu = QMenu(self)
        menu.setObjectName("MenuLangMenu")
        for code in I18N.LANGS:
            act = QAction(I18N.native(code), menu)
            act.setCheckable(True)
            act.setChecked(code == I18N.lang)
            act.triggered.connect(lambda _=False, c=code: I18N.set_lang(c))
            menu.addAction(act)
        self.setMenu(menu)

    def update_text(self):
        self.setText(" " + I18N.native(I18N.lang))


class SectionLabel(QLabel):
    def __init__(self, key, parent=None):
        super().__init__(parent)
        self._key = key
        self.setObjectName("MenuSection")
        self.setFont(FONT_HELP)
        self.update_text()
        I18N.language_changed.connect(lambda *_: self.update_text())

    def update_text(self):
        self.setText(tr(self._key))


class MenuPanel(QWidget):
    """Painel lateral re-desenhado com ícones SVG, animação de entrada e
    seletor de idioma (topo-direito)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MenuPanel")

        root = self._self_layout = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(0)

        # Header: language switcher numa linha própria.
        row = QHBoxLayout()
        row.setSpacing(6)
        self.lang_btn = LanguageButton(self)
        row.addStretch(1)
        row.addWidget(self.lang_btn)
        root.addLayout(row)
        root.addSpacing(8)

        self._section1 = SectionLabel("section.controlo")
        root.addWidget(self._section1)
        root.addSpacing(6)

        self.btn_pause = MenuButton("btn.pause", "menu-pause", checkable=False)
        self.btn_save = MenuButton("btn.save", "menu-save")
        self.btn_voice = MenuButton("btn.voice", "menu-voice", checkable=True)
        self.btn_snap = MenuButton("btn.snap", "menu-snap", checkable=True)
        for btn in (self.btn_pause, self.btn_save, self.btn_voice, self.btn_snap):
            btn.setFixedHeight(34)
            root.addWidget(btn)
            root.addSpacing(6)

        root.addWidget(MenuPanel._make_divider())
        root.addSpacing(6)

        self._section2 = SectionLabel("section.sistema")
        root.addWidget(self._section2)
        root.addSpacing(6)

        self.btn_camera = MenuButton("btn.camera", "menu-camera", checkable=True)
        self.btn_help = MenuButton("btn.help", "menu-help", checkable=True)
        self.btn_config = MenuButton("btn.config", "menu-gear")
        self.btn_quit = MenuButton("btn.quit", "menu-quit")
        for btn in (self.btn_camera, self.btn_help, self.btn_config, self.btn_quit):
            btn.setFixedHeight(34)
            root.addWidget(btn)
            root.addSpacing(6)

        root.addStretch(1)

        # Upgrade Pro — destaque visual quando em modo Free (sem ícone: texto só).
        self.btn_upgrade = MenuButton("btn.upgrade", "menu-upgrade")
        self.btn_upgrade.setObjectName("MenuBtnUpgrade")
        self.btn_upgrade.setIcon(QIcon())
        self.btn_upgrade.setFixedHeight(34)
        root.addWidget(self.btn_upgrade)
        self._upgrade_pulse = None

        self._play_entrance()

    def set_upgrade_pulse(self, active: bool):
        """Liga/desliga o brilho pulsante do botão de upgrade (Free: ativo)."""
        if active and self._upgrade_pulse is None:
            self._upgrade_pulse = breathe_glow(
                self.btn_upgrade, QColor(231, 76, 60),
                min_alpha=70, max_alpha=200, min_blur=4, max_blur=18, ms=800,
            )
        elif not active and self._upgrade_pulse is not None:
            self._upgrade_pulse.stop()
            self.btn_upgrade.setGraphicsEffect(None)
            self._upgrade_pulse = None

    # ── Animação de entrada (fade + slide) ───────────────────────────
    def _play_entrance(self):
        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)

        self._anim = QVariantAnimation(self)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(350)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

        def tick(val):
            self._effect.setOpacity(val)
            m = self._self_layout.contentsMargins()
            self._self_layout.setContentsMargins(
                int((1 - val) * 14), m.top(), m.right(), m.bottom()
            )

        self._anim.valueChanged.connect(tick)
        self._anim.start()

    # ── Helpers ──────────────────────────────────────────────────────
    @staticmethod
    def _make_divider():
        bar = QFrame()
        bar.setObjectName("MenuDivider")
        bar.setFixedHeight(1)
        return bar
