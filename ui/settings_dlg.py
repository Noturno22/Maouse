"""Settings dialog — sidebar navigation + painéis agrupados."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from config import SMOOTH_PRESETS
from core.licensing import Tier, is_pro_locked
from i18n import tr
from ui.icon_kits import menu_icon
from ui.theme import FONT_MONO, FONT_PRIMARY, MAIN_STYLESHEET
from ui.tune_slider import TuneSlider


# ── Sidebar item (checkable button) ────────────────────────────────
def _sidebar_button(text, icon_name=None, parent=None):
    btn = QPushButton(text, parent)
    btn.setObjectName("SettingsSidebarItem")
    btn.setCheckable(True)
    btn.setFixedHeight(42)
    btn.setCursor(Qt.PointingHandCursor)
    if icon_name:
        btn.setIcon(menu_icon(icon_name))
    return btn


# ── Group helpers ───────────────────────────────────────────────────
def _group(title, caption):
    g = QGroupBox(title)
    g.setFont(FONT_PRIMARY)
    lay = QVBoxLayout()
    lay.setSpacing(10)
    if caption:
        cap = QLabel(caption)
        cap.setObjectName("KeyCaption")
        cap.setWordWrap(True)
        lay.addWidget(cap)
    g.setLayout(lay)
    return g, lay


class SettingsDialog(QDialog):

    def __init__(self, cfg, smooth_name, parent=None, license_mgr=None):
        super().__init__(parent)
        self._cfg = cfg
        self._smooth_name = smooth_name
        self._tier = license_mgr.tier if license_mgr is not None else Tier.FREE
        self.setWindowTitle("Definições — Mãouse")
        self.setObjectName("SettingsDialog")
        self.setStyleSheet(MAIN_STYLESHEET)
        self.setMinimumSize(640, 480)
        self.resize(680, 600)
        self._build()

    # ── PRO checkbox helper ──────────────────────────────────────────
    def _pro_checkbox(self, feature, text, enabled, caption=None):
        wrapper = QVBoxLayout()
        ch = QCheckBox(text)
        locked = is_pro_locked(self._tier, feature)
        ch.setChecked(enabled and not locked)
        if locked:
            ch.setEnabled(False)
            ch.setText(f"{text}  [PRO]")
            ch.setToolTip("Disponível no Mãouse Pro — clique em UPGRADE PRO no menu.")
        wrapper.addWidget(ch)
        if caption:
            cap = QLabel(caption)
            cap.setObjectName("KeyCaption")
            cap.setWordWrap(True)
            wrapper.addWidget(cap)
        return ch, wrapper

    # ── Build ────────────────────────────────────────────────────────
    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(0)
        lay.setContentsMargins(0, 0, 0, 0)

        # ── Header fixo ──────────────────────────────────────────
        header = QFrame()
        header.setObjectName("HelpPanelHeader")
        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(20, 14, 20, 14)
        chip = QLabel("AJUSTES")
        chip.setObjectName("HeroChip")
        hlay.addWidget(chip)
        hlay.addSpacing(10)
        title = QLabel("Definições")
        title.setObjectName("HeroTitle")
        hlay.addWidget(title)
        hlay.addStretch()
        lay.addWidget(header)

        # ── Corpo: sidebar + stacked panels ──────────────────────
        body = QHBoxLayout()
        body.setSpacing(0)
        body.setContentsMargins(0, 0, 0, 0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("SettingsSidebar")
        sidebar.setFixedWidth(170)
        slay = QVBoxLayout(sidebar)
        slay.setContentsMargins(0, 8, 0, 8)
        slay.setSpacing(0)

        self._sidebar_buttons = []
        nav_items = [
            ("settings.nav.cursor", "nav-cursor"),
            ("settings.nav.features", "nav-features"),
            ("settings.nav.voice", "menu-voice"),
            ("settings.nav.camera", "menu-camera"),
            ("settings.nav.remote", "nav-remote"),
            ("settings.nav.trading", "nav-trading"),
        ]
        for key, icon_name in nav_items:
            btn = _sidebar_button(tr(key), icon_name)
            btn.clicked.connect(lambda checked, b=btn: self._on_nav(b))
            slay.addWidget(btn)
            self._sidebar_buttons.append(btn)
        slay.addStretch()
        body.addWidget(sidebar)

        # Stacked panels
        self._stack = QStackedWidget()
        self._build_cursor_panel()
        self._build_features_panel()
        self._build_voice_panel()
        self._build_camera_panel()
        self._build_remote_panel()
        self._build_trading_panel()
        body.addWidget(self._stack, 1)
        lay.addLayout(body, 1)

        # ── Footer ───────────────────────────────────────────────
        footer = QFrame()
        footer.setObjectName("HelpPanelHeader")
        flay = QHBoxLayout(footer)
        flay.setContentsMargins(20, 10, 20, 10)
        reset = QPushButton(tr("settings.reset_defaults"))
        reset.setObjectName("SettingsButtonGhost")
        reset.clicked.connect(self._reset_defaults)
        flay.addWidget(reset)
        flay.addStretch()
        cancel = QPushButton("Cancelar")
        cancel.setObjectName("SettingsButtonGhost")
        cancel.clicked.connect(self.reject)
        flay.addWidget(cancel)
        save = QPushButton("Gravar")
        save.setObjectName("SettingsButton")
        save.setFixedWidth(120)
        save.setFixedHeight(36)
        save.clicked.connect(self._save)
        flay.addWidget(save)
        lay.addWidget(footer)

        # Ativa o primeiro painel
        self._on_nav(self._sidebar_buttons[0])

    # ── Sidebar navigation ──────────────────────────────────────────
    def _on_nav(self, active_btn):
        for btn in self._sidebar_buttons:
            btn.setChecked(btn is active_btn)
        idx = self._sidebar_buttons.index(active_btn)
        self._stack.setCurrentIndex(idx)

    # ── Painel 1: Cursor ────────────────────────────────────────────
    def _build_cursor_panel(self):
        panel = QWidget()
        panel.setObjectName("SettingsPanel")
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(20, 16, 20, 16)
        pl.setSpacing(12)

        sub = QLabel("Ajusta o rácio de movimento, suavidade e estabilidade.")
        sub.setObjectName("HeroSubtitle")
        sub.setWordWrap(True)
        pl.addWidget(sub)

        g, gl = _group("Ganho do cursor", "Quão rápido o cursor segue a mão.")
        self._gain_sl = TuneSlider("Rácio de movimento", lambda v: f"{v / 10:.1f}")
        self._gain_sl.setRange(6, 50)
        self._gain_sl.setValue(int(self._cfg.move_gain * 10))
        gl.addWidget(self._gain_sl)
        pl.addWidget(g)

        s, sl = _group("Suavidade", "Entre um movimento suave e um reativo.")
        self._smooth_cb = QComboBox()
        self._smooth_cb.setObjectName("SettingsCombo")
        for name, _, _ in SMOOTH_PRESETS:
            self._smooth_cb.addItem(name)
        idx = next((i for i, (n, _, _) in enumerate(SMOOTH_PRESETS) if n == self._smooth_name), 1)
        self._smooth_cb.setCurrentIndex(idx)
        sl.addWidget(self._smooth_cb)
        pl.addWidget(s)

        p2, p2l = _group("Estabilidade", "Zona morta e estabilidade do gesto.")
        self._dead_sl = TuneSlider("Zona morta do cursor", lambda v: f"{v}px")
        self._dead_sl.setRange(0, 20)
        self._dead_sl.setValue(int(self._cfg.deadzone_px))
        p2l.addWidget(self._dead_sl)
        self._stable_sl = TuneSlider(
            "Estabilidade do gesto", lambda v: f"{v} frames"
        )
        self._stable_sl.setRange(1, 6)
        self._stable_sl.setValue(int(self._cfg.gesture_stable_frames))
        p2l.addWidget(self._stable_sl)
        pl.addWidget(p2)
        pl.addStretch()
        self._stack.addWidget(panel)

    # ── Painel 2: Funcionalidades ───────────────────────────────────
    def _build_features_panel(self):
        panel = QWidget()
        panel.setObjectName("SettingsPanel")
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(20, 16, 20, 16)
        pl.setSpacing(12)

        sub = QLabel("Liga ou desliga cada capacidade do Mãouse.")
        sub.setObjectName("HeroSubtitle")
        sub.setWordWrap(True)
        pl.addWidget(sub)

        t, tl = _group("Funcionalidades", None)
        self._snap_ch, snap_lay = self._pro_checkbox(
            "snap", "Snap magnético", self._cfg.snap_enabled
        )
        tl.addLayout(snap_lay)
        self._voice_ch, voice_lay = self._pro_checkbox(
            "voice", "Comandos de voz", self._cfg.voice_enabled
        )
        tl.addLayout(voice_lay)
        self._tts_ch, tts_lay = self._pro_checkbox(
            "tts", "Voz falada (TTS)", self._cfg.tts_enabled
        )
        tl.addLayout(tts_lay)
        self._ai_ch, ai_lay = self._pro_checkbox(
            "ai", "IA de gestos", self._cfg.ai_enabled
        )
        tl.addLayout(ai_lay)
        self._at_ch, at_lay = self._pro_checkbox(
            "autotune", "Auto-afinação", self._cfg.autotune_enabled
        )
        tl.addLayout(at_lay)
        pl.addWidget(t)
        pl.addStretch()
        self._stack.addWidget(panel)

    # ── Painel 3: Voz ──────────────────────────────────────────────
    def _build_voice_panel(self):
        panel = QWidget()
        panel.setObjectName("SettingsPanel")
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(20, 16, 20, 16)
        pl.setSpacing(12)

        sub = QLabel("O que usar para entender o que dizes.")
        sub.setObjectName("HeroSubtitle")
        sub.setWordWrap(True)
        pl.addWidget(sub)

        v, vl = _group(tr("settings.voice.stt_provider"), None)
        self._stt_combo = QComboBox()
        self._stt_combo.setObjectName("SettingsCombo")
        self._stt_combo.addItem(tr("settings.voice.provider.auto"), "auto")
        self._stt_combo.addItem(tr("settings.voice.provider.cloud"), "cloud")
        self._stt_combo.addItem(tr("settings.voice.provider.local"), "local")
        try:
            idx = ("auto", "cloud", "local").index(self._cfg.stt_provider)
        except ValueError:
            idx = 0
        self._stt_combo.setCurrentIndex(idx)
        vl.addWidget(self._stt_combo)

        self._direct_ch = QCheckBox(tr("settings.voice.direct_commands"))
        self._direct_ch.setChecked(self._cfg.voice_always_on)
        vl.addWidget(self._direct_ch)

        from core.audio_devices import list_input_devices

        devices = list_input_devices()
        mic_lbl = QLabel(tr("settings.voice.mic_label"))
        mic_lbl.setObjectName("MicHint")
        vl.addWidget(mic_lbl)
        if devices:
            self._mic_combo = QComboBox()
            self._mic_combo.setObjectName("SettingsCombo")
            self._mic_combo.addItem(tr("settings.voice.mic_default"), "")
            for _idx, name in devices:
                self._mic_combo.addItem(name, name)
            pos = self._mic_combo.findData(self._cfg.mic_device)
            self._mic_combo.setCurrentIndex(pos if pos >= 0 else 0)
            vl.addWidget(self._mic_combo)
        else:
            self._mic_combo = None
            warn = QLabel(tr("settings.voice.mic_list_failed"))
            warn.setObjectName("MicHint")
            warn.setWordWrap(True)
            vl.addWidget(warn)
        hint = QLabel(tr("settings.voice.groq_key"))
        hint.setObjectName("MicHint")
        hint.setWordWrap(True)
        vl.addWidget(hint)
        pl.addWidget(v)
        pl.addStretch()
        self._stack.addWidget(panel)

    # ── Painel 4: Imagem ───────────────────────────────────────────
    def _build_camera_panel(self):
        panel = QWidget()
        panel.setObjectName("SettingsPanel")
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(20, 16, 20, 16)
        pl.setSpacing(12)

        sub = QLabel("Preferências pessoais de imagem e gestos.")
        sub.setObjectName("HeroSubtitle")
        sub.setWordWrap(True)
        pl.addWidget(sub)

        p, pl2 = _group("Imagem", None)
        self._mirror_ch = QCheckBox("Espelhar imagem")
        self._mirror_ch.setChecked(self._cfg.mirror)
        pl2.addWidget(self._mirror_ch)
        self._left_hand_ch = QCheckBox("Comandos mão esquerda")
        self._left_hand_ch.setChecked(self._cfg.left_hand_commands)
        pl2.addWidget(self._left_hand_ch)
        self._lowlight_ch = QCheckBox("Realce em pouca luz")
        self._lowlight_ch.setChecked(self._cfg.low_light_boost)
        pl2.addWidget(self._lowlight_ch)
        pl.addWidget(p)
        pl.addStretch()
        self._stack.addWidget(panel)

    # ── Painel 5: Remoto ───────────────────────────────────────────
    def _build_remote_panel(self):
        panel = QWidget()
        panel.setObjectName("SettingsPanel")
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(20, 16, 20, 16)
        pl.setSpacing(12)

        sub = QLabel("Rato e teclado a partir do telemóvel, na rede local ou pela Internet.")
        sub.setObjectName("HeroSubtitle")
        sub.setWordWrap(True)
        pl.addWidget(sub)

        r, rl = _group("Controlo remoto", None)
        self._remote_en_ch = QCheckBox("Ativar controlo por telemóvel (rato + teclado)")
        self._remote_en_ch.setChecked(self._cfg.remote_enabled)
        rl.addWidget(self._remote_en_ch)

        port_lay = QHBoxLayout()
        port_lbl = QLabel("Porta:")
        port_lbl.setObjectName("SettingsLabel")
        port_lay.addWidget(port_lbl)
        self._remote_port_spin = QSpinBox()
        self._remote_port_spin.setRange(1024, 65535)
        self._remote_port_spin.setValue(self._cfg.remote_port)
        port_lay.addWidget(self._remote_port_spin)
        port_lay.addStretch(1)
        rl.addLayout(port_lay)

        self._remote_bind_cb = QComboBox()
        self._remote_bind_cb.setObjectName("SettingsCombo")
        self._remote_bind_cb.addItem("Rede local + Internet (0.0.0.0)", "0.0.0.0")
        self._remote_bind_cb.addItem("Só neste PC (127.0.0.1)", "127.0.0.1")
        idx = self._remote_bind_cb.findData(self._cfg.remote_bind)
        self._remote_bind_cb.setCurrentIndex(idx if idx >= 0 else 0)
        rl.addWidget(self._remote_bind_cb)

        token_lay = QHBoxLayout()
        token_lbl = QLabel("Token:")
        token_lbl.setObjectName("SettingsLabel")
        token_lay.addWidget(token_lbl)
        self._remote_token_edit = QLineEdit()
        self._remote_token_edit.setObjectName("KeyField")
        self._remote_token_edit.setReadOnly(True)
        token_lay.addWidget(self._remote_token_edit)
        gen = QPushButton("Gerar")
        gen.setObjectName("SettingsButtonGhost")
        gen.clicked.connect(self._gen_token)
        token_lay.addWidget(gen)
        rl.addLayout(token_lay)

        self._remote_info = QLabel()
        self._remote_info.setObjectName("MicHint")
        self._remote_info.setWordWrap(True)
        self._remote_info.setFont(FONT_MONO)
        rl.addWidget(self._remote_info)
        self._refresh_remote_info()
        pl.addWidget(r)
        pl.addStretch()
        self._stack.addWidget(panel)

    # ── Painel 6: Trading ──────────────────────────────────────────
    def _build_trading_panel(self):
        panel = QWidget()
        panel.setObjectName("SettingsPanel")
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(20, 16, 20, 16)
        pl.setSpacing(12)

        sub = QLabel(
            "Botão de TV no ecrã principal para ativar o modo dedicado a"
            " trading (abre o TradingView + comando remoto pelo telemóvel)."
        )
        sub.setObjectName("HeroSubtitle")
        sub.setWordWrap(True)
        pl.addWidget(sub)

        tm, tml = _group("Modo Trading Master", None)
        self._tv_btn_ch = QCheckBox("Mostrar o botão 'Modo Trading Master' no ecrã principal")
        self._tv_btn_ch.setChecked(self._cfg.tv_button_enabled)
        tml.addWidget(self._tv_btn_ch)
        tv_hint = QLabel(
            "Atalhos de voz -> teclado do TradingView, um por linha no"
            " formato 'chave = combo' (ex: h = alt+h, s = ctrl+k)."
            " Chaves válidas: t (linha), h (horizontal), v (vertical),"
            " c (cruz), f (fibonacci), s (trocar gráfico)."
        )
        tv_hint.setObjectName("MicHint")
        tv_hint.setWordWrap(True)
        tml.addWidget(tv_hint)
        self._tv_combos_edit = QPlainTextEdit()
        self._tv_combos_edit.setObjectName("KeyField")
        self._tv_combos_edit.setFont(FONT_MONO)
        self._tv_combos_edit.setMinimumHeight(120)
        self._tv_combos_edit.setPlainText(
            "\n".join(f"{k} = {v}" for k, v in self._cfg.tv_tool_combos.items())
        )
        tml.addWidget(self._tv_combos_edit)
        pl.addWidget(tm)
        pl.addStretch()
        self._stack.addWidget(panel)

    # ── Ações ───────────────────────────────────────────────────────
    def _gen_token(self):
        from core.remote import generate_token

        self._cfg.remote_token = generate_token()
        self._remote_token_edit.setText(self._cfg.remote_token)
        self._refresh_remote_info()

    def _refresh_remote_info(self):
        from core.remote import generate_token, lan_ips

        token = (self._cfg.remote_token or "").strip()
        if not token:
            token = generate_token()
            self._cfg.remote_token = token
        self._remote_token_edit.setText(token)
        ips = ", ".join(lan_ips()) or "IP local apenas"
        self._remote_info.setText(
            f"Telemóvel liga a:\nws://{ips}:{self._cfg.remote_port}\n"
            f"token: {token[:4]}…  ·  {len(token)} caracteres"
        )

    def _reset_defaults(self):
        from config import Config

        defaults = Config()
        self._gain_sl.setValue(int(defaults.move_gain * 10))
        self._smooth_cb.setCurrentIndex(1)
        self._snap_ch.setChecked(defaults.snap_enabled)
        self._voice_ch.setChecked(defaults.voice_enabled)
        self._tts_ch.setChecked(defaults.tts_enabled)
        self._ai_ch.setChecked(defaults.ai_enabled)
        self._at_ch.setChecked(defaults.autotune_enabled)
        self._mirror_ch.setChecked(defaults.mirror)
        self._left_hand_ch.setChecked(defaults.left_hand_commands)
        self._lowlight_ch.setChecked(defaults.low_light_boost)
        self._dead_sl.setValue(int(defaults.deadzone_px))
        self._stable_sl.setValue(defaults.gesture_stable_frames)
        self._remote_en_ch.setChecked(defaults.remote_enabled)
        self._remote_port_spin.setValue(defaults.remote_port)
        self._tv_btn_ch.setChecked(defaults.tv_button_enabled)

    def _save(self):
        self._cfg.move_gain = max(0.6, self._gain_sl.value() / 10.0)
        name = self._smooth_cb.currentText()
        for pname, cut, beta in SMOOTH_PRESETS:
            if pname == name:
                self._cfg.filter_min_cutoff = cut
                self._cfg.filter_beta = beta
                self._smooth_name = name
                break
        self._cfg.snap_enabled = self._snap_ch.isChecked()
        self._cfg.voice_enabled = self._voice_ch.isChecked()
        self._cfg.tts_enabled = self._tts_ch.isChecked()
        self._cfg.stt_provider = self._stt_combo.currentData()
        self._cfg.voice_always_on = self._direct_ch.isChecked()
        if getattr(self, "_mic_combo", None) is not None:
            self._cfg.mic_device = self._mic_combo.currentData() or ""
        self._cfg.ai_enabled = self._ai_ch.isChecked()
        self._cfg.autotune_enabled = self._at_ch.isChecked()
        self._cfg.mirror = self._mirror_ch.isChecked()
        self._cfg.left_hand_commands = self._left_hand_ch.isChecked()
        self._cfg.low_light_boost = self._lowlight_ch.isChecked()
        self._cfg.deadzone_px = float(self._dead_sl.value())
        self._cfg.gesture_stable_frames = self._stable_sl.value()
        self._cfg.remote_enabled = self._remote_en_ch.isChecked()
        self._cfg.remote_port = self._remote_port_spin.value()
        self._cfg.remote_bind = self._remote_bind_cb.currentData()
        self._cfg.remote_token = self._remote_token_edit.text().strip()
        self._cfg.tv_button_enabled = self._tv_btn_ch.isChecked()
        self._cfg.tv_tool_combos = self._parse_tv_combos()
        self.accept()

    def _parse_tv_combos(self):
        from config import DEFAULT_TV_TOOL_COMBOS

        out = dict(DEFAULT_TV_TOOL_COMBOS)
        for raw in self._tv_combos_edit.toPlainText().splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, _, combo = line.partition("=")
            k = k.strip().lower()
            combo = combo.strip().lower()
            if k and combo:
                out[k] = combo
        return out

    @property
    def smooth_name(self):
        return self._smooth_name
