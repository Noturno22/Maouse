import argparse
import json
import os
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from core.camera import CameraStream
from core.corpus import LABEL_KEY_CHOICES, describe_device
from core.filters import FilterPair2D  # noqa: F401  (mantem paridade com main)
from core.gesture_ai import CLASSES as AI_CLASSES
from core.gestures import Gesture
from core.tracker import HAND_CONNECTIONS, HandTracker, ensure_model

# As duas listas vivem em lado nenhum deste ficheiro.
#
# `AI_CLASSES` e o que `tools/train_gesture_ai.py` sabe ler: 9 classes, e os
# pesos que o produto distribui sao um modelo de 9 classes. Este ficheiro
# declarava as suas 9 como uma tupla literal, e duplicar a tabela e como as duas
# ja divergiram uma vez — basta alguem acrescentar uma classe a uma das pontas
# para o tool passar a oferecer 9 de 10 sem ninguem dar por isso.
#
# `CLASS_KEY_CHOICES` vem do `core/corpus.py`: as MESMAS teclas que o
# `--record` usa. Este tool tinha 1-9 pela ordem de `AI_CLASSES` e `c` para
# limpar, e o `--record` tem 0-9 pela ordem de `Gesture` e `x` para limpar — dois
# teclados para a mesma tarefa. Errar a tecla aqui nao dá erro nenhum: grava o
# gesto errado, que e a forma mais cara de errar sobre mãos reais, que não se
# recolhem duas vezes.
#
# `COLLECTABLE` e o que este tool consegue gravar. E maior de proposito: da
# confusao PINKY/SHAKA (que o RECONHECIMENTO_MAOS.md marca como "por confirmar
# em maos reais"), `PINKY` nao e classe do modelo actual e por isso nao tinha
# tecla nenhuma — uma confusao que nao se resolve a recolher mais dados porque
# os dados de um dos lados nao se podiam recolher.
#
# Guardar as duas listas separadas tambem evita o erro simetrico: fazer o tool
# aceitar so as 9 do modelo esconderia a lacuna em vez de a mostrar.
AI_NAMES = tuple(g.name for g in AI_CLASSES)
COLLECTABLE = tuple(g for g in Gesture if g is not Gesture.NONE)
COLLECTABLE_NAMES = tuple(g.name for g in COLLECTABLE)
AI_NAME_SET = frozenset(AI_NAMES)
OUT_OF_MODEL = tuple(n for n in COLLECTABLE_NAMES if n not in AI_NAME_SET)

# Teclas 1..9 para as classes do modelo, pela ordem de `AI_CLASSES`; as
# restantes classes do enumerado ficam em d/c/g, como no `--record`. Os ids
# guardados sao os de `COLLECTABLE`, e nao os do modelo: e o que permite ler o
# ficheiro sem depender da posicao.
CLASS_KEY_CHOICES = {
    ch: n for ch, n in LABEL_KEY_CHOICES.items() if n in COLLECTABLE_NAMES
}
CLASS_KEYS = {
    ord(ch): (n, COLLECTABLE_NAMES.index(n))
    for ch, n in CLASS_KEY_CHOICES.items()
}
CLASS_NAMES = COLLECTABLE_NAMES  # alias legado para o `draw` existente

# Teclas que este tool usa para comandos. `x` limpa por causa do `--record`, que
# ja usa `x` para o mesmo: quem recolhe com as duas ferramentas nao pode ter de
# decorar dois teclados para a mesma tarefa. `c` deixa de limpar precisamente
# porque no `--record` e SHAKA — um `c` com os dois sentidos rotulava o gesto
# errado sem erro nenhum.
KEY_UNDO = "z"
KEY_CLEAR = "x"
KEY_SAVE = "s"
MAX_PER_CLASS = 5000
COLOR_DARK = (22, 22, 22)
COLOR_GREEN = (90, 220, 90)
COLOR_YELLOW = (80, 200, 235)
COLOR_RED = (60, 60, 235)
COLOR_WHITE = (245, 245, 245)
COLOR_GRAY = (160, 160, 160)


