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
    event = scrub_value(event)
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
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
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
