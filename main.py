"""Maouse — bootstrap/CLI.

Extraído para ``core/`` todo o motor (``core.engine``), hotkeys
(``core.hotkeys``), comandos (``core.commands``) e renderização do preview
(``core.overlay``). Este módulo fica responsável apenas por:
  * parsing de CLI e single-instance
  * abrir câmara/modelos/serviços (snap, voz, TTS, bandeja, assistente)
  * escolher o UI (janela nativa PySide6 vs preview OpenCV) e arrancar o loop

`main` continua a re-exportar ``process_frame``/``make_engine_ctx``/``AppCtl``
para scripts/ferramentas que os importam daqui, por retrocompatibilidade.
"""
import argparse
import ctypes
import logging
import os
import sys

import cv2

from config import (
    SETTINGS_FILE,
    SMOOTH_PRESETS,
    Config,
    load_settings,
    save_settings,
    user_models_dir,
)
from core.assistant import Assistant3D
from core.autotune import AutoTuner
from core.camera import CameraStream
from core.commands import AppCtl, apply_command
from core.discovery import MaouseAdvertiser
from core.engine import run_loop
from core.gesture_ai import GestureAI, ensure_ai_model
from core.licensing import (
    LicenseManager,
    UsageWatchdog,
    entitlements,
    is_pro_locked,
    set_active_license,
)
from core.llm import ChatClient
from core.log import get_logger, setup_logging
from core.mouse_ctl import MouseCtl, MuteMouse
from core.remote import RemoteArbiter, RemoteServer, lan_ips
from core.remote_ble import SERVICE_UUID as BLE_SERVICE_UUID
from core.remote_ble import RemoteBLE
from core.snap import SnapEngine
from core.tracker import HandTracker, ensure_model
from core.tray import TrayAppAdapter, TrayIcon
from core.tts import Speaker
from core.twohand import MagnifierCtl
from core.voice import VoiceEngine

log = get_logger("cli")


