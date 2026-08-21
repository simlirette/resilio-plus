"""The coach decides; the tools execute.

Until now the graph decided everything — which block, when to extract, when to
finish — and the model only wrote the sentence. That is a narrator, not an
agent, and it is why a direct question ("quand t'ai-je dit 8h ?") went
unanswered three times: the model was under orders to collect, not to converse.

Each tool wraps machinery that already exists and is already tested. The model
never computes a pace, a zone or a VDOT; it decides *when* to ask for one.

Every tool returns a result the model can read, including on failure. A tool
that raises would end the athlete's turn; a tool that reports "je n'ai pas pu"
lets the coach say so.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from app.db.models import AthleteModel
from app.services.coach_tools import TOOL_SCHEMAS, ToolContext, run_tool

ATHLETE = "tool-1"


@pytest.fixture
def db_session():
    from app.db import models  # noqa: F401 -- registers ORM models with Base
    from app.db.database import Base
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import Session as SASession

    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def _fk(conn, _):
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(engine)
    with SASession(engine) as s:
        yield s
    Base.metadata.drop_all(engine)


@pytest.fixture
def athlete(db_session) -> AthleteModel:
    row = AthleteModel(
        id=ATHLETE,
        name="Simon",
        age=24,
        sex="M",
        weight_kg=77.1,
        height_cm=182.9,
        hours_per_week=8.0,
        primary_sport="running",
        sports_json='["running"]',
        goals_json="[]",
        available_days_json="[]",
        equipment_json="[]",
        journey_phase="onboarding",
    )
    db_session.add(row)
    db_session.commit()
    return row


@pytest.fixture
def ctx(db_session, athlete) -> ToolContext:
    return ToolContext(athlete_id=ATHLETE, db=db_session)


class TestTheSchemas:
    def test_the_four_capabilities_are_all_there(self) -> None:
        """Profile, goal, plan, follow-up — the athlete's four asks."""
        names = {schema["name"] for schema in TOOL_SCHEMAS}

        assert {
            "update_profile",
            "assess_goal",
            "generate_plan",
            "review_training",
        } <= names

    @pytest.mark.parametrize("schema", TOOL_SCHEMAS, ids=lambda s: s["name"])
    def test_each_schema_is_well_formed(self, schema: dict) -> None:
        assert schema["description"].strip()
        assert schema["input_schema"]["type"] == "object"

    def test_no_tool_lets_the_model_write_a_pace(self) -> None:
        """Tools compute; the model phrases. That boundary is the whole point."""
        forbidden = {"pace", "vdot", "duration_min", "workout_type"}
        for schema in TOOL_SCHEMAS:
            properties = set(schema["input_schema"].get("properties", {}))
            assert not (properties & forbidden), schema["name"]


class TestUpdateProfile:
    def test_it_writes_what_the_athlete_said(self, ctx, athlete) -> None:
        result = run_tool(
            "update_profile", {"sports": ["running", "lifting"]}, ctx
        )

        assert result.ok
        assert "lifting" in athlete.sports_json

    def test_it_reports_which_fields_changed(self, ctx) -> None:
        result = run_tool("update_profile", {"resting_hr": 52}, ctx)

        assert "resting_hr" in result.content

    def test_a_refused_value_is_reported_not_hidden(self, ctx) -> None:
        """The coach must be able to say "ça ne rentre pas" rather than lie."""
        result = run_tool("update_profile", {"weight_kg": 400}, ctx)

        assert result.ok
        assert "weight_kg" not in result.content

    def test_nothing_to_write_is_not_an_error(self, ctx) -> None:
        result = run_tool("update_profile", {}, ctx)

        assert result.ok


class TestAssessGoal:
    def test_it_reports_the_projection(self, ctx, athlete, db_session) -> None:
        athlete.vdot = 31.0
        athlete.goals_json = '["semi en moins de 2h"]'
        db_session.commit()

        result = run_tool("assess_goal", {}, ctx)

        assert result.ok
        assert "2h" in result.content

    def test_without_a_vdot_it_says_so_rather_than_guessing(
        self, ctx, athlete, db_session
    ) -> None:
        athlete.vdot = None
        athlete.goals_json = '["semi en moins de 2h"]'
        db_session.commit()

        result = run_tool("assess_goal", {}, ctx)

        assert result.ok
        assert "chrono" in result.content.lower() or "vdot" in result.content.lower()


class TestReviewTraining:
    def test_it_reports_a_missed_session(self, ctx, athlete, db_session) -> None:
        from datetime import date, timedelta

        from app.db.models import TrainingPlanModel

        yesterday = date.today() - timedelta(days=1)
        db_session.add(
            TrainingPlanModel(
                id="p1",
                athlete_id=ATHLETE,
                start_date=yesterday,
                end_date=yesterday + timedelta(days=6),
                phase="competition",
                total_weekly_hours=8.0,
                acwr=1.0,
                weekly_slots_json=(
                    '[{"date": "%s", "sport": "running", '
                    '"workout_type": "easy_z1", "duration_min": 45}]'
                    % yesterday.isoformat()
                ),
            )
        )
        db_session.commit()

        with patch(
            "app.services.coach_tools._completed_sessions", return_value=[]
        ):
            result = run_tool("review_training", {"days": 7}, ctx)

        assert result.ok
        assert "non faite" in result.content

    def test_no_plan_is_reported_plainly(self, ctx) -> None:
        result = run_tool("review_training", {"days": 7}, ctx)

        assert result.ok
        assert result.content.strip()


class TestGeneratePlan:
    def test_it_delegates_to_the_engine(self, ctx) -> None:
        with patch(
            "app.services.coach_tools._build_week",
            return_value={"sessions": [{"sport": "running"}]},
        ) as build:
            result = run_tool("generate_plan", {}, ctx)

        assert build.called
        assert result.ok

    def test_an_engine_failure_is_told_to_the_coach(self, ctx) -> None:
        """Raising would end the athlete's turn; reporting lets the coach speak."""
        with patch(
            "app.services.coach_tools._build_week",
            side_effect=RuntimeError("graph exploded"),
        ):
            result = run_tool("generate_plan", {}, ctx)

        assert not result.ok
        assert result.content.strip()


class TestUnknownAndBroken:
    def test_an_unknown_tool_is_reported_not_raised(self, ctx) -> None:
        result = run_tool("delete_everything", {}, ctx)

        assert not result.ok
        assert "delete_everything" in result.content

    def test_bad_arguments_are_reported_not_raised(self, ctx) -> None:
        result = run_tool("update_profile", {"sports": "not a list"}, ctx)

        assert result.ok
