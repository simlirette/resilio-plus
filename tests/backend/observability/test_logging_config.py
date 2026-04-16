import json
import logging

from app.observability.correlation import correlation_id_ctx, athlete_id_ctx
from app.observability.logging_config import JSONFormatter, configure_logging


def _format_record(record: logging.LogRecord) -> dict:
    return json.loads(JSONFormatter().format(record))


def _make_record(msg: str, level: int = logging.INFO, extra: dict | None = None) -> logging.LogRecord:
    record = logging.LogRecord(
        name="app.test", level=level, pathname=__file__,
        lineno=1, msg=msg, args=None, exc_info=None,
    )
    if extra:
        for k, v in extra.items():
            setattr(record, k, v)
    return record


def test_json_formatter_shape():
    rec = _make_record("hello world")
    out = _format_record(rec)
    assert out["msg"] == "hello world"
    assert out["level"] == "info"
    assert out["logger"] == "app.test"
    assert "ts" in out
    assert out["correlation_id"] == "-"  # default


def test_json_formatter_extra_merged():
    rec = _make_record("event", extra={"athlete_id": "a1", "duration_ms": 42})
    out = _format_record(rec)
    assert out["athlete_id"] == "a1"
    assert out["duration_ms"] == 42


def test_json_formatter_reads_correlation_id_from_contextvar():
    token = correlation_id_ctx.set("corr-42")
    try:
        rec = _make_record("event")
        out = _format_record(rec)
        assert out["correlation_id"] == "corr-42"
    finally:
        correlation_id_ctx.reset(token)


def test_json_formatter_reads_athlete_id_from_contextvar():
    token = athlete_id_ctx.set("athlete-77")
    try:
        rec = _make_record("event")
        out = _format_record(rec)
        assert out["athlete_id"] == "athlete-77"
    finally:
        athlete_id_ctx.reset(token)


def test_json_formatter_serializes_exception():
    try:
        raise ValueError("boom")
    except ValueError:
        import sys
        rec = logging.LogRecord(
            name="app.test", level=logging.ERROR, pathname=__file__,
            lineno=1, msg="failed", args=None, exc_info=sys.exc_info(),
        )
    out = _format_record(rec)
    assert out["error"]["type"] == "ValueError"
    assert out["error"]["message"] == "boom"
    assert "stack" in out["error"]


def test_configure_logging_attaches_pii_filter(caplog, monkeypatch):
    import app.observability.logging_config as _lc
    # Reset the guard so configure_logging() re-runs (it may have been called
    # at module import time by main.py's top-level _configure_logging() call).
    monkeypatch.setattr(_lc, "_CONFIGURED", False)
    configure_logging()
    logger = logging.getLogger("app.test.configure")
    logger.info("user a@b.com logged in")
    # The root logger filter should have scrubbed the email
    # caplog captures the raw message text post-filter
    assert all("a@b.com" not in rec.getMessage() for rec in caplog.records)
