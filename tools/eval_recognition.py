"""Harness de avaliacao do reconhecimento de gestos (Onda 0).

Responde a uma unica pergunta, de forma objectiva e repetivel:

    *dadas* as landmarks que o tracker produziu, o classificador escolhe o
    gesto certo, e dispara cliques apenas quando o utilizador queria?

Corre sem camera, sem rato e sem modelo de IA, sobre um corpus gravado com
``--record``. Por isso da para correr em CI e usar como criterio de aceitacao
de uma mudanca.

Dois niveis de metrica
----------------------
frame  : precisao / recall / F1 por gesto + confusion matrix
evento : cliques fantasma por hora + latencia de reacao (ms)

A metrica de evento e a que importa. O debounce e a histerese do engine atrasam
o clique alguns frames de proposito; medir por frame trataria esse atraso como
erro. Por isso os cliques sao contados por *episodio* (maximo de ``left_down``
consecutivos) e so contam como fantasma os que disparam FORA de um segmento em
que o ground truth era um gesto de clique.

Frames em transicao
-------------------
Um corpus anotado tem de marcar como ``SETTLE`` os primeiros frames de cada
segmento: o gesto destino ja comecou, mas o debounce (2 frames, 1 na pinca)
ainda nao fechou. Esses frames nao entram no F1 — contam apenas na latencia,
que e onde o atraso e visivel ao utilizador. Sem esta distincao, o F1 mede
quantos segmentos o corpus tem em vez da qualidade do classificador.

Uso
----
    python tools/eval_recognition.py data/sessao.npz
    python tools/eval_recognition.py data/sessao.npz --json
    python tools/eval_recognition.py data/sessao.npz --min-f1 0.97 --gate
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from typing import NamedTuple

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.corpus import (  # noqa: E402
    ABSENT_LABEL,
    LABEL_NAMES,
    SETTLE_LABEL,
    Corpus,
)
from core.gestures import Gesture  # noqa: E402

# Gesto que pode gerar clique esquerdo. Espelha LEFT_BUTTON_GESTURES do engine:
# qualquer clique que apareca fora daqui e um clique fantasma.
CLICK_GESTURES = frozenset({Gesture.PINCH})
CLICK_EVENTS = frozenset({"left_down"})

# Alvos de aceitacao (docs/RECONHECIMENTO_MAOS.md, Onda 0).
DEFAULT_MIN_F1 = 0.97
DEFAULT_MIN_PINCH_PRECISION = 0.99
DEFAULT_MAX_PHANTOM_PER_HOUR = 0.0

MAX_CONFUSIONS = 8


class Prediction(NamedTuple):
    """Uma decisao do classificador face ao ground truth."""

    frame: int
    hand: int
    truth: str
    pred: str


class PRF(NamedTuple):
    precision: float
    recall: float
    f1: float
    support: int


class Confusion(NamedTuple):
    truth: str
    pred: str
    hits: int   # nao se chama "count": colidiria com tuple.count()


class ClickEpisode(NamedTuple):
    start_frame: int
    length: int
    is_phantom: bool


# --------------------------------------------------------------------- ordem


def ordered_labels(base, pairs, label_order=None) -> list:
    """Eixos canonicos da confusion matrix: ``sorted(base | observados)``.

    A ordem nao pode depender da ordem em que o caller lista as classes, senao
    a mesma evidencia daria matrizes diferentes (e o bug escondia-se em testes
    que comparavam indices crus).
    """
    if label_order is not None:
        order = list(label_order)
        known = set(order)
        for truth, pred in pairs:
            for name in (truth, pred):
                if name is not None and name not in known:
                    raise KeyError(
                        f"label_order nao cobre {name!r}; faltam as observadas"
                    )
        return order
    seen = set(base)
    for truth, pred in pairs:
        seen.update(n for n in (truth, pred) if n is not None)
    return sorted(seen)


def _as_pair(item) -> tuple:
    """Extrai ``(verdadeiro, previsto)``.

    Aceita tuplas simples e ``Prediction``. Ler por posicao seria um erro
    silencioso: em ``Prediction`` as duas primeiras posicoes sao ``frame`` e
    ``hand``, nao a verdade e a previsao.
    """
    if hasattr(item, "truth"):
        return (str(item.truth), str(item.pred))
    truth, pred = item[0], item[1]
    return (str(truth), str(pred))


# ------------------------------------------------------------------ metricas


def confusion_matrix(pairs, base_labels, label_order=None) -> np.ndarray:
    """Conta (verdadeiro, previsto). Linhas = verdade, colunas = previsao."""
    pairs = [_as_pair(p) for p in pairs]
    order = ordered_labels(base_labels, pairs, label_order)
    ix = {name: i for i, name in enumerate(order)}
    m = np.zeros((len(order), len(order)), dtype=np.int64)
    for truth, pred in pairs:
        m[ix[truth], ix[pred]] += 1
    return m


def per_class_prf(matrix: np.ndarray, labels) -> dict:
    """Precisao/recall/F1 por classe. Divisao por zero devolve 0.0, nunca NaN."""
    labels = list(labels)
    out = {}
    for i, name in enumerate(labels):
        tp = int(matrix[i, i])
        support = int(matrix[i].sum())
        predicted = int(matrix[:, i].sum())
        precision = tp / predicted if predicted else 0.0
        recall = tp / support if support else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        out[name] = PRF(precision, recall, f1, support)
    return out


def macro_f1(matrix: np.ndarray, labels) -> float:
    """Media do F1 sobre as classes com evidencia real.

    Classes sem ``support`` nao contam: uma classe que nunca foi pedida nao
    pode fazer descer a nota global.
    """
    prf = per_class_prf(matrix, labels)
    values = [v.f1 for name, v in prf.items() if v.support > 0]
    return float(sum(values) / len(values)) if values else 0.0


def _percentile(values, q: float):
    if not values:
        return None
    return float(np.percentile(np.asarray(values, dtype=np.float64), q))


# -------------------------------------------------------------------- eventos


@dataclass
class EventStats:
    """Metricas ao nivel do evento, que sao as que o utilizador sente."""

    total_clicks: int = 0
    phantom_clicks: int = 0
    duration_s: float = 0.0
    latencies_ms: list = field(default_factory=list)

    @property
    def phantom_per_hour(self) -> float:
        if self.duration_s <= 0:
            return 0.0
        return self.phantom_clicks * 3600.0 / self.duration_s

    @property
    def latency_p50_ms(self):
        return _percentile(self.latencies_ms, 50)

    @property
    def latency_p95_ms(self):
        return _percentile(self.latencies_ms, 95)


def click_episodes(events, labels) -> list:
    """Agrupa ``left_down`` consecutivos em episodios de clique.

    Um episodio e "fantasma" quando arranca num frame cujo ground truth nao e um
    gesto de clique. Um clique que chega 2 frames de atraso (debounce) ainda
    cai dentro do segmento PINCH e conta como correcto.
    """
    truth_of = _resolved_truth(labels)
    episodes = []
    start = None
    length = 0
    for i, ev in enumerate(events):
        if ev in CLICK_EVENTS:
            if start is None:
                start = i
                length = 0
            length += 1
            continue
        if start is not None:
            episodes.append(_episode(start, length, truth_of))
            start = None
            length = 0
    if start is not None:
        episodes.append(_episode(start, length, truth_of))
    return episodes


def _episode(start: int, length: int, truth_of) -> ClickEpisode:
    truth = truth_of[start] if start < len(truth_of) else None
    return ClickEpisode(
        start_frame=start,
        length=length,
        is_phantom=truth not in {g.name for g in CLICK_GESTURES},
    )


def _resolved_truth(labels) -> list:
    """Substitui cada janela ``SETTLE`` pelo gesto que se segue.

    Um clique que dispara no primeiro frame de um segmento de PINCH cai no
    frame de transicao (o debounce da pinca e de 1 frame). Julgar esse frame
    pelo gesto *anterior* contaria um clique correcto como fantasma. A janela de
    transicao pertence, por definicao, ao gesto que se esta a entrar.
    """
    out = list(labels)
    for i, name in enumerate(out):
        if name != SETTLE_LABEL:
            continue
        nxt = next((out[j] for j in range(i + 1, len(out)) if out[j] != SETTLE_LABEL),
                   None)
        prv = None
        for j in range(i - 1, -1, -1):
            if out[j] != SETTLE_LABEL:
                prv = out[j]
                break
        out[i] = nxt if nxt is not None else prv
    return out


def _click_latencies(episodes, labels, t_ms) -> list:
    """Tempo entre o inicio de um segmento de clique e o clique que nele ocorre.

    O inicio do segmento e o primeiro frame do segmento *resolvido* — e a
    resolucao e o que junta a janela ``SETTLE`` ao gesto destino, portanto o
    atraso do debounce fica dentro do segmento e conta desde a sua primeira
    frame.

    Uma latencia de 0 ms e um valor real, nao ausencia de medicao: significa
    que o commit aconteceu na primeira frame do segmento. Descartar esses
    samples (o que se fez quando isto foi escrito) fazia o relatorio mostrar
    "sem dados" precisamente no caso em que o classificador esta no melhor
    estado possivel — o pior sitio para um numero disappearing.
    """
    if not t_ms:
        return []
    truth_of = _resolved_truth(labels)
    out = []
    for ep in episodes:
        i = ep.start_frame
        if i >= len(truth_of) or i >= len(t_ms):
            continue
        seg = i
        while seg > 0 and truth_of[seg - 1] == truth_of[i]:
            seg -= 1
        out.append(float(t_ms[i]) - float(t_ms[seg]))
    return out


# --------------------------------------------------------------------- score


@dataclass
class Score:
    frames: int = 0
    total: int = 0
    settle: int = 0
    correct: int = 0
    accuracy: float = 0.0
    macro_f1: float = 0.0
    order: list = field(default_factory=list)
    per_class: dict = field(default_factory=dict)
    confusion: np.ndarray | None = None
    worst_confusions: list = field(default_factory=list)
    events: EventStats = field(default_factory=EventStats)


def _worst_confusions(matrix, labels, limit=MAX_CONFUSIONS) -> list:
    out = []
    for i, truth in enumerate(labels):
        for j, pred in enumerate(labels):
            if i == j:
                continue
            count = int(matrix[i, j])
            if count > 0:
                out.append(Confusion(truth, pred, count))
    out.sort(key=lambda c: (-c.hits, c.truth, c.pred))
    return out[:limit]


def score_predictions(pairs, events, labels, duration_s=0.0, t_ms=None) -> Score:
    """Consolida as previsoes e os eventos num unico objecto de resultado.

    Ficam de fora da matriz de confusao os frames que **nao sao avaliaveis**:
    ``NONE`` (nao havia mao) e ``SETTLE`` (o gesto destino ja comecou mas o
    debounce ainda nao fechou). Contar a transicao como erro faria o F1 medir a
    estrutura do corpus — quantos segmentos tem — em vez da qualidade do
    classificador, e tornaria o alvo de 0.97 inalcançavel por construcao. O
    custo do debounce continua medido, mas onde ele é visivel ao utilizador:
    na latencia de clique.
    """
    pairs = [_as_pair(p) for p in pairs]
    settling = [p for p in pairs if p[0] == SETTLE_LABEL]
    evaluated = [p for p in pairs if p[0] not in (ABSENT_LABEL, SETTLE_LABEL)]
    labelled = evaluated
    order = ordered_labels(LABEL_NAMES, evaluated)
    matrix = confusion_matrix(evaluated, LABEL_NAMES, label_order=order)

    total = len(labelled)
    correct = sum(1 for t, p in labelled if t == p)

    episodes = click_episodes(events, labels)
    stats = EventStats(
        total_clicks=len(episodes),
        phantom_clicks=sum(1 for e in episodes if e.is_phantom),
        duration_s=duration_s,
        latencies_ms=_click_latencies(episodes, labels, t_ms),
    )

    return Score(
        frames=len(pairs),
        total=total,
        settle=len(settling),
        correct=correct,
        accuracy=(correct / total) if total else 0.0,
        macro_f1=macro_f1(matrix, order) if total else 0.0,
        order=order,
        per_class=per_class_prf(matrix, order),
        confusion=matrix,
        worst_confusions=_worst_confusions(matrix, order),
        events=stats,
    )


# ------------------------------------------------------------------ aceitacao


@dataclass
class Acceptance:
    min_f1: float = DEFAULT_MIN_F1
    min_pinch_precision: float = DEFAULT_MIN_PINCH_PRECISION
    max_phantom_per_hour: float = DEFAULT_MAX_PHANTOM_PER_HOUR
    failures: tuple = ()

    @property
    def passed(self) -> bool:
        return not self.failures

    def render(self) -> str:
        if self.passed:
            return "ACEITE: todos os alvos cumpridos."
        return "REJEITE:\n" + "\n".join(f"  - {f}" for f in self.failures)


def acceptance_report(
    score: Score,
    min_f1: float = DEFAULT_MIN_F1,
    min_pinch_precision: float = DEFAULT_MIN_PINCH_PRECISION,
    max_phantom_per_hour: float = DEFAULT_MAX_PHANTOM_PER_HOUR,
) -> Acceptance:
    failures = []

    if score.total > 0 and score.macro_f1 < min_f1:
        failures.append(
            f"F1 macro {score.macro_f1:.3f} abaixo do alvo {min_f1:.3f}"
        )

    pinch = score.per_class.get(Gesture.PINCH.name)
    if pinch is not None and pinch.support > 0 and pinch.precision < min_pinch_precision:
        failures.append(
            f"PINCH precisao {pinch.precision:.3f} abaixo do alvo "
            f"{min_pinch_precision:.3f} ({pinch.support} amostras)"
        )

    if score.events.phantom_per_hour > max_phantom_per_hour:
        failures.append(
            f"cliques fantasma {score.events.phantom_per_hour:.2f}/h acima do "
            f"alvo {max_phantom_per_hour:.2f}/h"
        )

    return Acceptance(
        min_f1=min_f1,
        min_pinch_precision=min_pinch_precision,
        max_phantom_per_hour=max_phantom_per_hour,
        failures=tuple(failures),
    )


# --------------------------------------------------------------------- report


@dataclass
class Report:
    corpus_path: str = ""
    corpus_frames: int = 0
    corpus_hands: int = 0
    duration_s: float = 0.0
    width: int = 0
    height: int = 0
    score: Score = field(default_factory=Score)
    acceptance: Acceptance = field(default_factory=Acceptance)

    @property
    def passed(self) -> bool:
        return self.acceptance.passed

    def to_dict(self) -> dict:
        ev = self.score.events
        return {
            "corpus": {
                "path": self.corpus_path,
                "frames": self.corpus_frames,
                "hands": self.corpus_hands,
                "duration_s": round(self.duration_s, 3),
                "width": self.width,
                "height": self.height,
            },
            "frames": self.score.frames,
            "labelled": self.score.total,
            "settle": self.score.settle,
            "correct": self.score.correct,
            "accuracy": round(self.score.accuracy, 6),
            "macro_f1": round(self.score.macro_f1, 6),
            "per_class": {
                name: {
                    "precision": round(v.precision, 6),
                    "recall": round(v.recall, 6),
                    "f1": round(v.f1, 6),
                    "support": v.support,
                }
                for name, v in self.score.per_class.items()
                if v.support > 0
            },
            "worst_confusions": [
                {"truth": c.truth, "pred": c.pred, "hits": c.hits}
                for c in self.score.worst_confusions
            ],
            "events": {
                "total_clicks": ev.total_clicks,
                "phantom_clicks": ev.phantom_clicks,
                "phantom_per_hour": round(ev.phantom_per_hour, 4),
                "latency_p50_ms": ev.latency_p50_ms,
                "latency_p95_ms": ev.latency_p95_ms,
            },
            "acceptance": {
                "passed": self.acceptance.passed,
                "min_f1": self.acceptance.min_f1,
                "min_pinch_precision": self.acceptance.min_pinch_precision,
                "max_phantom_per_hour": self.acceptance.max_phantom_per_hour,
                "failures": list(self.acceptance.failures),
            },
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
    def render(self) -> str:
        d = self.to_dict()
        lines = [
            f"Corpus        : {self.corpus_path}",
            f"Frames / maos : {d['corpus']['frames']} / {d['corpus']['hands']}"
            f"  ({d['corpus']['duration_s']:.1f}s)"
            f"  [{self.width}x{self.height}]",
            f"Acerto (frame): {self.score.accuracy:.4f}"
            f"  ({self.score.correct}/{self.score.total})",
            f"F1 macro      : {self.score.macro_f1:.4f}",
            f"Transicao     : {self.score.settle} frames em SETTLE"
            f" (excluidos do F1; o custo do debounce aparece na latencia)",
            "",
            "Por gesto (so classes com evidencia):",
        ]
        if d["per_class"]:
            lines.append(
                f"  {'gesto':<11} {'P':>7} {'R':>7} {'F1':>7} {'N':>7}"
            )
            for name, v in sorted(d["per_class"].items()):
                lines.append(
                    f"  {name:<11} {v['precision']:>7.3f} {v['recall']:>7.3f}"
                    f" {v['f1']:>7.3f} {v['support']:>7d}"
                )
        else:
            lines.append("  (nenhuma)")

        ev = d["events"]
        lines += [
            "",
            "Eventos:",
            f"  cliques            : {ev['total_clicks']}",
            f"  cliques fantasma   : {ev['phantom_clicks']}"
            f"  ({ev['phantom_per_hour']:.2f}/h)",
        ]
        if ev["latency_p50_ms"] is not None:
            lines.append(
                f"  latencia clique    : p50 {ev['latency_p50_ms']:.0f} ms"
                f" | p95 {ev['latency_p95_ms']:.0f} ms"
            )

        if d["worst_confusions"]:
            lines += ["", "Confusoes mais frequentes:"]
            for c in d["worst_confusions"]:
                lines.append(f"  {c['truth']:<11} -> {c['pred']:<11} {c['hits']:>6d}")

        lines += ["", self.acceptance.render()]
        return "\n".join(lines)


# ---------------------------------------------------------------------- replay


def _match_hands(results, sides):
    """Associa cada mao do ground truth ao resultado do pool.

    O ``HandPool`` descarta duplicados e pode trocar os labels, portanto nao ha
    garantia de correspondencia posicional. Primeiro procuramos pelo lado
    registado; em falta, usamos qualquer resultado ainda livre. Sem resultado,
    o ground truth foi descartado e a previsao e ``NONE``.
    """
    out = []
    used = set()
    for side in sides:
        key = side if side in results and side not in used else None
        if key is None:
            free = [k for k in results if k not in used]
            key = free[0] if free else None
        if key is None:
            out.append((ABSENT_LABEL, None))
        else:
            used.add(key)
            hf, ev, _value = results[key]
            out.append((hf.gesture.name, ev))
    return out


def replay_corpus(corpus: Corpus, cfg, width: int, height: int, gesture_ai=None):
    """Corre o corpus pelo mesmo ``HandPool`` do runtime.

    Devolve ``(pairs, events, truth_labels, t_ms)`` onde ``events`` /
    ``truth_labels`` sao por frame e referem-se a mao do cursor (``active``),
    que e a que gera cliques.
    """
    from core.twohand import HandPool

    pool = HandPool(cfg, gesture_ai)
    pairs = []
    events = []
    truth = []
    t_ms = []
    for i, (t, hands, sides, labels, active) in enumerate(corpus.replay()):
        results = pool.update(hands, sides, width, height)
        matched = _match_hands(results, sides)
        for h, name in enumerate(labels):
            pred = matched[h][0] if h < len(matched) else ABSENT_LABEL
            pairs.append(Prediction(frame=i, hand=h, truth=name, pred=pred))
        if active is not None and 0 <= active < len(labels):
            events.append(matched[active][1] if active < len(matched) else None)
            truth.append(labels[active])
        else:
            events.append(None)
            truth.append(None)
        t_ms.append(t)
    return pairs, events, truth, t_ms


def evaluate(
    path,
    width: int = 640,
    height: int = 480,
    cfg=None,
    gesture_ai=None,
    min_f1: float = DEFAULT_MIN_F1,
    min_pinch_precision: float = DEFAULT_MIN_PINCH_PRECISION,
    max_phantom_per_hour: float = DEFAULT_MAX_PHANTOM_PER_HOUR,
) -> Report:
    """Avalia um corpus gravado e devolve o relatorio completo."""
    from config import Config

    corpus = Corpus.load(path)
    if cfg is None:
        cfg = Config()
    pairs, events, truth, t_ms = replay_corpus(
        corpus, cfg, width, height, gesture_ai
    )
    score = score_predictions(
        pairs, events, truth, duration_s=corpus.duration_s(), t_ms=t_ms
    )
    return Report(
        corpus_path=os.fspath(path),
        corpus_frames=corpus.frames,
        corpus_hands=corpus.total,
        duration_s=corpus.duration_s(),
        width=width,
        height=height,
        score=score,
        acceptance=acceptance_report(
            score, min_f1, min_pinch_precision, max_phantom_per_hour
        ),
    )


# ------------------------------------------------------------------------ CLI


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Avalia um corpus de landmarks gravado com --record."
    )
    p.add_argument("corpus", help="ficheiro .npz gravado com --record")
    p.add_argument("--width", type=int, default=640, help="largura de replay")
    p.add_argument("--height", type=int, default=480, help="altura de replay")
    p.add_argument("--min-f1", type=float, default=DEFAULT_MIN_F1)
    p.add_argument("--min-pinch-precision", type=float,
                   default=DEFAULT_MIN_PINCH_PRECISION)
    p.add_argument("--max-phantom-per-hour", type=float,
                   default=DEFAULT_MAX_PHANTOM_PER_HOUR)
    p.add_argument("--json", action="store_true", help="saida em JSON")
    p.add_argument("--gate", action="store_true",
                   help="devolve 1 se algum alvo falhar (para CI)")
    args = p.parse_args(argv)

    try:
        report = evaluate(
            args.corpus,
            width=args.width,
            height=args.height,
            min_f1=args.min_f1,
            min_pinch_precision=args.min_pinch_precision,
            max_phantom_per_hour=args.max_phantom_per_hour,
        )
    except FileNotFoundError as exc:
        print(f"ERRO: corpus nao encontrado ({args.corpus}): {exc}")
        return 2
    except ValueError as exc:
        print(f"ERRO: corpus invalido ({args.corpus}): {exc}")
        return 2

    print(report.to_json() if args.json else report.render())
    if args.gate and not report.passed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