def open_camera(cfg):
    candidates = [cfg.camera_index] if cfg.camera_index is not None else [0, 1, 2]
    for index in candidates:
        cam = CameraStream(index)
        if cam.open(cfg.frame_width, cfg.frame_height, 30):
            return cam
        cam.release()
    return None


class Collector:
    def __init__(self):
        self.samples = {i: [] for i in range(len(CLASS_NAMES))}
        self.confs = {i: [] for i in range(len(CLASS_NAMES))}
        self.active: int | None = None

    def counts(self):
        return [len(self.samples[i]) for i in range(len(CLASS_NAMES))]

    def total(self):
        return sum(self.counts())

    def add(self, cls_id, pts, conf=float("nan")):
        """Acrescenta uma amostra. `conf` e a confiança da classificacao.

        O default e `NaN`, nao 0.0: um default de 0 seria uma medida que ninguem
        fez, e um limiar de abstenção aplicado depois descartaria todas as
        amostras sem ninguem saber porque.
        """
        if len(self.samples[cls_id]) >= MAX_PER_CLASS:
            return False
        self.samples[cls_id].append(pts)
        self.confs[cls_id].append(conf)
        return True

    def undo(self):
        if self.active is not None and self.samples[self.active]:
            self.samples[self.active].pop()
            self.confs[self.active].pop()
            return True
        return False

    def clear_active(self):
        if self.active is not None:
            self.samples[self.active].clear()
            self.confs[self.active].clear()
            return True
        return False

    def out_of_model(self):
        """Classes gravadas que `tools/train_gesture_ai.py` nao consegue ler."""
        return [CLASS_NAMES[i] for i, n in enumerate(self.counts())
                if n and CLASS_NAMES[i] in OUT_OF_MODEL]


def save(out_path, collector, meta=None):
    """Grava o `.npz` no formato que `load_real` le.

    Alem do `X`/`y`/`classes` de sempre, grava a **confianca** e a
    **proveniencia**. Sem a primeira, um corpus de maos reais fica sem a coluna
    que `RECONHECIMENTO_MAOS.md` §1.2 quer para a abstencao, e nao ha segunda
    recolha. Sem a segunda, o ficheiro nao diz de que maquina e a que taxa foi
    gravado — e `HARDWARE/LAB.md` tem uma matriz de dispositivos precisamente
    porque isso muda o que os dados provam.
    """
    xs, ys, cs = [], [], []
    for cls_id, arr in collector.samples.items():
        for k, pts in enumerate(arr):
            xs.append(np.asarray(pts, dtype=np.float32))
            ys.append(cls_id)
            cs.append(collector.confs[cls_id][k])
    if not xs:
        print("Nada para gravar.")
        return False
    parent = os.path.dirname(os.path.abspath(out_path))
    os.makedirs(parent, exist_ok=True)
    info = {"source": "real", "tool": "collect_gestures.py", "device": describe_device()}
    info.update(meta or {})
    # `meta` e JSON, nao `np.save` com pickle: o ficheiro vai parar a outra
    # máquina e `allow_pickle=False` tem de continuar a ser verdade na leitura.
    np.savez_compressed(
        out_path,
        X=np.stack(xs),
        y=np.array(ys, dtype=np.int64),
        classes=np.array(CLASS_NAMES),
        conf=np.array(cs, dtype=np.float32),
        meta=np.array(json.dumps(info, ensure_ascii=False)),
    )
    fora = collector.out_of_model()
    print(f"Gravado: {out_path} | total {len(xs)} amostras | por classe "
          f"{dict(zip(CLASS_NAMES, collector.counts(), strict=True))}")
    if fora:
        print(
            f"AVISO: {len(fora)} classe(s) fora do modelo de IA "
            f"({', '.join(fora)}): o treinador vai recusar este ficheiro "
            f"enquanto o modelo tiver {len(AI_CLASSES)} classes. Guardar "
            f"serve para quando houver retreino; treinar agora nao serve."
        )
    return True


