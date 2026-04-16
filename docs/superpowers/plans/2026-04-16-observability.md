# V3-U Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add minimal V1 observability (structured JSON logging, correlation IDs, in-memory metrics, conditional Sentry) to the Resilio+ FastAPI backend without touching `backend/app/deployment/` or `Dockerfile`.

**Architecture:** New `backend/app/observability/` module hosting PII filter, logging config, ContextVars + middleware, metrics singleton, Sentry init. Wired at the top of `backend/app/main.py`. `/admin/metrics` endpoint reuses V3-S `_require_admin` dep. Root-logger JSON formatter transparently uniformizes every existing `logging.getLogger(__name__)` call.

**Tech Stack:** Python 3.13, FastAPI, Starlette's `BaseHTTPMiddleware`, Python `logging` with `dictConfig`, `contextvars.ContextVar`, `sentry-sdk` (optional runtime dep), pytest + `caplog` + FastAPI `TestClient`.

**Spec:** `docs/superpowers/specs/2026-04-16-observability-design.md`

**Invariants to re-check after every task:**
- `poetry install` succeeds (only relevant after Task 14 adds `sentry-sdk`)
- `pytest tests/` passes (target: 2310 → 2349 passing at end; 2 pre-existing unrelated failures unchanged)
- No new `logging.basicConfig()` calls added anywhere (root config handled by `configure_logging()`)

**Pytest path (Windows):** `C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe` — referenced as `pytest` in commands below; Windows users substitute full path or activate the venv.

---

## File Structure

**New files:**
- `backend/app/observability/__init__.py` — package re-exports
- `backend/app/observability/pii_filter.py` — blocklist + regex scrubbing (`logging.Filter`)
- `backend/app/observability/logging_config.py` — `JSONFormatter` + `configure_logging()` via `dictConfig`
- `backend/app/observability/correlation.py` — `correlation_id_ctx`, `athlete_id_ctx`, `CorrelationIdMiddleware`
- `backend/app/observability/metrics.py` — `LatencySummary`, `Metrics`, `metrics` singleton, `MetricsMiddleware`, `track_agent_call`
- `backend/app/observability/sentry.py` — `init_sentry()` + `_sentry_pii_scrubber`
- `tests/backend/observability/__init__.py` — empty
- `tests/backend/observability/test_pii_filter.py`
- `tests/backend/observability/test_logging_config.py`
- `tests/backend/observability/test_correlation.py`
- `tests/backend/observability/test_metrics.py`
- `tests/backend/observability/test_admin_metrics.py`
- `tests/backend/observability/test_sentry.py`
- `docs/backend/OBSERVABILITY.md` — user-facing reference

**Modified files:**
- `backend/app/main.py` — add `configure_logging()`, `init_sentry()`, middleware stack
- `backend/app/routes/admin.py` — add `GET /admin/metrics`
- `backend/app/jobs/runner.py` — set `correlation_id_ctx`, emit structured logs, increment `metrics.inc_job`
- `backend/app/agents/head_coach.py` — wrap `build_week` + specialist call loop with `track_agent_call`
- `.env.example` — add Sentry vars
- `pyproject.toml` — add `sentry-sdk`

---

## Task 1: PII filter — field-name blocklist

**Files:**
- Create: `backend/app/observability/__init__.py`
- Create: `backend/app/observability/pii_filter.py`
- Create: `tests/backend/observability/__init__.py`
- Test: `tests/backend/observability/test_pii_filter.py`

- [ ] **Step 1: Create empty package init files**

```python
# backend/app/observability/__init__.py
"""Observability stack: logging, correlation, metrics, Sentry."""
```

```python
# tests/backend/observability/__init__.py
```

- [ ] **Step 2: Write the failing tests for field blocklist**

File: `tests/backend/observability/test_pii_filter.py`

```python
from app.observability.pii_filter import scrub_value

BLOCKLIST_FIELDS = [
    "password", "passwd", "token", "access_token", "refresh_token",
    "authorization", "auth", "api_key", "apikey", "secret",
    "fernet_key", "encryption_key", "smtp_password", "jwt", "bearer",
    "client_secret", "cookie",
]


def test_scrubs_flat_blocklisted_field():
    payload = {"password": "hunter2", "username": "alice"}
    result = scrub_value(payload)
    assert result["password"] == "***"
    assert result["username"] == "alice"


def test_scrubs_case_insensitive():
    payload = {"Password": "hunter2", "API_KEY": "abc", "Authorization": "xyz"}
    result = scrub_value(payload)
    assert result["Password"] == "***"
    assert result["API_KEY"] == "***"
    assert result["Authorization"] == "***"


def test_scrubs_nested_dict():
    payload = {"user": {"email": "a@b.com", "token": "secret"}}
    result = scrub_value(payload)
    assert result["user"]["token"] == "***"


def test_scrubs_list_of_dicts():
    payload = {"items": [{"password": "a"}, {"password": "b"}]}
    result = scrub_value(payload)
    assert result["items"][0]["password"] == "***"
    assert result["items"][1]["password"] == "***"


def test_preserves_legitimate_fields():
    payload = {"username": "alice", "athlete_id": "uuid-1", "path": "/api"}
    result = scrub_value(payload)
    assert result == payload


def test_all_blocklist_fields_scrubbed():
    for field in BLOCKLIST_FIELDS:
        payload = {field: "leak"}
        assert scrub_value(payload)[field] == "***", f"{field} not scrubbed"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/backend/observability/test_pii_filter.py -v`
Expected: all 6 FAIL with `ModuleNotFoundError: No module named 'app.observability.pii_filter'`.

- [ ] **Step 4: Implement `scrub_value` with field blocklist**

File: `backend/app/observability/pii_filter.py`

```python
"""PII filter — blocklist + regex scrubbers for logs and Sentry events."""
from __future__ import annotations

from typing import Any

_BLOCKLIST_FIELDS = frozenset({
    "password", "passwd", "token", "access_token", "refresh_token",
    "authorization", "auth", "api_key", "apikey", "secret",
    "fernet_key", "encryption_key", "smtp_password", "jwt", "bearer",
    "client_secret", "cookie",
})

_REDACTED = "***"
_MAX_DEPTH = 5


def _is_blocklisted(field_name: str) -> bool:
    return field_name.lower() in _BLOCKLIST_FIELDS


def scrub_value(value: Any, _depth: int = 0) -> Any:
    """Return a copy of value with PII scrubbed. Dicts/lists recursed up to depth 5."""
    if _depth >= _MAX_DEPTH:
        return value
    if isinstance(value, dict):
        return {
            k: (_REDACTED if _is_blocklisted(k) else scrub_value(v, _depth + 1))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [scrub_value(item, _depth + 1) for item in value]
    if isinstance(value, tuple):
        return tuple(scrub_value(item, _depth + 1) for item in value)
    return value
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/backend/observability/test_pii_filter.py -v`
Expected: 6 PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/observability/__init__.py backend/app/observability/pii_filter.py tests/backend/observability/__init__.py tests/backend/observability/test_pii_filter.py
git commit -m "feat(observability): add PII field-name blocklist scrubber"
```

---

## Task 2: PII filter — regex scrubbers for strings

**Files:**
- Modify: `backend/app/observability/pii_filter.py`
- Test: `tests/backend/observability/test_pii_filter.py` (append)

- [ ] **Step 1: Add failing tests for regex scrubbers**

Append to `tests/backend/observability/test_pii_filter.py`:

```python
from app.observability.pii_filter import scrub_string


def test_scrubs_jwt_in_string():
    s = "token is eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NSJ9.SflKxwRJSMeKKF2QT4"
    assert "eyJ" not in scrub_string(s)
    assert "***" in scrub_string(s)


def test_scrubs_bearer_token():
    s = "Authorization: Bearer abc123def456"
    assert "abc123def456" not in scrub_string(s)
    assert "***" in scrub_string(s)


def test_scrubs_email():
    s = "failed login for user alice@example.com"
    out = scrub_string(s)
    assert "alice@example.com" not in out
    assert "***" in out


