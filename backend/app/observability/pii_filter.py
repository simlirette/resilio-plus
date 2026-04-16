"""PII filter — blocklist + regex scrubbers for logs and Sentry events."""
from __future__ import annotations

import re
from typing import Any

_BLOCKLIST_FIELDS = frozenset(
    {
        "password",
        "passwd",
        "token",
        "access_token",
        "refresh_token",
        "authorization",
        "auth",
        "api_key",
        "apikey",
        "secret",
        "fernet_key",
        "encryption_key",
        "smtp_password",
        "jwt",
        "bearer",
        "client_secret",
        "cookie",
    }
)

_REDACTED = "***"
_MAX_DEPTH = 5

# Order matters: more specific patterns first so they win.
_REGEX_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),  # JWT
    re.compile(r"[Bb]earer\s+[A-Za-z0-9_.-]+"),  # Bearer tokens
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),  # Email
    re.compile(r"[a-fA-F0-9]{32,}"),  # long hex (fernet, api keys)
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


import logging

_BUILTIN_LOGRECORD_ATTRS = frozenset(
    {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
        "asctime",
    }
)


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
