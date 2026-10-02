import collections
import math
from dataclasses import dataclass
from enum import Enum

from core.filters import LandmarkFilterBank

FINGER_TIPS_PIPS = ((8, 6), (12, 10), (16, 14), (20, 18))
PALM_IDS = (0, 5, 9, 13, 17)
INDEX, MIDDLE, RING, PINKY = 0, 1, 2, 3
THUMB_TIP, INDEX_TIP, MIDDLE_TIP = 4, 8, 12


class Gesture(Enum):
    # Os `value` são o que um humano lê no código; o que o utilizador vê está em
    # `core/overlay.py:BADGES` e `ui/theme.py:GESTURE_LABELS`, e tem de bater
    # certo com estes (trancado em tests/test_gesture_labels.py).
    #
    # REGRA: os valores têm de ser ÚNICOS. Num Enum do Python, dois membros com o
    # mesmo valor não são dois membros: o segundo vira alias do primeiro, some da
    # iteração e passa a devolver o nome do outro. A Onda 1 §1.4 mandava só
    # corrigir o FIST para "scroll" — com o PEACE já em "scroll" isso apagava o
    # PEACE em silêncio. Por isso os dois mudaram.
    NONE = "sem mao"
    OPEN = "mover"
    ONE = "mover (1 dedo)"
    PINCH = "clique esquerdo"
    PINCH_MID = "clique direito"
    FIST = "scroll"
    PEACE = "dois dedos"
    THREE = "volume"
    THUMB_UP = "play/pausa"
    THUMB_DOWN = "deslike"
    PINKY = "copiar"
    SHAKA = "colar"
    ROCK = "interface"


@dataclass
class HandFrame:
    points_px: list
    hand_scale_px: float
    pinch_ratio: float
    pinch_mid_ratio: float
    raw_gesture: "Gesture"
    gesture: "Gesture"
    index_tip: tuple
    palm_center: tuple
    ai_conf: float = 0.0
    # True se a mao abriu totalmente (todos os dedos bem esticados). Usado para
    # abrir o alternador de janelas quase de imediato (gesto claro e intencional).
    fully_open: bool = False
    # Onda 1 §1.2. `nan` = "nao medido" (corpus v1, ou tracker sem score), e NAO
    # "confianca zero" — nunca interpretar como 0.
    class_conf: float = math.nan


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


