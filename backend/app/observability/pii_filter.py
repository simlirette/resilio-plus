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
