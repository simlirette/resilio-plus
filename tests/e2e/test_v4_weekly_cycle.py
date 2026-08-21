"""V4 acceptance, end to end: unprompted week → buttons → approve → calendar.

Everything below the transport is real — the approval store, the revision
latch, the calendar reconciler, the event bodies. Only the two outside worlds
are faked: the coaching graph (an LLM) and the Google API (a network).
"""
from __future__ import annotations

import uuid
from typing import Any

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session as SASession

from app.db import models as _models  # noqa: F401 — registers ORM models
from app.db.database import Base
from app.db.models import (
    AthleteModel,
    CalendarEventModel,
    GoogleCalendarCredentialModel,
    MessagingIdentityModel,
    PendingApprovalModel,
)
from app.integrations.google_calendar.calendar_sync_service import CalendarSyncService
from app.jobs.weekly_jobs import run_weekly_cycle_now
from app.messaging.approval_service import ApprovalService
from app.messaging.approvals import parse_callback
from app.messaging.base import Button
from app.messaging.gateway import MessagingGateway

ATHLETE_ID = "athlete-v4-e2e"
EXTERNAL_ID = "555000"
CALENDAR_ID = "cal-resilio"

WEEK_ONE = {
    "phase": "build",
    "acwr": {"ratio": 1.08, "status": "safe", "acute_7d": 400.0, "chronic_28d": 370.0,
             "max_safe_weekly_load": 481.0},
    "sessions": [
        {
            "id": "slot-mon",
            "date": "2031-06-02",
            "sport": "running",
            "workout_type": "easy",
            "duration_min": 45,
            "notes": "conversational",
        },
        {
            "id": "slot-wed",
            "date": "2031-06-04",
            "sport": "running",
            "workout_type": "intervals",
            "duration_min": 70,
            "notes": "6 x 800 m",
        },
    ],
    "notes": ["Volume flat, one quality session."],
}

WEEK_ONE_REVISED = {
    **WEEK_ONE,
    "sessions": [WEEK_ONE["sessions"][0]],  # type: ignore[index]
    "notes": ["Wednesday pulled — you asked for less volume."],
}


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    with SASession(engine) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


class Channel:
    """Stands in for Telegram; records exactly what the athlete would see."""

    name = "telegram"

    def __init__(self) -> None:
        self.messages: list[tuple[str, list[Button] | None]] = []

    def send(self, external_id: str, text: str) -> str:
        self.messages.append((text, None))
        return f"m{len(self.messages)}"

    def send_with_buttons(
        self, external_id: str, text: str, buttons: list[Button]
    ) -> str:
        self.messages.append((text, buttons))
        return f"m{len(self.messages)}"

    def max_message_length(self) -> int:
        return 4096

    def format(self, text: str) -> str:
        return text


class Notifier:
    def __init__(self, channel: Channel) -> None:
        self._channel = channel

    def send(
        self,
        athlete_id: str,
        text: str,
        buttons: list[Button] | None = None,
        *,
        kind: str = "notification",
    ) -> list[str]:
        if buttons:
            return [self._channel.send_with_buttons(EXTERNAL_ID, text, buttons)]
        return [self._channel.send(EXTERNAL_ID, text)]


class FakeGoogle:
    def __init__(self) -> None:
        self.events: dict[str, dict[str, Any]] = {}
        self.writes: list[str] = []
        self._next = 0

    def get_calendar(self, calendar_id: str) -> dict[str, Any]:
        return {"id": calendar_id}

    def create_calendar(self, summary: str, time_zone: str) -> dict[str, Any]:
        return {"id": CALENDAR_ID}

    def insert_event(self, calendar_id: str, body: Any) -> dict[str, Any]:
        self._next += 1
        event_id = f"evt-{self._next}"
        self.events[event_id] = dict(body)
        self.writes.append(f"insert:{event_id}")
        return {"id": event_id}

    def patch_event(self, calendar_id: str, event_id: str, body: Any) -> dict[str, Any]:
        self.events[event_id] = dict(body)
        self.writes.append(f"patch:{event_id}")
        return {"id": event_id}

    def delete_event(self, calendar_id: str, event_id: str) -> None:
        self.events.pop(event_id, None)
        self.writes.append(f"delete:{event_id}")