def parse_args():
    """Constrói e devolve o parser de argumentos da CLI.

    Devolve o ``ArgumentParser`` (não o resultado do parse) para que os testes
    possam inspecionar as flags disponíveis sem depender do ``sys.argv`` real.
    O parsing efetivo acontece em ``main()`` via ``parse_args().parse_args()``.
    """
    parser = argparse.ArgumentParser(description="Mãouse - controla o rato com a mao")
    parser.add_argument("--camera", type=int, default=None)
    parser.add_argument("--gain", type=float, default=None)
    parser.add_argument("--no-preview", action="store_true")
    parser.add_argument("--preview", action="store_true", help="forca janela mesmo em modo bandeja")
    parser.add_argument("--gpu", action="store_true", help="tenta usar delegado GPU no tracker")
    parser.add_argument("--tray", action="store_true",
                        help="modo bandeja: invisivel com icone na bandeja")
    parser.add_argument("--no-gui", action="store_true",
                        help="usa o preview OpenCV em vez da janela PySide6")
    parser.add_argument("--reset-config", action="store_true", help="apaga settings.json")
    parser.add_argument("--no-voice", action="store_true", help="desativa comandos de voz")
    parser.add_argument("--no-ai", action="store_true", help="desativa classificador IA de gestos")
    parser.add_argument("--no-autotune", action="store_true", help="desativa auto-afinacao")
    parser.add_argument("--pinch-debug", action="store_true",
                        help="imprime racios de pinca no console")
    parser.add_argument("--voice-always", action="store_true",
                        help="voz sempre ativa (sem wake word)")
    parser.add_argument("--no-tts", action="store_true", help="sem voz falada do Jarvis")
    parser.add_argument("--whisper-model", type=str, default=None,
                        help="modelo Whisper (tiny/base/small; default small)")
    parser.add_argument("--log-level", type=str, default="INFO",
                        choices=["DEBUG", "INFO", "WARNING"],
                        help="nivel de log (default: INFO)")
    parser.add_argument(
        "--frames",
        type=int,
        default=0,
        help="processa apenas N frames e sai (modo de teste)",
    )
    parser.add_argument(
        "--activate-key",
        type=str,
        default=None,
        metavar="CHAVE",
        help="ativa uma licenca Pro ONLINE e sai (MAO-XXXX-...).",
    )
    parser.add_argument(
        "--deactivate",
        action="store_true",
        help="remove a licenca Pro (volta a Free) e sai.",
    )
    # Onda 0: medir antes de optimizar. --record grava um corpus de landmarks
    # com etiquetas; --replay corre esse corpus e imprime as metricas. Sao
    # mutuamente exclusivos porque o replay tem de correr sem camera e sem
    # rato (e o record sem camera nao teria o que gravar).
    modo = parser.add_mutually_exclusive_group()
    modo.add_argument(
        "--record",
        type=str,
        default=None,
        metavar="FICHEIRO",
        help="grava um corpus de landmarks com etiquetas para avaliacao",
    )
    modo.add_argument(
        "--replay",
        type=str,
        default=None,
        metavar="FICHEIRO",
        help="reproduz um corpus e mostra as metricas (dry-run, sem camera/rato)",
    )
    parser.add_argument(
        "--record-max-frames",
        type=int,
        default=0,
        metavar="N",
        help="para a gravacao apos N frames (0 = sem limite)",
    )
    parser.add_argument(
        "--record-live",
        action="store_true",
        help="com --record, deixa o rato e os atalhos mexer no sistema. Sem "
             "isto a gravacao e muda: sem cliques a serio, sem Ctrl+C/Ctrl+V "
             "na janela em foco, sem o brilho mudar a luz que a camara ve",
    )
    parser.add_argument(
        "--replay-settle-guard-ms",
        type=float,
        default=0.0,
        metavar="MS",
        help="com --replay, diagnostico: recalcula o F1 excluindo esta janela "
             "em ms depois de cada mudanca de etiqueta. Nao altera o F1 "
             "principal nem o --replay-gate",
    )
    parser.add_argument(
        "--frame-width",
        type=int,
        default=640,
        help="largura de replay do corpus (corresponde a cfg.frame_width)",
    )
    parser.add_argument(
        "--frame-height",
        type=int,
        default=480,
        help="altura de replay do corpus (corresponde a cfg.frame_height)",
    )
    parser.add_argument(
        "--replay-gate",
        action="store_true",
        help="com --replay, sai com codigo 1 se algum alvo de aceitacao falhar",
    )
    return parser


def acquire_single_instance():
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = kernel32.CreateMutexW(None, False, "Maouse_JARVIS_v3")
        err = ctypes.get_last_error()
        if not handle or err == 183:
            return None
        return handle
    except Exception:
        return object()


def open_camera(cfg):
    candidates = [cfg.camera_index] if cfg.camera_index is not None else [0, 1, 2]
    for index in candidates:
        cam = CameraStream(index)
        if cam.open(cfg.frame_width, cfg.frame_height, 30):
            log.info("Camera %d ativa.", index)
            return cam
        cam.release()
    return None


def resolve_assistant(cfg):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    server_dir = cfg.assistant_dir or base_dir
    if os.path.isfile(os.path.join(server_dir, "server.py")):
        return Assistant3D(
            server_dir,
            cfg.assistant_url,
            window_hint=cfg.assistant_title,
            port=cfg.assistant_port,
        )
    log.warning("barehands (server.py) nao encontrado; assistente 3D desativado.")
    return None


