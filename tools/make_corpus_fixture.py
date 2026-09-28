"""Gera o corpus de REGRESSAO do reconhecimento (fixture versionada em git).

Porque um corpus sintetico e mesmo assim a unica opcao honesta
------------------------------------------------------------
O corpus que a Onda 0 pede (200-500 clips gravados) contem maos de pessoas
reais: nao pode ser versionado (e nao deve) e nao existe no CI. O que se
versiona e, portanto, um corpus **parametrico**: cadeias cinemáticas de dedos
colocadas dentro de um frame e reproduzidas pelo mesmo ``GestureEngine`` /
``HandPool`` do runtime.

| | |
|---|---|
| **Mede** | se uma refactorizacao do pipeline geometrico muda o que ele decide (golden master) |
| **Nao mede** | qualidade em maos reais: pele, iluminacao, oclusao, distancia, tom de pele |

Este corpus e uma trava de regressao, nao um certificado de qualidade. O
certificado so existe quando houver clips gravados no hardware - e so esse
numero pode aparecer em marketing (``HARDWARE/PROBLEMAS_KNOWN.md`` e a norma do
projecto). Confundir os dois seria exactamente o erro que a Onda 0 existe para
impedir.

Porque a ordem das sequencias nao e aleatoria
----------------------------------------------
O custo de um limiar mal calibrado aparece na **transicao**, nao no estado
estavel. Por isso os segmentos sao agrupados em "runs" sem repouso no meio: e
a passagem FIST->THUMB_UP, PEACE->THREE e PINKY->SHAKA que tem de sobreviver a
histerese, e nao a pose parada. Entre runs ha frames **sem mao nenhuma**, que sao
a evidencia de que o pipeline nao inventa gestos (e onde vivem os cliques
fantasma).

Cinemática
----------
Os comprimentos de falange, os angulos maximos e a cadeia de juntas vem de
``tools/train_gesture_ai.py`` — sao constantes anatomicas do modelo, nao
decisoes de dataset. As *poses* sao definidas aqui de proposito: se o treino
mudar, a fixture tem de ficar parada, senao o golden master mudaria sozinho.

Uso
---
    python tools/make_corpus_fixture.py                 # escreve .npz + baseline
    python tools/make_corpus_fixture.py --check         # só verifica, não escreve
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.corpus import ACTIVE_NONE, SETTLE_LABEL, Corpus  # noqa: E402
from tools.eval_recognition import evaluate  # noqa: E402
from tools.train_gesture_ai import (  # noqa: E402
    FINGER_CHAINS,
    FINGER_LEN,
    MAX_ANGLES,
    OPEN_SKELETON,
    THUMB_MAX,
    _chain,
)

# --------------------------------------------------------------- parametros

SEED = 20260928
WIDTH, HEIGHT = 640, 480
# dist(wrist, landmark 9) em pixels. min_hand_scale_px = 55, portanto 120 px da
# uma folga comfortable sem a mao sair do frame (a mao ocupa ~240 px de altura
# a 480 px de video).
SCALE_PX = 120.0
FRAME_MS = 33          # ~30 fps
SEGMENT_FRAMES = 6     # 6 frames = 2 de debounce + 4 de estado
REST_FRAMES = 5        # sem mao nenhuma
NOISE_FRAC = 0.008     # sigma do jitter, em fracao de SCALE_PX
# Fraccao da escala a que a ponta do dedo fecha sobre a ponta do polegar.
# 0.30 fica bem dentro do ligacao (pinch_on_ratio = 0.42): uma pinca firme,
# nao uma pinca a vibrar em cima do limiar.
PINCH_CLOSE_FRAC = 0.30

# Gestos cujo debounce e o da pinca (1 frame) em vez do geral (2 frames). O
# numero de frames marcados como SETTLE sai da Config, nao de um literal: se o
# debounce mudar, a fixture tem de mudar com ele.
PINCH_LIKE = frozenset({"PINCH", "PINCH_MID"})

OPEN_CURL = (0.05, 0.04, 0.03)
FOLDED_CURL = (0.94, 0.96, 0.95)

# (indicador, medio, anelar, mindinho). 0 = esticado, 1 = dobrado.
FINGER_CURLS = {
    "OPEN": (0.05, 0.04, 0.03, 0.04),
    "ONE": (0.05, 0.94, 0.93, 0.94),
    "FIST": (0.94, 0.96, 0.95, 0.96),
    "PEACE": (0.05, 0.05, 0.93, 0.95),
    "THREE": (0.05, 0.05, 0.06, 0.93),
    "ROCK": (0.05, 0.93, 0.94, 0.05),
    "PINKY": (0.93, 0.94, 0.94, 0.05),
    "SHAKA": (0.93, 0.94, 0.94, 0.05),
    "PINCH": (0.55, 0.18, 0.34, 0.38),
    "PINCH_MID": (0.17, 0.55, 0.36, 0.40),
    "THUMB_UP": (0.94, 0.96, 0.95, 0.95),
    "THUMB_DOWN": (0.94, 0.96, 0.95, 0.95),
}

# Polegar: "tucked" = recolhido sobre a palma; "out" = aberto para o lado
# (o unico sinal que separa PINKY de SHAKA, ver nota abaixo); "up"/"down" =
# a apontar, com a base deslocada para o punho fechado.
THUMB_PLACEMENT = {
    "OPEN": ("relaxed", 0.0),
    "ONE": ("tucked", 0.0),
    "FIST": ("tucked", 0.0),
    "PEACE": ("tucked", 0.0),
    "THREE": ("relaxed", 0.0),
    "ROCK": ("tucked", 0.0),
    "PINKY": ("tucked", 0.0),
    "SHAKA": ("out", 0.0),
    "PINCH": ("pinch", 0.0),
    "PINCH_MID": ("pinch", 0.0),
    "THUMB_UP": ("up", 0.0),
    "THUMB_DOWN": ("down", 0.0),
}

# Runs de segmentos. Sem repouso entre segmentos de um run: a histerese tem de
# aguentar a transicao. Entre runs ha repouso.
RUNS = (
    # OPEN<->ONE e o par para que a histerese (1.06/0.94) foi criada.
    ("OPEN", "ONE", "OPEN", "ONE"),
    # FIST<->THUMB_UP/DOWN: so o polegar decide, e decide por direccao.
    ("FIST", "THUMB_UP", "FIST", "THUMB_DOWN", "FIST", "THUMB_UP"),
    # PEACE<->THREE: o anelar a meio caminho. ROCK<->PEACE: o mindelho.
    ("PEACE", "THREE", "PEACE", "ROCK", "PEACE", "ROCK"),
    # PINKY<->SHAKA: a mesma pose, so o polegar em "out" ou "tucked".
    ("PINKY", "SHAKA", "PINKY", "SHAKA", "PINKY"),
    # Ida e volta do clique, incluindo right-click: e aqui que vive o clique
    # fantasma, porque e a unica transicao que dispara `left_down`.
    ("PINCH", "OPEN", "PINCH", "PINCH_MID", "OPEN", "PINCH", "OPEN"),
)


# ------------------------------------------------------------------ poses


def _deg(value: float) -> float:
    return np.deg2rad(value)


def _skeleton(gesture: str, rng) -> np.ndarray:
    """Esqueleto (21, 3) da pose de `gesture`, no referencial do modelo.

    As coordenadas sao as do modelo cinematico (pulso na origem, unidade ~1.1
    entre o pulso e a base do medio). `_place` converte para o frame.
    """
    curls = FINGER_CURLS[gesture]
    skel: list = [None] * 21
    skel[0] = np.array([OPEN_SKELETON[0][0], OPEN_SKELETON[0][1], 0.0])
    skel[1] = np.array(
        [OPEN_SKELETON[1][0] + rng.uniform(-0.03, 0.03),
         OPEN_SKELETON[1][1] + rng.uniform(-0.03, 0.03), 0.0]
    )
    skel[2], skel[3], skel[4] = _thumb(gesture, rng)

    for name, base_id, curl in zip(
        ("index", "middle", "ring", "pinky"), (5, 9, 13, 17), curls, strict=True
    ):
        ids, ang0 = FINGER_CHAINS[name]
        lengths = tuple(L * (1.0 + rng.uniform(-0.08, 0.08)) for L in FINGER_LEN[name])
        c = tuple(min(max(curl + rng.uniform(-0.12, 0.12), 0.0), 1.0) for _ in range(3))
        base = np.array(
            [OPEN_SKELETON[base_id][0] + rng.uniform(-0.04, 0.04),
             OPEN_SKELETON[base_id][1] + rng.uniform(-0.04, 0.04), 0.0]
        )
        pts = _chain(base, ang0 + rng.uniform(-0.09, 0.09), lengths, c, MAX_ANGLES)
        for k, i in enumerate(ids):
            skel[i] = pts[k]

    out = np.stack([np.asarray(p, dtype=np.float64) for p in skel])
    if out.shape != (21, 3):
        raise AssertionError(f"pose {gesture} -> {out.shape}, esperado (21, 3)")
    return out


def _thumb(gesture: str, rng) -> tuple:
    """Polegar segundo o papel: recolhido, aberto, a apontar, ou em pinça."""
    placement, _ = THUMB_PLACEMENT[gesture]
    jit = lambda a: rng.uniform(-a, a)  # noqa: E731

    if placement == "tucked":
        # Sobre a palma. Coordenadas fixas (como no treino): uma cadeia com
        # curls altos acabaria com a ponta colada ao pulso e a falsear o
        # calculo de pinca.
        bx, by = OPEN_SKELETON[1][0], OPEN_SKELETON[1][1]
        return (
            np.array([bx + jit(0.03), by + jit(0.03), -0.30]),
            np.array([bx - 0.13 + jit(0.04), by - 0.24 + jit(0.04), -0.34]),
            np.array([bx - 0.04 + jit(0.04), by - 0.44 + jit(0.04), -0.38]),
        )

    if placement == "out":
        # Polegar aberto para o lado, como quem mostra o mindinho com o polegar
        # esticado. NOTA: o predicado SHAKA mede o deslocamento da ponta em
        # relacao a IP e compara-o com 0.30/0.25 da escala, mas a falange distal
        # do modelo so mede 0.28 da escala - o limiar esta no limite fisico do
        # gesto. Ver tests/test_corpus_fixture.py::test_pinky_and_shaka_are_one_pose
        base = np.array([OPEN_SKELETON[1][0], OPEN_SKELETON[1][1], 0.0])
        pts = _chain(base, _deg(-160.0) + jit(0.05), FINGER_LEN["thumb"],
                     (0.35 + jit(0.06), 0.45 + jit(0.06), 0.40 + jit(0.06)), THUMB_MAX)
        return pts[1], pts[2], pts[3]

    if placement in ("up", "down"):
        # Punho fechado com o polegar a apontar claramente para cima/baixo,
        # acima/abaixo de todos os MCPs (predicado exige 0.15*scale).
        sign = -1.0 if placement == "up" else 1.0
        base = np.array([OPEN_SKELETON[1][0] - 0.26 * (1.0 if placement == "up" else 0.0),
                         OPEN_SKELETON[1][1] - 0.29 * (1.0 if placement == "up" else 0.0), 0.0])
        up_curls = (max(0.01 + jit(0.03), 0.0), max(0.01 + jit(0.03), 0.0),
                    max(0.005 + jit(0.02), 0.0))
        pts = _chain(base, _deg(90.0 * sign), FINGER_LEN["thumb"], up_curls, THUMB_MAX)
        return pts[1], pts[2], pts[3]

    # "relaxed" e "pinch" partem da posicao de mao meio aberta.
    t_curls = (0.30 + jit(0.10), 0.28 + jit(0.10), 0.25 + jit(0.10))
    pts = _chain(
        np.array([OPEN_SKELETON[1][0], OPEN_SKELETON[1][1], 0.0]),
        _deg(-118.0) + jit(0.05), FINGER_LEN["thumb"], t_curls, THUMB_MAX,
    )
    return pts[1], pts[2], pts[3]


def _close_pinch(skel: list, tip_id: int, dip_id: int) -> None:
    """Aproxima a ponta (e a DIP) do dedo ate `PINCH_CLOSE_FRAC` da ponta do
    polegar, ao longo da direccao ja existente.

    Fazer isto explicitamente, em vez de depender dos angulos da cadeia, e o
    que garante que a fixture mede o *predicado* e nao a pontaria da pose.
    """
    wrist, m9 = skel[0], skel[9]
    scale = float(np.hypot(m9[0] - wrist[0], m9[1] - wrist[1]))
    thumb_tip = skel[4]
    delta = skel[tip_id] - thumb_tip
    norm = float(np.sqrt(float(np.dot(delta, delta))))
    if norm < 1e-6:
        return
    target = thumb_tip + delta / norm * (PINCH_CLOSE_FRAC * scale)
    move = target - skel[tip_id]
    skel[tip_id] = target
    # A DIP segue 40% do deslocamento da ponta, para a falange nao inverter.
    skel[dip_id] = skel[dip_id] + move * 0.4


# ------------------------------------------------------------------ frame


def _place(pts: np.ndarray, rng, width: int = WIDTH, height: int = HEIGHT,
           scale_px: float = SCALE_PX) -> np.ndarray:
    """Projecta o esqueleto do modelo para coordenadas normalizadas 0..1.

    MediaPipe devolve x normalizado pela largura, y pela altura e z com a
    escala do x (aproximadamente a largura). O `GestureEngine` reconstrói
    `pts = (x*width, y*height)` e calcula `scale = dist(wrist, lm9)` em pixels,
    por isso a conversao tem de respeitar as duas normalizações.
    """
    wrist = pts[0]
    unit = scale_px / max(float(np.hypot(pts[9][0] - wrist[0], pts[9][1] - wrist[1])), 1e-6)
    cx = 0.5 + rng.uniform(-0.05, 0.05)
    cy = 0.55 + rng.uniform(-0.04, 0.04)

    out = np.empty((21, 3), dtype=np.float32)
    out[:, 0] = cx + (pts[:, 0] - wrist[0]) * unit / width
    out[:, 1] = cy + (pts[:, 1] - wrist[1]) * unit / height
    out[:, 2] = pts[:, 2] * unit / width

    sigma = NOISE_FRAC * scale_px
    out[:, 0] += rng.normal(0.0, sigma / width, 21)
    out[:, 1] += rng.normal(0.0, sigma / height, 21)
    out[:, 2] += rng.normal(0.0, sigma * 0.3 / width, 21)
    return out


# ------------------------------------------------------------------ corpus


def make_corpus(seed: int = SEED, cfg=None) -> Corpus:
    """Corpus determinista: uma mao (lado `Right`), runs de segmentos e repouso.

    Os primeiros frames de cada segmento sao marcados ``SETTLE`` — o numero vem
    do debounce configurado (`pinch_stable_frames` / `gesture_stable_frames`),
    porque e esse debounce, e nao o classificador, que atrasa a decisao.
    """
    if cfg is None:
        from config import Config

        cfg = Config()
    rng = np.random.default_rng(seed)
    corpus = Corpus()
    t = 0

    def add(hand, label):
        nonlocal t
        if hand is None:
            corpus.add_frame(t, [], [], [], ACTIVE_NONE)
        else:
            corpus.add_frame(t, [hand], ["Right"], [label], 0)
        t += FRAME_MS

    for run in RUNS:
        for label in run:
            settling = (
                cfg.pinch_stable_frames if label in PINCH_LIKE
                else cfg.gesture_stable_frames
            )
            for frame in range(SEGMENT_FRAMES):
                skel = _skeleton(label, rng)
                if label == "PINCH":
                    _close_pinch(skel, 8, 7)
                elif label == "PINCH_MID":
                    _close_pinch(skel, 12, 11)
                add(_place(skel, rng),
                    SETTLE_LABEL if frame < settling else label)
        for _ in range(REST_FRAMES):
            add(None, "NONE")

    return corpus


# ------------------------------------------------------------------- saida

DEFAULT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "fixtures"
)
CORPUS_NAME = "corpus_regressao_v1.npz"
BASELINE_NAME = "corpus_regressao_v1.baseline.json"


def corpus_path(out_dir=None) -> str:
    return os.path.join(out_dir or DEFAULT_DIR, CORPUS_NAME)


def baseline_path(out_dir=None) -> str:
    return os.path.join(out_dir or DEFAULT_DIR, BASELINE_NAME)


def _portable_path(path: str) -> str:
    """Caminho relativo a raiz do repositorio, com barras normais.

    O baseline e um ficheiro versionado: gravar la um caminho absoluto
    (`C:\\Users\\<pessoa>\\...`) torna o diff ilegivel em qualquer outra
    maquina e diverge em cada checkout. O replay e determinista, portanto o
    caminho nao entra em nenhuma comparacao — so precisa de ser legivel.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.relpath(os.path.abspath(path), root).replace(os.sep, "/")