class FakeCoaching:
    """The plan graph: proposes week one, revises on feedback, finalises on yes."""

    def __init__(self) -> None:
        self.created: list[str] = []
        self.resumed: list[tuple[str, bool, str | None]] = []
        self.current: dict[str, Any] = WEEK_ONE

    def create_plan(
        self,
        athlete_id: str,
        athlete_dict: dict[str, Any],
        load_history: list[float],
        db: SASession,
    ) -> tuple[str, dict[str, Any] | None]:
        self.created.append(athlete_id)
        return "plan-thread", self.current

    def resume_plan(
        self,
        thread_id: str,
        approved: bool,
        feedback: str | None,
        db: SASession,
    ) -> dict[str, Any] | None:
        self.resumed.append((thread_id, approved, feedback))
        if approved:
            return {**self.current, "db_plan_id": "plan-db-1"}
        self.current = WEEK_ONE_REVISED
        return self.current


class Invoker:
    def __init__(self, coaching: FakeCoaching) -> None:
        self._coaching = coaching

    def invoke(
        self,
        graph_name: str,
        athlete_id: str,
        thread_id: str,
        payload: dict[str, Any],
        db: SASession,
    ) -> dict[str, Any] | None:
        assert graph_name == "plan_generation"
        plan_thread, plan = self._coaching.create_plan(athlete_id, {}, [], db)
        return {"plan_proposal": plan, "plan_thread_id": plan_thread}


@pytest.fixture
def athlete(db_session: SASession) -> str:
    db_session.add(
        AthleteModel(
            id=ATHLETE_ID,
            name="V4 Athlete",
            age=35,
            sex="M",
            weight_kg=74.0,
            height_cm=180.0,
            primary_sport="running",
            hours_per_week=7.0,
            sports_json='["running"]',
            goals_json="[]",
            available_days_json="[]",
            equipment_json="[]",
            journey_phase="steady_state",
            timezone="America/Montreal",
            preferred_session_hour_json='{"running": 7}',
        )
    )
    db_session.add(
        MessagingIdentityModel(
            id=str(uuid.uuid4()),
            athlete_id=ATHLETE_ID,
            channel="telegram",
            external_id=EXTERNAL_ID,
        )
    )
    db_session.add(
        GoogleCalendarCredentialModel(
            athlete_id=ATHLETE_ID,
            refresh_token_enc="encrypted",
            calendar_id=CALENDAR_ID,
        )
    )
    db_session.commit()
    return ATHLETE_ID


@pytest.fixture
def stub_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.jobs.weekly_jobs._PROVIDER_SYNCS",
        {"strava": lambda aid: None, "hevy": lambda aid: None, "terra": lambda aid: None},
    )
    monkeypatch.setattr("app.jobs.weekly_jobs.snapshot_athlete", lambda aid, db: None)


def _build(
    db_session: SASession, channel: Channel, coaching: FakeCoaching, google: FakeGoogle
) -> tuple[ApprovalService, MessagingGateway]:
    notifier = Notifier(channel)
    sync = CalendarSyncService(db_session, client=google)  # type: ignore[arg-type]

    def pusher(athlete_id: str, plan: Any, db: SASession) -> dict[str, int]:
        return sync.push_week(athlete_id, plan).as_dict()

    approvals = ApprovalService(
        db_session,
        notifier=notifier,
        coaching=coaching,
        calendar_pusher=pusher,
    )
    gateway = MessagingGateway(
        db_session,
        {channel.name: channel},
        notifier=notifier,
        approvals=approvals,
    )
    return approvals, gateway


def _last_buttons(channel: Channel) -> list[Button]:
    for _, buttons in reversed(channel.messages):
        if buttons:
            return buttons
    raise AssertionError("no message with buttons was sent")


def test_weekly_cycle_texts_a_week_and_approve_writes_the_calendar(
    db_session: SASession, athlete: str, stub_providers: None
) -> None:
    channel, coaching, google = Channel(), FakeCoaching(), FakeGoogle()
    approvals, _ = _build(db_session, channel, coaching, google)

    result = run_weekly_cycle_now(
        athlete, db_session, invoker=Invoker(coaching), approvals=approvals
    )

    assert result.plan_sent is True
    text, buttons = channel.messages[-1]
    assert "intervals" in text
    assert "Volume flat" in text
    assert buttons is not None and len(buttons) == 3

    token, resolution = parse_callback(buttons[0].token)  # type: ignore[misc]
    assert resolution == "approve"

    outcome = approvals.handle_button(
        athlete_id=athlete,
        channel="telegram",
        external_id=EXTERNAL_ID,
        token=token,
        resolution="approve",
    )

    assert outcome.calendar == {
        "created": 2,
        "updated": 0,
        "deleted": 0,
        "unchanged": 0,
        "skipped": 0,
    }
    assert coaching.resumed == [("plan-thread", True, None)]

    summaries = sorted(e["summary"] for e in google.events.values())
    assert summaries == ["🏃 easy — conversational", "🏃 intervals — 6 x 800 m"]
    starts = sorted(e["start"]["dateTime"] for e in google.events.values())
    assert starts[0].startswith("2031-06-02T07:00:00")
    assert db_session.query(CalendarEventModel).count() == 2


