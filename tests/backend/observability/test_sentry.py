import logging
import os
from unittest.mock import patch, MagicMock

from app.observability.sentry import init_sentry, _sentry_pii_scrubber


def test_init_sentry_noop_without_dsn(caplog):
    with patch.dict(os.environ, {"SENTRY_DSN": ""}, clear=False):
        caplog.set_level(logging.INFO)
        init_sentry()
    assert any("sentry_disabled_no_dsn" in rec.getMessage() for rec in caplog.records)


def test_init_sentry_noop_on_importerror(caplog):
    """Simulate sentry-sdk not installed."""
    import sys
    saved = sys.modules.pop("sentry_sdk", None)
    # Make future `import sentry_sdk` raise ImportError
    sys.modules["sentry_sdk"] = None  # type: ignore[assignment]
    try:
        with patch.dict(os.environ, {"SENTRY_DSN": "https://x@y.ingest.sentry.io/1"}, clear=False):
            caplog.set_level(logging.WARNING)
            init_sentry()
        assert any("sentry_sdk_not_installed" in rec.getMessage() for rec in caplog.records)
    finally:
        if saved is not None:
            sys.modules["sentry_sdk"] = saved
        else:
            sys.modules.pop("sentry_sdk", None)


def test_before_send_scrubs_email_in_message():
    event = {"message": "user a@b.com failed login"}
    out = _sentry_pii_scrubber(event, hint={})
    assert "a@b.com" not in out["message"]


def test_before_send_scrubs_token_in_extra():
    event = {"extra": {"password": "hunter2", "user_id": "ok"}}
    out = _sentry_pii_scrubber(event, hint={})
    assert out["extra"]["password"] == "***"
    assert out["extra"]["user_id"] == "ok"


def test_before_send_scrubs_request_data():
    event = {"request": {"headers": {"Authorization": "Bearer abc.def.ghi"}}}
    out = _sentry_pii_scrubber(event, hint={})
    assert out["request"]["headers"]["Authorization"] == "***"
