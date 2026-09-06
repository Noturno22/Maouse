import json

import config


def test_defaults_consistent():
    cfg = config.Config()
    assert cfg.num_hands == 2
    assert cfg.pinch_on_ratio < cfg.pinch_off_ratio
    assert 0.0 <= cfg.move_gain
    assert cfg.gesture_stable_frames >= 1
    assert cfg.pinch_stable_frames >= 1


def test_guard_against_duplicate_num_hands():
    """Regressão: num_hands aparecia duas vezes (config.py:34 e :98)."""
    fields = [f for f in config.Config.__dataclass_fields__]
    assert fields.count("num_hands") == 1


def test_presets_reference_real_fields():
    for _name, cut, beta in config.SMOOTH_PRESETS:
        assert 0.4 <= cut <= 3.0
        assert 0.008 <= beta <= 0.08


def test_load_settings_clamps_gain(monkeypatch, tmp_path):
    monkeypatch.setattr(
        config, "SETTINGS_FILE", str(tmp_path / "settings.json")
    )
    (tmp_path / "settings.json").write_text(
        json.dumps({"move_gain": 999.0}), encoding="utf-8"
    )
    cfg = config.Config()
    idx = config.load_settings(cfg)
    assert cfg.move_gain == 999.0
    assert idx == -1 or idx == 1


def test_load_settings_bad_file_keeps_defaults(monkeypatch, tmp_path):
    monkeypatch.setattr(
        config, "SETTINGS_FILE", str(tmp_path / "missing.json")
    )
    cfg = config.Config()
    assert config.load_settings(cfg) == 1
    assert cfg.move_gain == 2.0


def test_save_settings_roundtrip(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(
        config, "SETTINGS_FILE", str(tmp_path / "settings.json")
    )
    cfg = config.Config()
    cfg.move_gain = 3.7
    config.save_settings(cfg, "NORMAL")
    assert (tmp_path / "settings.json").exists()
    loaded = json.loads(
        (tmp_path / "settings.json").read_text(encoding="utf-8")
    )
    assert loaded["move_gain"] == 3.7
    assert loaded["suavidade"] == "NORMAL"
    assert loaded["pinch_stable_frames"] >= 1


def test_suave_preset_persists(monkeypatch, tmp_path):
    monkeypatch.setattr(
        config, "SETTINGS_FILE", str(tmp_path / "settings.json")
    )
    (tmp_path / "settings.json").write_text(
        json.dumps({"suavidade": "SUAVE", "move_gain": 2.0}), encoding="utf-8"
    )
    cfg = config.Config()
    idx = config.load_settings(cfg)
    assert idx == 0
    assert cfg.filter_min_cutoff == 0.9
    assert cfg.filter_beta == 0.02


def test_voice_always_on_default_true():
    assert config.Config().voice_always_on is True


def test_stt_provider_default_auto():
    assert config.Config().stt_provider == "auto"
    assert config.Config().stt_model == "whisper-large-v3-turbo"
    assert config.Config().stt_base_url == "https://api.groq.com/openai/v1"
    assert config.Config().stt_api_key_env == "GROQ_API_KEY"


def test_save_load_voice_settings(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "SETTINGS_FILE", str(tmp_path / "settings.json"))
    cfg = config.Config()
    cfg.voice_always_on = False
    cfg.stt_provider = "local"
    config.save_settings(cfg, "NORMAL")
    cfg2 = config.Config()
    config.load_settings(cfg2)
    assert cfg2.voice_always_on is False
    assert cfg2.stt_provider == "local"


def test_voice_robustez_config_defaults():
    cfg = config.Config()
    assert cfg.mic_device == ""
    assert cfg.whisper_vad_filter is True
    assert cfg.whisper_beam_size == 3
    assert cfg.whisper_language == "pt"


def test_mic_device_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "SETTINGS_FILE", str(tmp_path / "settings.json"))
    cfg = config.Config()
    cfg.mic_device = "Microfone Realtek"
    config.save_settings(cfg, "NORMAL")
    cfg2 = config.Config()
    config.load_settings(cfg2)
    assert cfg2.mic_device == "Microfone Realtek"
