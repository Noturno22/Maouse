import pytest

from core import audio_devices as ad


def fake_query():
    return [
        {"name": "Microfone Realtek HD", "max_input_channels": 2},
        {"name": "Alto-falantes", "max_input_channels": 0},
    ]


def test_list_only_inputs():
    assert ad.list_input_devices(query=fake_query) == [(0, "Microfone Realtek HD")]


def test_list_empty_on_query_failure():
    def boom():
        raise Exception("no audio api")

    assert ad.list_input_devices(query=boom) == []


def test_select_by_name_substring():
    assert ad.select_device("realtek", query=fake_query) == 0
    assert ad.select_device("MICROFONE", query=fake_query) == 0


def test_select_by_index():
    assert ad.select_device("0", query=fake_query) == 0


def test_select_empty_means_default():
    assert ad.select_device("", query=fake_query) is None
    assert ad.select_device(None, query=fake_query) is None


def test_select_unknown_raises():
    with pytest.raises(ad.DeviceError):
        ad.select_device("webcam x", query=fake_query)

    with pytest.raises(ad.DeviceError):
        ad.select_device("9", query=fake_query)


def test_select_int_zero_means_device_zero():
    assert ad.select_device(0, query=fake_query) == 0


def test_list_ignores_malformed_entries():
    def q():
        return [
            {"name": "Mic A", "max_input_channels": 1},
            {"name": "Speaker", "max_input_channels": 0},
            {"name": "Weird", "max_input_channels": "2"},
            "not-a-dict",
        ]

    assert ad.list_input_devices(query=q) == [(0, "Mic A")]
