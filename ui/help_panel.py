"""Toggleable help overlay panel — cards, grid de atalhos, barra de pesquisa."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from i18n import I18N, tr
from ui.icon_kits import menu_icon
from ui.theme import (
    ACCENT,
    FONT_PRIMARY_BOLD,
    gesture_color,
)

HELP_BG_SOLID = "#0C0C18"
HELP_BORDER = "#2A2A45"

# Ícones Unicode por secção de gestos
_SECTION_ICONS = {
    "help.sec.move": "help-move",
    "help.sec.scroll": "help-scroll",
    "help.sec.bright": "help-brightness",
    "help.sec.media": "help-media",
    "help.sec.window": "help-windows",
    "help.sec.kb": "menu-gear",
    "help.sec.voice": "menu-voice",
}


def _dot(gesture):
    color = gesture_color(gesture)
    return f'<span style="color:{color.name()};font-size:13px;">&#9679;</span>'


def _icon(name, size):
    return menu_icon(name, size=size)


def _icon_label(icon_name, text, size=16):
    """QLabel com ícone SVG à esquerda + texto."""
    lbl = QLabel()
    pm = menu_icon(icon_name, size=size).pixmap(size, size)
    lbl.setPixmap(pm)
    lbl.setText(f"  {text}")
    return lbl


def _val(key):
    return tr(key)


# Cada secção: (chave_título_i18n, [ (gesture|None, chave_gesto, chave_ação) ])
SECTIONS = [
    ("help.sec.move", [
        (None, "help.g.move", "help.g.one"),
        (None, "help.g.click", ""),
        (None, "help.g.mid", "help.g.right"),
    ]),
    ("help.sec.scroll", [
        (None, "help.g.scroll", "help.g.scroll_act"),
        (None, "help.g.vol", "help.g.vol_act"),
    ]),
    ("help.sec.bright", [
        (None, "help.g.peace_l", "help.g.dim"),
        (None, "help.g.peace_r", "help.g.raise"),
    ]),
    ("help.sec.media", [
        (None, "help.g.thumb", "help.g.play"),
        (None, "help.g.pinky", "help.g.copy"),
        (None, "help.g.shaka", "help.g.paste"),
        (None, "help.g.2fist", "help.g.wind"),
        (None, "help.g.bye", "help.g.min"),
        (None, "help.g.zoomm", "help.g.zoom"),
    ]),
    ("help.sec.window", [
        (None, "help.g.swipe", "help.g.nextwin"),
        (None, "help.g.swipel", "help.g.prevwin"),
        (None, "help.g.hold", "help.g.switch"),
        (None, "help.g.peace_toggle", "help.g.ui_toggle"),
    ]),
]

KB_SHORTCUTS = [
    ("[ / ]", "help.kb.gain"),
    (", / .", "help.kb.smooth"),
    ("M", "help.kb.snap"),
    ("C", "help.kb.cam"),
    ("A", "help.kb.auto"),
    ("V", "help.kb.voice"),
    ("S", "help.kb.save"),
    ("espaço", "help.kb.pause"),
    ("Q", "help.kb.quit"),
    ("F1", "help.kb.help"),
]


class HelpPanel(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("HelpPanel")
        self.setFixedWidth(420)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.hide()

        # Cabeçalho fixo
        header = QWidget(self)
        header.setObjectName("HelpPanelHeader")
        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(14, 12, 12, 10)
        hlay.setSpacing(10)

        self._icon_lbl = QLabel()
        self._icon_lbl.setPixmap(_icon("menu-help", 22).pixmap(22, 22))
        hlay.addWidget(self._icon_lbl)

        txt = QVBoxLayout()
        txt.setSpacing(1)
        self._title = QLabel(tr("help.title"))
        self._title.setObjectName("HelpTitle")
        self._title.setFont(FONT_PRIMARY_BOLD)
        self._subtitle = QLabel(tr("help.subtitle"))
        self._subtitle.setObjectName("HelpSubtitle")
        txt.addWidget(self._title)
        txt.addWidget(self._subtitle)
        hlay.addLayout(txt)
        hlay.addStretch()
        self._header = header

        # Barra de pesquisa
        self._search = QLineEdit()
        self._search.setObjectName("HelpSearch")
        self._search.setPlaceholderText(tr("help.search_placeholder"))
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._filter)

        # Corpo com scroll
        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setStyleSheet(
            f"QScrollArea {{ background: transparent; border: none; }}"
            f"QScrollArea > QWidget > QWidget {{ background: {HELP_BG_SOLID}; }}"
            f"QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}"
            f"QScrollBar::handle:vertical {{ background: #3A3A5A; border-radius: 4px; min-height: 24px; }}"  # noqa: E501
            f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}"
            f"QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}"  # noqa: E501
        )

        self._body = None
        self._build_body()

        # Layout externo
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._header)
        outer.addWidget(self._search)
        outer.addWidget(self._scroll, 1)

        I18N.language_changed.connect(lambda *_: self._build_body())

    # ── Conteúdo ──────────────────────────────────────────────────────
    def _build_body(self):
        if self._body is not None:
            self._scroll.takeWidget()
            self._body.deleteLater()
        body = QWidget()
        body.setObjectName("HelpPanelBody")
        self._body = body
        lay = QVBoxLayout(body)
        lay.setContentsMargins(12, 8, 10, 12)
        lay.setSpacing(0)

        self._title.setText(tr("help.title"))
        self._subtitle.setText(tr("help.subtitle"))

        # Secções de gestos em cards
        for sec_key, rows in SECTIONS:
            card = QFrame()
            card.setObjectName("HelpCard")
            card_lay = QVBoxLayout(card)
            card_lay.setContentsMargins(10, 8, 10, 8)
            card_lay.setSpacing(2)

            icon_key = _SECTION_ICONS.get(sec_key)
            if icon_key:
                sec = _icon_label(icon_key, tr(sec_key))
            else:
                sec = QLabel(tr(sec_key))
            sec.setObjectName("HelpCardTitle")
            card_lay.addWidget(sec)

            for gesture, gk, ak in rows:
                dot = _dot(gesture) if gesture is not None else (
                    '<span style="color:#3A3A5A;font-size:12px;">&#8226;</span>'
                )
                gesto = _val(gk)
                acao = _val(ak) if ak else ""
                if acao:
                    row = QLabel(f"{dot} {gesto}  ·  <b>{acao}</b>")
                else:
                    row = QLabel(f"{dot} {gesto}")
                row.setObjectName("HelpRow")
                row.setWordWrap(True)
                row.setTextFormat(Qt.RichText)
                card_lay.addWidget(row)

            lay.addWidget(card)
            lay.addSpacing(6)

        # Atalhos de teclado em grid 2 colunas
        kb_card = QFrame()
        kb_card.setObjectName("HelpCard")
        kb_lay = QVBoxLayout(kb_card)
        kb_lay.setContentsMargins(10, 8, 10, 8)
        kb_lay.setSpacing(4)

        kb_title = _icon_label("menu-gear", tr("help.sec.kb"))
        kb_title.setObjectName("HelpCardTitle")
        kb_lay.addWidget(kb_title)

        kb_grid = QGridLayout()
        kb_grid.setSpacing(4)
        for i, (combo, ak) in enumerate(KB_SHORTCUTS):
            row = i // 2
            col = (i % 2) * 2
            key_lbl = QLabel(
                f'<span style="color:{ACCENT.name()};'
                f"font-family:'Consolas';font-weight:bold;\">{combo}</span>"
            )
            key_lbl.setTextFormat(Qt.RichText)
            kb_grid.addWidget(key_lbl, row, col)
            desc_lbl = QLabel(_val(ak))
            desc_lbl.setObjectName("HelpRow")
            kb_grid.addWidget(desc_lbl, row, col + 1)
        kb_lay.addLayout(kb_grid)
        lay.addWidget(kb_card)
        lay.addSpacing(6)

        # Voz
        voice_card = QFrame()
        voice_card.setObjectName("HelpCard")
        vc_lay = QVBoxLayout(voice_card)
        vc_lay.setContentsMargins(10, 8, 10, 8)
        vc_lay.setSpacing(4)
        voice_title = _icon_label("menu-voice", tr("help.sec.voice"))
        voice_title.setObjectName("HelpCardTitle")
        vc_lay.addWidget(voice_title)
        voice_row = QLabel(tr("help.voice_tip"))
        voice_row.setObjectName("HelpRow")
        voice_row.setTextFormat(Qt.RichText)
        voice_row.setWordWrap(True)
        vc_lay.addWidget(voice_row)
        lay.addWidget(voice_card)

        lay.addStretch(1)
        self._scroll.setWidget(body)

    # ── Filtro de pesquisa ────────────────────────────────────────────
    def _filter(self, text):
        text = text.strip().lower()
        if not self._body:
            return
        for card in self._body.findChildren(QFrame):
            if card.objectName() != "HelpCard":
                continue
            if not text:
                card.show()
                continue
            visible_rows = 0
            for row in card.findChildren(QLabel):
                if row.objectName() == "HelpRow":
                    if text in row.text().lower():
                        row.show()
                        visible_rows += 1
                    else:
                        row.hide()
            card.setVisible(visible_rows > 0)

    # ── Toggle ────────────────────────────────────────────────────────
    def toggle(self):
        if self.isVisible():
            self.hide()
        else:
            self._fit()
            self.show()
            self.raise_()

    def _fit(self):
        if self.parent():
            ph = self.parent().height()
            self.setFixedHeight(min(ph - 40, 560))
            self.move(12, int(ph * 0.15))
