from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from sqlalchemy.orm import Session

from app.db.models import AthleteModel, ChatMessageModel
from app.services.graph_invoker import (
    DefaultGraphInvoker,
    build_live_coordinator,
    recent_intents,
)

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

        def fake_run_chat_turn(**kwargs: Any) -> dict[str, Any]:
            seen.update(kwargs)
            return {"final_response": "ok", "intent_decision": "HEAD_COACH_DIRECT"}

        monkeypatch.setattr(
            "app.graphs.chat_turn.run_chat_turn", fake_run_chat_turn, raising=True
        )

        output = DefaultGraphInvoker().invoke(
            "chat_turn", athlete_id, "thread-1", {"message": "hello"}, db_session
        )

        assert output == {
            "final_response": "ok",
            "intent_decision": "HEAD_COACH_DIRECT",
        }
        assert seen["user_message"] == "hello"
        assert seen["last_3_intents"] == []

    def test_empty_message_does_not_run_the_graph(
        self, db_session: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        athlete_id = make_athlete(db_session)

        def explode(**_: Any) -> dict[str, Any]:
            raise AssertionError("graph must not run without a message")

        monkeypatch.setattr("app.graphs.chat_turn.run_chat_turn", explode)

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


class TestOnboarding:
    def test_first_message_starts_block_one(
        self, db_session: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        athlete_id = make_athlete(db_session, journey_phase="onboarding")

        def fake_respond(thread_id: str, message: str, db: Session) -> dict[str, Any]:
            raise ValueError("no thread")

        monkeypatch.setattr("app.graphs.onboarding.run_onboarding_respond", fake_respond)
        monkeypatch.setattr(
            "app.graphs.onboarding.run_onboarding_start",
            lambda athlete_id, db: {
                "thread_id": "t1",
                "current_block": 1,
                "question": "Tell me about yourself",
                "status": "in_progress",
            },
        )

        output = DefaultGraphInvoker().invoke(
            "onboarding", athlete_id, "thread-1", {"message": "hi"}, db_session
        )

        assert output is not None
        assert output["question"] == "Tell me about yourself"

    def test_subsequent_message_advances_the_thread(
        self, db_session: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        athlete_id = make_athlete(db_session, journey_phase="onboarding")
        monkeypatch.setattr(
            "app.graphs.onboarding.run_onboarding_respond",
            lambda thread_id, message, db: {
                "thread_id": thread_id,
                "current_block": 2,
                "question": "Age, sex, weight?",
                "status": "in_progress",
            },
        )
        monkeypatch.setattr(
            "app.graphs.onboarding.run_onboarding_start",
            lambda athlete_id, db: pytest.fail("must not restart a live thread"),
        )

        output = DefaultGraphInvoker().invoke(
            "onboarding", athlete_id, "thread-9", {"message": "I run"}, db_session
        )

        assert output is not None
        assert output["current_block"] == 2

    def test_completion_chains_into_a_plan_proposal(
        self, db_session: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        athlete_id = make_athlete(db_session, journey_phase="onboarding")
        coaching = FakeCoaching()
        monkeypatch.setattr(
            "app.graphs.onboarding.run_onboarding_respond",
            lambda thread_id, message, db: {
                "thread_id": thread_id,
                "current_block": 7,
                "question": None,
                "status": "completed",
            },
        )

        output = DefaultGraphInvoker(coaching=coaching).invoke(
            "onboarding", athlete_id, "thread-9", {"message": "yes"}, db_session
        )

        assert output is not None
        assert output["plan_proposal"] == PROPOSED_PLAN
        assert output["plan_thread_id"] == "plan-thread-1"
        assert coaching.calls == [(athlete_id, [])]


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
        monkeypatch.setattr(
            "app.graphs.onboarding.run_onboarding_respond",
            lambda thread_id, message, db: (_ for _ in ()).throw(ValueError("none")),
        )
        monkeypatch.setattr(
            "app.graphs.onboarding.run_onboarding_start",
            lambda athlete_id, db: {
                "thread_id": "t1",
                "current_block": 1,
                "question": "Who are you?",
                "status": "in_progress",
            },
        )

        result = build_live_coordinator().dispatch(
            athlete_id, "chat", {"message": "hello"}, db_session
        )

        assert result.graph_invoked == "onboarding"
        assert result.output is not None
        assert result.output["question"] == "Who are you?"
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


class TestConnectorInvitation:
    def _scripted(self, monkeypatch: pytest.MonkeyPatch, block: int) -> None:
        monkeypatch.setattr(
            "app.graphs.onboarding.run_onboarding_respond",
            lambda thread_id, message, db: {
                "thread_id": thread_id,
                "current_block": block,
                "question": "Sport history?",
                "status": "in_progress",
            },
        )

    def test_links_are_offered_once_goals_are_collected(
        self,
        db_session: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("PUBLIC_BASE_URL", "https://coach.example.com")
        athlete_id = make_athlete(db_session, journey_phase="onboarding")
        self._scripted(monkeypatch, block=4)

        output = DefaultGraphInvoker().invoke(
            "onboarding", athlete_id, "thread-1", {"message": "half in June"}, db_session
        )

        assert output is not None
        question = output["question"]
        assert question.startswith("Sport history?")
        assert question.count("https://coach.example.com/integrations/link/") == 4

    def test_no_links_on_other_blocks(
        self,
        db_session: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        athlete_id = make_athlete(db_session, journey_phase="onboarding")
        self._scripted(monkeypatch, block=3)

        output = DefaultGraphInvoker().invoke(
            "onboarding", athlete_id, "thread-1", {"message": "x"}, db_session
        )

        assert output is not None
        assert output["question"] == "Sport history?"

    def test_already_connected_providers_are_not_re_offered(
        self,
        db_session: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import uuid as _uuid

        from app.db.models import ConnectorCredentialModel

        monkeypatch.setenv("PUBLIC_BASE_URL", "https://coach.example.com")
        athlete_id = make_athlete(db_session, journey_phase="onboarding")
        for provider in ("strava", "hevy", "terra"):
            db_session.add(
                ConnectorCredentialModel(
                    id=str(_uuid.uuid4()),
                    athlete_id=athlete_id,
                    provider=provider,
                    extra_json="{}",
                )
            )
        db_session.commit()
        self._scripted(monkeypatch, block=4)

        output = DefaultGraphInvoker().invoke(
            "onboarding", athlete_id, "thread-1", {"message": "x"}, db_session
        )

        assert output is not None
        assert output["question"].count("integrations/link/") == 1
        assert "Google Calendar" in output["question"]

    def test_a_link_failure_does_not_sink_the_turn(
        self,
        db_session: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        athlete_id = make_athlete(db_session, journey_phase="onboarding")
        self._scripted(monkeypatch, block=4)

        def boom(*args: Any, **kwargs: Any) -> str:
            raise RuntimeError("db down")

        monkeypatch.setattr(
            "app.services.graph_invoker.connector_links_message", boom
        )

        output = DefaultGraphInvoker().invoke(
            "onboarding", athlete_id, "thread-1", {"message": "x"}, db_session
        )

        assert output is not None
        assert output["question"] == "Sport history?"
