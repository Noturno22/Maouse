"""OpenCV preview rendering (overlay, skeleton, badges).

Extraído de ``main.py``: apenas apresentação do preview; a lógica vive em
``core.engine.process_frame``, partilhada com a MainWindow PySide6.
"""
import math
import time

import cv2

from core.gestures import Gesture
from core.tracker import HAND_CONNECTIONS

BADGES = {
    Gesture.NONE: ("SEM MAO", (150, 150, 150)),
    Gesture.OPEN: ("MOVER", (80, 200, 255)),
    Gesture.ONE: ("MOVER 1D", (80, 200, 255)),
    Gesture.PINCH: ("CLIQUE ESQ", (90, 220, 90)),
    Gesture.PINCH_MID: ("CLIQUE DIR", (60, 60, 235)),
    Gesture.FIST: ("SCROLL", (255, 80, 200)),
    Gesture.PEACE: ("DOIS DEDOS", (255, 80, 200)),
    Gesture.THREE: ("VOLUME", (255, 170, 60)),
    Gesture.THUMB_UP: ("PLAY/PAUSA", (140, 225, 225)),
    Gesture.PINKY: ("COPIAR", (180, 120, 255)),
    Gesture.SHAKA: ("COLAR", (120, 200, 180)),
}
COLOR_GRAY = (160, 160, 160)
COLOR_WHITE = (245, 245, 245)
COLOR_GREEN = (90, 220, 90)
COLOR_PINK = (255, 80, 200)
COLOR_DARK = (22, 22, 22)


def draw_hand(frame, hand_frame, color):
    for a, b in HAND_CONNECTIONS:
        pa = tuple(int(v) for v in hand_frame.points_px[a])
        pb = tuple(int(v) for v in hand_frame.points_px[b])
        cv2.line(frame, pa, pb, (200, 200, 200), 1)
    px, py = int(hand_frame.palm_center[0]), int(hand_frame.palm_center[1])
    cv2.line(frame, (px - 14, py), (px + 14, py), color, 1)
    cv2.line(frame, (px, py - 14), (px, py + 14), color, 2)
    cv2.circle(frame, (px, py), 9, color, 2)


#: Cor de um gesto que o reconhecedor produz mas que ainda não tem rótulo
#: próprio. Neutra de propósito: é um estado por decidir, não um estado
#: bonito. Um amarelo vivo seria a tentação e seria o erro — a cor é o que o
#: utilizador lê antes da palavra, e diria "isto é um gesto oficial" quando é
#: uma lacuna.
#:
#: Não é o cinzento de `BADGES[Gesture.NONE]` (150, 150, 150): essa é a cor de
#: "não estou a ver a mão", e aqui quer-se o contrário disso. Também não é
#: nenhuma cor de `BADGES`, para que um gesto por nomear não se pareça com um
#: gesto já decidido — o esqueleto da mão é desenhado com esta cor, e dois
#: estados que se vêem iguais são dois estados que o utilizador não consegue
#: distinguir. `tests/test_overlay_badge_honesty.py` verifica as duas coisas.
COLOR_SEM_ROTULO = (200, 200, 200)


def _badge(hf):
    """O rótulo e a cor do gesto de `hf`.

    `BADGES` cobre os gestos que o utilizador já viu nomeados. O que falta
    **não pode cair no rótulo de NONE**: `BADGES.get(g, BADGES[Gesture.NONE])`
    punha "SEM MAO" com a mão no enquadramento, e o motor produz `THUMB_DOWN`
    (`core/gestures.py:248`) e `ROCK` (`:260`, confirmado pela IA em `:297`),
    nenhum dos dois com entrada em `BADGES`.

    O efeito era o pior possível num ecrã de feedback: o utilizador faz o gesto,
    o classificador concorda, e o único sinal que tem diz que o programa não
    está a ver a mão. Percebe que "não está a funcionar", repete o gesto — e é
    exactamente a tentativa cansativa que este projecto existe para tirar.

    O rótulo provisório é o `name` do enum, não uma palavra escolhida: o que
    fazer com estes dois gestos é decisão do dono do produto e ainda não está
    tomada, e inventar um rótulo aqui seria tomá-la em silêncio. Um nome de
    código no ecrã é feio e é honesto.
    """
    par = BADGES.get(hf.gesture)
    if par is not None:
        return par
    return (hf.gesture.name, COLOR_SEM_ROTULO)