class GestureEngine:
    LEFT_BUTTON_GESTURES = (Gesture.PINCH,)

    def __init__(self, cfg, gesture_ai=None):
        self.cfg = cfg
        self.ai = gesture_ai
        self.ai_conf = 0.0
        self._ai_window = collections.deque(maxlen=getattr(cfg, "ai_window", 5))
        # Onda 1 §1.1. Lida uma vez: o `,`/`.` do preview mexe em
        # `cfg.filter_min_cutoff` (a palma) e de proposito NAO nesta banca.
        self._landmark_filter = LandmarkFilterBank(
            min_cutoff=getattr(cfg, "landmark_min_cutoff", 3.0),
            beta=getattr(cfg, "landmark_beta", 0.010),
        )
        self._filter_landmarks = bool(getattr(cfg, "landmark_filter_enabled", True))
        self._pinch_index_on = False
        self._pinch_mid_on = False
        self._candidate = Gesture.NONE
        self._candidate_count = 0
        self._committed = Gesture.NONE
        self._scroll_prev_y = None
        self._scroll_acc_y = 0.0
        self._vol_prev_y = None
        self._vol_acc_y = 0.0
        self._prev_curled = [False, False, False, False]

    def reset(self):
        self._ai_window.clear()
        self._landmark_filter.reset()
        self._pinch_index_on = False
        self._pinch_mid_on = False
        self._candidate = Gesture.NONE
        self._candidate_count = 0
        self._committed = Gesture.NONE
        self._scroll_prev_y = None
        self._scroll_acc_y = 0.0
        self._vol_prev_y = None
        self._vol_acc_y = 0.0
        self._prev_curled = [False, False, False, False]

    def update(self, landmarks, width, height, conf=None, t=None):
        cfg = self.cfg
        # `has_z` decide-se pela ENTRADA, e nao pela saida da banca: a banca preenche
        # a z a 0.0, e ler a forma dela faria uma deteccao 2D parecer 3D.
        has_z = len(landmarks[0]) > 2
        # Onda 1 §1.1: filtrar os 21 pontos ANTES de qualquer limiar. Tudo o que
        # segue — escala, rácio de pinça, curl, SHAKA, palma — consome esta lista.
        # `t` e o timestamp do frame: sem ele o filtro mede o tempo pelo relogio
        # de parede e passa a depender da velocidade do loop (ver o filtro).
        src = (
            self._landmark_filter.filter(landmarks, width, height, t)
            if self._filter_landmarks
            else landmarks
        )
        pts = [(lm[0] * width, lm[1] * height) for lm in src]
        if has_z:
            pts3 = [(lm[0] * width, lm[1] * height, lm[2]) for lm in src]
        else:
            pts3 = pts
        self._ai_window.append(pts3)
        wrist = pts[0]
        scale = max(_dist(wrist, pts[9]), 1e-6)
        # racio 2D: fiável de frente para a câmara (os dedos sobrepõem-se na projeção)
        pinch_ratio_2d = _dist(pts[THUMB_TIP], pts[INDEX_TIP]) / scale
        pinch_mid_ratio_2d = _dist(pts[THUMB_TIP], pts[MIDDLE_TIP]) / scale
        if has_z:
            # racio 3D: imune a inclinacao da mao (foreshortening)
            ky = height / width
            p3 = [(lm[0], lm[1] * ky, lm[2]) for lm in src]

            def _d3(a, b):
                return math.sqrt(
                    (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2
                )

            scale3 = max(_d3(p3[0], p3[9]), 1e-6)
            pinch_ratio_3d = _d3(p3[THUMB_TIP], p3[INDEX_TIP]) / scale3
            pinch_mid_ratio_3d = _d3(p3[THUMB_TIP], p3[MIDDLE_TIP]) / scale3
        else:
            pinch_ratio_3d = pinch_ratio_2d
            pinch_mid_ratio_3d = pinch_mid_ratio_2d
        # Pinça do INDICADOR (clique esq): mínimo(2D,3D) — robusto de frente para a
        # câmara, onde o z-noise do MediaPipe inflaciona o rácio 3D acima do limiar.
        pinch_ratio = min(pinch_ratio_2d, pinch_ratio_3d)
        # Pinça do MÉDIO (clique dir): só 3D — a projeção 2D colapsa quando o polegar
        # se curva sobre a palma (durante o agarrar) e daria cliques-direitos fantasmas.
        pinch_mid_ratio = pinch_mid_ratio_3d

        # Dedos "dobrados" com deadband (Schmitt trigger): um dedo a pairar no
        # limiar de dobrar/esticar (razão tip/pip ~ 1.0) não faz o gesto tremer
        # de frame para frame (ex.: ONE<->OPEN, PEACE<->THREE, FIST<->THUMB_UP).
        # Só muda de estado depois de cruzar uma folga confortável, usando o
        # estado da frame anterior como memória. Casos claros comportam-se como
        # antes (dobrado<=esticado), pelo que os valores de fluxo normal se mantêm.
        fold_on_margin = 1.06   # para sair de "dobrado" tem de esticar bastante
        fold_off_margin = 0.94  # para sair de "esticado" tem de dobrar bastante
        curled = []
        for i, (tip, pip) in enumerate(FINGER_TIPS_PIPS):
            d_tip = _dist(pts[tip], wrist)
            d_pip = max(_dist(pts[pip], wrist), 1e-6)
            ratio = d_tip / d_pip
            if self._prev_curled[i]:
                now_curled = ratio < fold_on_margin
            else:
                now_curled = ratio < fold_off_margin
            curled.append(now_curled)
        self._prev_curled = curled

        if self._pinch_index_on:
            if pinch_ratio > cfg.pinch_off_ratio:
                self._pinch_index_on = False
        elif pinch_ratio < cfg.pinch_on_ratio:
            self._pinch_index_on = True

        if self._pinch_mid_on:
            if pinch_mid_ratio > cfg.pinch_off_ratio:
                self._pinch_mid_on = False
        elif pinch_mid_ratio < cfg.pinch_on_ratio:
            self._pinch_mid_on = True

        too_far = scale < cfg.min_hand_scale_px
        # Onda 1 §1.2. `nan` = nao medido, e nao medido nao e motivo para se
        # calar: o corpus v1 tem todas as confiancas a nan, e se `nan < min` fosse
        # lido como "baixa confianca" o gate silenciava-se a si proprio.
        class_conf = math.nan if conf is None else float(conf)
        low_conf = (
            not math.isnan(class_conf)
            and class_conf < getattr(cfg, "min_class_conf", 0.0)
        )
        all_curled = all(curled)

        def _clearly_curled(idx):
            tip, pip = FINGER_TIPS_PIPS[idx]
            return _dist(pts[tip], wrist) <= 0.92 * _dist(pts[pip], wrist)

        peace = (
            not curled[INDEX]
            and not curled[MIDDLE]
            and _clearly_curled(RING)
            and _clearly_curled(PINKY)
        )
        three = (
            not curled[INDEX]
            and not curled[MIDDLE]
            and not curled[RING]
            and _clearly_curled(PINKY)
        )
        # ROCK / "chifre": indicador + mindinho em pé, medio e anelar dobrados.
        rock = (
            not curled[INDEX]
            and not curled[PINKY]
            and _clearly_curled(MIDDLE)
            and _clearly_curled(RING)
        )
        one_finger = (
            not curled[INDEX]
            and curled[MIDDLE]
            and curled[RING]
            and curled[PINKY]
            and not self._pinch_index_on
        )
        pinky_only = (
            curled[INDEX]
            and curled[MIDDLE]
            and curled[RING]
            and not curled[PINKY]
        )
        # SHAKA: thumb extended (not curled toward wrist) + pinky extended.
        # The signal is how far the thumb tip sits from the index MCP
        # (landmark 5) relative to the hand scale: ~1.23 with the thumb out to
        # the side, ~0.85 tucked over the palm, so 1.05 splits the two cleanly.
        # Measuring the tip against its own IP (landmark 3) instead asked for
        # dx > 0.30 * scale, which is more than the distal phalanx itself
        # (~0.28 of scale) — geometrically impossible, so every SHAKA fell
        # through the priority chain to PINKY (Ctrl+C instead of Ctrl+V).
        thumb_out = False
        if all_curled or pinky_only:
            thumb_out = _dist(pts[THUMB_TIP], pts[5]) / scale > 1.05
        thumb_pinky = (
            thumb_out
            and not curled[PINKY]
            and curled[INDEX]
            and curled[MIDDLE]
            and curled[RING]
        )
        thumb_up = False
        if all_curled:
            # polegar apontando claramente para cima, acima de todos os MCPs
            tip_y = pts[THUMB_TIP][1]
            ip_y = pts[3][1]
            mcp_y = min(pts[i][1] for i in (5, 9, 13, 17))
            dy_up = ip_y - tip_y
            seg = _dist(pts[THUMB_TIP], pts[3])
            thumb_up = (
                tip_y < mcp_y - 0.15 * scale
                and seg > 1e-6
                and dy_up > 0.55 * seg
            )
        # "Deslike": punho fechado com o polegar apontando claramente para baixo
        # (espelho do THUMB_UP). Usado como gate para mostrar/ocultar a interface.
        thumb_down = False
        if all_curled:
            tip_y = pts[THUMB_TIP][1]
            ip_y = pts[3][1]
            mcp_y = max(pts[i][1] for i in (5, 9, 13, 17))
            dy_down = tip_y - ip_y
            seg = _dist(pts[THUMB_TIP], pts[3])
            thumb_down = (
                tip_y > mcp_y + 0.15 * scale
                and seg > 1e-6
                and dy_down > 0.55 * seg
            )

        if too_far or low_conf:
            geo = Gesture.NONE
        elif all_curled:
            if thumb_up:
                geo = Gesture.THUMB_UP
            elif thumb_down:
                geo = Gesture.THUMB_DOWN
            else:
                geo = Gesture.FIST
        elif self._pinch_mid_on:
            geo = Gesture.PINCH_MID
        elif self._pinch_index_on:
            geo = Gesture.PINCH
        elif three:
            geo = Gesture.THREE
        elif peace:
            geo = Gesture.PEACE
        elif rock:
            geo = Gesture.ROCK
        elif thumb_pinky:
            geo = Gesture.SHAKA
        elif pinky_only:
            geo = Gesture.PINKY
        elif one_finger:
            geo = Gesture.ONE
        else:
            geo = Gesture.OPEN

        raw = geo
        # Totalmente aberta: dedos bem esticados (racio tip/pip folgado), sem
        # estar em pinca. Tambem precisa de nao classificar como ONE/PEACE/etc.
        fully_open = (
            geo == Gesture.OPEN
            and not self._pinch_index_on
            and not self._pinch_mid_on
        )
        self.ai_conf = 0.0
        if self.ai is not None and not (too_far or low_conf) and self._ai_window:
            ml_g, ml_conf = self.ai.classify(list(self._ai_window))
            self.ai_conf = ml_conf
            if ml_g is not None and ml_conf >= cfg.ai_confidence_min:
                # a IA so pode confirmar o que a geometria tambem ve;
                # nunca inventa modos (THREE/PEACE/FIST) nem mata um clique ativo
                ml_ok = (
                    (ml_g == Gesture.OPEN and geo == Gesture.OPEN)
                    or (ml_g == Gesture.ONE and one_finger)
                    or (ml_g == Gesture.PINCH and self._pinch_index_on)
                    or (ml_g == Gesture.PINCH_MID and self._pinch_mid_on)
                    or (ml_g == Gesture.FIST and all_curled
                     and geo not in (Gesture.THUMB_UP, Gesture.THUMB_DOWN))
                    or (ml_g == Gesture.PEACE and peace)
                    or (ml_g == Gesture.THREE and three)
                    or (ml_g == Gesture.THUMB_UP and thumb_up)
                    or (ml_g == Gesture.PINKY and pinky_only)
                    or (ml_g == Gesture.SHAKA and thumb_pinky)
                    or (ml_g == Gesture.ROCK and geo == Gesture.ROCK)
                )
                geo_click = geo in (Gesture.PINCH, Gesture.PINCH_MID)
                if ml_ok and not (geo_click and ml_g == Gesture.OPEN):
                    raw = ml_g
                    if raw == Gesture.PINCH and pinch_ratio < cfg.pinch_off_ratio:
                        self._pinch_index_on = True
                    if raw == Gesture.PINCH_MID and pinch_mid_ratio < cfg.pinch_off_ratio:
                        self._pinch_mid_on = True

        if raw == self._candidate:
            self._candidate_count += 1
        else:
            self._candidate = raw
            self._candidate_count = 1

        # A pinca (clique) tem uma confirmacao propria e mais curta: o Schmitt
        # on/off ja suporta o ruido, pelo que acelerar aqui nao custa robustez.
        need_frames = (
            max(1, int(cfg.pinch_stable_frames))
            if raw in (Gesture.PINCH, Gesture.PINCH_MID)
            else cfg.gesture_stable_frames
        )
        deep_click = (
            raw == Gesture.PINCH and pinch_ratio < cfg.pinch_on_ratio * 0.75
        ) or (
            raw == Gesture.PINCH_MID and pinch_mid_ratio < cfg.pinch_on_ratio * 0.75
        )
        if deep_click:
            need_frames = 1

        fast_release = (
            self._committed in (Gesture.PINCH, Gesture.PINCH_MID, Gesture.FIST)
            and raw == Gesture.OPEN
        )
        if fast_release:
            need_frames = 1

        event = None
        value = None
        if (
            self._candidate_count >= need_frames
            and raw != self._committed
        ):
            previous = self._committed
            self._committed = raw
            event, value = self._transition(previous, raw)

        # Scroll: punho fechado (FIST) na mao de comandos; deslizar para cima/baixo
        # desloca o scroll na direcao oposta do movimento do punho.
        if self._committed == Gesture.FIST:
            mid_y = (pts[INDEX_TIP][1] + pts[MIDDLE_TIP][1]) / 2.0
            if self._scroll_prev_y is not None:
                dy = mid_y - self._scroll_prev_y
                self._scroll_acc_y += dy
                if abs(self._scroll_acc_y) >= cfg.scroll_deadzone_px:
                    event, value = "scroll", self._scroll_acc_y
                    self._scroll_acc_y = 0.0
            self._scroll_prev_y = mid_y
        else:
            self._scroll_prev_y = None
            self._scroll_acc_y = 0.0

        if self._committed == Gesture.THREE:
            vol_y = (pts[8][1] + pts[12][1] + pts[16][1]) / 3.0
            if self._vol_prev_y is not None:
                dy = vol_y - self._vol_prev_y
                # mesmo sinal do scroll: mover para baixo -> valor positivo
                self._vol_acc_y += dy
                if abs(self._vol_acc_y) >= cfg.volume_deadzone_px:
                    event, value = "volume", self._vol_acc_y
                    self._vol_acc_y = 0.0
            self._vol_prev_y = vol_y
        else:
            self._vol_prev_y = None
            self._vol_acc_y = 0.0

        palm_center = (
            sum(pts[i][0] for i in PALM_IDS) / len(PALM_IDS),
            sum(pts[i][1] for i in PALM_IDS) / len(PALM_IDS),
        )
        frame = HandFrame(
            points_px=pts,
            hand_scale_px=scale,
            pinch_ratio=pinch_ratio,
            pinch_mid_ratio=pinch_mid_ratio,
            raw_gesture=raw,
            gesture=self._committed,
            index_tip=pts[INDEX_TIP],
            palm_center=palm_center,
            ai_conf=self.ai_conf,
            fully_open=fully_open,
            class_conf=class_conf,
        )
        return frame, event, value

    @classmethod
    def _transition(cls, previous, current):
        if current == Gesture.PINCH_MID:
            return "right_click", None
        if current == Gesture.THUMB_UP:
            return "play_pause", None
        if current == Gesture.PINKY:
            return "copy", None
        if current == Gesture.SHAKA:
            return "paste", None
        was_left = previous in cls.LEFT_BUTTON_GESTURES
        is_left = current in cls.LEFT_BUTTON_GESTURES
        if is_left and not was_left:
            return "left_down", None
        if was_left and not is_left:
            return "left_up", None
        return None, None
