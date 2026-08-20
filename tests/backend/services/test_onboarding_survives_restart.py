"""Onboarding must not restart at block 1 when the process restarts.

Thread state lived only in `_thread_states`, a module-level dict. Any restart
-- a deploy, a crash, a laptop lid -- sent the athlete back to the first
question, and the coach asked everything again as though the conversation had
never happened. On a six-block onboarding conducted over text, across a
evening, that is the difference between usable and not.

The dict stays as the hot path. It is now a cache in front of
`athletes.onboarding_state_json`, which is written on every block advance and
read back when the cache misses.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from app.db.models import AthleteModel

ATHLETE = "77777777-7777-7777-7777-777777777777"


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


@pytest.fixture(autouse=True)
def athlete(db_session) -> AthleteModel:
    row = AthleteModel(
        id=ATHLETE,
        name="Simon",
        age=24,
        sex="M",
        weight_kg=77.0,
        height_cm=183.0,
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


@pytest.fixture(autouse=True)
def _clean_cache():
    from app.graphs import onboarding

    onboarding._thread_states.clear()
    yield
    onboarding._thread_states.clear()


def _quiet():
    """No LLM: a fixed question, and an extractor that finds nothing."""
    return (
        patch("app.graphs.onboarding._call_head_coach", return_value="Question?"),
        patch("app.services.onboarding_extraction.extract_block", return_value={}),
    )


def _advance_to(db_session, block: int) -> str:
    from app.graphs.onboarding import run_onboarding_respond, run_onboarding_start

    coach, extract = _quiet()
    with coach, extract:
        thread_id = str(run_onboarding_start(ATHLETE, db_session)["thread_id"])
        for _ in range(block - 1):
            run_onboarding_respond(thread_id, "une reponse", db_session)
    return thread_id


def _simulate_restart():
    """Drop the in-memory cache, keeping the database."""
    from app.graphs import onboarding

    onboarding._thread_states.clear()


class TestResumeAfterRestart:
    def test_the_block_is_remembered(self, db_session) -> None:
        from app.graphs.onboarding import run_onboarding_start

        _advance_to(db_session, 4)
        _simulate_restart()

        coach, extract = _quiet()
        with coach, extract:
            resumed = run_onboarding_start(ATHLETE, db_session)

        assert resumed["current_block"] == 4, "onboarding restarted from the top"

    def test_the_thread_id_is_the_same_one(self, db_session) -> None:
        from app.graphs.onboarding import run_onboarding_start

        original = _advance_to(db_session, 3)
        _simulate_restart()

        coach, extract = _quiet()
        with coach, extract:
            resumed = run_onboarding_start(ATHLETE, db_session)

        assert resumed["thread_id"] == original

    def test_earlier_answers_are_still_there(self, db_session) -> None:
        from app.graphs.onboarding import run_onboarding_respond, run_onboarding_start

        coach, extract = _quiet()
        with coach, extract:
            thread_id = str(run_onboarding_start(ATHLETE, db_session)["thread_id"])
            run_onboarding_respond(thread_id, "je suis Simon", db_session)

        _simulate_restart()

        coach, extract = _quiet()
        with coach, extract:
            run_onboarding_start(ATHLETE, db_session)
            result = run_onboarding_respond(thread_id, "24 ans", db_session)

        assert result["collected_data"]["intro_response"] == "je suis Simon"

    def test_the_conversation_can_be_finished_across_a_restart(
        self, db_session
    ) -> None:
        from app.graphs.onboarding import run_onboarding_respond, run_onboarding_start

        thread_id = _advance_to(db_session, 6)
        _simulate_restart()

        coach, extract = _quiet()
        with coach, extract:
            run_onboarding_start(ATHLETE, db_session)
            result = run_onboarding_respond(thread_id, "oui", db_session)

        assert result["status"] == "completed"
        db_session.expire_all()
        assert (
            db_session.get(AthleteModel, ATHLETE).journey_phase
            == "baseline_pending_confirmation"
        )


class TestRespondAfterRestartWithoutStart:
    def test_answering_directly_still_resolves_the_thread(self, db_session) -> None:
        """The athlete replies to a question the previous process asked."""
        from app.graphs.onboarding import run_onboarding_respond

        thread_id = _advance_to(db_session, 3)
        _simulate_restart()

        coach, extract = _quiet()
        with coach, extract:
            result = run_onboarding_respond(thread_id, "une reponse", db_session)

        assert result["current_block"] == 4

    def test_an_unknown_thread_still_raises(self, db_session) -> None:
        from app.graphs.onboarding import run_onboarding_respond

        with pytest.raises(ValueError):
            run_onboarding_respond("no-such-thread", "hello", db_session)


class TestPersistenceShape:
    def test_state_is_written_to_the_athlete_row(self, db_session) -> None:
        import json

        _advance_to(db_session, 3)
        db_session.expire_all()

        raw = db_session.get(AthleteModel, ATHLETE).onboarding_state_json
        assert raw, "nothing persisted"
        stored = json.loads(raw)
        assert stored["current_block"] == 3
        assert stored["status"] == "in_progress"

    def test_corrupt_state_does_not_break_the_conversation(self, db_session) -> None:
        """A restart is not the moment to start raising at the athlete."""
        from app.graphs.onboarding import run_onboarding_start

        _advance_to(db_session, 3)
        athlete = db_session.get(AthleteModel, ATHLETE)
        athlete.onboarding_state_json = "{not json"
        db_session.commit()
        _simulate_restart()

        coach, extract = _quiet()
        with coach, extract:
            result = run_onboarding_start(ATHLETE, db_session)

        assert result["status"] == "in_progress"
        assert result["current_block"] == 1
