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
from ..services.deep_link_service import SUPPORTED_PROVIDERS, connector_links_message
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
    "**Ce que je comprends**\n"
    "- `/connect` — liens pour connecter Strava, Hevy et Terra\n"
    "- `/status` — ce qui est connecté et où tu en es dans le parcours\n"
    "- `/plan` — construire la semaine maintenant sans attendre dimanche\n"
    "- `/help` — cette liste\n"
    "\n"
    "Le reste est une conversation normale — dis-moi simplement où tu en es."
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
        weekly_cycle: Callable[[str, Session], object] | None = None,
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
                f"Je ne connais pas `/{name}`. Essaie `/help`.",
                athlete_id,
            )
        return handler(athlete_id)

    # ─── Commands ────────────────────────────────────────────────────────────

    def _start(self, athlete_id: str) -> CommandOutcome:
        return self._reply(
            "start",
            "Je suis ton head coach Resilio. Parle-moi de toi et je construirai "
            "ton entraînement à partir de là. Utilise `/connect` quand tu veux "
            "brancher Strava, Hevy ou ta montre.",
            athlete_id,
        )

    def _help(self, athlete_id: str) -> CommandOutcome:
        return self._reply("help", _HELP, athlete_id)

    def _connect(self, athlete_id: str) -> CommandOutcome:
        try:
            # /connect always offers every provider — the athlete may want to
            # reconnect one that is already linked. The list comes from
            # SUPPORTED_PROVIDERS, not from _PROVIDER_LABEL: the labels also
            # name Terra so that an athlete who has it connected sees it in
            # /status, but nothing offers it any more.
            message = connector_links_message(
                self._db,
                athlete_id=athlete_id,
                providers=list(SUPPORTED_PROVIDERS),
            )
        except SQLAlchemyError:
            logger.warning("connect_links_failed", exc_info=True)
            return self._reply(
                "connect",
                "Je n'ai pas pu générer les liens de connexion — réessaie dans un instant.",
                athlete_id,
            )
        if message is None:
            return self._reply(
                "connect", "Tout est déjà connecté.", athlete_id
            )
        return self._reply("connect", message, athlete_id)

    def _status(self, athlete_id: str) -> CommandOutcome:
        athlete = self._db.get(AthleteModel, athlete_id)
        if athlete is None:
            return self._reply("status", "Je n'ai pas encore de profil pour toi.", athlete_id)

        connected = set(
            self._db.scalars(
                select(ConnectorCredentialModel.provider).where(
                    ConnectorCredentialModel.athlete_id == athlete_id
                )
            ).all()
        )
        if self._db.in_transaction():
            self._db.commit()

        rows = [f"- Phase du parcours : {athlete.journey_phase}"]
        for provider, label in _PROVIDER_LABEL.items():
            mark = "connecté" if provider in connected else "non connecté"
            rows.append(f"- {label}: {mark}")
        return self._reply("status", "**Où tu en es**\n" + "\n".join(rows), athlete_id)

    def _plan(self, athlete_id: str) -> CommandOutcome:
        if self._weekly_cycle is None:
            return self._reply(
                "plan",
                "La planification hebdomadaire n'est pas encore activée ici.",
                athlete_id,
            )
        self._notifier.send(athlete_id, "Je construis la semaine — un instant.")
        try:
            self._weekly_cycle(athlete_id, self._db)
        except Exception:
            logger.warning("manual_weekly_cycle_failed", exc_info=True)
            return self._reply(
                "plan",
                "Je n'ai pas pu construire la semaine. Réessaie dans quelques minutes.",
                athlete_id,
            )
        return CommandOutcome(handled=True, name="plan")

    # ─── Internals ───────────────────────────────────────────────────────────

    def _reply(self, name: str, text: str, athlete_id: str) -> CommandOutcome:
        self._notifier.send(athlete_id, text)
        return CommandOutcome(handled=True, name=name, text=text)
