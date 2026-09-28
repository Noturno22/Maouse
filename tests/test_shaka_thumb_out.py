"""O sinal que separa SHAKA (Ctrl+V) de PINKY (Ctrl+C) tem de existir.

`HARDWARE/PROBLEMAS_KNOWN.md` §1.4: com o `thumb_out` a medir o deslocamento
da ponta do polegar contra o proprio IP (landmark 3), 8 de 8 os SHAKA da
fixture saiam PINKY — o "hang loose" disparava Ctrl+C. A correcao passa a
medir a distancia da ponta do polegar a **base do indicador (landmark 5)**,
normalizada pela escala: com o polegar para o lado vale ~1.23, recolhido sobre
a palma ~0.85.

Estes testes sao sinteticos e inline (sem camara, sem fixture) para fixar o
predicado isolado: o portao sobre a fixture real esta em
`tests/test_corpus_fixture.py::TestShakaIsRecognised`.
"""
import numpy as np

from config import Config
from core.gestures import Gesture, GestureEngine
from tools.make_corpus_fixture import (
    HEIGHT,
    SEED,
    WIDTH,
    _place,
    _skeleton,
)

# 3 frames: `gesture_stable_frames = 2`, portanto o commit (e o evento de
# transicao) acontece no segundo. Sem isto so se media `raw_gesture`.
FRAMES = 3


def _read(label, seed=SEED, frames=FRAMES):
    """Le uma pose sintetica do `GestureEngine` e devolve (frame, evento).

    `update` so emite evento na **transicao** de commit; nas frames seguintes o
    gesto ja esta committed e devolve None. Por isso aqui se guarda o ultimo
    evento que disparou, e nao o do ultimo frame.
    """
    rng = np.random.default_rng(seed)
    landmarks = _place(_skeleton(label, rng), rng)
    eng = GestureEngine(Config(), gesture_ai=None)
    frame, fired = None, None
    for _ in range(frames):
        frame, event, _value = eng.update(landmarks, WIDTH, HEIGHT)
        if event is not None:
            fired = event
    return frame, fired


def test_shaka_thumb_tip_far_from_index_base():
    frame, event = _read("SHAKA")
    assert frame.raw_gesture is Gesture.SHAKA, (
        f"raw={frame.raw_gesture.name} (esperado SHAKA): mindinho esticado com "
        f"o polegar para o lado tem de bater a banda de separacao do PINKY"
    )
    assert event != "copy", (
        'o "hang loose" disparou "copy" (Ctrl+C) em vez de "paste" (Ctrl+V)'
    )


def test_tucked_thumb_still_reads_as_pinky():
    # Anti-regressao: a correcao tem de separar os dois gestos sem partir o
    # PINKY, que continua a ser Ctrl+C. Esta pose passa hoje e tem de
    # continuar a passar.
    frame, event = _read("PINKY")
    assert frame.raw_gesture is Gesture.PINKY, (
        f"raw={frame.raw_gesture.name} (esperado PINKY): com o polegar "
        f"recolhido sobre a palma o gesto tem de continuar a ser PINKY"
    )
    assert event == "copy", (
        f"evento={event!r} (esperado 'copy'): o PINKY tem de continuar a "
        f"disparar Ctrl+C"
    )
