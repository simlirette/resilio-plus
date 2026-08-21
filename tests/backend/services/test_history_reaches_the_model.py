"""The stored conversation must actually be sent to the model.

Phase A1 gave the system a memory. This pins that something reads it.

Both LLM entry points sent a single user turn and nothing else:

    messages=[{"role": "user", "content": user_content}]

so every reply was generated as though the conversation had just begun. On the
first live onboarding that produced a coach which asked for the goal at 20:55
after being told it at 20:54, asked for the running history at 20:56 after
being told it at 20:54, and asked for the race distance at 21:01 after it had
been stated twice.

Scope note: history goes to the Head Coach, which is the voice the athlete
hears. Specialists are consulted with a targeted question plus the notes they
need; giving each of up to three of them the whole transcript multiplies the
token cost of a turn for a part of the answer the athlete never reads.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from app.db.models import AthleteModel
from app.services.conversation import Turn, as_messages, record_message

ATHLETE = "hist-1"


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
        sports_json='["running", "lifting"]',
        goals_json="[]",
        available_days_json="[]",
        equipment_json="[]",
        journey_phase="onboarding",
    )
    db_session.add(row)
    db_session.commit()
    return row


@pytest.fixture(autouse=True)
def _clean_onboarding_cache():
    from app.graphs import onboarding

    onboarding._thread_states.clear()
    yield
    onboarding._thread_states.clear()


def _captured_client(captured: dict[str, Any]) -> MagicMock:
    """An Anthropic stand-in that records the messages it was handed."""
    block = MagicMock()
    block.text = "Réponse du coach."
    message = MagicMock()
    message.content = [block]

    client = MagicMock()

    def _create(**kwargs):
        captured["messages"] = kwargs.get("messages")
        captured["system"] = kwargs.get("system")
        return message

    client.messages.create.side_effect = _create
    return client


class TestAsMessages:
    def test_turns_become_an_anthropic_message_list(self) -> None:
        from datetime import datetime, timezone

        now = datetime(2026, 8, 20, tzinfo=timezone.utc)
        turns = [
            Turn(role="user", content="Salut", created_at=now),
            Turn(role="assistant", content="Bonjour", created_at=now),
        ]

        assert as_messages(turns) == [
            {"role": "user", "content": "Salut"},
            {"role": "assistant", "content": "Bonjour"},
        ]


class TestOnboardingSendsHistory:
    def test_the_next_question_sees_the_previous_answers(self, db_session) -> None:
        from app.graphs.onboarding import run_onboarding_respond, run_onboarding_start

        captured: dict[str, Any] = {}

        with (
            patch("app.graphs.onboarding._make_client", return_value=_captured_client(captured)),
            patch("app.services.onboarding_extraction.extract_block", return_value={}),
        ):
            thread_id = str(run_onboarding_start(ATHLETE, db_session)["thread_id"])
            run_onboarding_respond(
                thread_id, "Mon objectif est un semi le 19 septembre", db_session
            )

        sent = captured["messages"]
        assert len(sent) > 1, "the model still received a single isolated turn"
        joined = " ".join(m["content"] for m in sent)
        assert "19 septembre" in joined, "the athlete's answer never reached the model"

    def test_the_athlete_turn_is_recorded_before_the_question_is_built(
        self, db_session
    ) -> None:
        """Otherwise the coach composes its next question without the answer."""
        from app.graphs.onboarding import run_onboarding_respond, run_onboarding_start

        captured: dict[str, Any] = {}

        with (
            patch("app.graphs.onboarding._make_client", return_value=_captured_client(captured)),
            patch("app.services.onboarding_extraction.extract_block", return_value={}),
        ):
            thread_id = str(run_onboarding_start(ATHLETE, db_session)["thread_id"])
            run_onboarding_respond(thread_id, "Course et lifting", db_session)

        roles = [m["role"] for m in captured["messages"]]
        assert roles[-1] == "user"
        assert "assistant" in roles, "the coach's own question is missing from history"

    def test_the_whole_exchange_is_persisted(self, db_session) -> None:
        from app.db.models import ChatMessageModel
        from app.graphs.onboarding import run_onboarding_respond, run_onboarding_start

        captured: dict[str, Any] = {}

        with (
            patch("app.graphs.onboarding._make_client", return_value=_captured_client(captured)),
            patch("app.services.onboarding_extraction.extract_block", return_value={}),
        ):
            thread_id = str(run_onboarding_start(ATHLETE, db_session)["thread_id"])
            run_onboarding_respond(thread_id, "Course et lifting", db_session)

        rows = db_session.query(ChatMessageModel).all()
        contents = [r.content for r in rows]
        assert "Course et lifting" in contents, "the athlete's message was not stored"
        assert any(r.role == "assistant" for r in rows)


class TestChatTurnSendsHistory:
    def test_the_head_coach_receives_earlier_turns(self, db_session) -> None:
        from app.graphs.chat_turn import _call_agent

        record_message(db_session, ATHLETE, "user", "Je vise un semi en septembre")
        record_message(db_session, ATHLETE, "assistant", "Compris.")

        from app.services.conversation import recent_turns

        captured: dict[str, Any] = {}
        with patch("app.graphs.chat_turn._make_client", return_value=_captured_client(captured)):
            _call_agent(
                system_prompt="sys",
                user_content="Et pour cette semaine ?",
                history=recent_turns(db_session, ATHLETE),
            )

        sent = captured["messages"]
        assert [m["role"] for m in sent] == ["user", "assistant", "user"]
        assert sent[-1]["content"] == "Et pour cette semaine ?"
        assert "septembre" in sent[0]["content"]

    def test_no_history_still_sends_a_single_turn(self, db_session) -> None:
        from app.graphs.chat_turn import _call_agent

        captured: dict[str, Any] = {}
        with patch("app.graphs.chat_turn._make_client", return_value=_captured_client(captured)):
            _call_agent(system_prompt="sys", user_content="Bonjour")

        assert captured["messages"] == [{"role": "user", "content": "Bonjour"}]


class TestHistoryShapeIsValid:
    """Anthropic rejects a message list that does not alternate from `user`."""

    def test_a_leading_assistant_turn_survives_behind_an_opener(
        self, db_session
    ) -> None:
        """Onboarding opens with the coach; that question must not be thrown away.

        Dropping it was the first attempt, and it discarded the very question
        the athlete's next message was answering.
        """
        from app.graphs.chat_turn import _call_agent
        from app.services.conversation import recent_turns

        record_message(db_session, ATHLETE, "assistant", "Décris-toi en quelques mots.")
        record_message(db_session, ATHLETE, "user", "Course et lifting")

        captured: dict[str, Any] = {}
        with patch("app.graphs.chat_turn._make_client", return_value=_captured_client(captured)):
            _call_agent(
                system_prompt="sys",
                user_content="Et maintenant ?",
                history=recent_turns(db_session, ATHLETE),
            )

        sent = captured["messages"]
        assert sent[0]["role"] == "user", "the API needs the list to start with user"
        joined = " ".join(m["content"] for m in sent)
        assert "Décris-toi" in joined, "the coach's opening question was discarded"
        assert "Course et lifting" in joined

    def test_consecutive_same_role_turns_are_merged(self, db_session) -> None:
        from app.graphs.chat_turn import _call_agent
        from app.services.conversation import recent_turns

        record_message(db_session, ATHLETE, "user", "Première partie")
        record_message(db_session, ATHLETE, "user", "Deuxième partie")

        captured: dict[str, Any] = {}
        with patch("app.graphs.chat_turn._make_client", return_value=_captured_client(captured)):
            _call_agent(
                system_prompt="sys",
                user_content="Suite",
                history=recent_turns(db_session, ATHLETE),
            )

        roles = [m["role"] for m in captured["messages"]]
        assert roles == ["user"], f"roles must alternate, got {roles}"
        assert "Première partie" in captured["messages"][0]["content"]
        assert "Deuxième partie" in captured["messages"][0]["content"]
