"""Corpus de landmarks para avaliacao offline do reconhecimento (Onda 0).

Porque landmarks e nao video
---------------------------
Gravar video e reproduzi-lo mediria a variancia do MediaPipe, nao a do nosso
classificador. O que nos interessa e: *dadas* as landmarks que o tracker
produziu, o pipeline geometrico escolhe o gesto certo? Por isso o corpus
guarda as landmarks ja trackeadas (normalizadas 0..1) e a etiqueta humana
correspondente, e a replay corre exactamente o mesmo
``GestureEngine``/``HandPool`` do runtime, sem camera e sem rato.

Formato (``.npz``) — v2
    landmarks : (F, 2, 21, 3) float32  - posicoes normalizadas 0..1
    mask      : (F, 2)      bool        - True = esta mao existe neste frame
    labels    : (F, 2)      int8        - indice em LABEL_NAMES; -1 = sem mao
                                           -2 = SETTLE (frame em transicao)
    sides     : (F, 2)      int8        - SIDE_LEFT / SIDE_RIGHT
    active    : (F,)        int8        - indice da mao do cursor; -1 = nenhuma
    t_ms      : (F,)        int64       - timestamp do frame
    conf      : (F, 2)      float32     - confianca da CLASSIFICACAO da mao;
                                           NaN = nao medida (slot vazio ou
                                           tracker sem handedness)
    meta      : ()          str         - JSON com a origem da sessao
    version   : ()          int64       - FORMAT_VERSION

Frames sem mao nenhuma sao gravados de proposito (``mask`` todo False): sao os
que revelam alucinacao, ie. o pipeline a inventar gestos quando nao ha mao.

Porquê a v2: ver tests/test_corpus_v2.py. Resumo — a ``conf`` não se recupera
depois (e as maos reais não se recolhem duas vezes), e a ``meta["source"]`` é o
que separa "sintético" de "real" por máquina em vez de por nota de rodapé.
"""
from __future__ import annotations

import json
import os
import platform
from typing import NamedTuple

import numpy as np

from core.gestures import Gesture

# Indice de "nenhuma mao" numa das duas ranhuras.
ACTIVE_NONE = -1
MAX_HANDS = 2
N_LANDMARKS = 21

FORMAT_VERSION = 2

# Versoes que este codigo ainda sabe ler. A v1 não tinha `conf` nem `meta`, e a
# fixture `tests/fixtures/corpus_regressao_v1.npz` é o portão de regressão do
# CI: deixá-la de carregar seria tornar o gate vermelho por causa de uma
# alteração de instrumentação.
LEGACY_VERSIONS = (1,)

