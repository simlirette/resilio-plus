"""The conversation's memory — one place to write a turn and read it back.

`chat_messages` existed since Phase D and only `chat_turn` ever wrote to it.
Onboarding, which is where the athlete actually says who they are, wrote
nothing. After a full live onboarding the table held zero rows, and the coach
re-asked the goal one minute after being told it, re-asked the running history
two minutes after being told it, and re-asked the race distance that had been
stated twice. It was not forgetting; it had never been given anything to
remember.

Two deliberate asymmetries:

  - **Writing is best-effort.** A failed write costs the *next* turn some
    memory. Raising would cost the athlete the turn they are in.
  - **Reading is best-effort too**, and returns an empty history rather than
    failing. A coach with no memory is worse than one with memory, but far
    better than one that will not answer.

Ordering is by `created_at`, forced strictly increasing per process. Both
halves of a turn are written in the same instant, and consecutive turns can be
too; the row id is a random UUID and cannot break the tie, so a collision
would silently swap question and answer in the next prompt. Monotonicity is
process-local, which is enough: a single conversation is handled by one
process, and across processes the wall clock still separates turns.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)

ROLES = ("user", "assistant")

#: How many messages of history to hand a model. Twelve covers a full six-block
#: onboarding; beyond that the oldest turns matter less than the context they
#: cost.
DEFAULT_HISTORY_LIMIT = 12


@dataclass(frozen=True)
class Turn:
    """One message, in the shape an LLM message list wants."""

    role: str
    content: str
    created_at: datetime


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


_stamp_lock = Lock()
_last_stamp: datetime | None = None


def _next_stamp() -> datetime:
    """A timestamp strictly later than the last one handed out."""
    global _last_stamp
    with _stamp_lock:
        candidate = _utcnow()
        if _last_stamp is not None and candidate <= _last_stamp:
            candidate = _last_stamp + timedelta(microseconds=1)
        _last_stamp = candidate
        return candidate


def record_message(
    db: Any,
    athlete_id: str,
    role: str,
    content: str,
    *,
    intent_decision: str | None = None,
    specialists_consulted: str | None = None,
    at: datetime | None = None,
) -> None:
    """Write one message. Never raises for a database problem.

    An unknown role *does* raise: that is a programming error, not a runtime
    condition, and storing it would corrupt every later prompt.
    """
    if role not in ROLES:
        raise ValueError(f"role must be one of {ROLES}, got {role!r}")

    text = (content or "").strip()
    if not text:
        return

    try:
        from ..db.models import ChatMessageModel

        db.add(
            ChatMessageModel(
                id=str(uuid.uuid4()),
                athlete_id=athlete_id,
                role=role,
                content=text,
                intent_decision=intent_decision,
                specialists_consulted=specialists_consulted,
                created_at=at or _next_stamp(),
            )
        )
        db.commit()
    except Exception:
        logger.warning(
            "conversation_write_failed",
            extra={"athlete_id": athlete_id, "role": role},
            exc_info=True,
        )
        try:
            db.rollback()
        except Exception:
            pass


def record_turn(
    db: Any,
    athlete_id: str,
    user_message: str,
    assistant_response: str,
    *,
    intent_decision: str | None = None,
    specialists_consulted: str | None = None,
) -> None:
    """Write an athlete message and the coach's reply, in that order.

    Each message takes the next monotonic stamp, so the reply always sorts
    after the question that prompted it -- and the next turn always sorts
    after both.
    """
    record_message(db, athlete_id, "user", user_message)
    record_message(
        db,
        athlete_id,
        "assistant",
        assistant_response,
        intent_decision=intent_decision,
        specialists_consulted=specialists_consulted,
    )


def recent_turns(
    db: Any,
    athlete_id: str,
    limit: int = DEFAULT_HISTORY_LIMIT,
) -> list[Turn]:
    """The last `limit` messages, oldest first.

    Oldest first because that is the order an LLM message list is read in;
    handing it back newest-first inverts the conversation.
    """
    try:
        from sqlalchemy import desc

        from ..db.models import ChatMessageModel

        rows = (
            db.query(ChatMessageModel)
            .filter(ChatMessageModel.athlete_id == athlete_id)
            .order_by(desc(ChatMessageModel.created_at), desc(ChatMessageModel.id))
            .limit(max(0, limit))
            .all()
        )
    except Exception:
        logger.warning(
            "conversation_read_failed",
            extra={"athlete_id": athlete_id},
            exc_info=True,
        )
        return []

    return [
        Turn(role=row.role, content=row.content, created_at=row.created_at)
        for row in reversed(rows)
    ]


def as_messages(turns: list[Turn]) -> list[dict[str, str]]:
    """Turns in the shape the Anthropic SDK expects."""
    return [{"role": turn.role, "content": turn.content} for turn in turns]