def test_re_running_the_same_week_updates_instead_of_duplicating(
    db_session: SASession, athlete: str, stub_providers: None
) -> None:
    channel, coaching, google = Channel(), FakeCoaching(), FakeGoogle()
    approvals, _ = _build(db_session, channel, coaching, google)

    for _ in range(2):
        run_weekly_cycle_now(
            athlete, db_session, invoker=Invoker(coaching), approvals=approvals
        )
        token, _res = parse_callback(_last_buttons(channel)[0].token)  # type: ignore[misc]
        approvals.handle_button(
            athlete_id=athlete,
            channel="telegram",
            external_id=EXTERNAL_ID,
            token=token,
            resolution="approve",
        )

    assert len(google.events) == 2
    assert db_session.query(CalendarEventModel).count() == 2
    assert google.writes.count("insert:evt-1") == 1
    assert not any(w.startswith("insert:evt-3") for w in google.writes)


def test_plain_language_revision_reshapes_the_week_and_drops_the_session(
    db_session: SASession, athlete: str, stub_providers: None
) -> None:
    channel, coaching, google = Channel(), FakeCoaching(), FakeGoogle()
    approvals, gateway = _build(db_session, channel, coaching, google)

    run_weekly_cycle_now(
        athlete, db_session, invoker=Invoker(coaching), approvals=approvals
    )
    token, _res = parse_callback(_last_buttons(channel)[0].token)  # type: ignore[misc]

    approvals.handle_button(
        athlete_id=athlete,
        channel="telegram",
        external_id=EXTERNAL_ID,
        token=token,
        resolution="revise",
    )
    assert "qu'est-ce qui doit changer" in channel.messages[-1][0].lower()

    gateway.handle_inbound("telegram", EXTERNAL_ID, "too much volume Wednesday")

    assert coaching.resumed[-1] == ("plan-thread", False, "too much volume Wednesday")
    revised_text, revised_buttons = channel.messages[-1]
    assert "intervals" not in revised_text
    assert revised_buttons is not None

    new_token, _ = parse_callback(revised_buttons[0].token)  # type: ignore[misc]
    assert new_token != token

    approvals.handle_button(
        athlete_id=athlete,
        channel="telegram",
        external_id=EXTERNAL_ID,
        token=new_token,
        resolution="approve",
    )

    assert len(google.events) == 1
    assert next(iter(google.events.values()))["summary"] == "🏃 easy — conversational"


def test_dropping_a_session_next_week_deletes_its_event(
    db_session: SASession, athlete: str, stub_providers: None
) -> None:
    channel, coaching, google = Channel(), FakeCoaching(), FakeGoogle()
    approvals, _ = _build(db_session, channel, coaching, google)

    run_weekly_cycle_now(
        athlete, db_session, invoker=Invoker(coaching), approvals=approvals
    )
    token, _res = parse_callback(_last_buttons(channel)[0].token)  # type: ignore[misc]
    approvals.handle_button(
        athlete_id=athlete,
        channel="telegram",
        external_id=EXTERNAL_ID,
        token=token,
        resolution="approve",
    )
    assert len(google.events) == 2

    coaching.current = WEEK_ONE_REVISED
    run_weekly_cycle_now(
        athlete, db_session, invoker=Invoker(coaching), approvals=approvals
    )
    token, _res = parse_callback(_last_buttons(channel)[0].token)  # type: ignore[misc]
    outcome = approvals.handle_button(
        athlete_id=athlete,
        channel="telegram",
        external_id=EXTERNAL_ID,
        token=token,
        resolution="approve",
    )

    assert outcome.calendar is not None and outcome.calendar["deleted"] == 1
    assert len(google.events) == 1
    assert db_session.query(CalendarEventModel).count() == 1


def test_skipping_the_week_writes_nothing(
    db_session: SASession, athlete: str, stub_providers: None
) -> None:
    channel, coaching, google = Channel(), FakeCoaching(), FakeGoogle()
    approvals, _ = _build(db_session, channel, coaching, google)

    run_weekly_cycle_now(
        athlete, db_session, invoker=Invoker(coaching), approvals=approvals
    )
    buttons = _last_buttons(channel)
    token, resolution = parse_callback(buttons[2].token)  # type: ignore[misc]
    assert resolution == "reject"

    approvals.handle_button(
        athlete_id=athlete,
        channel="telegram",
        external_id=EXTERNAL_ID,
        token=token,
        resolution="reject",
    )

    assert google.writes == []
    assert coaching.resumed == []
    row = db_session.get(PendingApprovalModel, token)
    assert row is not None and row.resolution == "reject"
