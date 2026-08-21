"""Extract the profile from the whole conversation, not one block at a time.

Per-block extraction lost data in three distinct ways, all reproduced on the
live transcript and again on a replay after Phase A:

  - **Mismatched targets.** Block 2 asked the athlete for a recent race time;
    the block-2 extractor looked only for age, sex, weight and height. Both
    stated times — 5 km 26:47 and 10 km 1:04:43 — went in the bin, so `vdot`
    stayed NULL after an onboarding whose entire point was to establish it.
  - **Silent narrowing.** "Prioriser la course" rewrote `sports_json` from
    running *and* lifting to running alone, and `build_agents` then never
    instantiated the LiftingCoach. Zero lifting sessions in the plan.
  - **Sessions read as hours.** "je vise 3 sorties" became
    `hours_per_week = 3.0`, capping the week at 1h30.

Reading the whole conversation removes the first by construction. The other
two are rules, and rules need tests.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import patch

import pytest
from app.db.models import AthleteModel
from app.services.conversation import Turn
from app.services.onboarding_extraction import apply_extraction, extract_profile

ATHLETE = "prof-1"


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
        sports_json='["running", "lifting"]',
        goals_json="[]",
        available_days_json="[]",
        equipment_json="[]",
    )
    db_session.add(row)
    db_session.commit()
    return row


def _turns(*pairs: tuple[str, str]) -> list[Turn]:
    now = datetime(2026, 8, 20, 20, 0, tzinfo=timezone.utc)
    return [Turn(role=role, content=text, created_at=now) for role, text in pairs]


def _llm(payload: str):
    return patch(
        "app.services.onboarding_extraction._call_profile_extractor", return_value=payload
    )


class TestExtractionSeesTheWholeConversation:
    def test_every_turn_is_sent_to_the_extractor(self) -> None:
        captured: dict[str, str] = {}

        def _fake(prompt: str) -> str:
            captured["prompt"] = prompt
            return "{}"

        with patch(
            "app.services.onboarding_extraction._call_profile_extractor", side_effect=_fake
        ):
            extract_profile(
                _turns(
                    ("assistant", "Décris-toi."),
                    ("user", "Course et lifting, semi le 19 septembre"),
                    ("assistant", "Ton chrono récent ?"),
                    ("user", "5km: 26min47s"),
                )
            )

        assert "19 septembre" in captured["prompt"]
        assert "26min47s" in captured["prompt"], (
            "a race time from an earlier turn never reached the extractor"
        )

    def test_a_race_time_given_in_the_wrong_block_still_counts(self) -> None:
        """The exact live failure: the time was stated while being asked for weight."""
        payload = '{"race_distance": "5k", "race_time_seconds": 1607}'
        with _llm(payload):
            data = extract_profile(
                _turns(
                    ("assistant", "Ton âge, ton poids, ta taille ?"),
                    ("user", "5km: 26min47s, 10km: 1h04min43s."),
                )
            )

        assert data["race_distance"] == "5k"

    def test_an_empty_conversation_extracts_nothing(self) -> None:
        assert extract_profile([]) == {}


class TestScopeIsNeverNarrowedSilently:
    def test_a_priority_statement_does_not_delete_a_sport(
        self, db_session, athlete
    ) -> None:
        """"Prioriser la course" is about emphasis, not about dropping lifting."""
        apply_extraction(athlete, {"sports": ["running"]}, db_session)

        assert "lifting" in athlete.sports_json, "lifting was silently removed"
        assert "running" in athlete.sports_json

    def test_a_new_sport_is_added(self, db_session, athlete) -> None:
        apply_extraction(athlete, {"sports": ["swimming"]}, db_session)

        for sport in ("running", "lifting", "swimming"):
            assert sport in athlete.sports_json

    def test_an_explicit_removal_is_honoured(self, db_session, athlete) -> None:
        """The athlete may still drop a sport — it just has to be deliberate."""
        apply_extraction(athlete, {"sports_removed": ["lifting"]}, db_session)

        assert "lifting" not in athlete.sports_json
        assert "running" in athlete.sports_json

    def test_removing_every_sport_is_refused(self, db_session, athlete) -> None:
        """An athlete with no sports cannot be coached; that is a bad extraction."""
        apply_extraction(
            athlete, {"sports_removed": ["running", "lifting"]}, db_session
        )

        assert "running" in athlete.sports_json


class TestSessionsAreNotHours:
    def test_sessions_per_week_is_stored_separately(
        self, db_session, athlete
    ) -> None:
        changed = apply_extraction(
            athlete, {"sessions_per_week": {"running": 3, "lifting": 4}}, db_session
        )

        assert "sessions_per_week" in changed
        assert "running" in athlete.sessions_per_week_json
        assert athlete.hours_per_week == 8.0, "session counts overwrote weekly hours"

    def test_an_absurd_session_count_is_refused(self, db_session, athlete) -> None:
        apply_extraction(
            athlete, {"sessions_per_week": {"running": 40}}, db_session
        )

        assert not athlete.sessions_per_week_json

    def test_an_unknown_sport_is_dropped_from_the_counts(
        self, db_session, athlete
    ) -> None:
        apply_extraction(
            athlete,
            {"sessions_per_week": {"running": 3, "quidditch": 2}},
            db_session,
        )

        assert "quidditch" not in (athlete.sessions_per_week_json or "")
        assert "running" in athlete.sessions_per_week_json

    def test_hours_per_week_still_works_on_its_own(
        self, db_session, athlete
    ) -> None:
        apply_extraction(athlete, {"hours_per_week": 6.5}, db_session)

        assert athlete.hours_per_week == 6.5


class TestTheLiveConversationEndsWithAUsableProfile:
    """The whole point: replay the real answers and check the row is right."""

    def test_the_row_reflects_what_the_athlete_actually_said(
        self, db_session, athlete
    ) -> None:
        athlete.sports_json = '["running"]'
        athlete.hours_per_week = 8.0
        db_session.commit()

        extracted = {
            "sports": ["running", "lifting"],
            "sessions_per_week": {"running": 3, "lifting": 4},
            "hours_per_week": 8.0,
            "race_distance": "10k",
            "race_time_seconds": 3883,
            "target_race_date": "2026-09-19",
            "goals": ["semi-marathon Usti nad Labem sous 2h"],
        }
        apply_extraction(athlete, extracted, db_session)

        assert "lifting" in athlete.sports_json
        assert "running" in athlete.sessions_per_week_json
        assert athlete.hours_per_week == 8.0
        assert athlete.vdot is not None, "the stated race time produced no VDOT"
        assert athlete.target_race_date == date(2026, 9, 19)
