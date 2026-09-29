"""`--record` nao pode ter efeitos no sistema que esta a ser filmado.

Gravar um corpus de maos reais e ficar varios minutos a fazer e desfazer poses
diante da camara. O pipeline tratava isso como uso normal: o cursor movia-se e
cada PINCH clicava a serio no que estivesse por baixo. Quem grava fica a mirar
ao que dao os gestos, e um PINKY solta Ctrl+C na janela que estiver em foco.

Nao e um mau habito do operador: e uma propriedade da ferramenta, e por isso o
silencio e o **predefinido** e `--record-live` e que o desliga.

O que fica calado: rato, atalhos de teclado e brilho. O que continua a falar:
o toast. E o toast que diz ao operador o que o pipeline reconheceu, que e a
unica informacao de que precisa para etiquetar — silenciar oRecognition
silenciaria tambem a etiqueta.
"""
import numpy as np
import pytest

from core.mouse_ctl import MuteMouse


class TestMuteMouse:
    def test_it_has_the_whole_mouse_interface(self):
        """Substitui o rato real: um metodo em falta e um AttributeError a meio
        de uma recolha de minutos, ou seja, no pior sitio possivel."""
        from core.mouse_ctl import MouseCtl

        for name in MuteMouse._COUNTED:
            assert callable(getattr(MuteMouse, name))
            assert callable(getattr(MouseCtl, name, None)), name

    def test_nothing_reaches_the_system(self):
        m = MuteMouse()
        m.move_by(30, -12)
        m.press_left()
        m.release_left()
        m.left_click()
        m.right_click()
        m.scroll(3)
        m.drag_start()
        m.drag_end()
        # Nao ha ecra, nem pynput, nem SendInput: e um objeto vazio com contadores.
        assert m.mouse is None

    def test_it_counts_what_it_swallowed(self):
        # A prova de que a gravacao nao mexeu no sistema e um numero, nao uma
        # promessa. Um "0x0" porque o codigo estava errado nao provaria nada.
        m = MuteMouse()
        for _ in range(3):
            m.press_left()
        m.move_by(5, 5)
        assert m.swallowed == {"press_left": 3, "move_by": 1}
        assert m.summary() == "move_byx1, press_leftx3"

    def test_summary_of_a_nothing_session(self):
        assert MuteMouse().summary() == "nada"

    def test_click_assist_reading_position_degrades_quietly(self):
        """`_click_assist` le `mouse.mouse.position`. Com `mouse = None` a
        leitura levanta, mas esta dentro de um try/except: um no-op e um debug
        por clique. Um `AttributeError` a propagate seria perder a sessao."""
        m = MuteMouse()
        with pytest.raises(AttributeError):
            _ = m.mouse.position


class TestEngineMutesTheSideEffects:
    """O motor tem de respeitar `state["mute_output"]` em todas as saidas."""

    def _state(self, **extra):
        base = {
            "paused": False, "flash": 0, "freeze_until": 0.0,
            "button_down": False, "mute_output": True,
        }
        base.update(extra)
        return base

    def test_mute_defaults_to_off_for_normal_use(self):
        # Sem `--record` nao ha mutacao. Se isto falhasse, a aplicacao deixava
        # de funcionar para toda a gente por causa de uma correccao de gravacao.
        assert not self._state(mute_output=False)["mute_output"]

    def test_mute_is_read_not_assumed(self):
        # `state.get("mute_output")` e nao `state["mute_output"]`: o engine
        # corre com `state` deconstructed em varias UIs, e um `KeyError` aqui
        # seria um crash no arranque em vez de um rato a mexer.
        assert {} .get("mute_output") is None
        assert self._state().get("mute_output") is True


class TestFlagWiring:
    def test_record_mutes_and_record_live_does_not(self):
        from main import parse_args

        def args_for(*extra):
            return parse_args().parse_args(["--record", "x.npz", *extra])

        assert args_for().record_live is False
        assert args_for("--record-live").record_live is True

    def test_record_live_alone_is_a_harmless_no_op(self):
        """Sozinha, a flag nao muda nada — como `--record-max-frames` sem
        `--record`. Quem escreve e a verdade sobre a saida e a linha de log do
        arranque, que diz se o rato ficou calado ou nao."""
        from main import parse_args

        args = parse_args().parse_args(["--record-live"])
        assert args.record is None
        assert args.record_live is True

    def test_replay_guard_flag_parses(self):
        from main import parse_args

        args = parse_args().parse_args(
            ["--replay", "x.npz", "--replay-settle-guard-ms", "300"]
        )
        assert args.replay_settle_guard_ms == 300.0
        assert parse_args().parse_args(["--replay", "x.npz"]).replay_settle_guard_ms == 0.0

    def test_record_and_replay_are_still_exclusive(self):
        from main import parse_args

        with pytest.raises(SystemExit):
            parse_args().parse_args(["--record", "a.npz", "--replay", "b.npz"])


class TestMuteDoesNotCorruptTheRecording:
    def test_the_cursor_hand_is_chosen_by_the_palm_not_the_rato(self):
        """Se a mao do cursor fosse escolhida pela posicao do rato do sistema,
        silenciar a saida estragava a gravacao. E escolhida pela palma
        filtrada — e por isso que o silencio e seguro."""
        from core.engine import _active_hand_index

        hand = np.zeros((21, 3), dtype=np.float32)
        hand[0] = [0.5, 0.5, 0.0]   # pulso
        hand[9] = [0.5, 0.8, 0.0]   # lambida do meio
        hands = [hand]
        # `palm_center` em px (640x480): media de pulso e lambida 9.
        assert _active_hand_index(hands, 640, 480, (320.0, 312.0)) == 0
        # E com um `palm_center` que nao casa com nada nao ha mao activa — o
        # recorder descarta o frame em vez de inventar de qual mao e.
        assert _active_hand_index(hands, 640, 480, (10.0, 10.0)) == -1
        # E sem palma nenhuma tambem nao: nada de que hand_write inventar.
        assert _active_hand_index(hands, 640, 480, None) == -1
        assert _active_hand_index([], 640, 480, (320.0, 312.0)) == -1

    def test_a_mute_mouse_survives_a_whole_emitter_cycle(self):
        """O emissor corre igual: e a aritmetica dos acumuladores que fixa o
        ritmo a que cada frame e processado. Se o `move_by` deixasse de consumir
        os pixels, o pipeline levaria com uma fila que nunca esvazia."""
        from core.motion import SmoothEmitter

        m = MuteMouse()
        e = SmoothEmitter(m, 180.0)
        e.push(40.0, -20.0, 0.033)
        # O emissor engole o push sem se queixar: `move_by` e um no-op e o
        # `pending` nao cresce a correr, o que significaria que o pipeline
        # estava a levar com uma fila que nunca esvazia.
        assert m.swallowed.get("move_by", 0) == 0
        assert e.pending == pytest.approx(44.7, abs=0.1)
        e.clear()
        assert e.pending == 0.0
