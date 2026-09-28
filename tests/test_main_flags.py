"""--dev-pro removido. O teste usa um argv controlado (não o sys.argv do pytest)."""
import sys

import pytest

import main


def test_no_dev_pro_in_parse_args(monkeypatch):
    # controla argv para o argparse não ler os args reais do pytest
    monkeypatch.setattr(sys, "argv", ["airmouse", "--no-gui"])
    parser = main.parse_args()
    opts = set()
    for action in parser._actions:
        opts.update(action.option_strings)
    assert "--dev-pro" not in opts


def _options():
    opts = set()
    for action in main.parse_args()._actions:
        opts.update(action.option_strings)
    return opts


class TestOnda0Flags:
    def test_record_and_replay_exist(self):
        opts = _options()
        assert "--record" in opts
        assert "--replay" in opts

    def test_defaults_are_none(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["airmouse"])
        args = main.parse_args().parse_args()
        assert args.record is None
        assert args.replay is None

    def test_record_takes_a_path(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["airmouse", "--record", "data/s.npz"])
        assert main.parse_args().parse_args().record == "data/s.npz"

    def test_replay_takes_a_path(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["airmouse", "--replay", "data/s.npz"])
        assert main.parse_args().parse_args().replay == "data/s.npz"

    def test_record_and_replay_are_mutually_exclusive(self, monkeypatch):
        # Gravar e reproduzir ao mesmo tempo nao faz sentido: o replay tem de
        # correr sem camera, e o record sem rato.
        monkeypatch.setattr(
            sys, "argv", ["airmouse", "--record", "a.npz", "--replay", "b.npz"]
        )
        with pytest.raises(SystemExit):
            main.parse_args().parse_args()

    def test_record_max_frames_defaults_to_unlimited(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["airmouse"])
        assert main.parse_args().parse_args().record_max_frames == 0

    def test_replay_gate_is_opt_in(self, monkeypatch):
        # Imprimir o relatorio nao reprova. O portao e explicito, para que o
        # passo de CI que mostra os numeros nunca fique vermelho por um alvo que
        # ainda nao e atingido.
        monkeypatch.setattr(sys, "argv", ["airmouse", "--replay", "c.npz"])
        assert main.parse_args().parse_args().replay_gate is False
        monkeypatch.setattr(
            sys, "argv", ["airmouse", "--replay", "c.npz", "--replay-gate"]
        )
        assert main.parse_args().parse_args().replay_gate is True

    def test_replay_without_gate_returns_zero_on_a_failing_target(self, monkeypatch):
        import argparse

        class _Failing:
            passed = False

            def render(self):
                return "REJEITE"

        monkeypatch.setattr(
            "tools.eval_recognition.evaluate", lambda *a, **k: _Failing()
        )
        args = argparse.Namespace(
            replay="c.npz", frame_width=640, frame_height=480, replay_gate=False
        )
        assert main.run_replay(args) == 0
        args.replay_gate = True
        assert main.run_replay(args) == 1

    def test_replay_missing_corpus_returns_two(self, capsys):
        import argparse

        args = argparse.Namespace(
            replay="nao-existe.npz",
            frame_width=640,
            frame_height=480,
            replay_gate=False,
        )
        assert main.run_replay(args) == 2
        assert "corpus" in capsys.readouterr().out.lower()

