from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from typing import Any

import pytest
from app.db.models import AthleteModel, TrainingPlanModel
from app.jobs.weekly_jobs import (
    WeeklyCycleError,
    daily_reminder_enabled,
    run_weekly_cycle_now,
    send_daily_reminder,
)
from app.messaging.base import Button
from sqlalchemy.orm import Session


@pytest.fixture
def db_session():
    """Local SQLite session — tests/backend/jobs has no conftest of its own."""
    from app.db import models  # noqa: F401 — registers ORM models with Base
    from app.db.database import Base
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import Session as SASession

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


ATHLETE_ID = "athlete-weekly"

PLAN = {
    "phase": "build",
    "sessions": [
        {
            "id": "slot-1",
            "date": "2031-06-02",
            "sport": "running",
            "workout_type": "tempo",
            "duration_min": 60,
            "notes": "8 km @ 4:35/km",
        }
    ],
}


class FakeInvoker:
    def __init__(self, output: dict[str, Any] | None) -> None:
        self.output = output
        self.calls: list[tuple[str, str]] = []

    def invoke(
        self,
        graph_name: str,
        athlete_id: str,
        thread_id: str,
        payload: dict[str, Any],
        db: Session,
    ) -> dict[str, Any] | None:
        self.calls.append((graph_name, athlete_id))
        return self.output


class FakeApprovals:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def send_plan_for_approval(
        self,
        *,
        athlete_id: str,
        thread_id: str,
        kind: str = "weekly_plan",
        plan: Any = None,
        degraded_sources: Any = None,
        payload: dict[str, Any] | None = None,
        # The coach's read on the week that just ended, sent above the new plan.
        preamble: str | None = None,
    ) -> str:
        self.calls.append(
            {
                "athlete_id": athlete_id,
                "thread_id": thread_id,
                "plan": plan,
                "degraded_sources": degraded_sources,
                "payload": payload,
            }
        )
        return "token-1"


@pytest.fixture
def athlete(db_session: Session) -> str:
    db_session.add(
        AthleteModel(
            id=ATHLETE_ID,
            name="Weekly Athlete",
            age=33,
            sex="M",
            weight_kg=73.0,
            height_cm=179.0,
            primary_sport="running",
            hours_per_week=8.0,
            sports_json='["running"]',
            goals_json="[]",
            available_days_json="[]",
            equipment_json="[]",
        )
    )
    db_session.commit()
    return ATHLETE_ID


@pytest.fixture
def stub_steps(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[str]]:
    """Neutralise the provider syncs and the snapshot; tests opt back in."""
    called: dict[str, list[str]] = {"sync": [], "snapshot": []}

    monkeypatch.setattr(
        "app.jobs.weekly_jobs._PROVIDER_SYNCS",
        {
            "strava": lambda aid: called["sync"].append("strava"),
            "hevy": lambda aid: called["sync"].append("hevy"),
            "terra": lambda aid: called["sync"].append("terra"),
        },
    )
    monkeypatch.setattr(
        "app.jobs.weekly_jobs.snapshot_athlete",
        lambda aid, db: called["snapshot"].append(aid),
    )
    return called


