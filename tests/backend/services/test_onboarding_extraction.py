"""Onboarding must keep what it collects.

The six onboarding blocks stored their answers in `state.collected_data` -- a
process-local dict -- and the handoff wrote exactly one field to the database:
`journey_phase`. Everything the athlete said about their body, their goal,
their history and their preferences was returned to the caller and dropped.
Finish onboarding, restart the process, and the athlete row is untouched.

So this module extracts typed fields from each block answer and writes them.
Two rules carry most of the weight, because a coach acting on a bad number is
worse than one acting on none:

  - a value outside a physiologically sane range is refused, not clamped;
  - an extraction never overwrites an existing value with nothing.

VDOT is deliberately *not* asked of the model. The model reports the race and
the time; `calculate_vdot` derives the number. A language model guessing a
VDOT would set every prescribed pace for the whole block.
"""
from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest
from app.db.models import AthleteModel
from app.services.onboarding_extraction import apply_extraction, extract_block

FENCE = chr(96) * 3


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
        id="onb-1",
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
    )
    db_session.add(row)
    db_session.commit()
    return row


def _llm(payload: str):
    return patch(
        "app.services.onboarding_extraction._call_extractor", return_value=payload
    )


class TestExtractionParsing:
    def test_a_plain_json_object_is_read(self) -> None:
        with _llm('{"age": 31, "weight_kg": 70.5}'):
            assert extract_block(2, "31 ans, 70.5 kg") == {
                "age": 31,
                "weight_kg": 70.5,
            }

    def test_a_fenced_object_is_read(self) -> None:
        with _llm(FENCE + 'json\n{"age": 31}\n' + FENCE):
            assert extract_block(2, "31 ans")["age"] == 31

    def test_nulls_are_dropped_rather_than_stored(self) -> None:
        with _llm('{"age": 31, "weight_kg": null, "max_hr": null}'):
            assert extract_block(2, "31 ans") == {"age": 31}

    def test_unparseable_output_yields_nothing_and_does_not_raise(self) -> None:
        with _llm("I could not determine anything useful."):
            assert extract_block(2, "bonjour") == {}

    def test_an_llm_failure_yields_nothing_and_does_not_raise(self) -> None:
        """A broken extraction must not end the onboarding conversation."""
        with patch(
            "app.services.onboarding_extraction._call_extractor",
            side_effect=RuntimeError("api down"),
        ):
            assert extract_block(2, "31 ans") == {}


class TestValidation:
    @pytest.mark.parametrize(
        "field,value",
        [
            ("age", 4),
            ("age", 130),
            ("weight_kg", 12.0),
            ("weight_kg", 400.0),
            ("height_cm", 40.0),
            ("height_cm", 300.0),
            ("max_hr", 60),
            ("max_hr", 260),
            ("resting_hr", 10),
            ("resting_hr", 150),
            ("hours_per_week", 0.0),
            ("hours_per_week", 100.0),
        ],
    )
    def test_an_impossible_value_is_refused(
        self, db_session, athlete, field: str, value
    ) -> None:
        changed = apply_extraction(athlete, {field: value}, db_session)

        assert field not in changed
        assert getattr(athlete, field) != value

    def test_a_sane_value_is_written(self, db_session, athlete) -> None:
        changed = apply_extraction(athlete, {"resting_hr": 52}, db_session)

        assert "resting_hr" in changed
        assert athlete.resting_hr == 52

    def test_an_unknown_field_is_ignored(self, db_session, athlete) -> None:
        changed = apply_extraction(athlete, {"favourite_colour": "blue"}, db_session)

        assert changed == []
        assert not hasattr(athlete, "favourite_colour")

    def test_a_wrong_type_is_refused(self, db_session, athlete) -> None:
        changed = apply_extraction(athlete, {"age": "trente et un"}, db_session)

        assert changed == []
        assert athlete.age == 24


class TestNoClobber:
    def test_a_missing_value_never_erases_a_known_one(
        self, db_session, athlete
    ) -> None:
        apply_extraction(athlete, {"age": None, "weight_kg": None}, db_session)

        assert athlete.age == 24
        assert athlete.weight_kg == 77.0

    def test_a_later_answer_may_correct_an_earlier_one(
        self, db_session, athlete
    ) -> None:
        """Overwriting with a real value is the point; only nothing is refused."""
        apply_extraction(athlete, {"weight_kg": 75.5}, db_session)

        assert athlete.weight_kg == 75.5


class TestVdotIsDerivedNotGuessed:
    def test_a_race_result_becomes_a_vdot(self, db_session, athlete) -> None:
        changed = apply_extraction(
            athlete,
            {"race_distance": "10k", "race_time_seconds": 47 * 60},
            db_session,
        )

        assert "vdot" in changed
        assert athlete.vdot == 40.0

    def test_a_vdot_offered_directly_by_the_model_is_ignored(
        self, db_session, athlete
    ) -> None:
        """The model does not get to set training paces."""
        changed = apply_extraction(athlete, {"vdot": 65.0}, db_session)

        assert "vdot" not in changed
        assert athlete.vdot is None

    def test_an_unknown_distance_is_refused(self, db_session, athlete) -> None:
        changed = apply_extraction(
            athlete,
            {"race_distance": "backyard ultra", "race_time_seconds": 90000},
            db_session,
        )

        assert changed == []
        assert athlete.vdot is None

    def test_an_absurd_time_is_refused(self, db_session, athlete) -> None:
        changed = apply_extraction(
            athlete,
            {"race_distance": "10k", "race_time_seconds": 60},
            db_session,
        )

        assert changed == []
        assert athlete.vdot is None


class TestListAndDateFields:
    def test_goals_are_stored_as_json(self, db_session, athlete) -> None:
        apply_extraction(athlete, {"goals": ["semi Usti nad Labem"]}, db_session)

        assert "Usti" in athlete.goals_json

    def test_a_race_date_is_stored(self, db_session, athlete) -> None:
        apply_extraction(athlete, {"target_race_date": "2026-09-19"}, db_session)

        assert athlete.target_race_date == date(2026, 9, 19)

    def test_an_unparseable_date_is_refused(self, db_session, athlete) -> None:
        changed = apply_extraction(
            athlete, {"target_race_date": "next september"}, db_session
        )

        assert changed == []
        assert athlete.target_race_date is None

    def test_sports_are_normalised_and_stored(self, db_session, athlete) -> None:
        apply_extraction(athlete, {"sports": ["Running", "LIFTING"]}, db_session)

        assert "running" in athlete.sports_json
        assert "lifting" in athlete.sports_json

    def test_an_unknown_sport_is_dropped_not_stored(self, db_session, athlete) -> None:
        apply_extraction(athlete, {"sports": ["running", "quidditch"]}, db_session)

        assert "quidditch" not in athlete.sports_json
        assert "running" in athlete.sports_json


class TestPersistence:
    def test_the_write_survives_a_fresh_read(self, db_session, athlete) -> None:
        apply_extraction(athlete, {"resting_hr": 48}, db_session)
        db_session.expire_all()

        assert db_session.get(AthleteModel, "onb-1").resting_hr == 48
