"""Best-effort push to whatever channel the athlete is actually reachable on.

Used by code that is *not* handling an inbound message — OAuth callbacks,
background jobs — and therefore has no channel object in hand. Delivery is
best-effort by design: a connector callback must not 500 because Telegram is
misconfigured.
"""
from __future__ import annotations

import logging
import os
from collections.abc import Mapping

from sqlalchemy.orm import Session

from .base import Button, MessagingChannel
from .notification_service import NotificationService

logger = logging.getLogger(__name__)


def configured_channels() -> Mapping[str, MessagingChannel]:
    """Return the channels this deployment can send on, empty when none are."""
    if not os.getenv("TELEGRAM_BOT_TOKEN", "").strip():
        return {}
    try:
        from ..integrations.telegram.runtime import get_telegram_runtime

        runtime = get_telegram_runtime()
    except Exception:
        logger.warning("outbound_channel_unavailable", exc_info=True)
        return {}
    return {runtime.channel.name: runtime.channel}


def notify_athlete(
    db: Session,
    athlete_id: str,
    text: str,
    *,
    buttons: list[Button] | None = None,
    kind: str = "notification",
) -> bool:
    """Send ``text`` to the athlete. Returns whether it was delivered."""
    channels = configured_channels()
    if not channels:
        logger.info("outbound_no_channel_configured")
        return False
    try:
        NotificationService(db, channels).send(athlete_id, text, buttons, kind=kind)
    except Exception:
        logger.warning("outbound_delivery_failed", exc_info=True)
        return False
    return True
