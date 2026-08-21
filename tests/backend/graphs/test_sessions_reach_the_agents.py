"""The frequency the athlete declared must reach the generators.

`sessions_per_week_json` is populated by onboarding and read by nobody. The
planning graph builds `AgentContext` from `AthleteProfile`, which has no such
field, so the number of runs and lifts in a week stayed an accident of
dividing an hours budget into chunks.

The first live plan held two running sessions and no lifting at all, for an
athlete who runs three times a week and lifts four.

Degrades the same way `_connector_inputs` does: no database, an unreadable
column or a missing athlete yields an empty mapping, which leaves each
generator on exactly its previous behaviour.
"""
from __future__ import annotations

import pytest
from app.db.models import AthleteModel
from app.graphs.nodes import _sessions_per_week

ATHLETE = "sess-1"


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


def _athlete(db_session, sessions: str | None) -> AthleteModel:
    row = AthleteModel(
        id=ATHLETE,
        name="Simon",
        age=24,
        sex="M",
        weight_kg=77.1,
        height_cm=182.9,
        hours_per_week=8.0,
        primary_sport="running",
        sports_json='["running", "lifting"]',
        goals_json='["semi"]',
        available_days_json="[]",
        equipment_json="[]",
        sessions_per_week_json=sessions,
    )
    db_session.add(row)
    db_session.commit()
    return row


def _config(db) -> dict:
    return {"configurable": {"db": db}}


class TestItReachesTheContext:
    def test_declared_counts_are_returned(self, db_session) -> None:
        _athlete(db_session, '{"running": 3, "lifting": 4}')

        assert _sessions_per_week(ATHLETE, _config(db_session)) == {
            "running": 3,
            "lifting": 4,
        }

    def test_counts_are_integers(self, db_session) -> None:
        """A float session count would be handed straight to `range`-like logic."""
        _athlete(db_session, '{"running": 3.0}')

        assert _sessions_per_week(ATHLETE, _config(db_session)) == {"running": 3}


class TestDegradation:
    def test_no_declaration_is_an_empty_mapping(self, db_session) -> None:
        """Empty means "not stated", which leaves the generators unchanged."""
        _athlete(db_session, None)

        assert _sessions_per_week(ATHLETE, _config(db_session)) == {}

    def test_no_database_in_config_is_an_empty_mapping(self) -> None:
        assert _sessions_per_week(ATHLETE, {"configurable": {}}) == {}

    def test_an_unknown_athlete_is_an_empty_mapping(self, db_session) -> None:
        assert _sessions_per_week("nobody", _config(db_session)) == {}

    def test_unreadable_json_does_not_break_the_planning_run(
        self, db_session
    ) -> None:
        _athlete(db_session, "{not json")

        assert _sessions_per_week(ATHLETE, _config(db_session)) == {}

    def test_a_non_numeric_count_is_dropped(self, db_session) -> None:
        _athlete(db_session, '{"running": "trois", "lifting": 4}')

        assert _sessions_per_week(ATHLETE, _config(db_session)) == {"lifting": 4}


class TestTheContextCarriesIt:
    def test_agent_context_has_the_field(self) -> None:
        import dataclasses

        from app.agents.base import AgentContext

        names = {f.name for f in dataclasses.fields(AgentContext)}
        assert "sessions_per_week" in names

    @pytest.mark.parametrize("agent", ["running_coach", "lifting_coach"])
    def test_each_sport_agent_passes_it_on(self, agent: str) -> None:
        """A field on the context nobody reads is the bug this replaces."""
        import importlib
        import inspect

        module = importlib.import_module(f"app.agents.{agent}")
        source = inspect.getsource(module)

        assert "sessions_target=" in source
        assert "sessions_per_week" in source