def run_gui(cfg, cam, tracker, mouse, smooth_idx, gesture_ai, voice, tuner, speaker,
            snap, assistant, magnifier, ctx, state, tray_icon, license_mgr=None,
            remote=None, discovery=None, ble=None):
    """Arranca a janela nativa PySide6 (MainWindow) como interface principal.

    A MainWindow apresenta o feed com o esqueleto e overlays; a lógica de
    reconhecimento/movimento vive em ``process_frame`` (partilhada com o
    preview OpenCV), garantindo paridade total de comportamento.
    """
    try:
        from PySide6.QtWidgets import QApplication

        from ui.main_window import MainWindow
    except Exception as exc:
        log.error("ERRO CRITICO: GUI PySide6 falhou a importar (%s). "
                  "A cair para preview OpenCV. Corrige antes de usar.", exc)
        cfg.gui_enabled = False
        return None

    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    from ui.fonts import ensure_fonts

    ensure_fonts()
    window = MainWindow(
        cfg, cam, tracker, mouse, gesture_ai=gesture_ai, voice=voice,
        tuner=tuner, speaker=speaker, snap=snap,
        assistant=assistant, magnifier=magnifier,
        license_mgr=license_mgr, remote=remote, discovery=discovery,
        ble=ble, state=state,
    )
    window.setWindowTitle("Mãouse")
    window.resize(900, 640)
    # Arranca OCULTA: a interface so aparece com o comando gui_toggle
    # (gesto de paz com a mao esquerda). Serve apenas para configuracao.
    window.hide()

    # Ctrl+C e `kill` devem fechar a Maouse de forma limpa. O detalhe que
    # demora a perceber e que **fechar a janela nao sai da aplicacao**: com
    # o icone de bandeja a correr, o `window.close()` dispara o `closeEvent`
    # (e o BLE e restaurado, ja medido) mas o `QApplication` fica vivo a
    # espera no event loop. Por isso o pedido e `app.quit()`: o `exec()`
    # regressa e o `window.close()` logo a seguir em `main.py` faz o teardown
    # todo, pela ordem que o BLE precisa.
    #
    # O `SIGTERM` — o `kill`, o `systemd`, o logout — leva uma rede de
    # seguranca: se o event loop estiver preso (uma leitura da camara que nao
    # devolve, um modal aberto), `quit()` nao chega a correr e quem mandou o
    # sinal fica a espera — ou vem com um `SIGKILL` que deixaria o adaptador
    # **anunciavel**. A rede repete o pedido e, se ainda assim nao sair,
    # sai na mesma. E uma rede, nao o caminho normal.
    try:
        import signal as _sig

        from PySide6.QtCore import QTimer as _QTimer

        def _sair(signum, frame):
            _QTimer.singleShot(0, app.quit)

            def _segurar():
                _QTimer.singleShot(5000, app.quit)
                _QTimer.singleShot(10000, lambda: os._exit(0))

            if signum == _sig.SIGTERM:
                _segurar()

        _sig.signal(_sig.SIGINT, _sair)
        _sig.signal(_sig.SIGTERM, _sair)
    except Exception:
        pass

    app.exec()
    window.close()
    return window


def run_replay(args) -> int:
    """Avalia um corpus gravado e devolve o codigo de saida do portao.

    Dry-run total: sem camera, sem rato, sem interface, sem licenca. E o que
    torna a Onda 0 utilizavel em CI.

    Imprimir o relatorio NAO e reprovar: o codigo de saida e 1 apenas com
    ``--gate``, tal como em ``tools/eval_recognition.py``. Sao duas perguntas
    diferentes — "como esta o reconhecimento?" (sempre se responde) e "esta
    bom o suficiente?" (so se pergunta quando se quer bloquear).
    """
    from tools.eval_recognition import evaluate

    try:
        report = evaluate(
            args.replay,
            width=args.frame_width,
            height=args.frame_height,
            settle_guard_ms=getattr(args, "replay_settle_guard_ms", 0.0),
        )
    except FileNotFoundError as exc:
        print(f"ERRO: corpus nao encontrado ({args.replay}): {exc}")
        return 2
    except ValueError as exc:
        print(f"ERRO: corpus invalido ({args.replay}): {exc}")
        return 2
    print(report.render())
    if args.replay_gate and not report.passed:
        return 1
    return 0


