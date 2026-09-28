"""Corpus de landmarks para avaliacao offline do reconhecimento (Onda 0).

Porque landmarks e nao video
---------------------------
Gravar video e reproduzi-lo mediria a variancia do MediaPipe, nao a do nosso
classificador. O que nos interessa e: *dadas* as landmarks que o tracker
produziu, o pipeline geometrico escolhe o gesto certo? Por isso o corpus
guarda as landmarks ja trackeadas (normalizadas 0..1) e a etiqueta humana
correspondente, e a replay corre exactamente o mesmo
``GestureEngine``/``HandPool`` do runtime, sem camera e sem rato.

Formato (``.npz``)
    landmarks : (F, 2, 21, 3) float32  - posicoes normalizadas 0..1
    mask      : (F, 2)      bool        - True = esta mao existe neste frame
    labels    : (F, 2)      int8        - indice em LABEL_NAMES; -1 = sem mao
                                           -2 = SETTLE (frame em transicao)
    sides     : (F, 2)      int8        - SIDE_LEFT / SIDE_RIGHT
    active    : (F,)        int8        - indice da mao do cursor; -1 = nenhuma
    t_ms      : (F,)        int64       - timestamp do frame
    version   : ()          int64       - FORMAT_VERSION

Frames sem mao nenhuma sao gravados de proposito (``mask`` todo False): sao os
que revelam alucinacao, ie. o pipeline a inventar gestos quando nao ha mao.
"""
from __future__ import annotations

import os
from typing import NamedTuple

import numpy as np

from core.gestures import Gesture

# Indice de "nenhuma mao" numa das duas ranhuras.
ACTIVE_NONE = -1
MAX_HANDS = 2
N_LANDMARKS = 21

FORMAT_VERSION = 1

SIDE_LEFT = 0
SIDE_RIGHT = 1
_SIDE_BY_NAME = {"Left": SIDE_LEFT, "Right": SIDE_RIGHT}
_SIDE_NAMES = ("Left", "Right")

# NONE primeiro: e o estado "sem mao" e tambem o estado inicial do engine.
LABEL_NAMES = tuple(g.name for g in Gesture)
_LABEL_INDEX = {name: i for i, name in enumerate(LABEL_NAMES)}
N_LABELS = len(LABEL_NAMES)

# "sem mao" nao e um gesto: as metricas tem de o excluir, senao os frames em
# que nao havia mao nenhuma diluem o F1 com um classe trivial.
ABSENT_LABEL = LABEL_NAMES[0]

# "a mudar de gesto": o ground truth ja diz qual e o gesto destino, mas o
# debounce do engine (2 frames, 1 na pinca) ainda nao fechou. Nao e uma classe
# de gesto e nao entra no F1 - ver tools/eval_recognition.py::score_predictions.
# Sem isto, TODO inicio de segmento contaria como erro e o F1 mediria a
# estrutura do corpus em vez da qualidade do classificador.
SETTLE_INDEX = -2
SETTLE_LABEL = "SETTLE"

_EMPTY_LANDMARKS = np.zeros((MAX_HANDS, N_LANDMARKS, 3), dtype=np.float32)


class CorpusArrays(NamedTuple):
    """Vistas em memoria do corpus. Campos nomeados de proposito: a ordem
    posicional de seis arrays e uma fabrica de bugs silenciosos."""

    landmarks: np.ndarray  # (F, 2, 21, 3)
    mask: np.ndarray       # (F, 2) bool
    labels: np.ndarray     # (F, 2) int8, -1 = slot vazio
    sides: np.ndarray      # (F, 2) int8
    active: np.ndarray     # (F,) int8
    t_ms: np.ndarray       # (F,) int64


def label_index(name) -> int:
    """Indice de um nome de gesto (ou de um ``Gesture``) em ``LABEL_NAMES``.

    ``SETTLE_LABEL`` devolve ``SETTLE_INDEX`` (negativo): nao e um gesto, e um
    marcador de frame em transicao.
    """
    if isinstance(name, Gesture):
        return _LABEL_INDEX[name.name]
    if name == SETTLE_LABEL:
        return SETTLE_INDEX
    if isinstance(name, str) and name in _LABEL_INDEX:
        return _LABEL_INDEX[name]
    raise KeyError(f"gesto desconhecido: {name!r}")


