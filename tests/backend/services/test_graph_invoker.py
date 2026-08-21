from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from app.db.models import AthleteModel, ChatMessageModel
from app.services.graph_invoker import (
    DefaultGraphInvoker,
    build_live_coordinator,
    recent_intents,
)
from sqlalchemy.orm import Session

PROPOSED_PLAN = {"phase": "base", "sessions": []}


class FakeCoaching:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[float]]] = []

    def create_plan(
        self,
        athlete_id: str,
        athlete_dict: dict[str, Any],
        load_history: list[float],
        db: Session,
    ) -> tuple[str, dict[str, Any] | None]:
        self.calls.append((athlete_id, load_history))
        return "plan-thread-1", PROPOSED_PLAN


def make_athlete(db_session: Session, **overrides: Any) -> str:
    athlete_id = overrides.pop("id", str(uuid.uuid4()))
    db_session.add(
        AthleteModel(
            id=athlete_id,
            name="Invoker Athlete",
            age=33,
            sex="M",
            weight_kg=72.0,
            height_cm=178.0,
            primary_sport="running",
            hours_per_week=7.0,
            sports_json='["running"]',
            goals_json='["fitness"]',
            available_days_json="[0, 2, 4]",
            equipment_json="[]",
            **overrides,
        )
    )
    db_session.commit()
    return athlete_id


class TestChatTurn:
    def test_forwards_message_and_recent_intents(
        self, db_session: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        athlete_id = make_athlete(db_session)
        seen: dict[str, Any] = {}

        class FakeTurn:
            reply = "ok"
            ok = True
            tools_used: list[str] = []

        def fake_turn(**kwargs: Any) -> FakeTurn:
            seen.update(kwargs)
            return FakeTurn()

        monkeypatch.setattr(
            "app.services.graph_invoker.run_coach_turn", fake_turn, raising=True
        )

        output = DefaultGraphInvoker().invoke(
            "chat_turn", athlete_id, "thread-1", {"message": "hello"}, db_session
        )

        assert output is not None
        assert output["message"] == "ok"
        assert seen["user_message"] == "hello"

    def test_empty_message_does_not_run_the_graph(
        self, db_session: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        athlete_id = make_athlete(db_session)

        def explode(**_: Any) -> dict[str, Any]:
            raise AssertionError("graph must not run without a message")

        monkeypatch.setattr("app.services.graph_invoker.run_coach_turn", explode)

        assert (
            DefaultGraphInvoker().invoke(
                "chat_turn", athlete_id, "thread-1", {"message": "  "}, db_session
            )
            is None
        )


class TestRecentIntents:
    def test_returns_last_three_oldest_first(self, db_session: Session) -> None:
        athlete_id = make_athlete(db_session)
        base = datetime(2031, 1, 1, tzinfo=timezone.utc)
        for index, intent in enumerate(["A", "B", "C", "D"]):
            db_session.add(
                ChatMessageModel(
                    id=str(uuid.uuid4()),
                    athlete_id=athlete_id,
                    role="user",
                    content=f"m{index}",
                    intent_decision=intent,
                    created_at=base + timedelta(minutes=index),
                )
            )
        db_session.commit()

        assert recent_intents(athlete_id, db_session) == ["B", "C", "D"]

    def test_empty_history_returns_empty_list(self, db_session: Session) -> None:
        athlete_id = make_athlete(db_session)
        assert recent_intents(athlete_id, db_session) == []


class TestPlanGeneration:
    def test_opens_a_proposal_for_the_athlete(self, db_session: Session) -> None:
        athlete_id = make_athlete(
            db_session, journey_phase="baseline_pending_confirmation"
        )
        coaching = FakeCoaching()

        output = DefaultGraphInvoker(coaching=coaching).invoke(
            "plan_generation", athlete_id, "thread-1", {}, db_session
        )

        assert output == {
            "plan_proposal": PROPOSED_PLAN,
            "plan_thread_id": "plan-thread-1",
        }
        assert len(coaching.calls[0][1]) == 28

    def test_the_load_history_reflects_real_training(
        self, db_session: Session
    ) -> None:
        """Sessions the athlete actually did must reach ACWR."""
        import uuid as _uuid
        from datetime import datetime, timedelta
        from datetime import timezone as _tz

        from app.db.models import StravaActivityModel

        athlete_id = make_athlete(
            db_session, journey_phase="baseline_pending_confirmation"
        )
        db_session.add(
            StravaActivityModel(
                id=f"strava_{_uuid.uuid4().hex[:8]}",
                athlete_id=athlete_id,
                strava_id=int(_uuid.uuid4().int % 10**12),
                sport_type="running",
                name="long run",
                started_at=datetime.now(_tz.utc) - timedelta(days=1),
                duration_s=3600,
                perceived_exertion=10.0,
            )
        )
        db_session.commit()
        coaching = FakeCoaching()

        DefaultGraphInvoker(coaching=coaching).invoke(
            "plan_generation", athlete_id, "thread-1", {}, db_session
        )

        load_history = coaching.calls[0][1]
        assert sum(load_history) > 0

    def test_unknown_athlete_returns_none(self, db_session: Session) -> None:
        coaching = FakeCoaching()
        assert (
            DefaultGraphInvoker(coaching=coaching).invoke(
                "plan_generation", "ghost", "thread-1", {}, db_session
            )
            is None
        )
        assert coaching.calls == []


class TestUnknownGraph:
    def test_returns_none_without_raising(self, db_session: Session) -> None:
        athlete_id = make_athlete(db_session)
        assert (
            DefaultGraphInvoker().invoke(
                "nope", athlete_id, "thread-1", {}, db_session
            )
            is None
        )


class TestLiveCoordinator:
    def test_first_chat_message_walks_signup_into_onboarding(
        self, db_session: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        athlete_id = make_athlete(db_session, journey_phase="signup")
        class FakeTurn:
            reply = "Who are you?"
            ok = True
            tools_used: list[str] = []

        monkeypatch.setattr(
            "app.services.graph_invoker.run_coach_turn",
            lambda **_: FakeTurn(),
        )

        result = build_live_coordinator().dispatch(
            athlete_id, "chat", {"message": "hello"}, db_session
        )

        assert result.graph_invoked == "onboarding"
        assert result.output is not None
        assert result.output["message"] == "Who are you?"
        athlete = db_session.get(AthleteModel, athlete_id)
        assert athlete is not None
        assert athlete.journey_phase == "onboarding"

    def test_default_coordinator_stays_inert(self, db_session: Session) -> None:
        from app.services.coordinator_service import CoordinatorService

        athlete_id = make_athlete(db_session, journey_phase="signup")
        result = CoordinatorService().dispatch(
            athlete_id, "chat", {"message": "hello"}, db_session
        )

        assert result.graph_invoked is None
        athlete = db_session.get(AthleteModel, athlete_id)
        assert athlete is not None
        assert athlete.journey_phase == "signup"

# Removed 2026-08-21. `TestOnboarding` pinned the six-block script and
# `TestConnectorInvitation` pinned links fired at block 4; neither exists.
# Onboarding and chat are one agentic loop now, and the connect links are a
# tool the coach calls when it needs data it does not have —
# see `test_coach_loop_is_the_conversation.py` and `test_coach_tools.py`.
