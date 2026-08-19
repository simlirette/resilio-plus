"""Seam between an approved week and whatever writes it to a calendar.

Kept separate so the messaging layer never imports a calendar provider
directly: the transport only needs "is a pusher configured, and if so, call
it". When no pusher is configured the approval still resolves and the athlete
is told plainly that nothing was written.
"""
from __future__ import annotations

import logging
import os

from .approval_service import CalendarPusher

logger = logging.getLogger(__name__)


def calendar_enabled() -> bool:
    """True when calendar writes are switched on for this deployment."""
    return os.getenv("GOOGLE_CALENDAR_ENABLED", "true").lower() in ("1", "true", "yes")


def get_calendar_pusher() -> CalendarPusher | None:
    """Return the configured calendar push callable, or None when unavailable.

    Returns None rather than raising when the integration is switched off, so
    an approval still resolves and the athlete is told plainly that nothing was
    written.
    """
    if not calendar_enabled():
        return None
    from ..integrations.google_calendar.calendar_sync_service import (
        push_week_for_athlete,
    )

    return push_week_for_athlete