def label_name(index: int) -> str:
    """Nome do label de indice `index`, incluindo os sentinelas negativos.

    Indexar ``LABEL_NAMES`` a ceu aberto com -1 ou -2 devolveria o penultimo
    elemento: um erro silencioso que transformaria "sem mao" num gesto.
    """
    if index == SETTLE_INDEX:
        return SETTLE_LABEL
    if not 0 <= index < len(LABEL_NAMES):
        raise ValueError(f"indice de label fora de intervalo: {index}")
    return LABEL_NAMES[index]


def side_name(index: int) -> str:
    return _SIDE_NAMES[index]


def side_index(name) -> int:
    try:
        return _SIDE_BY_NAME[name]
    except (KeyError, TypeError):
        raise ValueError(f"lado desconhecido: {name!r} (use 'Left' ou 'Right')") from None


class Corpus:
    """Sequencia de frames gravados, com ground truth por mao."""

    def __init__(self) -> None:
        self._landmarks: list[np.ndarray] = []
        self._mask: list[list[bool]] = []
        self._labels: list[list[int]] = []
        self._sides: list[list[int]] = []
        self._active: list[int] = []
        self._t_ms: list[int] = []

    # ------------------------------------------------------------------ estado

    @property
    def frames(self) -> int:
        return len(self._t_ms)

    @property
    def total(self) -> int:
        """Total de mao-frames (a unidade de avaliacao do classificador)."""
        return int(sum(m for pair in self._mask for m in pair))

    @property
    def two_hand_frames(self) -> int:
        return sum(1 for pair in self._mask if all(pair))

    def __len__(self) -> int:
        return self.frames

    def clear(self) -> None:
        self._landmarks.clear()
        self._mask.clear()
        self._labels.clear()
        self._sides.clear()
        self._active.clear()
        self._t_ms.clear()

    # ------------------------------------------------------------------ escrita

    def add_frame(
        self,
        t_ms: int,
        hands,
        sides,
        labels,
        active: int = ACTIVE_NONE,
    ) -> None:
        """Acrescenta um frame.

        ``hands`` sao listas de 21 landmarks normalizadas ``(x, y, z)``; ``sides``
        e ``labels`` devem ter o mesmo comprimento. ``active`` e o indice da
        mao do cursor (a que genera comandos), ou ``ACTIVE_NONE``.

        ``labels`` aceita um ``Gesture``, um nome de ``LABEL_NAMES``, ou
        ``SETTLE_LABEL`` para um frame em que o gesto destino ja comecou mas o
        debounce ainda nao fechou.
        """
        hands = list(hands)
        sides = list(sides)
        labels = list(labels)
        n = len(hands)
        if n > MAX_HANDS:
            raise ValueError(f"maximo {MAX_HANDS} maos por frame (recebi {n})")
        if len(sides) != n or len(labels) != n:
            raise ValueError(
                f"hands/sides/labels com comprimentos diferentes: "
                f"{n}/{len(sides)}/{len(labels)}"
            )
        if not -1 <= active < MAX_HANDS:
            raise ValueError(f"active fora de intervalo: {active}")
        if n == 0 and active != ACTIVE_NONE:
            raise ValueError("active so faz sentido com pelo menos uma mao")

        lm = _EMPTY_LANDMARKS.copy()
        mask = [False] * MAX_HANDS
        lb = [-1] * MAX_HANDS
        sd = [SIDE_LEFT] * MAX_HANDS
        for i in range(n):
            pts = np.asarray(hands[i], dtype=np.float32)
            if pts.shape != (N_LANDMARKS, 3):
                raise ValueError(
                    f"mao {i} com {pts.shape} pontos; esperado ({N_LANDMARKS}, 3)"
                )
            if not np.all(np.isfinite(pts)):
                raise ValueError(f"mao {i} tem coordenadas nao finitas")
            lm[i] = pts
            mask[i] = True
            lb[i] = label_index(labels[i])
            sd[i] = side_index(sides[i])

        self._landmarks.append(lm)
        self._mask.append(mask)
        self._labels.append(lb)
        self._sides.append(sd)
        self._active.append(int(active))
        self._t_ms.append(int(t_ms))

    # ------------------------------------------------------------------ leitura

    def arrays(self) -> CorpusArrays:
        f = self.frames
        if f == 0:
            return CorpusArrays(
                landmarks=np.zeros((0, MAX_HANDS, N_LANDMARKS, 3), dtype=np.float32),
                mask=np.zeros((0, MAX_HANDS), dtype=bool),
                labels=np.full((0, MAX_HANDS), -1, dtype=np.int8),
                sides=np.zeros((0, MAX_HANDS), dtype=np.int8),
                active=np.zeros(0, dtype=np.int8),
                t_ms=np.zeros(0, dtype=np.int64),
            )
        return CorpusArrays(
            landmarks=np.stack(self._landmarks),
            mask=np.array(self._mask, dtype=bool),
            labels=np.array(self._labels, dtype=np.int8),
            sides=np.array(self._sides, dtype=np.int8),
            active=np.array(self._active, dtype=np.int8),
            t_ms=np.array(self._t_ms, dtype=np.int64),
        )

    def replay(self):
        """Itera os frames por ordem cronologica, no mesmo formato que
        ``HandTracker.process`` devolve, para encaixar directo no ``HandPool``."""
        order = sorted(range(self.frames), key=lambda i: self._t_ms[i])
        for i in order:
            hands, sides, labels = [], [], []
            for h in range(MAX_HANDS):
                if not self._mask[i][h]:
                    continue
                hands.append(self._landmarks[i][h])
                sides.append(_SIDE_NAMES[self._sides[i][h]])
                labels.append(label_name(self._labels[i][h]))
            yield (self._t_ms[i], hands, sides, labels, self._active[i])

    def label_counts(self) -> dict:
        counts = {name: 0 for name in LABEL_NAMES}
        counts[SETTLE_LABEL] = 0
        for pair_lb, pair_mask in zip(self._labels, self._mask, strict=True):
            for h in range(MAX_HANDS):
                if pair_mask[h]:
                    counts[label_name(pair_lb[h])] += 1
        return counts

    def duration_s(self) -> float:
        if self.frames < 2:
            return 0.0
        return (max(self._t_ms) - min(self._t_ms)) / 1000.0

    # -------------------------------------------------------------- persistencia

    def save(self, path) -> bool:
        path = os.fspath(path)
        if self.frames == 0:
            return False
        a = self.arrays()
        parent = os.path.dirname(os.path.abspath(path))
        os.makedirs(parent, exist_ok=True)
        np.savez_compressed(
            path,
            landmarks=a.landmarks,
            mask=a.mask,
            labels=a.labels,
            sides=a.sides,
            active=a.active,
            t_ms=a.t_ms,
            version=np.array(FORMAT_VERSION, dtype=np.int64),
        )
        return True

    @classmethod
    def load(cls, path) -> Corpus:
        path = os.fspath(path)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"corpus inexistente: {path}")
        with np.load(path, allow_pickle=False) as z:
            if "version" not in z.files:
                raise ValueError(f"corpus sem versao (formato antigo): {path}")
            version = int(z["version"])
            if version != FORMAT_VERSION:
                raise ValueError(
                    f"versao de corpus {version} incompativel com {FORMAT_VERSION}: "
                    f"{path}"
                )
            a = CorpusArrays(
                landmarks=np.asarray(z["landmarks"], dtype=np.float32),
                mask=np.asarray(z["mask"], dtype=bool),
                labels=np.asarray(z["labels"], dtype=np.int8),
                sides=np.asarray(z["sides"], dtype=np.int8),
                active=np.asarray(z["active"], dtype=np.int8),
                t_ms=np.asarray(z["t_ms"], dtype=np.int64),
            )
        c = cls()
        for i in range(a.landmarks.shape[0]):
            hands = [a.landmarks[i][h] for h in range(MAX_HANDS) if a.mask[i][h]]
            sides = [_SIDE_NAMES[int(a.sides[i][h])]
                     for h in range(MAX_HANDS) if a.mask[i][h]]
            labels = [label_name(int(a.labels[i][h]))
                      for h in range(MAX_HANDS) if a.mask[i][h]]
            c.add_frame(int(a.t_ms[i]), hands, sides, labels, int(a.active[i]))
        return c


