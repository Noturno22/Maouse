import i18n

LANGS = i18n.LANGS


def test_all_keys_translated_in_all_langs():
    langs = set(i18n.LANGS)
    for key, table in i18n._STRINGS.items():
        assert set(table) == langs, f"{key}: {set(table) ^ langs}"
        for lang in i18n.LANGS:
            val = table[lang]
            assert val and isinstance(val, str), f"{key}/{lang} vazio"


def test_all_keys_fallback_resolves():
    for key in i18n._STRINGS:
        t = i18n.tr(key)
        assert t and t != key


def test_license_block_strings_exist():
    for key in ("license.trial_remaining", "license.trial_ended",
                "license.trial_ended_sub", "license.activate_now",
                "license.revalidate_failed", "license.ledge_blocked",
                "license.has_key", "license.activate_key", "license.key_hint",
                "license.enter_key", "license.activate_failed",
                "license.needs_connection"):
        t = i18n.tr(key)
        assert t and t != key


def test_set_lang_all_codes():
    original = i18n.I18N.lang
    try:
        for lang in LANGS:
            if lang != original:
                assert i18n.I18N.set_lang(lang)
            assert i18n.I18N.lang == lang
            for key in i18n._STRINGS:
                assert i18n.tr(key), f"vazio em {lang}: {key}"
    finally:
        i18n.I18N.set_lang(original)


def test_invalid_lang_rejected():
    assert not i18n.I18N.set_lang("xx")
    assert not i18n.I18N.set_lang("")


def test_toggle_cycles_through_all_langs():
    original = i18n.I18N.lang
    try:
        seq = []
        for _ in LANGS:
            i18n.I18N.toggle()
            seq.append(i18n.I18N.lang)
        expected = list(LANGS[1:]) + [LANGS[0]]
        assert seq == expected
    finally:
        i18n.I18N.set_lang(original)


def test_voice_keys_exist_in_all_langs():
    keys = [
        "voice.prompt", "voice.not_heard", "voice.not_understood",
        "voice.status.preparing", "voice.status.ready",
        "voice.status.listening", "voice.status.thinking", "voice.status.on",
        "voice.backend.cloud", "voice.backend.local",
        "settings.voice.stt_provider", "settings.voice.direct_commands",
        "settings.voice.groq_key",
        "settings.voice.provider.auto", "settings.voice.provider.cloud",
        "settings.voice.provider.local",
    ]
    for key in keys:
        assert key in i18n._STRINGS, key
        for lang in i18n.LANGS:
            assert i18n._STRINGS[key][lang], f"{key}/{lang}"


def test_unknown_key_returns_key():
    assert i18n.tr("no.such.key") == "no.such.key"


def test_native_names_cover_all_langs():
    assert set(i18n.NATIVE) == set(LANGS)
    for code in LANGS:
        assert i18n.NATIVE[code]
        key = f"lang.{'br' if code == i18n.PT_BR else code}"
        assert key in i18n._STRINGS
