"""The onboarding graph must actually call the extractor.

`test_onboarding_extraction.py` pins what extraction does. This pins that it
happens at all: the extractor existing but never being wired in is exactly the
failure mode this whole change exists to fix.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from app.db.models import AthleteModel


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
        id="wire-1",
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


def _start(db_session, athlete_id: str) -> str:
    from app.graphs.onboarding import run_onboarding_start

    with patch("app.graphs.onboarding._call_head_coach", return_value="Question?"):
        return str(run_onboarding_start(athlete_id, db_session)["thread_id"])


class TestTheAnswerReachesTheRow:
    def test_a_block_answer_is_extracted_and_written(
        self, db_session, athlete
    ) -> None:
        from app.graphs.onboarding import run_onboarding_respond

        thread_id = _start(db_session, athlete.id)

        with (
            patch("app.graphs.onboarding._call_head_coach", return_value="Next?"),
            patch(
                "app.services.onboarding_extraction.extract_block",
                return_value={"resting_hr": 48},
            ),
        ):
            run_onboarding_respond(thread_id, "mon pouls au repos est 48", db_session)

        db_session.expire_all()
        assert db_session.get(AthleteModel, athlete.id).resting_hr == 48

    def test_a_race_result_becomes_a_vdot_on_the_row(
        self, db_session, athlete
    ) -> None:
        from app.graphs.onboarding import run_onboarding_respond

        thread_id = _start(db_session, athlete.id)

        with (
            patch("app.graphs.onboarding._call_head_coach", return_value="Next?"),
            patch(
                "app.services.onboarding_extraction.extract_block",
                return_value={"race_distance": "10k", "race_time_seconds": 2820},
            ),
        ):
            run_onboarding_respond(thread_id, "10 km en 47 minutes", db_session)

        db_session.expire_all()
        assert db_session.get(AthleteModel, athlete.id).vdot == 40.0


class TestExtractionIsNotLoadBearing:
    def test_a_failing_extractor_does_not_break_the_conversation(
        self, db_session, athlete
    ) -> None:
        """Losing a fact is recoverable; losing the conversation is not."""
        from app.graphs.onboarding import run_onboarding_respond

        thread_id = _start(db_session, athlete.id)

        with (
            patch("app.graphs.onboarding._call_head_coach", return_value="Next?"),
            patch(
                "app.services.onboarding_extraction.extract_block",
                side_effect=RuntimeError("extractor exploded"),
            ),
        ):
            result = run_onboarding_respond(thread_id, "31 ans", db_session)

        assert result["status"] == "in_progress"
        assert result["question"] == "Next?"

    def test_an_empty_extraction_changes_nothing(self, db_session, athlete) -> None:
        from app.graphs.onboarding import run_onboarding_respond

        thread_id = _start(db_session, athlete.id)

        with (
            patch("app.graphs.onboarding._call_head_coach", return_value="Next?"),
            patch("app.services.onboarding_extraction.extract_block", return_value={}),
        ):
            run_onboarding_respond(thread_id, "bonjour", db_session)

        db_session.expire_all()
        row = db_session.get(AthleteModel, athlete.id)
        assert row.age == 24
        assert row.weight_kg == 77.0