# ------------------------------------------------------------------- recorder

# Teclas do operador para escolher o ground truth. Cobre todas as classes do
# enum; 0 e o repouso ("sem mao"), que e o estado que mais importa para medir
# alucinacao. A tabela vive em ``LABEL_KEY_CHOICES`` (char legivel) e
# ``LABEL_KEYS`` e derivada, para as duas nao poderem divergir.
#
# Os digitos 1-9 seguem o que o collect_gestures.py ja usava. As tres classes
# restantes ficam em c/d/g porque q/s/a/b/m/v/h ja sao teclas de controlo do
# preview (test_engine_recording.py fixa essa nao-colisao).
LABEL_KEY_CHOICES = {
    "0": "NONE",
    "1": "OPEN",
    "2": "ONE",
    "3": "PINCH",
    "4": "PINCH_MID",
    "5": "FIST",
    "6": "PEACE",
    "7": "THREE",
    "8": "THUMB_UP",
    "9": "THUMB_DOWN",
    "d": "PINKY",
    "c": "SHAKA",
    "g": "ROCK",
}
LABEL_KEYS = {ord(ch): name for ch, name in LABEL_KEY_CHOICES.items()}


class CorpusRecorder:
    """Acumula a mao do cursor de cada frame com a etiqueta escolhida a mao.

    So a mao activa e gravada. Com duas mao visiveis, uma unica tecla nao
    descreve com honestidade o que ambas estao a fazer, e um corpus mal
    etiquetado e pior do que um corpus pequeno: mediria a etiqueta errada.
    """

    def __init__(self, path=None, label: str = ABSENT_LABEL, max_frames: int = 0):
        self.path = path
        self.corpus = Corpus()
        self._label = ABSENT_LABEL
        self._max_frames = max_frames
        self.set_label(label)

    # ------------------------------------------------------------------ estado

    @property
    def label(self) -> str:
        return self._label

    @property
    def frames(self) -> int:
        return self.corpus.frames

    @property
    def total(self) -> int:
        return self.corpus.total

    @property
    def full(self) -> bool:
        return bool(self._max_frames) and self.corpus.frames >= self._max_frames

    def set_label(self, label) -> None:
        self._label = LABEL_NAMES[label_index(label)]

    def set_label_by_key(self, key: int) -> bool:
        """Selecciona a etiqueta pela tecla premida. Devolve True se mudou."""
        name = LABEL_KEYS.get(key)
        if name is None:
            return False
        changed = name != self._label
        self._label = name
        return changed

    def reset(self) -> None:
        self.corpus.clear()

    # ----------------------------------------------------------------- escrita

    def observe(self, hands, sides, index: int, t_ms: int) -> bool:
        """Grava a mao ``index`` de ``hands`` com a etiqueta actual.

        Em repouso (``NONE``) um frame sem mao tambem e gravado, porque e a
        evidencia de que o pipeline nao inventou um gesto. Com qualquer outra
        etiqueta, um frame sem mao e descartado: nao ha nada para avaliar.
        """
        if self.full:
            return False
        hands = list(hands)
        sides = list(sides)
        resting = self._label == ABSENT_LABEL
        if not hands:
            if not resting:
                return False
            self.corpus.add_frame(t_ms, [], [], [], ACTIVE_NONE)
            return True
        if not 0 <= index < len(hands):
            return False
        self.corpus.add_frame(
            t_ms, [hands[index]], [sides[index]], [self._label], 0
        )
        return True

    def flush(self) -> bool:
        if self.path is None:
            return False
        return self.corpus.save(self.path)
