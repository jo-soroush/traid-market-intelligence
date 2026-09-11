from traid.config import SettingsError, load_settings


def test_defaults_are_deterministic() -> None:
    assert load_settings({}).environment == "development"
    assert load_settings({}).port == 8000


def test_invalid_port_fails_closed() -> None:
    try:
        load_settings({"TRAID_PORT": "not-a-port"})
    except SettingsError as exc:
        assert "TRAID_PORT" in str(exc)
    else:
        raise AssertionError("invalid configuration unexpectedly loaded")
