"""Settings dialog for real-time parameter adjustment."""
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
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from config import SMOOTH_PRESETS
from core.licensing import Tier, is_pro_locked
from i18n import tr
from ui.theme import FONT_MONO, FONT_PRIMARY, MAIN_STYLESHEET


def _group(title, caption):
    """Grupo de configuração com título + descrição curta por cima dos controlos."""
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


def _slider_block(parent_lay, name, value_text, on_change, lo, hi, val):
    """Linha nome + valor à direita, com o slider por baixo."""
    row = QHBoxLayout()
    name_lbl = QLabel(name)
    name_lbl.setObjectName("SettingsLabel")
    row.addWidget(name_lbl)
    row.addStretch(1)
    value = QLabel(value_text)
    value.setObjectName("SliderValue")
    value.setFont(FONT_MONO)
    row.addWidget(value)
    parent_lay.addLayout(row)

    sl = QSlider(Qt.Horizontal)
    sl.setRange(int(lo), int(hi))
    sl.setValue(int(val))
    sl.valueChanged.connect(lambda v: value.setText(on_change(v)))
    parent_lay.addWidget(sl)
    return sl, value


class SettingsDialog(QDialog):

    def __init__(self, cfg, smooth_name, parent=None, license_mgr=None):
        super().__init__(parent)
        self._cfg = cfg
        self._smooth_name = smooth_name
        self._tier = license_mgr.tier if license_mgr is not None else Tier.FREE
        self.setWindowTitle("Definições — Mãouse")
        self.setObjectName("SettingsDialog")
        self.setStyleSheet(MAIN_STYLESHEET)
        self.setMinimumSize(500, 360)
        self.resize(500, 760)
        self._build()

    def _pro_checkbox(self, feature, text, enabled, caption=None):
        """Cria um QCheckBox que fica DESLIGADO e bloqueado se a funcionalidade
        for Pro-locked no tier atual (mostra a etiqueta 'PRO')."""
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

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.setContentsMargins(20, 18, 20, 16)

        # ── Cabeçalho ───────────────────────────────────────────────
        header = QHBoxLayout()
        chip = QLabel("AJUSTES")
        chip.setObjectName("HeroChip")
        header.addWidget(chip)
        header.addSpacing(10)
        title = QLabel("Definições")
        title.setObjectName("HeroTitle")
        header.addWidget(title)
        header.addStretch()
        lay.addLayout(header)

        sub = QLabel(
            "Ajusta o cursor, a suavidade, a voz e o controlo remoto em tempo real."
        )
        sub.setObjectName("HeroSubtitle")
        sub.setWordWrap(True)
        lay.addWidget(sub)

        # ── Área rolável (ecrãs pequenos nunca cortam conteúdo) ─────
        scroll = QScrollArea()
        scroll.setObjectName("SettingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        content.setObjectName("SettingsScrollContent")
        clay = QVBoxLayout(content)
        clay.setContentsMargins(0, 8, 10, 0)
        clay.setSpacing(12)
        scroll.setWidget(content)
        lay.addWidget(scroll, 1)

        # Gain
        g, gl = _group("Ganho do cursor", "Quão rápido o cursor segue a mão.")
        self._gain_sl, self._gain_lbl = _slider_block(
            gl,
            "Rácio de movimento",
            f"{self._cfg.move_gain:.1f}",
            lambda v: f"{v / 10:.1f}",
            6,
            50,
            self._cfg.move_gain * 10,
        )
        clay.addWidget(g)

        # Smoothness
        s, sl = _group("Suavidade", "Entre um movimento suave e um reativo.")
        self._smooth_cb = QComboBox()
        self._smooth_cb.setObjectName("SettingsCombo")
        for name, _, _ in SMOOTH_PRESETS:
            self._smooth_cb.addItem(name)
        idx = next((i for i, (n, _, _) in enumerate(SMOOTH_PRESETS) if n == self._smooth_name), 1)
        self._smooth_cb.setCurrentIndex(idx)
        sl.addWidget(self._smooth_cb)
        clay.addWidget(s)

        # Toggles
        t, tl = _group("Funcionalidades", "Liga ou desliga cada capacidade.")
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
        clay.addWidget(t)

        # Voz / reconhecimento
        v, vl = _group(
            tr("settings.voice.stt_provider"),
            "O que usar para entender o que dizes.",
        )
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
        clay.addWidget(v)

        # Personalizacao
        p, pl = _group("Personalização", "Preferências pessoais de imagem e gestos.")
        self._mirror_ch = QCheckBox("Espelhar imagem")
        self._mirror_ch.setChecked(self._cfg.mirror)
        pl.addWidget(self._mirror_ch)
        self._left_hand_ch = QCheckBox("Comandos mão esquerda")
        self._left_hand_ch.setChecked(self._cfg.left_hand_commands)
        pl.addWidget(self._left_hand_ch)
        self._lowlight_ch = QCheckBox("Realce em pouca luz")
        self._lowlight_ch.setChecked(self._cfg.low_light_boost)
        pl.addWidget(self._lowlight_ch)

        self._dead_sl, self._dead_lbl = _slider_block(
            pl,
            "Zona morta do cursor",
            f"{self._cfg.deadzone_px:.0f}px",
            lambda v: f"{v}px",
            0,
            20,
            self._cfg.deadzone_px,
        )
        self._stable_sl, self._stable_lbl = _slider_block(
            pl,
            "Estabilidade do gesto",
            f"{self._cfg.gesture_stable_frames} frames",
            lambda v: f"{v} frames",
            1,
            6,
            self._cfg.gesture_stable_frames,
        )
        clay.addWidget(p)

        # Controlo remoto por telemovel (rato + teclado via WiFi/Internet)
        r, rl = _group(
            "Controlo remoto (mobile)",
            "Rato e teclado a partir do telemóvel, na rede local ou pela Internet.",
        )
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
        clay.addWidget(r)

        # Modo Trading Master — botão circular (tv.png) no ecrã principal
        tm, tml = _group(
            "Modo Trading Master",
            "Botão de TV no ecrã principal para ativar o modo dedicado a"
            " trading (abre o TradingView + comando remoto pelo telemóvel).",
        )
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
        clay.addWidget(tm)

        clay.addStretch()

        # ── Rodapé ──────────────────────────────────────────────────
        bl = QHBoxLayout()
        bl.addStretch()
        cancel = QPushButton("Cancelar")
        cancel.setObjectName("SettingsButtonGhost")
        cancel.clicked.connect(self.reject)
        bl.addWidget(cancel)
        save = QPushButton("Gravar")
        save.setObjectName("SettingsButton")
        save.setFixedWidth(120)
        save.setFixedHeight(36)
        save.clicked.connect(self._save)
        bl.addWidget(save)
        lay.addLayout(bl)

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
        """Lê a lista 'chave = combo' e devolve fundida com os predefinidos."""
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