def _wrap_pairs(pairs, max_chars):
    """Quebra ``["0 NONE", "1 OPEN", ...]`` em linhas de ate ``max_chars``.

    A largura util depende da resolucao da camara (640x480 no default), e a
    tabela de teclas e a unica coisa que o operador nao pode deixar de ver.
    Logo a quebra e calculada a partir do texto real com `getTextSize`, e nao
    de um numero de caracteres fixo: um `len()` fixo truncava a tabela em
    cameras largas e empurrava a ultima linha para fora do ecra nas estreitas.
    """
    lines, cur = [], ""
    for p in pairs:
        cand = p if not cur else f"{cur} | {p}"
        if cur and len(cand) > max_chars:
            lines.append(cur)
            cur = p
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return lines


def record_keymap_lines(w, keys, scale=0.42):
    """As linhas do rodape: a tabela de teclas partida para a largura `w`.

    A largura por caractere e medida do proprio texto com `getTextSize` e nao
    de uma constante: `'0'` e mais estreito que `'W'`, e o separador `" | "`
    gasta tres caracteres. Um `len()` fixo dava uma tabela truncada ou a sair
    do ecra, conforme a camara - e quem se descobre com `THUMB_D` a meio de
    uma recolha nao tem nem como corrigir.
    """
    (pw, _), _ = cv2.getTextSize("0" * 20, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
    max_chars = max(8, int((w - 24) / (pw / 20.0)))
    return _wrap_pairs([f"{k} {n}" for k, n in keys.items()], max_chars)


def _fps_txt(fps):
    """fps medido, ou `--` enquanto ainda nao ha dois frames.

    `--` e nao `0`: zero fps e uma leitura (a camara parou) e aqui so
    significa "ainda nao medido". A diferenca e a diferenca entre um numero que
    mente e um que admite que nao sabe.
    """
    if not fps:
        return "fps: --"
    return f"{fps:.0f} fps"


def draw_record_panel(frame, info):
    """Faixa de gravacao: em que etiqueta se esta, e com que tecla se repete.

    A alternativa era um toast de 1,3 s e memoria. Quem grava tem de ler a
    etiqueta corrente sem desviar os olhos da mao, e tem de confirmar que a
    tecla que acabou de carregar foi aceite - porque uma etiqueta errada fica
    no ficheiro e `x` nao desfaz a ultima, limpa tudo.

    A tabela de teclas fica permanentemente no rodape. E o unico sitio onde o
    mapeamento (que e um `dict` no codigo) pode ser conferido com o que o
    operador acha que primeu, sem sair da janela.
    """
    h, w = frame.shape[:2]
    label, key = info["label"], info["key"]
    hands = info.get("hands", 0)
    rows = [
        (f"A GRAVAR: {label} [{key}] | {info['frames']}f"
         f" (neste {info['seg_frames']})", COLOR_GREEN, 0.5),
        (f"{_fps_txt(info.get('fps'))} | H ajuda | Q sai e grava",
         COLOR_WHITE, 0.45),
    ]
    if hands > 1:
        rows.append(
            (f"{hands} MAOS NO ECRA: SO A MAO DA DIREITA E GRAVADA",
             COLOR_PINK, 0.45))

    y0, lh = 70, 20
    cv2.rectangle(frame, (0, y0 - 4), (w, y0 + lh * len(rows)), COLOR_DARK, -1)
    cv2.rectangle(frame, (0, y0 - 4), (w, y0 + lh * len(rows)), COLOR_GREEN, 1)
    for i, (txt, col, sc) in enumerate(rows):
        cv2.putText(frame, txt, (12, y0 + lh * i + 12),
                    cv2.FONT_HERSHEY_SIMPLEX, sc, col, 1, cv2.LINE_AA)

    # Rodape: a tabela inteira, sempre. Deriva de `info["keys"]`, que o motor
    # copiou de `core.corpus.LABEL_KEY_CHOICES` - o preview nao tem tabela
    # propria para divergir.
    scale = 0.42
    lines = record_keymap_lines(w, info["keys"], scale)
    y1, klh = h - 16 * len(lines) - 6, 16
    cv2.rectangle(frame, (0, y1), (w, h), COLOR_DARK, -1)
    cv2.rectangle(frame, (0, y1), (w, y1), COLOR_GREEN, 1)
    for i, line in enumerate(lines):
        cv2.putText(frame, line, (12, y1 + 14 + klh * i),
                    cv2.FONT_HERSHEY_SIMPLEX, scale, COLOR_WHITE, 1, cv2.LINE_AA)


def draw_overlay(frame, all_frames, active_side, last_scroll, fps, cfg,
                 smooth_name, paused, show_help, flash, ui):
    h, w = frame.shape[:2]
    hand_frame = all_frames.get(active_side)
    color = BADGES[Gesture.NONE][1]

    for side, hf in all_frames.items():
        c = _badge(hf)[1]
        if side != active_side:
            draw_hand(frame, hf, COLOR_GRAY)
        else:
            draw_hand(frame, hf, c)
            thumb = tuple(int(v) for v in hf.points_px[4])
            tip = tuple(int(v) for v in hf.index_tip)
            pinch_color = COLOR_GREEN if hf.gesture == Gesture.PINCH else COLOR_GRAY
            cv2.line(frame, thumb, tip, pinch_color, 2)
            if hf.gesture == Gesture.FIST:
                mid = tuple(int(v) for v in hf.points_px[12])
                cv2.circle(frame, mid, 7, BADGES[Gesture.FIST][1], 2)
            color = c

    if paused:
        label = "PAUSA"
    elif hand_frame is None:
        label = BADGES[Gesture.NONE][0]
    else:
        label = _badge(hand_frame)[0]
    cv2.rectangle(frame, (12, 10), (268, 66), COLOR_DARK, -1)
    cv2.rectangle(frame, (12, 10), (268, 66), color, 2)
    cv2.putText(frame, label, (24, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2, cv2.LINE_AA)

    x_right = w - 118
    if ui["ai_on"]:
        conf = ui["ai_conf"]
        ai_txt = f"IA {int(conf * 100):3d}%" if hand_frame is not None else "IA  ok"
        ai_col = COLOR_GREEN if conf >= cfg.ai_confidence_min else COLOR_WHITE
        cv2.rectangle(frame, (x_right, 10), (w - 12, 40), COLOR_DARK, -1)
        cv2.putText(frame, ai_txt, (x_right + 10, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, ai_col, 1, cv2.LINE_AA)
        x_right -= 96
    class_conf = ui.get("class_conf", math.nan)
    if (
        hand_frame is not None
        and not math.isnan(class_conf)
        and class_conf < getattr(cfg, "min_class_conf", 0.0)
    ):
        cv2.rectangle(frame, (x_right, 10), (w - 12, 40), COLOR_DARK, -1)
        cv2.putText(frame, "MAO ???", (x_right + 10, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_GRAY, 1, cv2.LINE_AA)
        x_right -= 96
    if ui.get("magnify"):
        cv2.rectangle(frame, (x_right, 10), (w - 12, 40), COLOR_DARK, -1)
        cv2.putText(frame, f"LUPA {ui['magnify']}", (x_right + 8, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_PINK, 1, cv2.LINE_AA)
        x_right -= 110
    if ui.get("hands"):
        cv2.rectangle(frame, (x_right, 10), (w - 12, 40), COLOR_DARK, -1)
        cv2.putText(frame, f"{ui['hands']} MAOS", (x_right + 10, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_WHITE, 1, cv2.LINE_AA)

    if ui["voice"] != "off":
        vtxt = {"on": "VOZ ON ", "listening": "VOZ <OUVINDO>"}.get(
            ui["voice"], f'VOZ {cfg.voice_wake_word.upper()}'
        )
        cv2.rectangle(frame, (12, 74), (190, 98), COLOR_DARK, -1)
        vcol = COLOR_PINK if ui["voice"] != "wake" else COLOR_GRAY
        if ui["voice"] == "on":
            vcol = COLOR_PINK
        cv2.putText(frame, vtxt, (20, 92),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, vcol, 1, cv2.LINE_AA)

    if ui["toast_until"] > time.monotonic() and ui["toast"]:
        txt = ui["toast"]
        (tw, _), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        tx = (w - tw) // 2
        cv2.rectangle(frame, (tx - 10, 44), (tx + tw + 10, 76), COLOR_DARK, -1)
        cv2.putText(frame, txt, (tx, 68),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_GREEN, 2, cv2.LINE_AA)

    if last_scroll is not None:
        cv2.putText(
            frame, f"scroll {last_scroll:+.0f} px/frame", (16, 112),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, BADGES[Gesture.FIST][1], 1, cv2.LINE_AA,
        )

    if ui.get("light"):
        cv2.putText(frame, "LUZ BAIXA: realce ON", (16, 132),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (80, 180, 255), 1, cv2.LINE_AA)

    if not ui.get("record"):
        cv2.putText(
            frame, "H ajuda | Q sai", (w - 170, h - 34),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, COLOR_GRAY, 1, cv2.LINE_AA,
        )

    if cfg.license_tier != "pro":
        wtxt = "MAouse FREE"
        (tww, twh), _ = cv2.getTextSize(wtxt, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        cv2.putText(
            frame, wtxt, ((w - tww) // 2, 44),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (90, 180, 255), 2, cv2.LINE_AA,
        )

    if hand_frame is not None:
        ratio = min(hand_frame.pinch_ratio / 1.2, 1.0)
        pinch_color = COLOR_GREEN if hand_frame.gesture == Gesture.PINCH else COLOR_GRAY
        cv2.rectangle(frame, (12, h - 30), (12 + int(ratio * (w - 24)), h - 24), pinch_color, -1)

    # A faixa de gravacao substitui esta barra: durante a recolha o ganho e a
    # suavidade ficam parados, e a tabela de teclas e o que o operador precisa
    # de ter no ecra. O fps ja vai na faixa de cima.
    if not ui.get("record"):
        at_txt = "AT" if ui["autotune"] else ""
        strip = f"{fps:4.0f} fps | ganho {cfg.move_gain:.1f} | {smooth_name}"
        if at_txt:
            strip += f" | {at_txt}"
        if ui.get("tts"):
            strip += f" | voz-neural:{ui['tts']}"
        cv2.rectangle(frame, (0, h - 22), (w, h), COLOR_DARK, -1)
        cv2.putText(
            frame, strip, (max(w - 520, 8), h - 7),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_WHITE, 1, cv2.LINE_AA,
        )

    if ui.get("record"):
        # Depois da barra de fps (que e substituida) e antes da ajuda (que a
        # ajuda fica por cima de tudo o resto, como deve ser).
        draw_record_panel(frame, ui["record"])

    if show_help:
        lines = [
            "AJUDA",
            "mao aberta / 1 dedo ... mover cursor",
            "pinca index ............ botao esquerdo (manter=arrastar)",
            "punho + cima/baixo ..... scroll",
            "pinca medio ............ clique direito",
            "dois dedos ............. (sem funcao)",
            "tres dedos + cima/baixo = volume",
            "polegar cima ........... play/pausa multimédia",
            "dedo mindinho .......... copiar (Ctrl+C)",
            "polegar + mindinho ..... colar (Ctrl+V)",
            "swipe < com mao esq ..... janela anterior (Alt+Tab)",
            "swipe > com mao esq ..... proxima janela (Alt+Tab)",
            "segurar mao esq aberta ... escolher janela (alternador)",
            "dois dedos esq (2 maos)  diminuir brilho",
            "dois dedos dir (2 maos)  aumentar brilho",
            "fechar/abrir punho x2 .. Win+D",
            "bye bye (onda) ......... minimizar janela (Win+↓)",
            "ondas 2 maos ........... Alt+Tab",
            "PALMAS (x3) ........... Alt+Tab",
            "2 maos abertas + afastar = lupa (zoom)",
            "[ / ] ................. ganho -/+",
            ", / . ................. suavidade",
            "m ..................... snap magnetico ON/OFF",
            "a ............. auto-afinacao | v voz | s gravar",
            "espaco ................ pausar | Q sair",
            "voz: jarvis <comando natural>",
        ]
        if ui.get("record"):
            # O rodape ja tem a tabela de teclas; aqui ficam as tres regras que
            # nao se deduzem dela e quecustam a sessao quando se falha uma.
            lines += [
                "--- A GRAVAR (--record) ---",
                "a tecla vai ANTES de adoptar o gesto:",
                "  a etiqueta conta a partir do momento",
                "  em que a carregaste, nao em que viste",
                "so a mao do CURSOR e gravada (a da DIREITA",
                "  do ecra). A outra fora de vista.",
                "frames em 0f = etiqueta posta sem mao.",
                "x limpa a sessao toda. Q sai e grava.",
            ]
        # Durante a gravacao a faixa de cima ocupa ate y=130: a ajuda desce para
        # nao ficar coberta pela linha que a explica.
        hy = 140 if ui.get("record") else 120
        cv2.rectangle(frame, (12, hy), (430, hy + 20 * len(lines) + 12), COLOR_DARK, -1)
        cv2.rectangle(frame, (12, hy), (430, hy + 20 * len(lines) + 12), COLOR_GRAY, 1)
        for i, line in enumerate(lines):
            cv2.putText(
                frame, line, (24, hy + 20 + 20 * i),
                cv2.FONT_HERSHEY_SIMPLEX, 0.48, COLOR_WHITE, 1, cv2.LINE_AA,
            )

    if flash > 0:
        cv2.rectangle(frame, (0, 0), (w - 1, h - 1), COLOR_GREEN, 6)
    return frame
