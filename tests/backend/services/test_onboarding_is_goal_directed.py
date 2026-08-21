"""Onboarding asks for what is missing, not for whatever block it is on.

Six fixed instructions drove the conversation. Block 4 said "collecte
l'historique sportif", block 5 said "fréquence souhaitée par discipline" -- so
the coach asked for running volume in blocks 3, 4 *and* 5, even after Phase A
gave it the full history and it visibly read it ("Tu cours 3x par semaine
depuis mai"). It was not forgetting. It was obeying.

The script is replaced by a gap list. The model is told what the profile still
lacks and picks what to ask; when nothing required is missing it summarises and
asks for confirmation.

Completion stays deterministic. Letting the model decide when onboarding is
over invites both failure modes: stopping with an unusable profile, or
interviewing forever. Gaps decide readiness; the model only decides wording.
"""
from __future__ import annotations

import pytest
from app.db.models import AthleteModel
from app.services.onboarding_goal import (
    REQUIRED_FIELDS,
    describe_gaps,
    profile_gaps,
)

ATHLETE = "goal-1"


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


def _athlete(db_session, **overrides) -> AthleteModel:
    """A row as it exists right after signup.

    Body measurements are NOT NULL on `athletes` and are always set when the
    row is created, so they are never a gap -- that is why they are not in
    REQUIRED_FIELDS.
    """
    fields: dict = {
        "id": ATHLETE,
        "name": "Simon",
        "age": 24,
        "sex": "M",
        "weight_kg": 77.1,
        "height_cm": 182.9,
        "hours_per_week": 8.0,
        "primary_sport": "running",
        "sports_json": "[]",
        "goals_json": "[]",
        "available_days_json": "[]",
        "equipment_json": "[]",
    }
    fields.update(overrides)
    row = AthleteModel(**fields)
    db_session.add(row)
    db_session.commit()
    return row


def _complete(db_session, **overrides) -> AthleteModel:
    fields = {
        "sports_json": '["running", "lifting"]',
        "goals_json": '["semi sous 2h"]',
        "sessions_per_week_json": '{"running": 3, "lifting": 4}',
    }
    fields.update(overrides)
    return _athlete(db_session, **fields)


class TestGapsAreFound:
    def test_a_fresh_athlete_is_missing_everything_required(self, db_session) -> None:
        gaps = profile_gaps(_athlete(db_session))

        assert set(gaps) == set(REQUIRED_FIELDS)

    def test_body_measurements_are_never_a_gap(self, db_session) -> None:
        """They are NOT NULL and set at signup; asking for them is the old bug."""
        for field in ("age", "sex", "weight_kg", "height_cm", "hours_per_week"):
            assert field not in REQUIRED_FIELDS

    def test_a_complete_athlete_has_no_required_gaps(self, db_session) -> None:
        assert profile_gaps(_complete(db_session)) == []

    @pytest.mark.parametrize(
        "field,override",
        [
            ("goals", {"goals_json": "[]"}),
            ("sessions_per_week", {"sessions_per_week_json": None}),
        ],
    )
    def test_each_missing_field_is_reported(
        self, db_session, field: str, override: dict
    ) -> None:
        gaps = profile_gaps(_complete(db_session, **override))

        assert gaps == [field]

    def test_missing_sports_drags_session_counts_with_it(self, db_session) -> None:
        """Counts cannot cover sports that are not known yet — that is not noise."""
        gaps = profile_gaps(_complete(db_session, sports_json="[]"))

        assert gaps == ["sports", "sessions_per_week"]

    def test_counts_must_cover_every_sport(self, db_session) -> None:
        """A partial answer used to close this gap and end onboarding early.

        On a live replay the extractor read "dek hockey 1x/semaine" as
        `{"biking": 1}`. That alone satisfied the requirement, so the profile
        looked complete after two answers and the athlete reached a plan
        without ever saying how often they run or lift.
        """
        athlete = _complete(db_session, sessions_per_week_json='{"running": 3}')

        assert "sessions_per_week" in profile_gaps(athlete)

    def test_an_empty_sports_list_counts_as_missing(self, db_session) -> None:
        """"[]" is not the same as "not asked yet" to a plan generator."""
        assert "sports" in profile_gaps(_complete(db_session, sports_json="[]"))


class TestGapsAreDescribedForTheModel:
    def test_the_description_names_the_missing_fields(self, db_session) -> None:
        text = describe_gaps(profile_gaps(_complete(db_session, goals_json="[]")))

        assert "objectif" in text.lower()

    def test_a_complete_profile_says_so(self, db_session) -> None:
        text = describe_gaps(profile_gaps(_complete(db_session)))

        assert text
        assert "aucun" in text.lower() or "rien" in text.lower()

    def test_it_never_returns_an_empty_string(self, db_session) -> None:
        """An empty instruction leaves the model to invent a purpose."""
        assert describe_gaps([]).strip()


class TestTheOldScriptIsGone:
    """Deleting the block instructions is the point, not a side effect."""

    def test_no_fixed_block_instructions_remain(self) -> None:
        from app.graphs import onboarding

        assert not hasattr(onboarding, "_BLOCK_INSTRUCTIONS"), (
            "the six-block script is what made the coach re-ask"
        )

    def test_the_prompt_builder_is_driven_by_gaps(self) -> None:
        import inspect

        from app.graphs import onboarding

        source = inspect.getsource(onboarding._onboarding_instruction)

        assert "gap" in source.lower()


class TestCompletionIsDeterministic:
    def test_a_profile_with_gaps_is_not_ready(self, db_session) -> None:
        from app.services.onboarding_goal import ready_to_confirm

        assert not ready_to_confirm(
            _complete(db_session, sessions_per_week_json=None), turns_taken=3
        )

    def test_a_complete_profile_is_ready(self, db_session) -> None:
        from app.services.onboarding_goal import ready_to_confirm

        assert ready_to_confirm(_complete(db_session), turns_taken=3)

    def test_an_endless_interview_is_cut_off(self, db_session) -> None:
        """The athlete must be able to reach a plan even if a field never lands."""
        from app.services.onboarding_goal import MAX_TURNS, ready_to_confirm

        assert ready_to_confirm(_athlete(db_session), turns_taken=MAX_TURNS)

    def test_the_cutoff_does_not_fire_early(self, db_session) -> None:
        from app.services.onboarding_goal import MAX_TURNS, ready_to_confirm

        assert not ready_to_confirm(_athlete(db_session), turns_taken=MAX_TURNS - 1)
