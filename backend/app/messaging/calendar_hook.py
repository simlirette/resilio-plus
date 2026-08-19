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

    V4-T5 (Google Calendar) supplies the implementation; until then every
    approval reports that no calendar is connected.
    """
    if not calendar_enabled():
        return None
    return None
