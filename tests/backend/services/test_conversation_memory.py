"""Every turn the athlete and the coach exchange must be written down.

`chat_messages` existed and only `chat_turn` ever wrote to it. Onboarding --
the six exchanges that actually establish who the athlete is -- wrote nothing.
After a full live onboarding the table held **zero rows**, which is why the
coach re-asked the goal at 20:55 that the athlete had given at 20:54, re-asked
the running history at 20:56 that was answered at 20:54, and re-asked the race
distance at 21:01 that had been stated twice.

This module is the single place a turn is recorded and read back. Recording is
best-effort: a failed write costs the *next* turn some memory, while raising
would cost the athlete the current one.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from app.db.models import AthleteModel, ChatMessageModel
from app.services.conversation import recent_turns, record_message, record_turn

ATHLETE = "conv-1"
OTHER = "conv-2"


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
def _athletes(db_session):
    for athlete_id in (ATHLETE, OTHER):
        db_session.add(
            AthleteModel(
                id=athlete_id,
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
        )
    db_session.commit()


class TestRecording:
    def test_a_single_message_is_stored(self, db_session) -> None:
        record_message(db_session, ATHLETE, "user", "Hello")

        rows = db_session.query(ChatMessageModel).all()
        assert len(rows) == 1
        assert rows[0].role == "user"
        assert rows[0].content == "Hello"

    def test_a_turn_stores_both_halves_in_order(self, db_session) -> None:
        record_turn(db_session, ATHLETE, "Quel est mon plan ?", "Voici la semaine.")

        turns = recent_turns(db_session, ATHLETE)
        assert [t.role for t in turns] == ["user", "assistant"]
        assert turns[0].content == "Quel est mon plan ?"
        assert turns[1].content == "Voici la semaine."

    def test_an_empty_message_is_not_stored(self, db_session) -> None:
        """A blank turn is noise in the next prompt."""
        record_message(db_session, ATHLETE, "assistant", "   ")

        assert db_session.query(ChatMessageModel).count() == 0

    def test_an_unknown_role_is_refused(self, db_session) -> None:
        with pytest.raises(ValueError):
            record_message(db_session, ATHLETE, "system", "hi")


class TestReadingBack:
    def test_turns_come_back_oldest_first(self, db_session) -> None:
        """An LLM message list is chronological; reversing it inverts the story."""
        for i in range(4):
            record_message(db_session, ATHLETE, "user", f"m{i}")

        assert [t.content for t in recent_turns(db_session, ATHLETE)] == [
            "m0",
            "m1",
            "m2",
            "m3",
        ]

    def test_only_this_athletes_turns_come_back(self, db_session) -> None:
        record_message(db_session, ATHLETE, "user", "mine")
        record_message(db_session, OTHER, "user", "theirs")

        assert [t.content for t in recent_turns(db_session, ATHLETE)] == ["mine"]

    def test_the_limit_keeps_the_most_recent(self, db_session) -> None:
        """A long history must not blow the context window; keep the tail."""
        for i in range(10):
            record_message(db_session, ATHLETE, "user", f"m{i}")

        kept = [t.content for t in recent_turns(db_session, ATHLETE, limit=3)]

        assert kept == ["m7", "m8", "m9"]

    def test_no_history_is_an_empty_list(self, db_session) -> None:
        assert recent_turns(db_session, ATHLETE) == []


class TestOrderingIsStable:
    def test_messages_written_in_the_same_second_keep_their_order(
        self, db_session
    ) -> None:
        """created_at alone ties; ordering must not depend on insertion luck."""
        moment = datetime(2026, 8, 20, 20, 54, tzinfo=timezone.utc)
        with patch("app.services.conversation._utcnow", return_value=moment):
            record_turn(db_session, ATHLETE, "question", "answer")
            record_turn(db_session, ATHLETE, "question 2", "answer 2")

        assert [t.content for t in recent_turns(db_session, ATHLETE)] == [
            "question",
            "answer",
            "question 2",
            "answer 2",
        ]

    def test_insertion_order_is_the_order_that_comes_back(self, db_session) -> None:
        """The guarantee is insertion order, not wall-clock order.

        A conversation is written in the order it happens, so those are the
        same thing. They diverge only for a backfill, and a backfilled message
        sorting into the middle of a live conversation would be worse than it
        landing at the end.
        """
        for content in ("first", "second", "third"):
            record_message(db_session, ATHLETE, "user", content)

        assert [t.content for t in recent_turns(db_session, ATHLETE)] == [
            "first",
            "second",
            "third",
        ]

    def test_stamps_are_strictly_increasing(self, db_session) -> None:
        record_turn(db_session, ATHLETE, "q1", "a1")
        record_turn(db_session, ATHLETE, "q2", "a2")

        stamps = [t.created_at for t in recent_turns(db_session, ATHLETE)]

        assert stamps == sorted(stamps)
        assert len(set(stamps)) == len(stamps), "two messages share an instant"


class TestRecordingNeverBreaksTheTurn:
    def test_a_failed_write_is_swallowed(self, db_session) -> None:
        """Losing memory of a turn beats losing the turn itself."""

        class Exploding:
            def add(self, *a, **k):
                raise RuntimeError("db gone")

            def commit(self):
                raise RuntimeError("db gone")

            def rollback(self):
                pass

        record_message(Exploding(), ATHLETE, "user", "hello")  # must not raise

    def test_a_failed_read_returns_nothing(self, db_session) -> None:
        class Exploding:
            def query(self, *a, **k):
                raise RuntimeError("db gone")

        assert recent_turns(Exploding(), ATHLETE) == []
