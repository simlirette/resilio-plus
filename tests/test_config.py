"""Tests pour core/config.py — Settings Pydantic v2."""

import pytest
from pydantic import ValidationError


def test_settings_load_with_defaults():
    """Settings se chargent avec les valeurs par défaut."""
    from core.config import Settings

    s = Settings(_env_file=None)
    assert s.APP_NAME == "Resilio+"
    assert s.DEBUG is False
    assert s.TESTING is False
    assert s.ANTHROPIC_MAX_TOKENS == 4096


def test_settings_reject_default_secret_key_in_production():
    """SECRET_KEY 'change-me-in-production' est rejeté quand DEBUG=False."""
    from core.config import Settings

    with pytest.raises(ValidationError, match="SECRET_KEY must be set in production"):
        Settings(
            DEBUG=False,
            SECRET_KEY="change-me-in-production",
            _env_file=None,
        )


def test_settings_allow_default_secret_key_in_debug_mode():
    """SECRET_KEY peut rester par défaut quand DEBUG=True."""
    from core.config import Settings

    s = Settings(DEBUG=True, SECRET_KEY="change-me-in-production", _env_file=None)
    assert s.SECRET_KEY == "change-me-in-production"


def test_settings_accept_valid_secret_key_in_production():
    """Une vraie SECRET_KEY est acceptée en production."""
    from core.config import Settings

    s = Settings(
        DEBUG=False,
        SECRET_KEY="a-real-secret-key-that-is-not-the-default",
        _env_file=None,
    )
    assert s.DEBUG is False
