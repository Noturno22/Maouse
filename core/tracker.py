import os
import urllib.request

import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision

from config import resolve_asset, user_models_dir
from core.log import get_logger

log = get_logger("tracker")

HAND_CONNECTIONS = (
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
)


def ensure_model(path, url, timeout_s=15.0):
    bundled = resolve_asset(path)
    if bundled:
        return bundled
    # O caminho podem nao ser escrevivel (ex.: Program Files). Descarrega para
    # o directorio do utilizador e devolve o caminho real usado.
    dest = os.path.join(user_models_dir(), os.path.basename(path))
    if os.path.isfile(dest):
        return dest
    tmp = dest + ".part"
    print(f"A baixar modelo MediaPipe para {dest} ...")
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            with open(tmp, "wb") as fh:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    fh.write(chunk)
        os.replace(tmp, dest)
    except Exception:
        try:
            os.remove(tmp)
        except OSError as e:
            log.debug("N\u00e3o foi poss\u00edvel limpar ficheiro tempor\u00e1rio %s: %s", tmp, e)
        raise
    print("Modelo pronto.")
    return dest


class HandTracker:
    def __init__(self, model_path, num_hands=1, use_gpu=False, num_threads=-1):
        self._landmarker = None
        num_hands = max(1, min(int(num_hands), 2))
        if use_gpu:
            try:
                base = mp_tasks.BaseOptions(
                    model_asset_path=model_path,
                    delegate=mp_tasks.BaseOptions.Delegate.GPU,
                )
                self._landmarker = self._build(base, num_hands)
                print("Tracker: delegado GPU ativo.")
            except Exception as exc:
                print(f"Aviso: GPU indisponivel ({exc.__class__.__name__}); a usar CPU.")
        if self._landmarker is None:
            base = mp_tasks.BaseOptions(model_asset_path=model_path)
            self._landmarker = self._build(base, num_hands)

    @staticmethod
    def _build(base_options, num_hands):
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_hands=num_hands,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        return vision.HandLandmarker.create_from_options(options)

    def process(self, rgb_frame, timestamp_ms):
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        result = self._landmarker.detect_for_video(image, timestamp_ms)
        return parse_landmarks_result(result)

    def close(self):
        self._landmarker.close()


def parse_landmarks_result(result):
    """Traduz o resultado do MediaPipe em ``(hands, sides, confs)``.

    Funcao pura e separada do ``detect_for_video`` de proposito: e o unico sitio
    onde a traducao acontece, e assim da para a testar sem camara e sem
    MediaPipe a correr (tests/test_tracker_confidence.py).

    ``confs[i]`` e o ``handedness[i][0].score`` — a confianca da **classificacao**
    (esquerda ou direita), que e o unico score que a API Python do
    ``HandLandmarker`` expoe. **Nao** e a confianca de deteccao da mao: essa nao
    e exposta, so os limiares `min_*_confidence` de deteccao, que sao um
    limiar e nao uma medida. Quando nao ha valor, devolve ``NaN``, que significa
    "nao medido" e nao "mediu zero" — a distincao decide se um limiar de
    abstencao descarta tudo sem ninguem saber porque.
    """
    hands = []
    sides = []
    confs = []
    handedness = result.handedness or ()
    for i, lm_list in enumerate(result.hand_landmarks):
        # `handedness` pode ser None, ou mais curto que a lista de maos. O
        # `zip(..., strict=True)` que aqui estava antes levantava ValueError
        # nesse caso — um crash em vez de uma mao sem confianca. Itera-se pelas
        # maos e le-se o handedness por indice, que e o que sobrevive a isso.
        handed = handedness[i] if i < len(handedness) else ()
        hands.append([(lm.x, lm.y, lm.z) for lm in lm_list])
        label = "Right"
        if handed:
            label = handed[0].category_name if handed[0].category_name in (
                "Left",
                "Right",
            ) else "Right"
        sides.append(label)
        score = getattr(handed[0], "score", None) if handed else None
        try:
            confs.append(float(score))
        except (TypeError, ValueError):
            confs.append(float("nan"))
    return hands, sides, confs
