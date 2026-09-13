"""Main frameless window with QTimer processing loop.

A MainWindow é apenas a APRESENTAÇÃO: toda a lógica de reconhecimento/
movimento/gestos vive em ``process_frame``/``make_engine_ctx`` (main.py),
partilhada com o preview OpenCV. Isto garante paridade total de comportamento
entre as duas UIs.
"""
import os
import time
import webbrowser

import cv2
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPainterPath, QPixmap, QRegion
from PySide6.QtWidgets import QLabel, QMainWindow, QWidget

from config import SMOOTH_PRESETS, save_settings
from core.gestures import Gesture
from core.log import get_logger
from i18n import I18N, tr
from ui.camera_view import CameraView
from ui.gesture_badge import GestureBadge
from ui.help_panel import HelpPanel
from ui.menu_panel import MenuPanel
from ui.status_indicators import StatusBadges
from ui.theme import (
    FONT_MONO,
    FONT_STATUS,
    MAIN_STYLESHEET,
    init_gesture_colors,
)
from ui.toast import Toast
from ui.tv_button import TvMasterButton
from ui.voice_bar import VoiceBar

log = get_logger("main_window")


class MainWindow(QMainWindow):

    # Emitido da thread do pynput (hotkey global); ligado a um slot do GUI
    # thread para o toggle ser processado com seguranca em Qt.
    hotkey_toggle = Signal()

    def __init__(self, cfg, cam, tracker, mouse, gesture_ai=None,
                 voice=None, tuner=None, speaker=None, snap=None,
                 assistant=None, magnifier=None, license_mgr=None, remote=None):
        super().__init__()
        init_gesture_colors()

        self._cfg = cfg
        self._cam = cam
        self._tracker = tracker
        self._mouse = mouse
        self._gesture_ai = gesture_ai
        self._voice = voice
        self._tuner = tuner
        self._speaker = speaker
        self._snap = snap
        self._assistant = assistant
        self._magnifier = magnifier
        self._license = license_mgr
        self._remote = remote

        self._paused = False
        self._show_help = False
        self._smooth_name = "NORMAL"
        self._ui_show = False
        self._hotkey_listener = None
        self._flash = 0
        self._last_frame = None
        self._all_frames = {}
        self._active_side = None
        self._fps = 0.0
        self._fps_counter = 0
        self._fps_time = time.perf_counter()

        # A câmara serve APENAS para configuração/verificação: não é o fundo da
        # janela nem interfere com o reconhecimento de gestos. O feed só aparece
        # quando o utilizador ativa "VER CÂMERA" no menu. O rastreio de gestos
        # continua sempre a correr em segundo plano.
        self._camera_on = False

        # Aviso "2 maos = premium" mostra uma unica vez por subida do contador.
        self._twohand_free_notified = False

        # Pop-up de bloqueio total: mostra UMA vez por sessão quando o
        # trial/lease esgotou (depois disso o utilizador reabre por menu).
        self._block_shown = False

        # Timer do alerta de bloqueio (toast vermelho + borda + logo-look).
        self._lock_flash_timer = None

        self._E = None
        self._ctx = None
        self._state = {}

        self._build_ui()
        self._build_shortcuts()
        self._start_global_hotkey()
        self._sync_license_ui()
        I18N.language_changed.connect(lambda *_: self._sync_toolbar())

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(0)

    def _build_ui(self):
        self.setWindowTitle("Mãouse")
        self.setObjectName("MainWindow")
        self.setMinimumSize(640, 480)
        self.resize(800, 600)
        self.setStyleSheet(MAIN_STYLESHEET)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self._apply_rounded_mask()

        central = QWidget()
        central.setObjectName("MainWindow")
        self.setCentralWidget(central)

        self._bg = QLabel(central)
        self._bg.setObjectName("DashboardBackground")
        self._bg.setGeometry(0, 0, self.width(), self.height())
        self._bg.lower()
        self._load_bg_image()

        self._cam_view = CameraView(central)
        self._cam_view.setObjectName("CameraPreview")
        self._cam_view.hide()

        self._gesture_badge = GestureBadge(central)
        self._gesture_badge.move(12, 10)

        self._voice_bar = VoiceBar(central)
        self._voice_bar.move(12, 70)

        self._status = StatusBadges(central)
        self._status.move(0, 10)
        self._status.resize(300, 28)

        self._toast = Toast(central)

        self._help = HelpPanel(central)
        self._help.move(12, 120)

        self._menu = MenuPanel(central)
        self._menu.setFixedWidth(168)

        self._tv_btn = TvMasterButton(central)
        self._tv_btn.set_on(bool(self._cfg.trading_master_enabled))
        self._tv_btn.toggled.connect(self._toggle_trading_master)
        self._sync_tv_button()

        self._status_bar = QLabel(central)
        self._status_bar.setObjectName("StatusBar")
        self._status_bar.setFont(FONT_STATUS)
        self._status_bar.setFixedHeight(22)

        self._fps_lbl = QLabel(central)
        self._fps_lbl.setObjectName("StatusBar")
        self._fps_lbl.setFont(FONT_MONO)
        self._fps_lbl.setFixedHeight(22)
        self._fps_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self._build_menu()
        self._build_shortcuts()

    def _apply_rounded_mask(self):
        """Recorta a janela frameless em cantos arredondados (vê-se o fundo)."""
        radius = 18
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), radius, radius)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def _load_bg_image(self):
        try:
            off = self._paused or not (self._license and self._license.is_pro)
            name = "logo-off.png" if off else "logo.png"
            self._set_bg_file(name)
        except Exception:
            self._bg.setPixmap(QPixmap())

    def _set_bg_file(self, name):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(root, "assets", "brand", name)
        pm = QPixmap(str(path))
        if not pm.isNull():
            self._bg.setPixmap(pm)
            self._fit_bg(self.width(), self.height())

    def _flash_locked(self, message):
        """Alerta de bloqueio do motor: toast vermelho + borda da janela
        vermelha + logo-look durante uns segundos, depois volta ao normal."""
        self._toast.show_toast(message, danger=True, duration_ms=2300)
        self.setProperty("locked", True)
        self.style().unpolish(self)
        self.style().polish(self)
        self._set_bg_file("logo-look.png")
        if self._lock_flash_timer is None:
            self._lock_flash_timer = QTimer(self)
            self._lock_flash_timer.setSingleShot(True)
            self._lock_flash_timer.timeout.connect(self._restore_locked_ui)
        self._lock_flash_timer.start(2600)

    def _restore_locked_ui(self):
        self.setProperty("locked", False)
        self.style().unpolish(self)
        self.style().polish(self)
        self._load_bg_image()

    def _fit_bg(self, w, h):
        if self._bg is None or w <= 0 or h <= 0:
            return
        pm = self._bg.pixmap()
        if pm is None or pm.isNull():
            return
        try:
            ratio = 0.7
            target_w = min(int(min(w, h) * ratio), 430)
            scaled = pm.scaled(
                target_w, target_w,
                Qt.KeepAspectRatio, Qt.SmoothTransformation,
            )
        except Exception:
            scaled = pm
        x = (w - scaled.width()) // 2
        y = (h - scaled.height()) // 2
        self._bg.setGeometry(x, y, scaled.width(), scaled.height())
        self._bg.setPixmap(scaled)
        self._bg.lower()

    def _build_menu(self):
        """Painel lateral de marca com botões agrupados (topo-direito)."""
        m = self._menu
        m.btn_pause.clicked.connect(self._toggle_pause)
        m.btn_voice.toggled.connect(self._toggle_voice)
        m.btn_snap.toggled.connect(self._toggle_snap)
        m.btn_camera.toggled.connect(self._toggle_camera)
        m.btn_help.toggled.connect(self._toggle_help)
        m.btn_config.clicked.connect(self._open_settings)
        m.btn_quit.clicked.connect(self.close)
        m.btn_upgrade.clicked.connect(self._open_license)
        self._menu_buttons = [
            m.btn_pause, m.btn_voice, m.btn_snap,
            m.btn_camera, m.btn_help, m.btn_config, m.btn_quit,
        ]

    def _build_shortcuts(self):
        pass

    def _start_global_hotkey(self):
        """Hotkey global (Ctrl+Shift+A) para abrir/fechar a interface de qualquer
        lugar, mesmo com a janela oculta. Corre em thread própria (pynput)."""
        try:
            from pynput import keyboard
        except Exception:
            return

        pressed = set()

        def on_press(key):
            try:
                if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                    pressed.add("ctrl")
                elif key in (keyboard.Key.shift_l, keyboard.Key.shift_r):
                    pressed.add("shift")
                else:
                    # Com Ctrl premido, o pynput reporta a tecla 'a' como o
                    # caractere de controlo '\x01'. Aceitamos as duas formas.
                    ch = getattr(key, "char", None)
                    if ch in ("a", "A", "\x01") and {"ctrl", "shift"} <= pressed:
                        self.hotkey_toggle.emit()
            except Exception as e:
                log.debug("Erro no callback de hotkey (press): %s", e)

        def on_release(key):
            try:
                if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                    pressed.discard("ctrl")
                elif key in (keyboard.Key.shift_l, keyboard.Key.shift_r):
                    pressed.discard("shift")
            except Exception as e:
                log.debug("Erro no callback de hotkey (release): %s", e)

        try:
            self.hotkey_toggle.connect(self._toggle_ui_global)
            self._hotkey_listener = keyboard.Listener(
                on_press=on_press, on_release=on_release, daemon=True
            )
            self._hotkey_listener.start()
        except Exception:
            self._hotkey_listener = None

    def _toggle_ui_global(self):
        if self._E is None:
            return
        self._E.ui["ui_show"] = not self._E.ui["ui_show"]
        self._toast.show_toast(tr("toast.ui_on" if self._E.ui["ui_show"] else "toast.ui_off"))


    def _menu_checkable(self, btn, checked):
        """Sincroniza o estado do botão SEM disparar o sinal toggled (que
        dispararia os handlers e reverteria o estado do motor)."""
        btn.blockSignals(True)
        btn.setChecked(checked)
        btn.blockSignals(False)

    def _toggle_pause(self):
        """Pausa/retoma CONTROLANDO o motor: o estado vive em ``state["paused"]``
        (lido por process_frame), não numa flag local da janela."""
        paused = not self._state.get("paused", False)
        if self._E is not None and self._E.emitter is not None:
            self._E.emitter.clear()
        self._state["paused"] = paused
        self._update_paused_state(paused)
        self._toast.show_toast(tr("toast.pause" if paused else "toast.resume"))

    def _update_paused_state(self, paused):
        """Reflete o estado pausa/retoma no botão (ON/OFF) e no logo de fundo."""
        self._paused = paused
        self._menu.btn_pause.set_key("btn.off" if paused else "btn.on")
        self._load_bg_image()

    def _view_license_locked(self, feature: str) -> bool:
        """True se a funcionalidade estiver Pro-locked (não deve ligar no Free)."""
        try:
            from core.licensing import active_tier, is_pro_locked
            return is_pro_locked(active_tier(), feature)
        except Exception:
            return False

    def _toggle_voice(self, checked):
        if self._view_license_locked("voice"):
            self._flash_locked("VOZ disponível no PRO — UPGRADE PRO")
            self._menu_checkable(self._menu.btn_voice, False)
            return
        if self._voice:
            mic_error = getattr(self._voice, "mic_error", None)
            if mic_error:
                self._toast.show_toast(
                    tr("voice.mic_error_status"), danger=True, duration_ms=2300
                )
            self._voice.toggle()
            on = self._voice.status not in ("off", "error")
            self._menu_checkable(self._menu.btn_voice, on)
            if self._voice.status == "error":
                return
            if on and self._voice.status == "preparing":
                self._toast.show_toast(tr("voice.status.preparing"))
            else:
                self._toast.show_toast(tr("toast.voice_on" if on else "toast.voice_off"))

    def _toggle_snap(self, checked):
        if self._view_license_locked("snap"):
            self._flash_locked("SNAP disponível no PRO — UPGRADE PRO")
            self._menu_checkable(self._menu.btn_snap, False)
            return
        if self._snap and self._snap.available:
            self._snap.enabled = checked
            self._cfg.snap_enabled = checked
            self._toast.show_toast(f"SNAP {'ON' if checked else 'OFF'}")

    def _toggle_help(self, checked):
        self._show_help = checked
        self._help.toggle()

    def _toggle_camera(self, checked):
        """Mostra/oculta o preview da câmara. O reconhecimento de gestos NÃO é
        afetado: o rastreio continua a correr em segundo plano o tempo todo."""
        self._camera_on = checked
        self._cam_view.setVisible(checked)
        self._layout_camera()
        self._toast.show_toast("CÂMARA ON" if checked else "CÂMARA OFF")

    def _sync_toolbar(self):
        self._menu.btn_pause.set_key("btn.off" if self._paused else "btn.on")
        self._menu_checkable(
            self._menu.btn_voice, bool(self._voice) and self._voice.status not in ("off", "error"),
        )
        self._menu_checkable(self._menu.btn_snap, bool(self._cfg.snap_enabled))
        self._tv_btn.set_on(bool(self._cfg.trading_master_enabled))

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key_Q, Qt.Key_Escape):
            self.close()
        elif key == Qt.Key_Space:
            self._toggle_pause()
        elif key in (Qt.Key_H, Qt.Key_F1):
            self._show_help = not self._show_help
            self._help.toggle()
        elif key == Qt.Key_S:
            self._save_settings()
            self._toast.show_toast("GRAVAR")
        elif key == Qt.Key_A:
            if self._tuner:
                self._toast.show_toast(self._tuner.toggle())
        elif key == Qt.Key_V:
            self._toggle_voice(None)
        elif key == Qt.Key_M:
            if self._view_license_locked("snap"):
                self._flash_locked("SNAP disponível no PRO — UPGRADE PRO")
            elif self._snap and self._snap.available:
                new_state = not self._snap.enabled
                self._snap.enabled = new_state
                self._cfg.snap_enabled = new_state
                self._menu_checkable(self._menu.btn_snap, new_state)
                self._toast.show_toast(f"SNAP {'ON' if new_state else 'OFF'}")
        elif key == Qt.Key_C:
            new_state = not self._camera_on
            self._menu.btn_camera.setChecked(new_state)
            self._toggle_camera(new_state)
        elif key == Qt.Key_T:
            new_state = not self._cfg.trading_master_enabled
            self._tv_btn.setChecked(new_state)
            self._toggle_trading_master(new_state)
        elif key == Qt.Key_F2:
            self._open_settings()
        elif key == Qt.Key_BracketLeft:
            self._cfg.move_gain = max(0.6, round(self._cfg.move_gain - 0.2, 2))
            if self._tuner:
                self._tuner.set_user_gain(self._cfg.move_gain)
            self._toast.show_toast(f"GANHO {self._cfg.move_gain:.1f}")
        elif key == Qt.Key_BracketRight:
            self._cfg.move_gain = max(0.6, round(self._cfg.move_gain + 0.2, 2))
            if self._tuner:
                self._tuner.set_user_gain(self._cfg.move_gain)
            self._toast.show_toast(f"GANHO {self._cfg.move_gain:.1f}")
        elif key == Qt.Key_Comma:
            self._step_smooth(-1)
        elif key == Qt.Key_Period:
            self._step_smooth(+1)
        else:
            super().keyPressEvent(event)

    def _step_smooth(self, direction):
        presets = SMOOTH_PRESETS
        cur = next((i for i, (n, _, _) in enumerate(presets) if n == self._smooth_name), 1)
        idx = (cur + direction) % len(presets)
        name, cut, beta = presets[idx]
        self._cfg.filter_min_cutoff = cut
        self._cfg.filter_beta = beta
        if self._E is not None:
            self._E.filters.set_params(cut, beta)
        self._smooth_name = name
        self._toast.show_toast(name)

    def _open_settings(self):
        from ui.settings_dlg import SettingsDialog
        dlg = SettingsDialog(self._cfg, self._smooth_name, self,
                             license_mgr=self._license)
        if dlg.exec() == SettingsDialog.Accepted:
            self._smooth_name = dlg.smooth_name
            if self._E is not None:
                self._E.filters.set_params(self._cfg.filter_min_cutoff, self._cfg.filter_beta)
            self._apply_remote_config()
            self._sync_tv_button()
            self._toast.show_toast("Definições atualizadas")

    def _sync_tv_button(self):
        """Mostra/oculta o botão de TV conforme as definições."""
        self._tv_btn.setVisible(bool(self._cfg.tv_button_enabled))
        self._tv_btn.raise_()

    def _apply_remote_config(self):
        """(Re)liga/desliga o servidor de controlo remoto conforme as definições."""
        cfg = self._cfg
        if self._remote is None and cfg.remote_enabled:
            from core.remote import RemoteServer

            self._remote = RemoteServer(cfg, self._mouse)
        if self._remote is None:
            return
        if cfg.remote_enabled:
            if not self._remote.is_running:
                if self._remote.start():
                    self._toast.show_toast(f"REMOTO ON :{cfg.remote_port}")
                else:
                    self._toast.show_toast("REMOTO — porta em uso?", danger=True)
            elif self._remote.bound_port != cfg.remote_port:
                if self._remote.restart():
                    self._toast.show_toast(f"REMOTO :{cfg.remote_port}")
        else:
            if self._remote.is_running:
                self._remote.stop()
                self._toast.show_toast("REMOTO OFF")

    def _toggle_trading_master(self, checked):
        """Ativa/desativa o Modo Trading Master: liga o controlo remoto por
        telemóvel (comandar o PC de trading) e guarda a preferência.

        Só assinantes Pro: no FREE o gate bloqueia e mostra o aviso."""
        if self._view_license_locked("trading_master"):
            self._tv_btn.set_on(False)
            self._flash_locked("TRADING MASTER é PRO — UPGRADE PRO")
            return
        self._cfg.remote_enabled = bool(checked)
        self._apply_remote_config()
        if checked and not (self._remote and self._remote.is_running):
            self._cfg.trading_master_enabled = False
            self._cfg.remote_enabled = False
            self._tv_btn.set_on(False)
            self._toast.show_toast("TRADING MASTER — PORTA EM USO?", danger=True)
            return
        self._cfg.trading_master_enabled = bool(checked)
        save_settings(self._cfg, self._smooth_name)
        if checked:
            self._open_tradingview()
        self._toast.show_toast(
            "TRADING MASTER ON" if checked else "TRADING MASTER OFF"
        )

    def _open_tradingview(self):
        """Abre o navegador padrão do utilizador com o TradingView aberto."""
        try:
            webbrowser.open("https://www.tradingview.com")
        except Exception as e:
            log.debug("Falha ao abrir o TradingView: %s", e)

    def _open_license(self):
        from ui.license_dlg import LicenseDialog
        dlg = LicenseDialog(self._cfg, self._license, self)
        if dlg.exec() == LicenseDialog.Accepted:
            self._sync_license_ui()

    def _maybe_show_block_dialog(self):
        """Mostra o pop-up de bloqueio total UMA vez por sessão, quando o
        trial/lease esgotou (o gate já impediu o movimento)."""
        if self._block_shown or not self._license or not self._license.is_blocked():
            return
        self._block_shown = True
        from ui.license_dlg import BlockDialog
        dlg = BlockDialog(self._cfg, self._license, self)
        if dlg.exec() == BlockDialog.Accepted:
            self._sync_license_ui()

    def _sync_license_ui(self):
        """Atualiza a UI consoante o estado da licença (Free vs Pro)."""
        is_pro = bool(self._license and self._license.is_pro)
        self._menu.btn_upgrade.set_key("btn.pro_active" if is_pro else "btn.upgrade")
        self._menu.btn_upgrade.setEnabled(not is_pro)
        self._menu.btn_voice.set_locked(not is_pro and self._view_license_locked("voice"))
        self._menu.btn_snap.set_locked(not is_pro and self._view_license_locked("snap"))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_rounded_mask()
        w, h = self.width(), self.height()
        self._layout_camera()
        self._fit_bg(w, h)
        self._status.move(w - 310, 10)
        self._status.resize(300, 28)
        self._status_bar.setGeometry(0, h - 22, w, 22)
        self._fps_lbl.setGeometry(w - 100, h - 22, 90, 22)
        tw = self._toast.width() if self._toast.width() > 0 else 200
        self._toast.move((w - tw) // 2, 50)

        bw = self._menu.width()
        mh = self._menu.sizeHint().height()
        x = w - bw - 10
        y = 10
        self._menu.setGeometry(x, y, bw, mh)

        tby = h - 22 - self._tv_btn.height() - 10
        self._tv_btn.move(12, tby)

    def _layout_camera(self):
        """Posiciona o preview da câmara como um painel centrado (não o fundo),
        mantendo a proporção e cachê sem esticar o vídeo."""
        w, h = self.width(), self.height()
        if not self._camera_on:
            return
        cfg = self._cfg
        fw, fh = cfg.frame_width, cfg.frame_height
        max_w = w - 40
        max_h = h - 90
        scale = min(max_w / max(fw, 1), max_h / max(fh, 1))
        sw = int(fw * scale)
        sh = int(fh * scale)
        x = (w - sw) // 2
        y = 40
        self._cam_view.setGeometry(x, y, sw, sh)
        self._cam_view.raise_()

    # ── Processing Loop ─────────────────────────────────────────────
    def _tick(self):
        from core.commands import AppCtl
        from core.engine import make_engine_ctx, process_frame
        from core.motion import SmoothEmitter

        if self._ctx is None:
            self._ctx = AppCtl()
        if self._E is None:
            self._E = make_engine_ctx(self._cfg, -1, self._gesture_ai, self._tuner, self._ctx)
            self._E.emitter = SmoothEmitter(self._mouse, self._cfg.emitter_rate_hz)
            self._E.emitter.start()
        self._state["smooth_name"] = self._smooth_name
        self._ctx.speaker = self._speaker
        self._ctx.snap = self._snap
        self._ctx.assistant = self._assistant
        self._ctx.magnifier = self._magnifier
        self._state.setdefault("paused", False)
        self._state.setdefault("show_help", False)
        self._state.setdefault("flash", 0)
        self._state.setdefault("freeze_until", 0.0)
        self._state.setdefault("button_down", False)
        self._state.setdefault("dbg_until", 0.0)
        # Gate de bloqueio + watchdog de uso, como no preview OpenCV.
        self._state.setdefault(
            "license_blocked",
            self._license.is_blocked() if self._license else False,
        )
        if "_usage_watchdog" not in self._state and self._license:
            from core.licensing import UsageWatchdog

            self._state["_usage_watchdog"] = UsageWatchdog(self._license, self._state)
        self._maybe_show_block_dialog()
        self._state["filters"] = self._E.filters
        self._state["tuner"] = self._tuner
        self._state["emitter"] = self._E.emitter

        # O Ctrl+C (SIGINT) pode interromper o MediaPipe no meio de
        # `tracker.process`. Para sair de forma limpa (sem tracebacks
        # repetidos nem janela presa), fechamos a janela: o closeEvent para
        # o timer e o app termina quando a janela única fechar.
        try:
            snap = process_frame(
                self._cfg, self._cam, self._tracker, self._mouse,
                self._gesture_ai, self._voice, self._tuner, self._ctx,
                self._state, self._E,
            )
        except KeyboardInterrupt:
            self.close()
            return
        if snap["done"] or self._ctx.exit_requested:
            self.close()
            return
        if not snap.get("to_render") or snap["frame"] is None:
            if self._ctx.exit_requested:
                self.close()
            return
        self._flash = snap.get("flash", self._state.get("flash", 0))
        self._update_fps()
        self._refresh_ui(snap)

        # Gate por gesto: a janela so se mostra/oculta conforme o ROCK (chifre)
        # na mao de comandos seja feito. Arranca oculta (apenas configuracao).
        ui_show = bool(snap.get("ui", {}).get("ui_show", self._ui_show))
        if ui_show != self._ui_show:
            self._ui_show = ui_show
            if ui_show:
                splash = None
                try:
                    from ui.splash import show_splash
                    splash = show_splash(ms=480)
                except Exception:
                    splash = None
                self.show()
                self.raise_()
                self.activateWindow()
                if splash is not None:
                    try:
                        splash.finish(self)
                    finally:
                        splash.close()
            else:
                self.hide()

    def _update_fps(self):
        self._fps_counter += 1
        elapsed = time.perf_counter() - self._fps_time
        if elapsed >= 0.5:
            self._fps = self._fps_counter / elapsed
            self._fps_counter = 0
            self._fps_time = time.perf_counter()
    def _refresh_ui(self, snap):
        frame = snap["frame"]
        all_frames = snap["all_frames"]
        active_side = snap["active_side"]
        self._last_frame = frame
        self._all_frames = all_frames
        self._active_side = active_side
        hand_frame = all_frames.get(active_side)

        self._sync_toolbar()

        gesture = hand_frame.gesture if hand_frame else Gesture.NONE

        # O motor pode pausar/retomar por voz (apply_command). Refletir esse
        # estado no badge/botão da janela.
        engine_paused = bool(self._state.get("paused", self._paused))
        if engine_paused != self._paused:
            self._update_paused_state(engine_paused)
        self._gesture_badge.update_gesture(gesture, engine_paused)
        if self._camera_on:
            self._cam_view.update_frame(frame, all_frames, active_side, self._flash)

        ai_conf = hand_frame.ai_conf if hand_frame else 0.0
        hands = len(all_frames)
        magnify = self._magnifier.last_action if (self._magnifier and self._magnifier.on) else ""
        self._status.update_state(self._gesture_ai is not None, ai_conf, magnify, hands)

        # No Free, duas maos sao DETETADAS e mostradas, mas os recursos de 2
        # maos ficam bloqueados pelo gate de licenca. Avisar o utilizador uma
        # vez por subida do contador (premium).
        is_pro = bool(self._license and self._license.is_pro)
        if not is_pro and hands >= 2 and not self._twohand_free_notified:
            self._twohand_free_notified = True
            self._flash_locked("2 MÃOS DETETADAS · RECURSOS PRO LOCKED")
        if hands < 2:
            self._twohand_free_notified = False

        if self._voice:
            self._voice_bar.update_state(
                self._voice.status,
                self._cfg.voice_wake_word,
                self._voice.backend,
                getattr(self._voice, "mic_error", None),
            )
        else:
            self._voice_bar.update_state("off")

        ui = snap["ui"]
        if ui.get("toast") and time.monotonic() < ui.get("toast_until", 0):
            self._toast.show_toast(ui["toast"])
            ui["toast_until"] = 0

        strip = f"{self._fps:4.0f} fps | ganho {self._cfg.move_gain:.1f} | {self._smooth_name}"
        if self._tuner and self._tuner.enabled:
            strip += " | AT"
        if self._speaker:
            strip += f" | voz:{self._speaker.status}"
        if self._license and not self._license.is_pro:
            strip += " | FREE"
        if self._cfg.trading_master_enabled:
            strip += " | TRADING MASTER"
        self._status_bar.setText(strip)
        self._fps_lbl.setText(f"{self._fps:4.0f} fps")

    @staticmethod
    def _key_combo(combo):
        try:
            from pynput.keyboard import Controller, Key
            kb = Controller()
            key_map = {
                "ctrl": Key.ctrl_l, "alt": Key.alt_l, "shift": Key.shift_l,
                "cmd": Key.cmd, "tab": Key.tab,
            }
            parts = combo.lower().split("+")
            keys = [key_map[p.strip()] if p.strip() in key_map else p.strip() for p in parts]
            for k in keys:
                kb.press(k)
            for k in reversed(keys):
                kb.release(k)
        except Exception as e:
            log.debug("Falha ao emitir atalho de teclado: %s", e)

    @staticmethod
    def _handle_media(event, value):
        VOLUME_STEP = 8.0
        try:
            from pynput.keyboard import Controller, Key
            kb = Controller()
        except Exception:
            return None
        if event == "volume":
            presses = int(abs(value) / VOLUME_STEP)
            if presses >= 1:
                key = Key.media_volume_up if value > 0 else Key.media_volume_down
                for _ in range(min(presses, 8)):
                    kb.press(key)
                    kb.release(key)
                return "VOL " + ("+" * min(presses, 4) if value > 0 else "-" * min(presses, 4))
        elif event == "play_pause":
            kb.press(Key.media_play_pause)
            kb.release(Key.media_play_pause)
            return "PLAY/PAUSA"
        return None

    def _save_settings(self):
        save_settings(self._cfg, self._smooth_name)

    def closeEvent(self, event):
        self._timer.stop()
        if self._hotkey_listener is not None:
            try:
                self._hotkey_listener.stop()
            except Exception as e:
                log.debug("Falha ao parar o listener de hotkey: %s", e)
            self._hotkey_listener = None
        try:
            if self._E is not None and self._E.emitter is not None:
                self._E.emitter.stop()
        except Exception as e:
            log.debug("Falha ao parar o emitter: %s", e)
        try:
            if self._state.get("button_down"):
                self._mouse.release_left()
        except Exception as e:
            log.debug("Falha ao largar o botao no fecho: %s", e)
        if self._remote is not None:
            try:
                self._remote.stop()
            except Exception as e:
                log.debug("Falha ao parar o controlo remoto: %s", e)
        for obj, meth in (
            (self._snap, "stop"), (self._voice, "stop"),
            (self._speaker, "stop"), (self._tracker, "close"),
            (self._cam, "release"),
        ):
            if obj is None or not hasattr(obj, meth):
                continue
            try:
                getattr(obj, meth)()
            except Exception as e:
                log.debug("Falha ao fechar %s.%s: %s", type(obj).__name__, meth, e)
        try:
            cv2.destroyAllWindows()
        except Exception as e:
            log.debug("Falha ao fechar janelas OpenCV: %s", e)
        event.accept()