class TestWeeklyCycle:
    def test_syncs_computes_generates_and_sends(
        self, db_session: Session, athlete: str, stub_steps: dict[str, list[str]]
    ) -> None:
        approvals = FakeApprovals()
        invoker = FakeInvoker(
            {"plan_proposal": PLAN, "plan_thread_id": "plan-thread"}
        )

        result = run_weekly_cycle_now(
            athlete, db_session, invoker=invoker, approvals=approvals
        )

        assert stub_steps["sync"] == ["strava", "hevy", "terra"]
        assert stub_steps["snapshot"] == [athlete]
        assert invoker.calls == [("plan_generation", athlete)]
        assert result.plan_sent is True
        assert result.approval_token == "token-1"
        assert result.thread_id == "plan-thread"
        assert approvals.calls[0]["plan"] == PLAN
        assert approvals.calls[0]["payload"] == {"trigger": "weekly_cycle"}

    def test_a_dead_provider_degrades_the_week_instead_of_aborting_it(
        self,
        db_session: Session,
        athlete: str,
        monkeypatch: pytest.MonkeyPatch,
        stub_steps: dict[str, list[str]],
    ) -> None:
        def boom(athlete_id: str) -> None:
            raise RuntimeError("hevy down")

        monkeypatch.setattr(
            "app.jobs.weekly_jobs._PROVIDER_SYNCS",
            {"strava": lambda aid: None, "hevy": boom, "terra": lambda aid: None},
        )
        approvals = FakeApprovals()

        result = run_weekly_cycle_now(
            athlete,
            db_session,
            invoker=FakeInvoker({"plan_proposal": PLAN, "plan_thread_id": "t"}),
            approvals=approvals,
        )

        assert result.degraded_sources == ["hevy"]
        assert result.plan_sent is True
        assert approvals.calls[0]["degraded_sources"] == ["hevy"]

    def test_a_failing_snapshot_does_not_stop_the_week(
        self,
        db_session: Session,
        athlete: str,
        monkeypatch: pytest.MonkeyPatch,
        stub_steps: dict[str, list[str]],
    ) -> None:
        def boom(athlete_id: str, db: Session) -> None:
            raise RuntimeError("no connector data")

        monkeypatch.setattr("app.jobs.weekly_jobs.snapshot_athlete", boom)

        result = run_weekly_cycle_now(
            athlete,
            db_session,
            invoker=FakeInvoker({"plan_proposal": PLAN, "plan_thread_id": "t"}),
            approvals=FakeApprovals(),
        )

        assert result.plan_sent is True

    def test_no_plan_means_nothing_is_sent(
        self, db_session: Session, athlete: str, stub_steps: dict[str, list[str]]
    ) -> None:
        approvals = FakeApprovals()

        result = run_weekly_cycle_now(
            athlete, db_session, invoker=FakeInvoker(None), approvals=approvals
        )

        assert result.plan_sent is False
        assert result.reason == "no_plan_generated"
        assert approvals.calls == []

    def test_plan_without_a_thread_is_not_sent(
        self, db_session: Session, athlete: str, stub_steps: dict[str, list[str]]
    ) -> None:
        approvals = FakeApprovals()

        result = run_weekly_cycle_now(
            athlete,
            db_session,
            invoker=FakeInvoker({"plan_proposal": PLAN, "plan_thread_id": None}),
            approvals=approvals,
        )

        assert result.plan_sent is False
        assert approvals.calls == []

    def test_unknown_athlete_raises(
        self, db_session: Session, stub_steps: dict[str, list[str]]
    ) -> None:
        with pytest.raises(WeeklyCycleError):
            run_weekly_cycle_now(
                "ghost",
                db_session,
                invoker=FakeInvoker(None),
                approvals=FakeApprovals(),
            )

    def test_result_serialises_for_the_job_log(
        self, db_session: Session, athlete: str, stub_steps: dict[str, list[str]]
    ) -> None:
        result = run_weekly_cycle_now(
            athlete,
            db_session,
            invoker=FakeInvoker({"plan_proposal": PLAN, "plan_thread_id": "t"}),
            approvals=FakeApprovals(),
        )

        assert result.as_dict()["plan_sent"] is True
        assert json.dumps(result.as_dict())


class TestDailyReminder:
    def _plan(self, db_session: Session, athlete_id: str, day: date) -> None:
        db_session.add(
            TrainingPlanModel(
                id=str(uuid.uuid4()),
                athlete_id=athlete_id,
                start_date=day,
                end_date=day,
                phase="base",
                total_weekly_hours=1.0,
                acwr=1.0,
                weekly_slots_json=json.dumps(
                    [
                        {
                            "id": "slot-today",
                            "date": day.isoformat(),
                            "sport": "running",
                            "workout_type": "easy",
                            "duration_min": 45,
                            "notes": "keep it conversational",
                        }
                    ]
                ),
                status="active",
                created_at=datetime.now(timezone.utc),
            )
        )
        db_session.commit()

    def test_disabled_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DAILY_REMINDER_ENABLED", raising=False)
        assert daily_reminder_enabled() is False

    def test_enabled_by_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DAILY_REMINDER_ENABLED", "true")
        assert daily_reminder_enabled() is True

    def test_sends_todays_session(
        self, db_session: Session, athlete: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._plan(db_session, athlete, date.today())
        sent: list[str] = []

        class Channel:
            name = "telegram"

            def send(self, external_id: str, text: str) -> str:
                sent.append(text)
                return "m1"

            def send_with_buttons(
                self, external_id: str, text: str, buttons: list[Button]
            ) -> str:
                return self.send(external_id, text)

            def max_message_length(self) -> int:
                return 4096

            def format(self, text: str) -> str:
                return text

        monkeypatch.setattr(
            "app.jobs.weekly_jobs.configured_channels", lambda: {"telegram": Channel()}
        )

        class Notifier:
            def __init__(self, db: Session, channels: Any) -> None:
                self._channels = channels

            def send(
                self,
                athlete_id: str,
                text: str,
                buttons: list[Button] | None = None,
                *,
                kind: str = "notification",
            ) -> list[str]:
                sent.append(text)
                return ["m1"]

        monkeypatch.setattr("app.jobs.weekly_jobs.NotificationService", Notifier)

        assert send_daily_reminder(athlete, db_session) is True
        assert "easy" in sent[0]
        assert "keep it conversational" in sent[0]

    def test_no_plan_means_no_reminder(
        self, db_session: Session, athlete: str
    ) -> None:
        assert send_daily_reminder(athlete, db_session) is False

    def test_no_session_today_means_no_reminder(
        self, db_session: Session, athlete: str
    ) -> None:
        self._plan(db_session, athlete, date(2020, 1, 1))
        assert send_daily_reminder(athlete, db_session) is False
