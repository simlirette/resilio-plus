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