def write_fixture(out_dir=None, seed: int = SEED) -> str:
    """Escreve o `.npz` e o baseline das metricas. Devolve o caminho do corpus."""
    directory = out_dir or DEFAULT_DIR
    os.makedirs(directory, exist_ok=True)
    path = corpus_path(directory)
    corpus = make_corpus(seed)
    if not corpus.save(path):
        raise RuntimeError("corpus vazio: nada gravado")
    report = evaluate(path, width=WIDTH, height=HEIGHT)
    data = report.to_dict()
    data["corpus"]["path"] = _portable_path(path)
    with open(baseline_path(directory), "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return path


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Gera o corpus de regressao do reconhecimento (fixture de CI)."
    )
    p.add_argument("--out", default=None, help="directorio destino")
    p.add_argument("--seed", type=int, default=SEED)
    p.add_argument(
        "--force", action="store_true",
        help="reescreve o corpus e o baseline (re-baseline deliberado)",
    )
    args = p.parse_args(argv)

    directory = args.out or DEFAULT_DIR
    path = corpus_path(directory)
    if os.path.isfile(path) and not args.force:
        report = evaluate(path, width=WIDTH, height=HEIGHT)
        print(f"Corpus existente: {path}")
        print(report.render())
        print()
        print("Para re-baselinear de proposito: --force")
        return 0

    path = write_fixture(directory, args.seed)
    report = evaluate(path, width=WIDTH, height=HEIGHT)
    print(f"Escrito: {path}")
    print(f"Baseline: {baseline_path(directory)}")
    print(report.render())
    return 0


if __name__ == "__main__":
    sys.exit(main())
