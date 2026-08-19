"""Slash commands the athlete can type instead of talking to the coach.

Everything here is deliberately mechanical — no LLM call, no graph — so the
athlete always has a way to connect a provider or see where they stand even if
the coaching layer is having a bad day.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..db.models import AthleteModel, ConnectorCredentialModel
from ..services.deep_link_service import issue_connector_links
from .base import Button

logger = logging.getLogger(__name__)

COMMAND_PREFIX = "/"

_PROVIDER_LABEL = {
    "strava": "Strava",
    "hevy": "Hevy",
    "terra": "Terra",
    "google": "Google Calendar",
}

_HELP = (
    "**What I understand**\n"
    "- `/connect` — links to connect Strava, Hevy and Terra\n"
    "- `/status` — what is connected and where you are in the journey\n"
    "- `/plan` — build next week now instead of waiting for Sunday\n"
    "- `/help` — this list\n"
    "\n"
    "Everything else is a normal conversation — just tell me what is going on."
)


class NotificationSender(Protocol):
    def send(
        self,
        athlete_id: str,
        text: str,
        buttons: list[Button] | None = None,
    ) -> object: ...


@dataclass(frozen=True, slots=True)
class CommandOutcome:
    handled: bool
    name: str | None = None
    text: str | None = None


def is_command(text: str) -> bool:
    return text.strip().startswith(COMMAND_PREFIX)


class CommandRouter:
    """Answer slash commands without involving the coaching graphs."""

    def __init__(
        self,
        db: Session,
        *,
        notifier: NotificationSender,
        weekly_cycle: Callable[[str, Session], None] | None = None,
    ) -> None:
        self._db = db
        self._notifier = notifier
        self._weekly_cycle = weekly_cycle

    def handle(self, athlete_id: str, text: str) -> CommandOutcome:
        """Handle ``text`` when it is a command; otherwise report unhandled."""
        stripped = text.strip()
        if not is_command(stripped):
            return CommandOutcome(handled=False)

        name = stripped[1:].split()[0].lower() if stripped[1:].split() else ""
        # Telegram sends "/help@resilio_bot" in groups.
        name = name.split("@", 1)[0]

        handler = {
            "start": self._start,
            "help": self._help,
            "connect": self._connect,
            "status": self._status,
            "plan": self._plan,
        }.get(name)

        if handler is None:
            return self._reply(
                name,
                f"I do not know `/{name}`. Try `/help`.",
                athlete_id,
            )
        return handler(athlete_id)

    # ─── Commands ────────────────────────────────────────────────────────────

    def _start(self, athlete_id: str) -> CommandOutcome:
        return self._reply(
            "start",
            "I am your Resilio head coach. Tell me about yourself and I will "
            "build your training from there. Use `/connect` whenever you want "
            "to hook up Strava, Hevy or your watch.",
            athlete_id,
        )

    def _help(self, athlete_id: str) -> CommandOutcome:
        return self._reply("help", _HELP, athlete_id)

    def _connect(self, athlete_id: str) -> CommandOutcome:
        try:
            links = issue_connector_links(self._db, athlete_id=athlete_id)
        except SQLAlchemyError:
            logger.warning("connect_links_failed", exc_info=True)
            return self._reply(
                "connect",
                "I could not mint connection links just now — try again shortly.",
                athlete_id,
            )

        lines = ["**Connect your data**", ""]
        for provider, url in links.items():
            label = _PROVIDER_LABEL.get(provider, provider)
            lines.append(f"- {label}: {url}")
        lines.append("")
        lines.append("Each link works once and expires in two hours.")
        return self._reply("connect", "\n".join(lines), athlete_id)

    def _status(self, athlete_id: str) -> CommandOutcome:
        athlete = self._db.get(AthleteModel, athlete_id)
        if athlete is None:
            return self._reply("status", "I have no profile for you yet.", athlete_id)

        connected = set(
            self._db.scalars(
                select(ConnectorCredentialModel.provider).where(
                    ConnectorCredentialModel.athlete_id == athlete_id
                )
            ).all()
        )
        if self._db.in_transaction():
            self._db.commit()

        rows = [f"- Journey phase: {athlete.journey_phase}"]
        for provider, label in _PROVIDER_LABEL.items():
            mark = "connected" if provider in connected else "not connected"
            rows.append(f"- {label}: {mark}")
        return self._reply("status", "**Where you stand**\n" + "\n".join(rows), athlete_id)

    def _plan(self, athlete_id: str) -> CommandOutcome:
        if self._weekly_cycle is None:
            return self._reply(
                "plan",
                "Weekly planning is not switched on for this deployment yet.",
                athlete_id,
            )
        self._notifier.send(athlete_id, "Building next week — one moment.")
        try:
            self._weekly_cycle(athlete_id, self._db)
        except Exception:
            logger.warning("manual_weekly_cycle_failed", exc_info=True)
            return self._reply(
                "plan",
                "I could not build the week just now. Try again in a few minutes.",
                athlete_id,
            )
        return CommandOutcome(handled=True, name="plan")

    # ─── Internals ───────────────────────────────────────────────────────────

    def _reply(self, name: str, text: str, athlete_id: str) -> CommandOutcome:
        self._notifier.send(athlete_id, text)
        return CommandOutcome(handled=True, name=name, text=text)