def main():
    args = parse_args().parse_args()
    setup_logging(level=getattr(logging, args.log_level, logging.INFO))

    # --replay corre ANTES de qualquer licenca, camera, rato ou motor: e uma
    # avaliacao offline pura, e tem de ser possivel correr em CI onde nada
    # disso existe. O mutex tambem fica de fora de proposito.
    if args.replay:
        return run_replay(args)

    cfg = Config()
    cfg.selftest_frames = args.frames

    # Licenciamento: o construtor já carrega o estado persistido (load interno).
    # Ao arrancar, reconcilia o trial com o servidor (fonte de verdade, não
    # reinicia) e tenta revalidar o lease Pro, tudo best-effort/online.
    lic_ = LicenseManager()
    lic_.reconcile_trial()
    lic_.maybe_revalidate()
    cfg.license_tier = lic_.tier.value

    # Ações CLI de licença (retornam imediatamente).
    if args.activate_key:
        if lic_.activate(args.activate_key):
            print("Licença Pro ATIVADA com sucesso.")
        else:
            print("ERRO: chave de licença inválida.")
        return 0
    if args.deactivate:
        lic_.deactivate()
        cfg.license_tier = "free"
        print("Licença removida (modo Free ativo).")
        return 0

    mutex = acquire_single_instance()
    if mutex is None:
        log.info("Mãouse ja esta em execucao.")
        return 1

    if args.reset_config:
        try:
            if os.path.isfile(SETTINGS_FILE):
                os.remove(SETTINGS_FILE)
                log.info("Definicoes apagadas.")
        except Exception:
            pass
    smooth_idx = load_settings(cfg)

    # Onda 0: gravacao de corpus. As teclas de etiqueta vivem no preview
    # OpenCV, portanto --record desliga a GUI PySide6 — e o rato tambem, porque
    # o pipeline tratava a recolha como uso normal: o cursor movia-se e cada
    # PINCH clicava a serio. Quem grava fica a mirar ao que dao os gestos, e
    # um PINKY solta Ctrl+C na janela que estiver em foco. `MuteMouse` e
    # `--record-live` tratam disso.
    recorder = None
    mute_output = bool(args.record) and not args.record_live
    if args.record:
        from core.corpus import CorpusRecorder, describe_device

        recorder = CorpusRecorder(
            path=args.record,
            max_frames=args.record_max_frames,
            # Quem vai ler este ficheiro em daqui a seis meses precisa de saber
            # em que máquina e a que taxa as mãos foram vistas, sem ter de
            # adivinhar. O fps medido é carimbado no `flush`, no fim.
            meta={
                "device": describe_device(),
                "camera": f"{cfg.cam_width}x{cfg.cam_height}@{cfg.cam_fps}",
            },
        )
        cfg.preview = True
        args.no_gui = True
        args.no_voice = True
        log.info(
            "A GRAVAR CORPUS: %s | etiqueta %s | teclas 0-9,d,c,g | x limpa | "
            "Q sai e grava | %s",
            args.record, recorder.label,
            "rato e atalhos CALADOS (--record-live reativa)" if mute_output
            else "rato e atalhos ACTIVOS (atencao: cliques a serio)",
        )

    # Gate Free/Pro — aplicado APÓS load_settings para que os settings do disco
    # NÃO reativem funcionalidades Pro-locked no Free (bug: voice_enabled=true
    # nos settings reativava a voz no Free). No Free, as features Pro-locked
    # ficam desligadas independentemente do que estiver guardado.
    set_active_license(lic_)
    ent = entitlements(lic_.tier)
    cfg.snap_enabled = cfg.snap_enabled and not is_pro_locked(lic_.tier, "snap")
    cfg.voice_enabled = cfg.voice_enabled and not is_pro_locked(lic_.tier, "voice")
    cfg.tts_enabled = cfg.tts_enabled and not is_pro_locked(lic_.tier, "tts")
    cfg.ai_enabled = cfg.ai_enabled and ent["ai"]
    cfg.autotune_enabled = cfg.autotune_enabled and ent["autotune"]
    cfg.trading_master_enabled = (
        cfg.trading_master_enabled
        and not is_pro_locked(lic_.tier, "trading_master")
    )
    cfg.tv_button_enabled = (
        cfg.tv_button_enabled
        and not is_pro_locked(lic_.tier, "trading_master")
    )
    cfg.low_light_boost = cfg.low_light_boost and ent["low_light"]
    cfg.magnifier_enabled = cfg.magnifier_enabled
    cfg.clap_enabled = cfg.clap_enabled
    cfg.left_hand_commands = cfg.left_hand_commands
    # Deteta SEMPRE ate 2 maos (para a UI poder mostrar "2 maos" tambem no
    # Free); o que fica bloqueado sao os RECURSOS de 2 maos, nao a deteccao.
    cfg.num_hands = 2

    log.info("License: %s", "PRO" if lic_.is_pro else "FREE")

    if args.camera is not None:
        cfg.camera_index = args.camera
    if args.gain is not None:
        cfg.move_gain = args.gain
    if args.tray:
        cfg.preview = bool(args.preview) and not args.no_preview
    else:
        if args.no_preview:
            cfg.preview = False
    if args.no_voice:
        cfg.voice_enabled = False
    if args.no_autotune:
        cfg.autotune_enabled = False
    if args.voice_always:
        cfg.voice_always_on = True
    if args.no_tts:
        cfg.tts_enabled = False
    if args.whisper_model:
        cfg.whisper_model = args.whisper_model

    gesture_ai = None
    if cfg.ai_enabled and not args.no_ai:
        try:
            ai_path = ensure_ai_model(cfg.ai_model_path)
            gesture_ai = GestureAI(ai_path)
            log.info("IA de gestos ativa (confianca min %.2f).", cfg.ai_confidence_min)
        except FileNotFoundError as exc:
            log.warning("IA de gestos indisponivel (%s); a usar regras geometricas.", exc)

    model_path = ensure_model(cfg.model_path, cfg.model_url)

    cam = open_camera(cfg)
    if cam is None:
        log.error("ERRO: nenhuma camera encontrada.")
        return 1

    tracker = HandTracker(
        model_path, num_hands=cfg.num_hands,
        use_gpu=args.gpu, num_threads=cfg.tracker_threads,
    )
    mouse = MuteMouse() if mute_output else MouseCtl()
    remote = None
    discovery = None
    ble = None
    if cfg.remote_enabled:
        remote = RemoteServer(cfg, mouse)
        if remote.start():
            log.info("Controlo remoto por telemovel ativo (IPs: %s, porta: %d).",
                     ", ".join(lan_ips()) or "-", cfg.remote_port)
            # Só anuncia quem tem algo para anunciar: um `_maouse._tcp` a
            # apontar para uma porta fechada é pior do que não anunciar, porque
            # o telefone escolhe-o e perde tempo a sondar.
            #
            # O objecto passa à janela mesmo quando o anúncio não arrancou.
            # Perder a referência aqui significava perder a única hipótese de
            # repassar quando a rede voltasse; `_apply_discovery` tenta de novo
            # a cada vez que as definições são gravadas.
            if cfg.remote_discovery:
                discovery = MaouseAdvertiser(cfg)
                discovery.start()

            # O BLE é um **segundo transporte para o mesmo rato**: o `RemoteBLE`
            # não tem comandos próprios, entrega-os ao `_handle` deste mesmo
            # servidor. Por isso só é criado aqui — sem um `RemoteServer` vivo não
            # há a quem entregar o comando — e não como uma via separada, que
            # acabaria com duas implementações da mesma coisa.
            if cfg.remote_ble:
                # Importar `dbus_next` e falar com o `bluetoothd` não é
                # garantido. Uma falha aqui não pode impedir a Maouse de
                # arrancar: quem não tem Bluetooth fica com o WiFi, que é o
                # que já existia, e o log diz porquê.
                try:
                    ble = RemoteBLE(cfg, remote)
                    if ble.start():
                        log.info("Controlo remoto por BLE ativo (servico %s).",
                                 BLE_SERVICE_UUID)
                    else:
                        log.warning(
                            "BLE nao arrancou (bluetoothd parado, adaptador "
                            "desligado ou sem permissao D-Bus). O WiFi continua."
                        )
                        ble = None
                except Exception as exc:
                    log.warning("BLE indisponivel (%s); a usar apenas WiFi.", exc)
                    ble = None
    else:
        log.info("Controlo remoto por telemovel desativado.")
    tuner = AutoTuner(cfg)

    speaker = None
    if cfg.tts_enabled:

        def _voice_path(name):
            bundled = os.path.join(cfg.piper_model_dir, name)
            if os.path.isfile(bundled):
                return bundled
            return os.path.join(user_models_dir(), "piper", name)

        voice_files = (
            (cfg.piper_onnx_url, _voice_path("pt_BR-faber-medium.onnx")),
            (cfg.piper_conf_url, _voice_path("pt_BR-faber-medium.onnx.json")),
        )
        speaker = Speaker(enabled=True, model_dir=cfg.piper_model_dir,
                          voice_files=voice_files)
        speaker.start()

    snap = SnapEngine(radius_px=cfg.snap_radius_px, strength=cfg.snap_strength,
                      poll_hz=cfg.snap_poll_hz, enabled=cfg.snap_enabled)
    snap.start()

    assistant = resolve_assistant(cfg)
    magnifier = MagnifierCtl(cfg.magnifier_step_frac) if cfg.magnifier_enabled else None

    voice = None
    if not args.no_voice:
        import queue as _queue

        voice = VoiceEngine(cfg, _queue.Queue())
        if speaker is not None:
            voice.set_speaker(speaker)
        if cfg.llm_enabled:
            voice.set_chat(ChatClient(cfg))
        if cfg.voice_enabled:
            voice.start()

    ctx = AppCtl()
    state = {
        "paused": False,
        "show_help": False,
        "flash": 0,
        "freeze_until": 0.0,
        "button_down": False,
        "pinch_debug": bool(getattr(args, "pinch_debug", False)),
        "dbg_until": 0.0,
        # Gate de bloqueio (process_frame): set no arranque e atualizado pelo
        # watchdog de uso enquanto o trial consome tempo.
        "license_blocked": lic_.is_blocked(),
        "_license_warned": False,
        # `--record` sem `--record-live`: nenhum efeito no sistema. O toast
        # continua a dizer o que foi reconhecido, que e o que o operador
        # precisa para etiquetar — o que se cala e so a accao sobre o rato, o
        # teclado e o brilho.
        "mute_output": mute_output,
    }
    state["_usage_watchdog"] = UsageWatchdog(lic_, state)
    # O motor da câmara e o telemóvel disputam o mesmo rato. O árbitro dá o
    # rato ao telemóvel enquanto este envia comandos e devolve-o à câmara
    # assim que fica em silêncio.
    arbiter = RemoteArbiter(state, hold_s=1.5)
    state["_remote_arbiter"] = arbiter
    if remote is not None:
        remote.on_activity = arbiter.note
        remote.on_command_begin = arbiter.begin_command
        remote.on_command_end = arbiter.end_command
    tray_icon = None
    tray_adapter = None

    def tray_apply(action, value):
        note = apply_command(action, value, cfg, mouse, state, ctx)
        if note and not cfg.preview:
            if tray_icon:
                tray_icon.notify("Mãouse", note)
            log.info("[bandeja] %s", note)

    if args.tray:
        tray_adapter = TrayAppAdapter(state, cfg, voice, snap, tuner,
                                      assistant, tray_apply)
        tray_icon = TrayIcon(tray_adapter)
        if tray_icon.start():
            log.info("Icone na bandeja ativo.")

    ctx.speaker = speaker
    ctx.snap = snap
    ctx.assistant = assistant
    ctx.magnifier = magnifier

    smooth_label = SMOOTH_PRESETS[smooth_idx][0] if smooth_idx >= 0 else "CUSTOM"
    log.info("Ecra: %dx%d | ganho: %.1f | suavidade: %s",
             mouse.screen_w, mouse.screen_h, cfg.move_gain, smooth_label)
    log.info(
        "Gestos: mao aberta/1 dedo=mover | pinca index=clique/arrastar |"
        " punho=cima/baixo=scroll | pinca medio=clique dir |"
        " 3 dedos=cima/baixo=volume | polegar=play/pausa"
    )
    # Os atalhos aqui são os que `core/engine.py` prime de facto (618 e 623) e
    # não os que se escreviam: diziam "Ctrl+D" e "Ctrl+E", que o motor nunca
    # prime. Quem seguisse a instrução carregava Ctrl+D — que no Excel duplica
    # a linha e no Explorer não faz nada — e a janela não minimizava.
    # `Win+Down` e não "Win+↓": a seta não existe em cp1252, que é o que a
    # consola do Windows usa, e um `log.info` com ela lá levanta
    # UnicodeEncodeError — ou seja, a correcção da mentira partia o arranque.
    # `tests/test_help_truthfulness.py` é o que impede isto de divergir outra vez.
    log.info(
        "Novo: mindinho=copy | polegar+mindinho=paste |"
        " dois dedos esq/dir (2 maos)=brilho | fechar/abrir punho x2=Win+D |"
        " bye bye=Win+Down | 3 palmas=Alt+Tab | lupa | snap"
    )
    log.info(
        "Teclas: [ ] ganho | , . suavidade | a auto-afinacao | v voz |"
        " s gravar | h ajuda | espaco pausa | Q sair"
    )

    exit_code = 0
    initial_params = (cfg.move_gain, cfg.filter_min_cutoff, cfg.filter_beta)
    use_gui = (not args.no_gui) and not (cfg.selftest_frames or args.frames)
    cfg.gui_enabled = use_gui
    try:
        if use_gui:
            result = run_gui(
                cfg, cam, tracker, mouse, smooth_idx, gesture_ai, voice,
                tuner, speaker, snap, assistant, magnifier, ctx, state,
                tray_icon, license_mgr=lic_, remote=remote,
                discovery=discovery, ble=ble,
            )
            if result is None:
                log.info("A usar preview OpenCV (sem PySide6).")
                end_state = run_loop(
                    cfg, cam, tracker, mouse, smooth_idx, gesture_ai, voice,
                    tuner, ctx, state, recorder=recorder,
                )
            else:
                end_state = state
                if (
                    (cfg.move_gain, cfg.filter_min_cutoff, cfg.filter_beta) != initial_params
                ) and tuner.enabled:
                    save_settings(cfg, state.get("smooth_name", "NORMAL"))
                end_state = None
            if (
                end_state is not None
                and (
                    (cfg.move_gain, cfg.filter_min_cutoff, cfg.filter_beta) != initial_params
                    or end_state.get("touched_settings")
                )
                and tuner.enabled
            ):
                save_settings(cfg, end_state["smooth_name"])
        else:
            end_state = run_loop(
                cfg, cam, tracker, mouse, smooth_idx, gesture_ai, voice, tuner, ctx,
                state, recorder=recorder,
            )
            if (
                (cfg.move_gain, cfg.filter_min_cutoff, cfg.filter_beta) != initial_params
                or end_state.get("touched_settings")
            ) and tuner.enabled:
                save_settings(cfg, end_state["smooth_name"])
    except KeyboardInterrupt:
        log.info("Ate ja!")
    except Exception as exc:
        log.error("ERRO fatal: %s", exc)
        import traceback
        traceback.print_exc()
        exit_code = 1
    finally:
        if tray_icon is not None:
            tray_icon.stop()
        if voice is not None:
            voice.stop()
        if speaker is not None:
            speaker.stop()
        snap.stop()
        # O BLE antes do `RemoteServer`: o `RemoteBLE` usa-o para entregar
        # comandos, e um `WriteValue` a meio do encerramento encontraria um
        # servidor já parado. A ordem é o contrário do que se lê bem.
        if ble is not None:
            try:
                ble.stop()
            except Exception:
                pass
        if remote is not None:
            try:
                remote.stop()
            except Exception:
                pass
        if discovery is not None:
            try:
                discovery.stop()
            except Exception:
                pass
        tracker.close()
        cam.release()
        cv2.destroyAllWindows()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