def draw(frame, points, collector, fps, quality_ok, auto_label):
    h, w = frame.shape[:2]
    if points is not None:
        for a, b in HAND_CONNECTIONS:
            pa = tuple(int(v) for v in points[a])
            pb = tuple(int(v) for v in points[b])
            cv2.line(frame, pa, pb, (200, 200, 200), 1)
    rec_on = collector.active is not None
    label = (
        f"A GRAVAR: {CLASS_NAMES[collector.active]}"
        if rec_on else "PRIME 1-9/d/c/g PARA ESCOLHER GESTO"
    )
    color = COLOR_RED if rec_on else COLOR_WHITE
    cv2.rectangle(frame, (12, 10), (430, 40), COLOR_DARK, -1)
    cv2.putText(frame, label, (24, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)

    # Duas colunas: com 12 classes, uma coluna unica saía do ecra e as ultimas
    # (as de fora do modelo, que sao as que faltavam) ficavam fora de vista.
    for i, name in enumerate(CLASS_NAMES):
        key = _key_de(name)
        col_idx, row = divmod(i, 6)
        x = 16 + col_idx * 210
        y = 64 + 22 * row
        mark = ">" if collector.active == i else " "
        # Uma classe que o modelo nao conhece e marcada a amarelo: recolhe-la
        # serve para um retreino futuro, treinar com ela hoje nao serve.
        fora = name in OUT_OF_MODEL
        col = COLOR_YELLOW if fora else (
            COLOR_GREEN if collector.counts()[i] > 0 else COLOR_GRAY
        )
        sufixo = "*" if fora else " "
        txt = f"{mark}[{key:<1}] {name:<9} {collector.counts()[i]:4d}{sufixo}"
        cv2.putText(frame, txt, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 1, cv2.LINE_AA)

    q_txt = "OK" if quality_ok else "MAO PERTO/QUALIDADE"
    q_col = COLOR_GREEN if quality_ok else COLOR_RED
    cv2.putText(frame, q_txt, (w - 240, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.55, q_col, 1, cv2.LINE_AA)
    cv2.putText(
        frame, f"{fps:4.0f} fps | {KEY_UNDO} apaga ultima | {KEY_CLEAR} limpa gesto"
               f" | {KEY_SAVE} grava | Q sai"
               f"   (* fora do modelo de IA: {len(OUT_OF_MODEL)})",
        (16, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.42, COLOR_GRAY, 1, cv2.LINE_AA,
    )
    if auto_label:
        cv2.putText(frame, f"MODO AUTO: {auto_label}", (w - 260, h - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_GREEN, 1, cv2.LINE_AA)


def _key_de(name: str) -> str:
    """A tecla que recolhe este gesto, ou '?' se nao houver."""
    for ch, (n, _cid) in CLASS_KEYS.items():
        if n == name:
            return chr(ch)
    return "?"


def run(args):
    cfg = Config()
    if args.camera is not None:
        cfg.camera_index = args.camera
    model_path = ensure_model(cfg.model_path, cfg.model_url)
    cam = open_camera(cfg)
    if cam is None:
        print("ERRO: nenhuma camera encontrada.")
        return 1
    tracker = HandTracker(model_path, num_hands=1)
    collector = Collector()
    auto_label = None
    auto_left = 0

    if args.frames > 0:
        if not args.cls:
            print("ERRO: --frames exige --class.")
            cam.release()
            tracker.close()
            return 1
        key = next((k for k, (n, _) in CLASS_KEYS.items() if n == args.cls.upper()), None)
        if key is None:
            print(f"ERRO: gesto desconhecido {args.cls!r}. Usa: {', '.join(COLLECTABLE_NAMES)}")
            cam.release()
            tracker.close()
            return 1
        if args.cls.upper() in OUT_OF_MODEL:
            # Avisa e recolhe na mesma. A recolha e o que demora 20 minutos; o
            # retreino e que precisa de GPU, dados e decisao. Recusar aqui
            # seria deitar fora o dado para poupar um minuto.
            print(
                f"AVISO: {args.cls.upper()} nao e classe do modelo de IA "
                f"({len(AI_CLASSES)} classes). A recolha corre e grava, mas o "
                f"treinador vai recusar o ficheiro enquanto nao houver "
                f"retreino. Serve guardar para esse dia."
            )
        auto_label, auto_left = args.cls.upper(), args.frames
        collector.active = CLASS_KEYS[key][1]

    # Proveniencia da sessao. `fps` e medido (media do loop), nao o pedido a
    # camara: o que interessa para um corpus e a taxa a que as maos foram vistas.
    session = {
        "camera": f"{cfg.frame_width}x{cfg.frame_height}",
        "mirror": bool(cfg.mirror),
    }

    fps = 0.0
    last_seq = -1
    warmup = max(cfg.warmup_frames, 0)
    window = "Maouse-Coleta"

    try:
        if not args.no_preview:
            cv2.namedWindow(window, cv2.WINDOW_NORMAL)
        while True:
            t0 = time.perf_counter()
            frame, seq = cam.read()
            if frame is None:
                time.sleep(0.002)
                continue
            if seq == last_seq:
                time.sleep(0.002)
                continue
            last_seq = seq
            if warmup > 0:
                warmup -= 1
                continue
            frame = cv2.flip(frame, 1) if cfg.mirror else frame
            h, w = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            hands, _sides, confs = tracker.process(
                rgb, time.monotonic_ns() // 1_000_000
            )

            points = None
            quality_ok = False
            conf = float("nan")
            if hands:
                lm = hands[0]
                pts = np.array(
                    [(p[0] * w, p[1] * h, p[2] if len(p) > 2 else 0.0) for p in lm],
                    dtype=np.float32,
                )
                scale = float(np.hypot(*(pts[9] - pts[0])))
                quality_ok = scale >= cfg.min_hand_scale_px * 1.15 and bool(
                    np.all(np.isfinite(pts))
                )
                points = pts
                if confs:
                    try:
                        conf = float(confs[0])
                    except (TypeError, ValueError):
                        conf = float("nan")
                if (
                    quality_ok
                    and collector.active is not None
                    and collector.add(collector.active, pts.copy(), conf=conf)
                ):
                    if auto_label:
                        auto_left -= 1
                        if auto_left <= 0:
                            break

            dt = time.perf_counter() - t0
            inst = 1.0 / dt if dt > 0 else 0.0
            fps = inst if fps == 0.0 else fps * 0.9 + inst * 0.1

            if not args.no_preview:
                draw(frame, points, collector, fps, quality_ok, auto_label)
                cv2.imshow(window, frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    break
                if key in CLASS_KEYS:
                    name, cid = CLASS_KEYS[key]
                    collector.active = None if collector.active == cid else cid
                    if auto_label is None:
                        print(f"Gesto ativo: {name if collector.active is not None else '-'}")
                elif key == ord(KEY_UNDO):
                    collector.undo()
                elif key == ord(KEY_CLEAR):
                    collector.clear_active()
                elif key == ord(KEY_SAVE):
                    save(args.out, collector, meta=session)
            elif auto_label and auto_left <= 0:
                break
    finally:
        ok = False
        if not args.no_save:
            # A sessao so se sabe no fim: fps medido e quantas amostras ficaram.
            session = dict(session, fps=round(fps, 1), frames=collector.total())
            ok = save(args.out, collector, meta=session)
        tracker.close()
        cam.release()
        cv2.destroyAllWindows()

    if args.frames > 0 and not args.no_save:
        got = collector.counts()[CLASS_NAMES.index(auto_label)] if auto_label else 0
        print(f"[coleta-selftest] pedido {args.frames} | gravado {got}")
        return 0 if got == args.frames else 1
    return 0 if (args.no_save or ok or collector.total() == 0) else 0


def parse_args():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    p = argparse.ArgumentParser(description="Coleta landmarks reais para treinar a IA de gestos")
    p.add_argument("--out", default=os.path.join(root, "data", "real_landmarks.npz"))
    p.add_argument("--camera", type=int, default=None)
    p.add_argument("--no-preview", action="store_true")
    p.add_argument("--no-save", action="store_true", help="nao grava ficheiro (teste)")
    p.add_argument(
        "--frames", type=int, default=0,
        help="modo automatico: captura N amostras do gesto --class e sai",
    )
    p.add_argument(
        "--class", dest="cls", default=None,
        help="OPEN|PINCH|PINCH_MID|FIST|PEACE|THREE|THUMB_UP|ROCK|SHAKA",
    )
    return p.parse_args()


if __name__ == "__main__":
    sys.exit(run(parse_args()))