def test_scrubs_long_hex_string():
    s = "fernet key: " + "a" * 32
    out = scrub_string(s)
    assert "a" * 32 not in out
    assert "***" in out


def test_preserves_short_hex():
    # short hex like "abc123" should NOT match
    s = "version abc123 deployed"
    assert scrub_string(s) == s


def test_scrub_value_applies_regex_to_string_values():
    payload = {"msg": "user a@b.com logged in"}
    result = scrub_value(payload)
    assert "a@b.com" not in result["msg"]


def test_scrub_idempotent():
    s = "user a@b.com token eyJabc.def.ghi"
    once = scrub_string(s)
    twice = scrub_string(once)
    assert once == twice
```

- [ ] **Step 2: Run tests — verify new ones fail**

Run: `pytest tests/backend/observability/test_pii_filter.py -v`
Expected: 7 new tests FAIL with `ImportError: cannot import name 'scrub_string'`.

- [ ] **Step 3: Add `scrub_string` and wire into `scrub_value`**

Replace entire `backend/app/observability/pii_filter.py`:

```python
"""PII filter — blocklist + regex scrubbers for logs and Sentry events."""
from __future__ import annotations

import re
from typing import Any

_BLOCKLIST_FIELDS = frozenset({
    "password", "passwd", "token", "access_token", "refresh_token",
    "authorization", "auth", "api_key", "apikey", "secret",
    "fernet_key", "encryption_key", "smtp_password", "jwt", "bearer",
    "client_secret", "cookie",
})

_REDACTED = "***"
_MAX_DEPTH = 5

# Order matters: more specific patterns first so they win.
_REGEX_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),   # JWT
    re.compile(r"[Bb]earer\s+[A-Za-z0-9_.-]+"),                          # Bearer tokens
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),                             # Email
    re.compile(r"[a-fA-F0-9]{32,}"),                                     # long hex (fernet, api keys)
)


def _is_blocklisted(field_name: str) -> bool:
    return field_name.lower() in _BLOCKLIST_FIELDS


def scrub_string(s: str) -> str:
    """Apply all regex scrubbers to a string."""
    out = s
    for pattern in _REGEX_PATTERNS:
        out = pattern.sub(_REDACTED, out)
    return out


def scrub_value(value: Any, _depth: int = 0) -> Any:
    """Return a copy of value with PII scrubbed. Dicts/lists recursed up to depth 5."""
    if _depth >= _MAX_DEPTH:
        return value
    if isinstance(value, dict):
        return {
            k: (_REDACTED if _is_blocklisted(k) else scrub_value(v, _depth + 1))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [scrub_value(item, _depth + 1) for item in value]
    if isinstance(value, tuple):
        return tuple(scrub_value(item, _depth + 1) for item in value)
    if isinstance(value, str):
        return scrub_string(value)
    return value
```

- [ ] **Step 4: Run tests — all pass**

Run: `pytest tests/backend/observability/test_pii_filter.py -v`
Expected: 13 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/observability/pii_filter.py tests/backend/observability/test_pii_filter.py
git commit -m "feat(observability): add regex scrubbers for JWT/Bearer/email/hex"
```

---

## Task 3: PIIFilter — logging.Filter integration

**Files:**
- Modify: `backend/app/observability/pii_filter.py`
- Test: `tests/backend/observability/test_pii_filter.py` (append)

- [ ] **Step 1: Add failing tests for `PIIFilter`**

Append to `tests/backend/observability/test_pii_filter.py`:

```python
import logging
from app.observability.pii_filter import PIIFilter


def _make_record(msg: str, extra: dict | None = None) -> logging.LogRecord:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=None,
        exc_info=None,
    )
    if extra:
        for k, v in extra.items():
            setattr(record, k, v)
    return record


def test_pii_filter_scrubs_msg():
    f = PIIFilter()
    record = _make_record("user a@b.com logged in")
    assert f.filter(record) is True
    assert "a@b.com" not in record.getMessage()


def test_pii_filter_scrubs_extra_dict():
    f = PIIFilter()
    record = _make_record("event", extra={"user": {"password": "secret"}})
    f.filter(record)
    assert record.user["password"] == "***"


def test_pii_filter_returns_true_always():
    f = PIIFilter()
    record = _make_record("hello")
    assert f.filter(record) is True
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `pytest tests/backend/observability/test_pii_filter.py -v -k PIIFilter`
Expected: 3 FAIL with `ImportError: cannot import name 'PIIFilter'`.

- [ ] **Step 3: Append `PIIFilter` class to `pii_filter.py`**

Append to `backend/app/observability/pii_filter.py`:

```python
import logging

_BUILTIN_LOGRECORD_ATTRS = frozenset({
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message", "asctime",
})


class PIIFilter(logging.Filter):
    """Scrub PII from LogRecord before formatter runs.

    Applies:
    - regex scrubbers on record.msg (if string)
    - field-name blocklist + regex on any custom attributes set via extra={...}
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = scrub_string(record.msg)
        for key in list(record.__dict__.keys()):
            if key in _BUILTIN_LOGRECORD_ATTRS:
                continue
            value = record.__dict__[key]
            if _is_blocklisted(key):
                record.__dict__[key] = _REDACTED
            else:
                record.__dict__[key] = scrub_value(value)
        return True
```

- [ ] **Step 4: Run tests — all pass**

Run: `pytest tests/backend/observability/test_pii_filter.py -v`
Expected: 16 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/observability/pii_filter.py tests/backend/observability/test_pii_filter.py
git commit -m "feat(observability): add PIIFilter logging.Filter wrapper"
```

---

## Task 4: ContextVars (correlation + athlete)

**Files:**
- Create: `backend/app/observability/correlation.py`
- Test: `tests/backend/observability/test_correlation.py`

- [ ] **Step 1: Write failing tests for ContextVars**

File: `tests/backend/observability/test_correlation.py`

```python
from app.observability.correlation import (
    correlation_id_ctx,
    athlete_id_ctx,
    get_correlation_id,
    get_athlete_id,
)


def test_correlation_id_default():
    assert get_correlation_id() == "-"


def test_correlation_id_set_and_get():
    token = correlation_id_ctx.set("abc-123")
    try:
        assert get_correlation_id() == "abc-123"
    finally:
        correlation_id_ctx.reset(token)
    assert get_correlation_id() == "-"


def test_athlete_id_default_none():
    assert get_athlete_id() is None


def test_athlete_id_set_and_get():
    token = athlete_id_ctx.set("uuid-xyz")
    try:
        assert get_athlete_id() == "uuid-xyz"
    finally:
        athlete_id_ctx.reset(token)
    assert get_athlete_id() is None
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `pytest tests/backend/observability/test_correlation.py -v`
Expected: 4 FAIL with `ModuleNotFoundError: No module named 'app.observability.correlation'`.

- [ ] **Step 3: Create correlation.py with ContextVars**

File: `backend/app/observability/correlation.py`

```python
"""Correlation ID + athlete ID ContextVars and middleware."""
from __future__ import annotations

from contextvars import ContextVar
from typing import Optional

correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="-")
athlete_id_ctx: ContextVar[Optional[str]] = ContextVar("athlete_id", default=None)


def get_correlation_id() -> str:
    return correlation_id_ctx.get()


def get_athlete_id() -> Optional[str]:
    return athlete_id_ctx.get()
```

- [ ] **Step 4: Run tests — all pass**

Run: `pytest tests/backend/observability/test_correlation.py -v`
Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/observability/correlation.py tests/backend/observability/test_correlation.py
git commit -m "feat(observability): add correlation_id and athlete_id ContextVars"
```

---

## Task 5: JSON formatter + `configure_logging()`

**Files:**
- Create: `backend/app/observability/logging_config.py`
- Test: `tests/backend/observability/test_logging_config.py`

- [ ] **Step 1: Write failing tests for JSONFormatter**

File: `tests/backend/observability/test_logging_config.py`

```python
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


def test_configure_logging_attaches_pii_filter(caplog):
    configure_logging()
    logger = logging.getLogger("app.test.configure")
    logger.info("user a@b.com logged in")
    # The root logger filter should have scrubbed the email
    # caplog captures the raw message text post-filter
    assert all("a@b.com" not in rec.getMessage() for rec in caplog.records)
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `pytest tests/backend/observability/test_logging_config.py -v`
Expected: 6 FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement JSONFormatter + configure_logging**

File: `backend/app/observability/logging_config.py`

```python
"""JSON formatter + root logger setup (call configure_logging() once at app startup)."""
from __future__ import annotations

import json
import logging
import traceback
from datetime import datetime, timezone
from logging.config import dictConfig
from typing import Any

from .correlation import get_athlete_id, get_correlation_id
from .pii_filter import PIIFilter

_STD_LOGRECORD_ATTRS = frozenset({
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message", "asctime",
})

_STACK_MAX = 4096


class JSONFormatter(logging.Formatter):
    """Format LogRecord as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        out: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "msg": record.getMessage(),
            "correlation_id": get_correlation_id(),
        }
        athlete_id = get_athlete_id()
        if athlete_id is not None:
            out["athlete_id"] = athlete_id

        # Merge extras (any attr not in standard LogRecord fields)
        for key, value in record.__dict__.items():
            if key in _STD_LOGRECORD_ATTRS or key.startswith("_"):
                continue
            if key in out:
                continue
            try:
                json.dumps(value)  # ensure JSON-serializable
                out[key] = value
            except (TypeError, ValueError):
                out[key] = repr(value)

        if record.exc_info:
            exc_type, exc_val, exc_tb = record.exc_info
            stack = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
            out["error"] = {
                "type": exc_type.__name__ if exc_type else "Unknown",
                "message": str(exc_val) if exc_val else "",
                "stack": stack[:_STACK_MAX],
            }

        return json.dumps(out, default=str)


