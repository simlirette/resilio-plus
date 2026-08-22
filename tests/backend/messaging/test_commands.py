from __future__ import annotations

import json
import uuid
from typing import Any

import pytest
from app.db.models import ConnectorCredentialModel, DeepLinkTokenModel
from app.messaging.commands import CommandRouter, is_command
from sqlalchemy.orm import Session


class RecordingNotifier:
    def __init__(self) -> None:
        self.sent: list[str] = []

    def send(
        self, athlete_id: str, text: str, buttons: list[Any] | None = None
    ) -> object:
        self.sent.append(text)
        return ["provider-1"]

    @property
    def last(self) -> str:
        return self.sent[-1]


@pytest.fixture
def notifier() -> RecordingNotifier:
    return RecordingNotifier()


def build_router(
    db_session: Session,
    notifier: RecordingNotifier,
    weekly_cycle: Any = None,
) -> CommandRouter:
    return CommandRouter(db_session, notifier=notifier, weekly_cycle=weekly_cycle)


class TestDetection:
    @pytest.mark.parametrize("text", ["/help", "  /connect", "/status extra"])
    def test_slash_prefixed_text_is_a_command(self, text: str) -> None:
        assert is_command(text)

    @pytest.mark.parametrize("text", ["help", "what is my plan?", ""])
    def test_plain_text_is_not(self, text: str) -> None:
        assert not is_command(text)

    def test_plain_text_is_left_for_the_coach(
        self, db_session: Session, athlete_id: str, notifier: RecordingNotifier
    ) -> None:
        outcome = build_router(db_session, notifier).handle(athlete_id, "hello")

        assert outcome.handled is False
        assert notifier.sent == []


class TestHelp:
    def test_lists_every_command(
        self, db_session: Session, athlete_id: str, notifier: RecordingNotifier
    ) -> None:
        outcome = build_router(db_session, notifier).handle(athlete_id, "/help")

        assert outcome.handled is True
        for command in ("/connect", "/status", "/plan", "/help"):
            assert command in notifier.last

    def test_bot_suffix_is_tolerated(
        self, db_session: Session, athlete_id: str, notifier: RecordingNotifier
    ) -> None:
        outcome = build_router(db_session, notifier).handle(
            athlete_id, "/help@resilio_bot"
        )
        assert outcome.name == "help"

    def test_unknown_command_points_at_help(
        self, db_session: Session, athlete_id: str, notifier: RecordingNotifier
    ) -> None:
        outcome = build_router(db_session, notifier).handle(athlete_id, "/nope")

        assert outcome.handled is True
        assert "/help" in notifier.last


class TestConnect:
    def test_issues_one_link_per_provider(
        self,
        db_session: Session,
        athlete_id: str,
        notifier: RecordingNotifier,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("PUBLIC_BASE_URL", "https://coach.example.com")

        build_router(db_session, notifier).handle(athlete_id, "/connect")

        text = notifier.last
        assert text.count("https://coach.example.com/integrations/link/") == 3
        for label in ("Strava", "Hevy", "Google Calendar"):
            assert label in text

        db_session.expire_all()
        rows = db_session.query(DeepLinkTokenModel).all()
        assert {row.provider for row in rows} == {"strava", "hevy", "google"}
        assert all(row.athlete_id == athlete_id for row in rows)


class TestStatus:
    def test_reports_phase_and_connected_providers(
        self, db_session: Session, athlete_id: str, notifier: RecordingNotifier
    ) -> None:
        db_session.add(
            ConnectorCredentialModel(
                id=str(uuid.uuid4()),
                athlete_id=athlete_id,
                provider="strava",
                extra_json=json.dumps({}),
            )
        )
        db_session.commit()

        build_router(db_session, notifier).handle(athlete_id, "/status")

        text = notifier.last
        assert "signup" in text
        assert "Strava: connecté" in text
        assert "Hevy: non connecté" in text

    def test_unknown_athlete_is_reported(
        self, db_session: Session, notifier: RecordingNotifier
    ) -> None:
        build_router(db_session, notifier).handle("ghost", "/status")
        assert "pas encore de profil" in notifier.last


class TestPlan:
    def test_runs_the_weekly_cycle_when_wired(
        self, db_session: Session, athlete_id: str, notifier: RecordingNotifier
    ) -> None:
        calls: list[str] = []

        build_router(
            db_session, notifier, weekly_cycle=lambda aid, db: calls.append(aid)
        ).handle(athlete_id, "/plan")

        assert calls == [athlete_id]
        assert "un instant" in notifier.sent[0]

    def test_reports_when_not_wired(
        self, db_session: Session, athlete_id: str, notifier: RecordingNotifier
    ) -> None:
        outcome = build_router(db_session, notifier).handle(athlete_id, "/plan")

        assert outcome.handled is True
        assert "pas encore activée" in notifier.last

    def test_failure_is_reported_not_swallowed_silently(
        self, db_session: Session, athlete_id: str, notifier: RecordingNotifier
    ) -> None:
        def boom(athlete_id: str, db: Session) -> None:
            raise RuntimeError("provider down")

        build_router(db_session, notifier, weekly_cycle=boom).handle(
            athlete_id, "/plan"
        )

        assert "pas pu construire la semaine" in notifier.last
