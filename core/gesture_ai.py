import os
import shutil
import urllib.request

import numpy as np

from config import resolve_asset, user_models_dir
from core.gestures import Gesture

CLASSES = (
    Gesture.OPEN,
    Gesture.PINCH,
    Gesture.PINCH_MID,
    Gesture.FIST,
    Gesture.PEACE,
    Gesture.THREE,
    Gesture.THUMB_UP,
    Gesture.ROCK,
    Gesture.SHAKA,
)
FEATURES = 120
N_CLASSES = len(CLASSES)

MODEL_URLS = (
    "https://github.com/airmouse-ai/models/releases/download/v1/gesture_mlp.npz",
)


def _normalize(points):
    pts = np.asarray(points, dtype=np.float64)
    # Fallback 2D legado: se a entrada não tem z, assume z = 0 (compatível).
    if pts.shape[1] == 2:
        pts = np.column_stack([pts, np.zeros(len(pts))])
    wrist = pts[0]
    v = pts[9] - wrist
    scale = np.hypot(v[0], v[1])
    if scale < 1e-6:
        return None
    theta = -np.arctan2(v[1], v[0])
    cos, sin = np.cos(theta), np.sin(theta)
    rel_xy = pts[1:, :2] - wrist[:2]
    x = rel_xy[:, 0] * cos - rel_xy[:, 1] * sin
    y = rel_xy[:, 0] * sin + rel_xy[:, 1] * cos
    # z relativo ao pulso, SEM dividir pela escala 2D em px: ao contrário de
    # x,y (que estão em px após lm*width/height), o z do MediaPipe já é
    # unidade interna da mão (scale-free, ~0.3-0.5, invariante à distância).
    # Dividir por scale (px) esmagaria o sinal 3D (z -> ~0.003, morto).
    z_rel = pts[1:, 2] - wrist[2]
    return np.concatenate([x / scale, y / scale, z_rel])


def _is_frame_list(p):
    try:
        first = p[0]
    except (IndexError, TypeError, KeyError):
        return False
    arr = np.asarray(first)
    return arr.ndim == 2


def _aggregate(frames):
    feats = []
    for f in frames:
        feat = _normalize(f)
        if feat is not None:
            feats.append(feat)
    if not feats:
        return None
    cur = feats[-1]
    mean = np.mean(np.stack(feats), axis=0)
    return np.concatenate([cur, mean])


class GestureAI:
    def __init__(self, path):
        if not os.path.isfile(path):
            raise FileNotFoundError(path)
        data = np.load(path)
        self.w1, self.b1 = data["w1"], data["b1"]
        self.w2, self.b2 = data["w2"], data["b2"]
        self.w3, self.b3 = data["w3"], data["b3"]
        if self.b3.shape[0] != N_CLASSES:
            raise FileNotFoundError(
                f"modelo obsoleto em {path} ({self.b3.shape[0]} classes; "
                f"esperado {N_CLASSES}). Retreina: tools\\train_gesture_ai.py"
            )
        if self.w1.shape[0] != FEATURES:
            raise FileNotFoundError(
                f"modelo obsoleto em {path} ({self.w1.shape[0]} features; "
                f"esperado {FEATURES} temporal). Retreina: tools\\train_gesture_ai.py"
            )

    def classify(self, points_px):
        frames = list(points_px) if _is_frame_list(points_px) else [points_px]
        feat = _aggregate(frames)
        if feat is None:
            return None, 0.0
        h1 = np.tanh(feat @ self.w1 + self.b1)
        h2 = np.tanh(h1 @ self.w2 + self.b2)
        logits = h2 @ self.w3 + self.b3
        e = np.exp(logits - logits.max())
        prob = e / e.sum()
        idx = int(prob.argmax())
        return CLASSES[idx], float(prob[idx])


def ensure_ai_model(path, url=None):
    bundled = resolve_asset(path)
    if bundled:
        return bundled
    # O caminho podem nao ser escrevivel (ex.: Program Files). Usa o
    # directorio do utilizador como destino e devolve o caminho real.
    dest = os.path.join(user_models_dir(), "gesture_mlp.npz")
    if os.path.isfile(dest):
        return dest
    source = None
    local = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gesture_mlp.npz")
    if os.path.isfile(local):
        source = local
    if source is None:
        bundled_in_repo = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "models", "gesture_mlp.npz",
        )
        if os.path.isfile(bundled_in_repo):
            source = bundled_in_repo
    if source is not None:
        try:
            shutil.copyfile(source, dest)
            print(f"Modelo IA copiado de {source}")
            return dest
        except OSError:
            pass
    urls = (url,) if url else MODEL_URLS
    for u in urls:
        try:
            print(f"A baixar modelo de gestos IA para {dest} ...")
            tmp = dest + ".part"
            urllib.request.urlretrieve(u, tmp)
            os.replace(tmp, dest)
            print("Modelo IA pronto.")
            return dest
        except Exception:
            continue
    raise FileNotFoundError(
        "Modelo gesture_mlp.npz nao encontrado. Corre: "
        ".venv\\Scripts\\python.exe tools\\train_gesture_ai.py"
    )