_CONFIGURED = False


def configure_logging(level: str = "INFO") -> None:
    """Configure root logger with JSON formatter + PII filter.

    Safe to call multiple times — only configures once per process.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "pii": {"()": "app.observability.pii_filter.PIIFilter"},
        },
        "formatters": {
            "json": {"()": "app.observability.logging_config.JSONFormatter"},
        },
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",
                "formatter": "json",
            },
        },
        # Attach PII filter at ROOT LOGGER level (not handler) so it runs before
        # any handler processes the record — including pytest's caplog handler
        # and Sentry's logging integration.
        "root": {
            "level": level,
            "handlers": ["default"],
            "filters": ["pii"],
        },
        "loggers": {
            "uvicorn.access": {"level": "INFO", "handlers": ["default"], "propagate": False},
            "uvicorn.error":  {"level": "INFO", "handlers": ["default"], "propagate": False},
        },
    })
    _CONFIGURED = True
```

- [ ] **Step 4: Run tests — all pass**

Run: `pytest tests/backend/observability/test_logging_config.py -v`
Expected: 6 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/observability/logging_config.py tests/backend/observability/test_logging_config.py
git commit -m "feat(observability): JSON formatter + configure_logging()"
```

---

## Task 6: CorrelationIdMiddleware

**Files:**
- Modify: `backend/app/observability/correlation.py`
- Test: `tests/backend/observability/test_correlation.py` (append)

- [ ] **Step 1: Add failing tests for middleware**

Append to `tests/backend/observability/test_correlation.py`:

```python
import re
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.observability.correlation import (
    CorrelationIdMiddleware,
    correlation_id_ctx,
)


def _make_app():
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/ping")
    def ping():
        return {"cid": correlation_id_ctx.get()}

    return app


def test_middleware_generates_uuid_when_header_missing():
    client = TestClient(_make_app())
    response = client.get("/ping")
    cid = response.headers["X-Request-ID"]
    # UUID4 is 36 chars with hyphens
    assert re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", cid)
    assert response.json()["cid"] == cid


def test_middleware_echoes_valid_header():
    client = TestClient(_make_app())
    response = client.get("/ping", headers={"X-Request-ID": "my-trace-id-42"})
    assert response.headers["X-Request-ID"] == "my-trace-id-42"
    assert response.json()["cid"] == "my-trace-id-42"


def test_middleware_regenerates_invalid_header():
    client = TestClient(_make_app())
    response = client.get("/ping", headers={"X-Request-ID": "bad id with spaces!@#"})
    cid = response.headers["X-Request-ID"]
    assert cid != "bad id with spaces!@#"
    assert re.match(r"^[0-9a-f-]+$", cid)


def test_middleware_regenerates_oversized_header():
    client = TestClient(_make_app())
    response = client.get("/ping", headers={"X-Request-ID": "x" * 200})
    cid = response.headers["X-Request-ID"]
    assert cid != "x" * 200


def test_middleware_resets_contextvar_between_requests():
    client = TestClient(_make_app())
    r1 = client.get("/ping", headers={"X-Request-ID": "first"})
    r2 = client.get("/ping")
    assert r1.headers["X-Request-ID"] == "first"
    assert r2.headers["X-Request-ID"] != "first"
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `pytest tests/backend/observability/test_correlation.py -v -k middleware`
Expected: 5 FAIL with `ImportError: cannot import name 'CorrelationIdMiddleware'`.

- [ ] **Step 3: Add middleware to correlation.py**

Replace `backend/app/observability/correlation.py` entirely:

```python
"""Correlation ID + athlete ID ContextVars and middleware."""
from __future__ import annotations

import re
import uuid
from contextvars import ContextVar
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="-")
athlete_id_ctx: ContextVar[Optional[str]] = ContextVar("athlete_id", default=None)

_VALID_CID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_HEADER = "X-Request-ID"


def get_correlation_id() -> str:
    return correlation_id_ctx.get()


def get_athlete_id() -> Optional[str]:
    return athlete_id_ctx.get()


def _coerce_cid(incoming: str | None) -> str:
    if incoming and _VALID_CID.match(incoming):
        return incoming
    return str(uuid.uuid4())


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Reads/generates X-Request-ID, sets ContextVar, echoes header back on response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        cid = _coerce_cid(request.headers.get(_HEADER))
        token = correlation_id_ctx.set(cid)
        try:
            response = await call_next(request)
        finally:
            correlation_id_ctx.reset(token)
        response.headers[_HEADER] = cid
        return response
```

- [ ] **Step 4: Run tests — all pass**

Run: `pytest tests/backend/observability/test_correlation.py -v`
Expected: 9 PASS (4 existing + 5 new).

- [ ] **Step 5: Commit**

```bash
git add backend/app/observability/correlation.py tests/backend/observability/test_correlation.py
git commit -m "feat(observability): CorrelationIdMiddleware reads/echoes X-Request-ID"
```

---

## Task 7: LatencySummary class

**Files:**
- Create: `backend/app/observability/metrics.py`
- Test: `tests/backend/observability/test_metrics.py`

- [ ] **Step 1: Write failing tests for LatencySummary**

File: `tests/backend/observability/test_metrics.py`

```python
from app.observability.metrics import LatencySummary


def test_latency_observe_increments_count_and_sum():
    s = LatencySummary()
    s.observe(10.0)
    s.observe(20.0)
    assert s.count == 2
    assert s.sum_ms == 30.0


def test_latency_mean():
    s = LatencySummary()
    s.observe(10.0)
    s.observe(20.0)
    s.observe(30.0)
    assert s.mean() == 20.0


def test_latency_mean_zero_samples():
    s = LatencySummary()
    assert s.mean() == 0.0


def test_latency_percentiles():
    s = LatencySummary()
    for v in range(1, 101):
        s.observe(float(v))
    assert s.percentile(50) == 50.0
    assert s.percentile(95) == 95.0
    assert s.percentile(99) == 99.0


def test_latency_percentile_empty():
    s = LatencySummary()
    assert s.percentile(50) == 0.0


def test_latency_deque_maxlen_enforced():
    s = LatencySummary(maxlen=5)
    for v in range(10):
        s.observe(float(v))
    assert s.count == 10              # counter not bounded
    assert len(s._samples) == 5       # deque bounded


def test_latency_snapshot_shape():
    s = LatencySummary()
    s.observe(5.0)
    snap = s.snapshot()
    assert set(snap.keys()) == {"count", "mean", "p50", "p95", "p99"}
    assert snap["count"] == 1
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `pytest tests/backend/observability/test_metrics.py -v`
Expected: 7 FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement LatencySummary**

File: `backend/app/observability/metrics.py`

```python
"""In-memory metrics: counters + latency summaries."""
from __future__ import annotations

import collections
import math
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any


class LatencySummary:
    """Bounded-memory latency collector. Stores up to maxlen samples for percentiles."""

    def __init__(self, maxlen: int = 1000) -> None:
        self.count: int = 0
        self.sum_ms: float = 0.0
        self._samples: collections.deque[float] = collections.deque(maxlen=maxlen)

    def observe(self, ms: float) -> None:
        self.count += 1
        self.sum_ms += ms
        self._samples.append(ms)

    def mean(self) -> float:
        if self.count == 0:
            return 0.0
        return self.sum_ms / self.count

    def percentile(self, p: float) -> float:
        if not self._samples:
            return 0.0
        sorted_samples = sorted(self._samples)
        # Nearest-rank method
        k = max(0, min(len(sorted_samples) - 1, int(math.ceil(p / 100.0 * len(sorted_samples))) - 1))
        return sorted_samples[k]

    def snapshot(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "mean": round(self.mean(), 3),
            "p50": round(self.percentile(50), 3),
            "p95": round(self.percentile(95), 3),
            "p99": round(self.percentile(99), 3),
        }
```

- [ ] **Step 4: Run tests — all pass**

Run: `pytest tests/backend/observability/test_metrics.py -v`
Expected: 7 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/observability/metrics.py tests/backend/observability/test_metrics.py
git commit -m "feat(observability): LatencySummary bounded-memory percentile collector"
```

---

## Task 8: Metrics singleton + counters

**Files:**
- Modify: `backend/app/observability/metrics.py` (append)
- Test: `tests/backend/observability/test_metrics.py` (append)

- [ ] **Step 1: Add failing tests for Metrics singleton**

Append to `tests/backend/observability/test_metrics.py`:

```python
import pytest
from app.observability.metrics import Metrics


def test_metrics_inc_http():
    m = Metrics()
    m.inc_http("GET", "/athletes/{id}", 200, 12.5)
    m.inc_http("GET", "/athletes/{id}", 200, 18.0)
    assert m.http_requests_total[("GET", "/athletes/{id}", 200)] == 2
    assert m.http_latency_ms[("GET", "/athletes/{id}")].count == 2


def test_metrics_inc_agent():
    m = Metrics()
    m.inc_agent("running_coach", "ok", 320.0)
    m.inc_agent("running_coach", "error", 15.0)
    assert m.agent_calls_total[("running_coach", "ok")] == 1
    assert m.agent_calls_total[("running_coach", "error")] == 1
    assert m.agent_latency_ms["running_coach"].count == 2


def test_metrics_inc_job():
    m = Metrics()
    m.inc_job("strava_sync", "ok")
    m.inc_job("strava_sync", "ok")
    m.inc_job("strava_sync", "timeout")
    assert m.jobs_total[("strava_sync", "ok")] == 2
    assert m.jobs_total[("strava_sync", "timeout")] == 1


def test_metrics_snapshot_shape():
    m = Metrics()
    m.inc_http("GET", "/foo", 200, 10.0)
    m.inc_agent("head_coach", "ok", 100.0)
    m.inc_job("daily_snapshot", "ok")
    snap = m.snapshot()
    assert "started_at" in snap
    assert snap["uptime_s"] >= 0
    assert snap["http"]["requests_total"]["GET /foo:200"] == 1
    assert "GET /foo" in snap["http"]["latency_ms"]
    assert snap["agents"]["calls_total"]["head_coach:ok"] == 1
    assert snap["jobs"]["runs_total"]["daily_snapshot:ok"] == 1


def test_metrics_thread_safety():
    import threading
    m = Metrics()

    def worker():
        for _ in range(1000):
            m.inc_http("GET", "/x", 200, 1.0)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert m.http_requests_total[("GET", "/x", 200)] == 4000
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `pytest tests/backend/observability/test_metrics.py -v -k Metrics`
Expected: 5 FAIL with `ImportError: cannot import name 'Metrics'`.

- [ ] **Step 3: Append Metrics class and singleton**

Append to `backend/app/observability/metrics.py`:

```python
class Metrics:
    """Thread-safe in-memory counters + latency summaries."""

    def __init__(self) -> None:
        self.started_at: datetime = datetime.now(timezone.utc)
        self.http_requests_total: dict[tuple[str, str, int], int] = collections.defaultdict(int)
        self.http_latency_ms: dict[tuple[str, str], LatencySummary] = collections.defaultdict(LatencySummary)
        self.agent_calls_total: dict[tuple[str, str], int] = collections.defaultdict(int)
        self.agent_latency_ms: dict[str, LatencySummary] = collections.defaultdict(LatencySummary)
        self.jobs_total: dict[tuple[str, str], int] = collections.defaultdict(int)
        self._lock: threading.Lock = threading.Lock()

    def inc_http(self, method: str, path: str, status: int, duration_ms: float) -> None:
        with self._lock:
            self.http_requests_total[(method, path, status)] += 1
            self.http_latency_ms[(method, path)].observe(duration_ms)

    def inc_agent(self, agent: str, status: str, duration_ms: float) -> None:
        with self._lock:
            self.agent_calls_total[(agent, status)] += 1
            self.agent_latency_ms[agent].observe(duration_ms)

    def inc_job(self, job_type: str, status: str) -> None:
        with self._lock:
            self.jobs_total[(job_type, status)] += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            uptime = (datetime.now(timezone.utc) - self.started_at).total_seconds()
            return {
                "started_at": self.started_at.isoformat().replace("+00:00", "Z"),
                "uptime_s": round(uptime, 1),
                "http": {
                    "requests_total": {
                        f"{m} {p}:{s}": n for (m, p, s), n in self.http_requests_total.items()
                    },
                    "latency_ms": {
                        f"{m} {p}": summary.snapshot()
                        for (m, p), summary in self.http_latency_ms.items()
                    },
                },
                "agents": {
                    "calls_total": {
                        f"{a}:{s}": n for (a, s), n in self.agent_calls_total.items()
                    },
                    "latency_ms": {
                        a: summary.snapshot()
                        for a, summary in self.agent_latency_ms.items()
                    },
                },
                "jobs": {
                    "runs_total": {
                        f"{jt}:{s}": n for (jt, s), n in self.jobs_total.items()
                    },
                },
            }


# Module-level singleton
metrics = Metrics()
```

- [ ] **Step 4: Run tests — all pass**

Run: `pytest tests/backend/observability/test_metrics.py -v`
Expected: 12 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/observability/metrics.py tests/backend/observability/test_metrics.py
git commit -m "feat(observability): Metrics singleton with thread-safe counters + snapshot"
```

---

## Task 9: MetricsMiddleware + track_agent_call

**Files:**
- Modify: `backend/app/observability/metrics.py` (append)
- Test: `tests/backend/observability/test_metrics.py` (append)

- [ ] **Step 1: Add failing tests for MetricsMiddleware and track_agent_call**

Append to `tests/backend/observability/test_metrics.py`:

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.observability.metrics import (
    MetricsMiddleware,
    track_agent_call,
    metrics,
)


def _reset_metrics():
    metrics.http_requests_total.clear()
    metrics.http_latency_ms.clear()
    metrics.agent_calls_total.clear()
    metrics.agent_latency_ms.clear()
    metrics.jobs_total.clear()


def test_middleware_increments_http_counter():
    _reset_metrics()
    app = FastAPI()
    app.add_middleware(MetricsMiddleware)

    @app.get("/foo")
    def foo():
        return {"ok": True}

    client = TestClient(app)
    client.get("/foo")
    client.get("/foo")
    assert metrics.http_requests_total[("GET", "/foo", 200)] == 2


def test_middleware_uses_path_template_not_raw():
    _reset_metrics()
    app = FastAPI()
    app.add_middleware(MetricsMiddleware)

    @app.get("/athletes/{athlete_id}")
    def get_athlete(athlete_id: str):
        return {"id": athlete_id}

    client = TestClient(app)
    client.get("/athletes/abc-123")
    client.get("/athletes/def-456")
    # Both hits should collapse to the template
    assert metrics.http_requests_total[("GET", "/athletes/{athlete_id}", 200)] == 2


def test_middleware_captures_status_code():
    _reset_metrics()
    app = FastAPI()
    app.add_middleware(MetricsMiddleware)

    @app.get("/bad")
    def bad():
        from fastapi import HTTPException
        raise HTTPException(status_code=404)

    client = TestClient(app)
    client.get("/bad")
    assert metrics.http_requests_total[("GET", "/bad", 404)] == 1


def test_track_agent_call_ok():
    _reset_metrics()
    with track_agent_call("running_coach"):
        pass
    assert metrics.agent_calls_total[("running_coach", "ok")] == 1
    assert metrics.agent_latency_ms["running_coach"].count == 1


def test_track_agent_call_error_reraises_and_records_error():
    _reset_metrics()
    with pytest.raises(ValueError):
        with track_agent_call("lifting_coach"):
            raise ValueError("boom")
    assert metrics.agent_calls_total[("lifting_coach", "error")] == 1
    assert metrics.agent_latency_ms["lifting_coach"].count == 1
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `pytest tests/backend/observability/test_metrics.py -v -k "middleware or track_agent"`
Expected: 5 FAIL with `ImportError`.

- [ ] **Step 3: Append MetricsMiddleware and track_agent_call**

Append to `backend/app/observability/metrics.py`:

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Record HTTP request count + latency per (method, path_template, status)."""

    async def dispatch(self, request: Request, call_next) -> Response:
        t0 = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            duration_ms = (time.perf_counter() - t0) * 1000
            # Prefer the parameterized route template; fall back to raw path
            route = request.scope.get("route")
            path = route.path if route is not None and hasattr(route, "path") else request.url.path
            metrics.inc_http(request.method, path, status, duration_ms)