# Quando `meta["source"]` não é preenchido. Não é "synthetic": é "não sei", que
# é a diferença entre honesto e conveniente.
SOURCE_UNKNOWN = "unknown"

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
    conf: np.ndarray       # (F, 2) float32, NaN = nao medido
    meta: dict             # metadados da sessao (JSON no disco)


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
        self._conf: list[list[float]] = []
        self._meta: dict = {"source": SOURCE_UNKNOWN}

    # ------------------------------------------------------------------ metadados

    @property
    def meta(self) -> dict:
        return dict(self._meta)

    def set_meta(self, **fields) -> None:
        """Acrescenta campos aos metadados da sessao.

        O que interessa não é o que se guarda, é o que fica guardado **por
        omissão**: `source` é ``"unknown"`` e não ``"synthetic"``. Um corpus
        que não diz de onde veio não pode ser usado para anunciar qualidade, e
        a diferença entre "não medi" e "medi e deu sintético" é a diferença
        entre honesto e conveniente.
        """
        for key, value in fields.items():
            if value is None:
                continue
            # Falha aqui e não no `save`: um metadado não serializável é um erro
            # de quem o escreveu, e descobrir isso 20 minutos de recolha depois
            # (ou no CI, sobre um corpus de outra pessoa) não serve.
            try:
                json.dumps(value, ensure_ascii=False)
            except (TypeError, ValueError) as exc:
                raise TypeError(
                    f"metadado {key!r} nao e serializavel em JSON: {exc}"
                ) from None
            self._meta[key] = value

    @property
    def source(self) -> str:
        return self._meta.get("source", SOURCE_UNKNOWN)

    @property
    def is_synthetic(self) -> bool:
        return self.source == "synthetic"

    def provenance(self) -> str:
        """Uma linha para ler junto de um número de métrica.

        Existe porque o `--replay-gate` anunciava F1 1.0000 e o `PROGRESSO.md`
        tinha de repetir três vezes, em três sítios, que era sobre corpus
        sintético. Passa a ser um campo, e não uma promessa.
        """
        if self.is_synthetic:
            return "SINTETICO (gerado; nao prova qualidade em maos reais)"
        if self.source == "real":
            return f"REAL ({self._meta.get('device', 'dispositivo desconhecido')})"
        return "ORIGEM DESCONHECIDA (nao usar para anunciar qualidade)"

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
        self._conf.clear()

    # ------------------------------------------------------------------ escrita

    def add_frame(
        self,
        t_ms: int,
        hands,
        sides,
        labels,
        active: int = ACTIVE_NONE,
        confs=None,
    ) -> None:
        """Acrescenta um frame.

        ``hands`` sao listas de 21 landmarks normalizadas ``(x, y, z)``; ``sides``
        e ``labels`` devem ter o mesmo comprimento. ``active`` e o indice da
        mao do cursor (a que genera comandos), ou ``ACTIVE_NONE``.

        ``labels`` aceita um ``Gesture``, um nome de ``LABEL_NAMES``, ou
        ``SETTLE_LABEL`` para um frame em que o gesto destino ja comecou mas o
        debounce ainda nao fechou.

        ``confs`` e a confianca da **classificacao** de cada mao (ver
        ``core/tracker.py::parse_landmarks_result``). E opcional: quem nao a
        tem grava ``NaN``, que significa "nao medido" e nao "mediu zero" —
        a diferença decide se um limiar de abstenção descarta todas as mãos.
        """
        hands = list(hands)
        sides = list(sides)
        labels = list(labels)
        confs = list(confs) if confs is not None else []
        n = len(hands)
        if n > MAX_HANDS:
            raise ValueError(f"maximo {MAX_HANDS} maos por frame (recebi {n})")
        if len(sides) != n or len(labels) != n:
            raise ValueError(
                f"hands/sides/labels com comprimentos diferentes: "
                f"{n}/{len(sides)}/{len(labels)}"
            )
        if confs and len(confs) != n:
            raise ValueError(
                f"confs com {len(confs)} valores para {n} maos: tem de ser "
                f"paralelo a hands, ou omitido"
            )
        if not -1 <= active < MAX_HANDS:
            raise ValueError(f"active fora de intervalo: {active}")
        if n == 0 and active != ACTIVE_NONE:
            raise ValueError("active so faz sentido com pelo menos uma mao")

        lm = _EMPTY_LANDMARKS.copy()
        mask = [False] * MAX_HANDS
        lb = [-1] * MAX_HANDS
        sd = [SIDE_LEFT] * MAX_HANDS
        cf = [float("nan")] * MAX_HANDS
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
            if confs:
                try:
                    cf[i] = float(confs[i])
                except (TypeError, ValueError):
                    cf[i] = float("nan")

        self._landmarks.append(lm)
        self._mask.append(mask)
        self._labels.append(lb)
        self._sides.append(sd)
        self._active.append(int(active))
        self._t_ms.append(int(t_ms))
        self._conf.append(cf)

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
                conf=np.full((0, MAX_HANDS), float("nan"), dtype=np.float32),
                meta=self.meta,
            )
        return CorpusArrays(
            landmarks=np.stack(self._landmarks),
            mask=np.array(self._mask, dtype=bool),
            labels=np.array(self._labels, dtype=np.int8),
            sides=np.array(self._sides, dtype=np.int8),
            active=np.array(self._active, dtype=np.int8),
            t_ms=np.array(self._t_ms, dtype=np.int64),
            conf=np.array(self._conf, dtype=np.float32),
            meta=self.meta,
        )

    def replay_with_conf(self):
        """Como ``replay()``, mas com a confiança da classificação por mão.

        Devolve 6 valores: ``(t_ms, hands, sides, labels, active, confs)``.
        Os ``confs`` vêm por frame, com ``NaN`` onde a mão não existe ou onde o
        tracker não deu score.
        """
        order = sorted(range(self.frames), key=lambda i: self._t_ms[i])
        for i in order:
            hands, sides, labels, confs = [], [], [], []
            for h in range(MAX_HANDS):
                if not self._mask[i][h]:
                    continue
                hands.append(self._landmarks[i][h])
                sides.append(_SIDE_NAMES[self._sides[i][h]])
                labels.append(label_name(self._labels[i][h]))
                confs.append(self._conf[i][h])
            yield (
                self._t_ms[i],
                hands,
                sides,
                labels,
                self._active[i],
                confs,
            )

    def replay(self):
        """Itera os frames por ordem cronologica, no mesmo formato que
        ``HandTracker.process`` devolve, para encaixar directo no ``HandPool``.

        Devolve 5 valores, como sempre. A confiança vive em
        ``replay_with_conf()``, e não aqui, porque há ~20 sítios que
        descompactam este tuplo e a forma deles não é o que se quer mudar.
        """
        for t_ms, hands, sides, labels, active, _confs in self.replay_with_conf():
            yield (t_ms, hands, sides, labels, active)

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
        # `json.dumps` e não `np.save` com pickle: o corpus é um ficheiro que
        # outra pessoa vai abrir, e `allow_pickle=False` na leitura tem de
        # continuar a ser verdade.
        np.savez_compressed(
            path,
            landmarks=a.landmarks,
            mask=a.mask,
            labels=a.labels,
            sides=a.sides,
            active=a.active,
            t_ms=a.t_ms,
            conf=a.conf,
            meta=np.array(json.dumps(a.meta, ensure_ascii=False)),
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
            if version not in (FORMAT_VERSION, *LEGACY_VERSIONS):
                # Um formato desconhecido e erro, nao um default: ler um v3 como
                # se fosse o conhecido perderia dados sem ninguem dar por isso.
                raise ValueError(
                    f"versao de corpus {version} incompativel com {FORMAT_VERSION}: "
                    f"{path}"
                )
            n_frames = int(np.asarray(z["t_ms"]).shape[0])
            # A v1 nao tinha `conf` nem `meta`. Carrega com a confianca a NaN e
            # a origem a "unknown" — que e o honesto, porque ninguem sabe de
            # onde veio, e e melhor do que assumir "synthetic" e dar-lhe
            # credibilidade que nao tem.
            if "conf" in z.files:
                conf = np.asarray(z["conf"], dtype=np.float32)
            else:
                conf = np.full((n_frames, MAX_HANDS), float("nan"), dtype=np.float32)
            meta = {"source": SOURCE_UNKNOWN}
            if "meta" in z.files:
                try:
                    loaded = json.loads(str(z["meta"]))
                    if isinstance(loaded, dict):
                        meta.update(loaded)
                except (TypeError, ValueError):
                    # Meta corrompido nao pode deitar o corpus fora: os
                    # landmarks valem mais do que a nota de origem.
                    pass
            a = CorpusArrays(
                landmarks=np.asarray(z["landmarks"], dtype=np.float32),
                mask=np.asarray(z["mask"], dtype=bool),
                labels=np.asarray(z["labels"], dtype=np.int8),
                sides=np.asarray(z["sides"], dtype=np.int8),
                active=np.asarray(z["active"], dtype=np.int8),
                t_ms=np.asarray(z["t_ms"], dtype=np.int64),
                conf=conf,
                meta=meta,
            )
        c = cls()
        c.set_meta(**{k: v for k, v in a.meta.items() if v is not None})
        for i in range(a.landmarks.shape[0]):
            hands = [a.landmarks[i][h] for h in range(MAX_HANDS) if a.mask[i][h]]
            sides = [_SIDE_NAMES[int(a.sides[i][h])]
                     for h in range(MAX_HANDS) if a.mask[i][h]]
            labels = [label_name(int(a.labels[i][h]))
                      for h in range(MAX_HANDS) if a.mask[i][h]]
            confs = [float(a.conf[i][h])
                     for h in range(MAX_HANDS) if a.mask[i][h]]
            c.add_frame(
                int(a.t_ms[i]), hands, sides, labels, int(a.active[i]), confs
            )
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


def describe_device() -> str:
    """Nome legível da máquina, para carimbar a sessão de recolha.

    Existe porque comparar dois corpora de mãos reais sem saber em que máquinas
    foram gravados não diz nada: o mesmo gesto lido numa máquina a 14,6 fps e
    noutra a 30 fps são evidences diferentes, e `HARDWARE/LAB.md` já tem uma
    matriz de dispositivos por causa disso.

    Compõe o que o sistema diz e **diz que não sabe** quando não diz. Um
    `platform.processor()` vazio no Windows é o caso comum, não a exceção, e
    devolver "" seria indistinguível de "não consultámos".
    """
    parts = []
    ident = os.environ.get("PROCESSOR_IDENTIFIER", "").strip()
    if ident:
        parts.append(ident)
    machine = platform.machine().strip()
    if machine and machine not in " ".join(parts):
        parts.append(machine)
    return ", ".join(parts) if parts else "desconhecido"


class CorpusRecorder:
    """Acumula a mao do cursor de cada frame com a etiqueta escolhida a mao.

    So a mao activa e gravada. Com duas mao visiveis, uma unica tecla nao
    descreve com honestidade o que ambas estao a fazer, e um corpus mal
    etiquetado e pior do que um corpus pequeno: mediria a etiqueta errada.
    """

    def __init__(
        self,
        path=None,
        label: str = ABSENT_LABEL,
        max_frames: int = 0,
        meta: dict | None = None,
    ):
        self.path = path
        self.corpus = Corpus()
        self._label = ABSENT_LABEL
        self._max_frames = max_frames
        self.set_label(label)
        # Um gravador de `--record` vê uma câmara e mãos de uma pessoa. Não há
        # caminho em que isto seja sintético, portanto declará-lo "real" não é
        # uma afirmação otimista, é o que o classe sabe. (O caminho sintético
        # passa por `tools/make_corpus_fixture.py`, que não usa esta classe.)
        self.corpus.set_meta(source="real", recorder="CorpusRecorder")
        if meta:
            self.corpus.set_meta(**meta)

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
        # `source` e `recorder` sobrevivem: continuam a ser verdadeiros depois de
        # um reset, que é o inicio de uma nova série da mesma sessão. O que
        # tem de desaparecer é o que era medido e deixou de ser — daí o fps.
        self.corpus.set_meta(fps=None, frames=None, seconds=None)

    def measured_fps(self) -> float | None:
        """Frames por segundo **medidos nesta gravação**, ou ``None``.

        Sai dos ``t_ms`` que o próprio gravador escreveu, não da taxa pedida à
        câmara: o que interessa para um corpus é a taxa a que as mãos foram
        vistas, que é a que limita o debounce e a latência.

        ``None`` com menos de dois frames. Com um só não há intervalo, e
        devolver ``0.0`` seria um número que parece uma medida e não é.
        """
        if self.corpus.frames < 2:
            return None
        span = self.corpus.duration_s()
        if span <= 0.0:
            return None
        return (self.corpus.frames - 1) / span

    # ----------------------------------------------------------------- escrita

    def observe(self, hands, sides, index: int, t_ms: int, confs=None) -> bool:
        """Grava a mao ``index`` de ``hands`` com a etiqueta actual.

        Em repouso (``NONE``) um frame sem mao tambem e gravado, porque e a
        evidencia de que o pipeline nao inventou um gesto. Com qualquer outra
        etiqueta, um frame sem mao e descartado: nao ha nada para avaliar.

        ``confs`` e a confianca da **classificacao**, paralela a ``hands``
        (``core/tracker.py::parse_landmarks_result``). E opcional, e um
        descasamento de tamanho aqui **nao levanta**: este codigo esta no meio
        de uma recolha de minutos e perdia-se a sessão toda por causa de uma
        lista. Fica a ``NaN`` — "nao medido" — e grava-se à mesma.
        """
        if self.full:
            return False
        hands = list(hands)
        sides = list(sides)
        confs = list(confs) if confs is not None else []
        resting = self._label == ABSENT_LABEL
        if not hands:
            if not resting:
                return False
            self.corpus.add_frame(t_ms, [], [], [], ACTIVE_NONE)
            return True
        if not 0 <= index < len(hands):
            return False
        conf = None
        if index < len(confs):
            try:
                conf = float(confs[index])
            except (TypeError, ValueError):
                conf = None
        self.corpus.add_frame(
            t_ms,
            [hands[index]],
            [sides[index]],
            [self._label],
            0,
            None if conf is None else [conf],
        )
        return True

    def flush(self) -> bool:
        if self.path is None:
            return False
        # O que se aprendeu com a sessao só se sabe no fim: fps, nº de frames e
        # duração. `set_meta` ignora None, por isso um `measured_fps()` sem
        # medição não escreve nada em vez de escrever 0.
        fps = self.measured_fps()
        self.corpus.set_meta(
            fps=round(fps, 1) if fps is not None else None,
            frames=self.corpus.frames,
            seconds=round(self.corpus.duration_s(), 3),
        )
        return self.corpus.save(self.path)
