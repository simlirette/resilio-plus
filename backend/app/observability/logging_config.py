"""JSON formatter + root logger setup (call configure_logging() once at app startup)."""
from __future__ import annotations

import json
import logging
import traceback
from datetime import datetime, timezone
from logging.config import dictConfig
from typing import Any

from .correlation import get_athlete_id, get_correlation_id

_STD_LOGRECORD_ATTRS = frozenset(
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

_STACK_MAX = 4096


class JSONFormatter(logging.Formatter):
    """Format LogRecord as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        out: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
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

    dictConfig(
        {
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
                "uvicorn.error": {"level": "INFO", "handlers": ["default"], "propagate": False},
            },
        }
    )
    _CONFIGURED = True