@contextmanager
def track_agent_call(agent_name: str):
    """Context manager: time an agent call, record ok/error status."""
    t0 = time.perf_counter()
    status = "ok"
    try:
        yield
    except Exception:
        status = "error"
        raise
    finally:
        ms = (time.perf_counter() - t0) * 1000
        metrics.inc_agent(agent_name, status, ms)
```

- [ ] **Step 4: Run tests — all pass**

Run: `pytest tests/backend/observability/test_metrics.py -v`
Expected: 17 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/observability/metrics.py tests/backend/observability/test_metrics.py
git commit -m "feat(observability): MetricsMiddleware + track_agent_call context manager"
```

---

## Task 10: Sentry module + before_send scrubber

**Files:**
- Create: `backend/app/observability/sentry.py`
- Test: `tests/backend/observability/test_sentry.py`

- [ ] **Step 1: Write failing tests**

File: `tests/backend/observability/test_sentry.py`

```python
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
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `pytest tests/backend/observability/test_sentry.py -v`
Expected: 5 FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement sentry.py**

File: `backend/app/observability/sentry.py`

```python
"""Conditional Sentry initialization — no-op if SENTRY_DSN unset or sentry-sdk missing."""
from __future__ import annotations

import logging
import os
from typing import Any

from .correlation import get_correlation_id
from .pii_filter import scrub_value

logger = logging.getLogger("app.observability.sentry")


def _sentry_pii_scrubber(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    """Scrub PII from Sentry event payloads before send."""
    # Top-level scrubbing of sensitive keys
    event = scrub_value(event)  # type: ignore[assignment]
    # Tag with correlation ID
    event.setdefault("tags", {})
    if isinstance(event["tags"], dict):
        event["tags"]["correlation_id"] = get_correlation_id()
    return event


def init_sentry() -> None:
    """Initialize Sentry SDK if SENTRY_DSN env var is set AND sentry-sdk installed."""
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        logger.info("sentry_disabled_no_dsn")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
    except (ImportError, TypeError):
        # TypeError covers the case where sys.modules["sentry_sdk"] = None
        logger.warning("sentry_sdk_not_installed")
        return

    sentry_sdk.init(
        dsn=dsn,
        environment=os.getenv("SENTRY_ENVIRONMENT", "development"),
        release=os.getenv("SENTRY_RELEASE") or None,
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.0")),
        send_default_pii=False,
        before_send=_sentry_pii_scrubber,
        integrations=[
            FastApiIntegration(),
            StarletteIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
    )
    logger.info("sentry_initialized")
```

- [ ] **Step 4: Run tests — all pass**

Run: `pytest tests/backend/observability/test_sentry.py -v`
Expected: 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/observability/sentry.py tests/backend/observability/test_sentry.py
git commit -m "feat(observability): conditional Sentry init with PII scrubber"
```

---

## Task 11: `/admin/metrics` endpoint

**Files:**
- Modify: `backend/app/routes/admin.py`
- Test: `tests/backend/observability/test_admin_metrics.py`

- [ ] **Step 1: Write failing tests**

File: `tests/backend/observability/test_admin_metrics.py`

```python
import os
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_current_athlete_id


def _override_athlete(athlete_id: str):
    def _dep() -> str:
        return athlete_id
    return _dep


def test_admin_metrics_requires_auth():
    # No override, no auth header
    client = TestClient(app)
    response = client.get("/admin/metrics")
    # Either 401 (missing token) or 403 (wrong athlete) is acceptable
    assert response.status_code in (401, 403)


def test_admin_metrics_forbidden_for_non_admin():
    app.dependency_overrides[get_current_athlete_id] = _override_athlete("not-admin-uuid")
    try:
        with patch.dict(os.environ, {"ADMIN_ATHLETE_ID": "admin-uuid-1"}):
            client = TestClient(app)
            response = client.get("/admin/metrics")
            assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_athlete_id, None)


def test_admin_metrics_ok_for_admin():
    app.dependency_overrides[get_current_athlete_id] = _override_athlete("admin-uuid-1")
    try:
        with patch.dict(os.environ, {"ADMIN_ATHLETE_ID": "admin-uuid-1"}):
            client = TestClient(app)
            response = client.get("/admin/metrics")
            assert response.status_code == 200
            body = response.json()
            assert "started_at" in body
            assert "uptime_s" in body
            assert "http" in body
            assert "agents" in body
            assert "jobs" in body
    finally:
        app.dependency_overrides.pop(get_current_athlete_id, None)


def test_admin_metrics_response_increments_http_counter():
    app.dependency_overrides[get_current_athlete_id] = _override_athlete("admin-uuid-1")
    try:
        with patch.dict(os.environ, {"ADMIN_ATHLETE_ID": "admin-uuid-1"}):
            client = TestClient(app)
            r1 = client.get("/admin/metrics")
            body1 = r1.json()
            r2 = client.get("/admin/metrics")
            body2 = r2.json()
            key = "GET /admin/metrics:200"
            assert body2["http"]["requests_total"][key] >= body1["http"]["requests_total"].get(key, 0) + 1
    finally:
        app.dependency_overrides.pop(get_current_athlete_id, None)
```

- [ ] **Step 2: Run tests — expect fail**

Run: `pytest tests/backend/observability/test_admin_metrics.py -v`
Expected: 4 FAIL with 404 on `/admin/metrics`.

Note: this test requires Task 13 (wire `MetricsMiddleware` into `main.py`) to get the counter assertion working. The first three tests (auth) will pass after Task 11 alone. Keep test 4 in this file but expect it to pass only after Task 13.

- [ ] **Step 3: Add `GET /admin/metrics` route**

Modify `backend/app/routes/admin.py` — add after the existing `list_jobs` function:

```python
from ..observability.metrics import metrics as _metrics_singleton


@router.get("/metrics")
def get_metrics(
    _: Annotated[str, Depends(_require_admin)],
) -> dict:
    """In-memory observability metrics snapshot (HTTP, agents, jobs)."""
    return _metrics_singleton.snapshot()
```

- [ ] **Step 4: Run 3-of-4 tests — pass**

Run: `pytest tests/backend/observability/test_admin_metrics.py::test_admin_metrics_requires_auth tests/backend/observability/test_admin_metrics.py::test_admin_metrics_forbidden_for_non_admin tests/backend/observability/test_admin_metrics.py::test_admin_metrics_ok_for_admin -v`
Expected: 3 PASS. (The 4th test — counter increment — will pass after Task 13 wires `MetricsMiddleware`.)

- [ ] **Step 5: Commit**

```bash
git add backend/app/routes/admin.py tests/backend/observability/test_admin_metrics.py
git commit -m "feat(observability): GET /admin/metrics snapshot endpoint"
```

---

## Task 12: Wire into `main.py` — logging, Sentry, middleware

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Read current `main.py`**

Current `backend/app/main.py` has this imports block (top), CORSMiddleware registration, and `include_router` calls. You need to prepend logging/Sentry init and add two middlewares.

- [ ] **Step 2: Rewrite `backend/app/main.py`**

Replace `backend/app/main.py` entirely:

```python
# Observability MUST be configured before anything else imports logging
from .observability.logging_config import configure_logging as _configure_logging
_configure_logging()

from .observability.sentry import init_sentry as _init_sentry
_init_sentry()

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .jobs.scheduler import setup_scheduler
from .observability.correlation import CorrelationIdMiddleware
from .observability.metrics import MetricsMiddleware
from .routes.auth import router as auth_router
from .routes.onboarding import router as onboarding_router
from .routes.athletes import router as athletes_router
from .routes.connectors import router as connectors_router
from .routes.plans import router as plans_router
from .routes.reviews import router as reviews_router
from .routes.nutrition import router as nutrition_router
from .routes.recovery import router as recovery_router
from .routes.sessions import router as sessions_router
from .routes.analytics import router as analytics_router
from .routes.food_search import router as food_search_router
from .routes.workflow import router as workflow_router
from .routes.mode import router as mode_router
from .routes.checkin import router as checkin_router
from .routes.external_plan import router as external_plan_router
from .routes.strain import router as strain_router
from .routes.integrations import router as integrations_router
from .routes.strava import router as strava_router
from .routes.admin import router as admin_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = setup_scheduler()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Resilio Plus API", version="0.1.0", lifespan=lifespan)

_raw = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:4000,http://localhost:8081,http://localhost:19000",
)
_ALLOWED_ORIGINS = [o.strip() for o in _raw.split(",") if o.strip()]

# Middleware stack — FastAPI applies in reverse registration order.
# Desired runtime flow on a request: CORS → CorrelationId → Metrics → handler.
# So add CORS first (outermost), then CorrelationId, then Metrics last (innermost).
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(MetricsMiddleware)

app.include_router(auth_router)
app.include_router(onboarding_router)   # MUST be before athletes_router
app.include_router(athletes_router)
app.include_router(connectors_router)
app.include_router(plans_router)
app.include_router(reviews_router)
app.include_router(nutrition_router)
app.include_router(recovery_router)
app.include_router(sessions_router)
app.include_router(analytics_router)
app.include_router(food_search_router)
app.include_router(workflow_router)
app.include_router(mode_router)
app.include_router(checkin_router)
app.include_router(external_plan_router)
app.include_router(strain_router)
app.include_router(integrations_router)
app.include_router(strava_router)
app.include_router(admin_router)
```

- [ ] **Step 3: Run all observability tests**

Run: `pytest tests/backend/observability/ -v`
Expected: 42 PASS (includes the 4th admin_metrics test — counter increment now works).

- [ ] **Step 4: Run full test suite to verify no regression**

Run: `pytest tests/ -q`
Expected: ≥2352 passing (2310 + ~42 new). 2 pre-existing unrelated failures unchanged.

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py
git commit -m "feat(observability): wire logging + Sentry + middleware into main.py"
```

---

## Task 13: Instrument `run_job()` with correlation + metrics

**Files:**
- Modify: `backend/app/jobs/runner.py`
- Test: `tests/backend/jobs/` — existing tests must still pass; add `test_runner_observability.py`

- [ ] **Step 1: Add failing test for observability integration**

File: `tests/backend/jobs/test_runner_observability.py`

```python
"""Verify run_job() sets correlation ID, emits structured logs, increments metric."""
import logging
import pytest
from unittest.mock import MagicMock
from app.jobs.runner import run_job
from app.observability.metrics import metrics
from app.observability.correlation import correlation_id_ctx


def _reset_metrics():
    metrics.jobs_total.clear()


def test_run_job_sets_correlation_id():
    _reset_metrics()
    captured = {}

    def fn():
        captured["cid"] = correlation_id_ctx.get()

    mock_db = MagicMock()
    run_job(job_id="test_job", job_type="test", athlete_id=None, fn=fn, db=mock_db, timeout_s=5)
    assert captured["cid"].startswith("job-")


def test_run_job_increments_metric_on_success():
    _reset_metrics()
    mock_db = MagicMock()
    run_job(job_id="test_job", job_type="test_type", athlete_id=None, fn=lambda: None, db=mock_db, timeout_s=5)
    assert metrics.jobs_total[("test_type", "ok")] == 1


def test_run_job_increments_metric_on_error():
    _reset_metrics()

    def boom():
        raise ValueError("fail")

    mock_db = MagicMock()
    run_job(job_id="test_job", job_type="test_type", athlete_id=None, fn=boom, db=mock_db, timeout_s=5)
    assert metrics.jobs_total[("test_type", "error")] == 1


def test_run_job_logs_job_start_and_end(caplog):
    _reset_metrics()
    caplog.set_level(logging.INFO, logger="resilio.jobs")
    mock_db = MagicMock()
    run_job(job_id="jx", job_type="jt", athlete_id=None, fn=lambda: None, db=mock_db, timeout_s=5)
    messages = [r.getMessage() for r in caplog.records if r.name == "resilio.jobs"]
    assert any("job_start" in m for m in messages)
    assert any("job_end" in m for m in messages)
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `pytest tests/backend/jobs/test_runner_observability.py -v`
Expected: 4 FAIL (current `run_job` does neither correlation nor metric nor `resilio.jobs` log).

- [ ] **Step 3: Rewrite `runner.py` to instrument**

Replace `backend/app/jobs/runner.py`:

```python
"""Job execution wrapper — logs every run to job_runs table + observability."""
from __future__ import annotations

import contextvars
import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy.orm import Session

from ..observability.correlation import correlation_id_ctx
from ..observability.metrics import metrics
from .models import JobRunModel

logger = logging.getLogger("resilio.jobs")

_MAX_ERROR_LEN = 2000


def run_job(
    *,
    job_id: str,
    job_type: str,
    athlete_id: str | None,
    fn: Callable[[], Any],
    db: Session,
    timeout_s: int | float = 60,
) -> None:
    """Execute fn() with timeout, log result to job_runs AND observability."""
    started_at = datetime.now(timezone.utc)
    cid = f"job-{uuid.uuid4()}"
    token = correlation_id_ctx.set(cid)

    try:
        logger.info(
            "job_start",
            extra={"job_id": job_id, "job_type": job_type, "athlete_id": athlete_id},
        )

        status = "ok"
        error_message: str | None = None
        exception_holder: list = []

        def _target():
            try:
                fn()
            except Exception as exc:
                exception_holder.append(exc)

        # Worker thread must inherit ContextVars (correlation_id) — use copy_context
        ctx = contextvars.copy_context()
        thread = threading.Thread(target=lambda: ctx.run(_target), daemon=True)
        thread.start()
        thread.join(timeout=timeout_s)

        if thread.is_alive():
            status = "timeout"
            error_message = f"Job timed out after {timeout_s}s"
            logger.warning(
                "job_timeout",
                extra={"job_id": job_id, "job_type": job_type, "timeout_s": timeout_s},
            )
        elif exception_holder:
            status = "error"
            error_message = str(exception_holder[0])[:_MAX_ERROR_LEN]
            logger.warning(
                "job_failed",
                extra={
                    "job_id": job_id,
                    "job_type": job_type,
                    "error_message": error_message,
                },
            )

        elapsed_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)

        metrics.inc_job(job_type, status)

        logger.info(
            "job_end",
            extra={
                "job_id": job_id,
                "job_type": job_type,
                "status": status,
                "duration_ms": elapsed_ms,
            },
        )

        run = JobRunModel(
            id=str(uuid.uuid4()),
            job_id=job_id,
            athlete_id=athlete_id,
            job_type=job_type,
            status=status,
            started_at=started_at,
            duration_ms=elapsed_ms,
            error_message=error_message,
        )
        try:
            db.add(run)
            db.commit()
        except Exception:
            logger.exception("persist_job_run_failed", extra={"job_id": job_id})
            try:
                db.rollback()
            except Exception:
                pass
    finally:
        correlation_id_ctx.reset(token)
```

- [ ] **Step 4: Run new + existing runner tests**

Run: `pytest tests/backend/jobs/ -v`
Expected: all existing tests pass (runner behaviour preserved) + 4 new observability tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/jobs/runner.py tests/backend/jobs/test_runner_observability.py
git commit -m "feat(observability): instrument run_job with correlation_id + structured logs + metrics"
```

---

## Task 14: Instrument head coach + specialist agents

**Files:**
- Modify: `backend/app/agents/head_coach.py`

- [ ] **Step 1: Inspect current `build_week` to locate exact wrap points**

Read `backend/app/agents/head_coach.py`. The function `build_week(context, load_history)` starts at line ~35. At line ~55, specialists are invoked in a list comprehension:
```python
recommendations: list[AgentRecommendation] = [
    a.analyze(context) for a in self.agents
]
```

Two wrap points:
- Entire `build_week` body → `with track_agent_call("head_coach"):`
- The specialist call `a.analyze(context)` → `with track_agent_call(f"{a.name}_coach"): a.analyze(...)`

- [ ] **Step 2: Write failing integration test**

File: `tests/backend/observability/test_agent_instrumentation.py`

```python
"""Verify HeadCoach.build_week + specialist calls are tracked in metrics."""
from datetime import date

from app.agents.base import AgentContext, AgentRecommendation, BaseAgent
from app.agents.head_coach import HeadCoach
from app.observability.metrics import metrics
from app.schemas.athlete import AthleteProfile, Sport
from app.schemas.fatigue import FatigueScore


class _FakeRunningAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "running"

    def analyze(self, context):
        return AgentRecommendation(
            agent_name="running",
            fatigue_score=FatigueScore(
                local_muscular=10.0, cns_load=5.0, metabolic_cost=5.0,
                recovery_hours=1.0, affected_muscles=["quads"],
            ),
            weekly_load=100.0,
            suggested_sessions=[],
        )


def _minimal_profile() -> AthleteProfile:
    # Schema fields mirror tests/backend/agents/test_running_coach.py _athlete() helper
    return AthleteProfile(
        name="Test",
        age=30,
        sex="M",
        weight_kg=70.0,
        height_cm=175.0,
        sports=[Sport.RUNNING],
        primary_sport=Sport.RUNNING,
        goals=["finish 5K"],
        target_race_date=date(2026, 10, 15),
        available_days=[0, 2, 4],
        hours_per_week=5.0,
    )


def _reset():
    metrics.agent_calls_total.clear()
    metrics.agent_latency_ms.clear()


def test_head_coach_build_week_tracks_head_coach_metric():
    _reset()
    agents = [_FakeRunningAgent()]
    hc = HeadCoach(agents=agents)
    ctx = AgentContext(
        athlete=_minimal_profile(),
        date_range=(date(2026, 4, 14), date(2026, 4, 20)),
        phase="BASE",
    )
    try:
        hc.build_week(ctx, load_history=[])
    except Exception:
        # Even if downstream fails, the head_coach call should have been tracked
        pass
    assert metrics.agent_calls_total[("head_coach", "ok")] + metrics.agent_calls_total[("head_coach", "error")] == 1


def test_head_coach_build_week_tracks_specialist_metric():
    _reset()
    agents = [_FakeRunningAgent()]
    hc = HeadCoach(agents=agents)
    ctx = AgentContext(
        athlete=_minimal_profile(),
        date_range=(date(2026, 4, 14), date(2026, 4, 20)),
        phase="BASE",
    )
    try:
        hc.build_week(ctx, load_history=[])
    except Exception:
        pass
    assert metrics.agent_calls_total[("running_coach", "ok")] == 1
```

- [ ] **Step 3: Run test — verify it fails**

Run: `pytest tests/backend/observability/test_agent_instrumentation.py -v`
Expected: 2 FAIL — metric keys absent.

Note: `_minimal_profile()` fields are aligned with `tests/backend/agents/test_running_coach.py::_athlete()` — if `AthleteProfile` schema has drifted, update both places.

- [ ] **Step 4: Wrap `build_week` and the specialist call (minimal diff)**

**Do NOT rewrite the whole method.** Apply only these three edits to `backend/app/agents/head_coach.py`:

**Edit A — add import** (near the other imports at the top):

```python
from ..observability.metrics import track_agent_call
```

**Edit B — wrap entire `build_week` body with `track_agent_call("head_coach")`.**

Find the line that currently reads:
```python
    def build_week(
        self,
        context: AgentContext,
        load_history: list[float],
    ) -> WeeklyPlan:
```

Directly after the docstring (before the first real statement, which is `budgets = analyze_goals(context.athlete)`), insert:
```python
        with track_agent_call("head_coach"):
```

Then indent every existing line in the method body by +4 spaces (Python editors can do this via select-all-in-method → Tab). The final `return` statement at the end of the method moves inside the `with` block.

**Edit C — replace the specialist list comprehension with a tracked for-loop.**

Find:
```python
        recommendations: list[AgentRecommendation] = [
            a.analyze(context) for a in self.agents
        ]
```
(after Edit B, this is now indented one level deeper.)

Replace it with:
```python
        recommendations: list[AgentRecommendation] = []
        for a in self.agents:
            with track_agent_call(f"{a.name}_coach"):
                recommendations.append(a.analyze(context))
```
(keeping the additional 4-space indent from Edit B.)

**No other lines change.** The ACWR, conflict detection, plan assembly, and `return WeeklyPlan(...)` logic stays exactly as-is, just shifted one indent level deeper from Edit B.

- [ ] **Step 5: Run agent tests + existing head coach tests**

Run: `pytest tests/backend/observability/test_agent_instrumentation.py tests/backend/ -k "head_coach or agent" -v`
Expected: 2 new tests PASS + existing head_coach tests still PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/agents/head_coach.py tests/backend/observability/test_agent_instrumentation.py
git commit -m "feat(observability): track_agent_call on HeadCoach.build_week + specialist calls"
```

---

## Task 15: Docs, `.env.example`, `pyproject.toml`

**Files:**
- Create: `docs/backend/OBSERVABILITY.md`
- Modify: `.env.example`
- Modify: `pyproject.toml`

- [ ] **Step 1: Add `sentry-sdk` to pyproject.toml**

Edit `pyproject.toml` — in the `dependencies` list, append after `"anthropic>=0.25,<1.0",`:

```toml
    "sentry-sdk[fastapi]>=2.0,<3.0",
```

- [ ] **Step 2: Update lock + install**

Run:
```bash
poetry lock --no-update
poetry install
```
Expected: sentry-sdk + dependencies installed.

- [ ] **Step 3: Update `.env.example`**

Append to `.env.example`:

```
# Observability — Sentry (optional; leave empty to disable)
SENTRY_DSN=
SENTRY_ENVIRONMENT=development
SENTRY_RELEASE=
SENTRY_TRACES_SAMPLE_RATE=0.0
```

- [ ] **Step 4: Create `docs/backend/OBSERVABILITY.md`**

File: `docs/backend/OBSERVABILITY.md`

```markdown
# Observability

Resilio+ emits structured JSON logs, per-request correlation IDs, in-memory runtime metrics, and optional Sentry error events.

## Log Format

Every log line is a single-line JSON object:

\`\`\`json
{
  "ts": "2026-04-16T12:34:56.789Z",
  "level": "info",
  "logger": "app.routes.plans",
  "msg": "plan_created",
  "correlation_id": "a1b2c3d4-...",
  "athlete_id": "uuid-...",
  "path": "/plans",
  "status": 201,
  "duration_ms": 123
}
\`\`\`

Fields:

| Field | When present | Source |
|---|---|---|
| `ts` | always | ISO 8601 UTC |
| `level` | always | `info` / `warning` / `error` / etc. |
| `logger` | always | Python logger name |
| `msg` | always | short snake_case event name preferred |
| `correlation_id` | always (`"-"` if unset) | `correlation_id_ctx` ContextVar |
| `athlete_id` | when request authenticated | `athlete_id_ctx` ContextVar |
| `error.type`, `error.message`, `error.stack` | on exceptions | `exc_info` |
| custom extra fields | when logger called with `extra={...}` | merged verbatim (after PII filter) |

## Correlation IDs

- HTTP requests: `CorrelationIdMiddleware` reads `X-Request-ID` header or generates a UUID4. The value is set on `correlation_id_ctx` for the request duration and echoed back in the response `X-Request-ID` header.
- Background jobs: `run_job()` sets `job-<uuid4>` as the correlation ID; the worker thread inherits it via `contextvars.copy_context()`.

To trace a request end-to-end in logs:

\`\`\`bash
curl -H "X-Request-ID: my-trace-id" http://localhost:8000/plans
# then search logs for "my-trace-id"
\`\`\`

## Metrics (`GET /admin/metrics`)

Protected by `ADMIN_ATHLETE_ID` (same gate as `/admin/jobs`). Returns:

\`\`\`json
{
  "started_at": "2026-04-16T00:00:00Z",
  "uptime_s": 3600,
  "http": {
    "requests_total": {"GET /athletes/{id}:200": 45, "POST /plans:201": 3},
    "latency_ms": {
      "GET /athletes/{id}": {"count": 45, "mean": 12.3, "p50": 9.0, "p95": 28.0, "p99": 55.0}
    }
  },
  "agents": {
    "calls_total": {"head_coach:ok": 12, "running_coach:error": 1},
    "latency_ms": {"head_coach": {"count": 12, "mean": 450.0, "p50": 410.0, "p95": 820.0, "p99": 1100.0}}
  },
  "jobs": {
    "runs_total": {"strava_sync:ok": 24, "hevy_sync:timeout": 1}
  }
}
\`\`\`

Counters reset on app restart. Latency summaries store the last 1000 samples per key (bounded memory).

Example:

\`\`\`bash
curl -H "Authorization: Bearer $JWT" http://localhost:8000/admin/metrics | jq
\`\`\`

## PII Filter

Attached to root logger + Sentry `before_send`. Scrubs automatically:

**Field-name blocklist (case-insensitive):**
\`password, passwd, token, access_token, refresh_token, authorization, auth, api_key, apikey, secret, fernet_key, encryption_key, smtp_password, jwt, bearer, client_secret, cookie\`

**Regex patterns (scrubbed in `msg` strings and string values):**
- JWT: `eyJ[...].[...].[...]`
- Bearer tokens: `Bearer <token>`
- Email addresses
- Long hex strings (≥32 chars, e.g., Fernet keys, API keys)

To add a new blocklisted field, edit `_BLOCKLIST_FIELDS` in `backend/app/observability/pii_filter.py` and add a regression test in `tests/backend/observability/test_pii_filter.py`.

## Sentry (optional)

Disabled by default. To enable, set `SENTRY_DSN` in `.env`. All Sentry events run through the same PII scrubber as logs. `send_default_pii=False` as defense in depth.

Env vars:

| Var | Default | Purpose |
|---|---|---|
| `SENTRY_DSN` | empty | Sentry project DSN; empty = disabled |
| `SENTRY_ENVIRONMENT` | `development` | e.g., `production`, `staging` |
| `SENTRY_RELEASE` | unset | version/git SHA for release tracking |
| `SENTRY_TRACES_SAMPLE_RATE` | `0.0` | performance traces sampling rate (0.0–1.0) |

## Cheat Sheet

**Add a metric counter for a new code path:**
\`\`\`python
from app.observability.metrics import metrics
metrics.inc_agent("my_new_agent", "ok", duration_ms)
\`\`\`

**Log a structured event:**
\`\`\`python
import logging
logger = logging.getLogger(__name__)
logger.info("thing_happened", extra={"thing_id": "123", "count": 5})
\`\`\`

**Trace a request:**
1. Frontend/client sets `X-Request-ID: <your-id>` header.
2. Backend echoes it back on the response.
3. Search logs for `"correlation_id": "<your-id>"`.

## Architecture

- Module: `backend/app/observability/`
- Middleware stack (outer → inner): `CORSMiddleware` → `CorrelationIdMiddleware` → `MetricsMiddleware` → handler
- `configure_logging()` called at the top of `backend/app/main.py` before any router imports
- `init_sentry()` called after `configure_logging()`; no-op if `SENTRY_DSN` unset or `sentry-sdk` not installed
```

(The file above uses `\`\`\`` within this plan as an escape; when writing the real file, use normal triple backticks.)

- [ ] **Step 5: Run full test suite**

Run: `pytest tests/ -q`
Expected: ≥2352 PASS (2310 + ~42 new observability tests).

- [ ] **Step 6: Commit**

```bash
git add docs/backend/OBSERVABILITY.md .env.example pyproject.toml poetry.lock
git commit -m "docs(observability): add OBSERVABILITY.md + sentry-sdk dep + env vars"
```

---

## Summary: Files Touched

**New (13 files):**
- `backend/app/observability/__init__.py`
- `backend/app/observability/pii_filter.py`
- `backend/app/observability/logging_config.py`
- `backend/app/observability/correlation.py`
- `backend/app/observability/metrics.py`
- `backend/app/observability/sentry.py`
- `tests/backend/observability/__init__.py`
- `tests/backend/observability/test_pii_filter.py`
- `tests/backend/observability/test_logging_config.py`
- `tests/backend/observability/test_correlation.py`
- `tests/backend/observability/test_metrics.py`
- `tests/backend/observability/test_admin_metrics.py`
- `tests/backend/observability/test_sentry.py`
- `tests/backend/observability/test_agent_instrumentation.py`
- `tests/backend/jobs/test_runner_observability.py`
- `docs/backend/OBSERVABILITY.md`

**Modified (6 files):**
- `backend/app/main.py`
- `backend/app/routes/admin.py`
- `backend/app/jobs/runner.py`
- `backend/app/agents/head_coach.py`
- `.env.example`
- `pyproject.toml` (+ `poetry.lock`)

**No changes to:** `backend/app/deployment/`, `Dockerfile` (parallel session territory).

**Final invariants:**
- `poetry install` OK (sentry-sdk installed)
- `pytest tests/` ≥2352 passing; 2 pre-existing unrelated failures unchanged
- `GET /admin/metrics` returns schema-valid JSON for admin; 403 otherwise
- Every response has `X-Request-ID` header
- Setting `SENTRY_DSN=` empty → zero Sentry network calls
- `grep -R "password\|Bearer eyJ\|@" logs/` on a smoke-test dump → zero matches
