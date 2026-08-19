"""Turn a coordinator routing decision into an actual graph run.

:class:`~app.services.coordinator_service.CoordinatorService` decides *which*
graph an event belongs to; this module runs it. The two are kept apart so unit
tests can exercise routing without an LLM, and so a surface that wants live
graphs opts in explicitly by passing an invoker.

Output keys are deliberately uniform for the transport layer:

``question`` / ``final_response``
    Text to send to the athlete.
``plan_proposal`` + ``plan_thread_id``
    A week awaiting approval; the transport sends it with approve/change/skip
    buttons rather than as plain text.
"""
from __future__ import annotations

import logging
from typing import Any, Protocol

from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..db.models import AthleteModel, ChatMessageModel
from .athlete_profile import athlete_profile_dict
from .coordinator_service import CoordinatorService

logger = logging.getLogger(__name__)

_RECENT_INTENT_LIMIT = 3


class PlanCreator(Protocol):
    """Structural subset of CoachingService used to open a plan proposal."""

    def create_plan(
        self,
        athlete_id: str,
        athlete_dict: dict[str, Any],
        load_history: list[float],
        db: Session,
    ) -> tuple[str, dict[str, Any] | None]: ...


class DefaultGraphInvoker:
    """Run the graph the coordinator selected and normalise its output."""

    def __init__(self, *, coaching: PlanCreator | None = None) -> None:
        self._coaching = coaching

    def invoke(
        self,
        graph_name: str,
        athlete_id: str,
        thread_id: str,
        payload: dict[str, Any],
        db: Session,
    ) -> dict[str, Any] | None:
        handler = getattr(self, f"_run_{graph_name}", None)
        if handler is None:
            logger.info("graph_invoker_no_handler", extra={"graph": graph_name})
            return None
        output: dict[str, Any] | None = handler(athlete_id, thread_id, payload, db)
        return output

    # ─── Graph handlers ──────────────────────────────────────────────────────

    def _run_chat_turn(
        self,
        athlete_id: str,
        thread_id: str,
        payload: dict[str, Any],
        db: Session,
    ) -> dict[str, Any] | None:
        from ..graphs.chat_turn import run_chat_turn

        message = _message_of(payload)
        if message is None:
            return None
        result: dict[str, Any] = run_chat_turn(
            athlete_id=athlete_id,
            user_message=message,
            db=db,
            last_3_intents=recent_intents(athlete_id, db),
        )
        return result

    def _run_onboarding(
        self,
        athlete_id: str,
        thread_id: str,
        payload: dict[str, Any],
        db: Session,
    ) -> dict[str, Any] | None:
        from ..graphs.onboarding import run_onboarding_respond, run_onboarding_start

        message = _message_of(payload)
        result: dict[str, Any] | None = None
        if message is not None:
            try:
                result = run_onboarding_respond(thread_id, message, db)
            except ValueError:
                # No live thread for this id — the process restarted, or this is
                # the athlete's first message. Ask block 1 instead of failing.
                result = None
        if result is None:
            result = run_onboarding_start(athlete_id, db)

        if result.get("status") == "completed":
            proposal = self._propose_plan(athlete_id, db)
            if proposal is not None:
                result = {**result, **proposal}
        return result

    def _run_followup_transition(
        self,
        athlete_id: str,
        thread_id: str,
        payload: dict[str, Any],
        db: Session,
    ) -> dict[str, Any] | None:
        from ..graphs.followup_transition import (
            run_followup_respond,
            run_followup_start,
        )

        message = _message_of(payload)
        if message is not None:
            try:
                respond_result: dict[str, Any] = run_followup_respond(
                    thread_id, message, db
                )
                return respond_result
            except ValueError:
                pass
        start_result: dict[str, Any] = run_followup_start(athlete_id, db)
        return start_result

    def _run_recovery_takeover(
        self,
        athlete_id: str,
        thread_id: str,
        payload: dict[str, Any],
        db: Session,
    ) -> dict[str, Any] | None:
        from ..graphs.recovery_takeover import (
            run_recovery_takeover_respond,
            run_recovery_takeover_start,
        )

        message = _message_of(payload) or str(payload.get("injury") or "").strip()
        if message:
            try:
                respond_result: dict[str, Any] = run_recovery_takeover_respond(
                    thread_id, message, db
                )
                return respond_result
            except ValueError:
                pass
        start_result: dict[str, Any] = run_recovery_takeover_start(
            athlete_id,
            message or "Injury reported over chat.",
            db,
        )
        return start_result

    def _run_plan_generation(
        self,
        athlete_id: str,
        thread_id: str,
        payload: dict[str, Any],
        db: Session,
    ) -> dict[str, Any] | None:
        return self._propose_plan(athlete_id, db)

    # ─── Internals ───────────────────────────────────────────────────────────

    def _propose_plan(
        self,
        athlete_id: str,
        db: Session,
    ) -> dict[str, Any] | None:
        athlete = db.query(AthleteModel).filter(AthleteModel.id == athlete_id).first()
        if athlete is None:
            return None
        plan_thread_id, proposed = self._plan_creator().create_plan(
            athlete_id=athlete_id,
            athlete_dict=athlete_profile_dict(athlete),
            load_history=[],
            db=db,
        )
        return {"plan_proposal": proposed, "plan_thread_id": plan_thread_id}

    def _plan_creator(self) -> PlanCreator:
        coaching = self._coaching
        if coaching is None:
            from .coaching_service import coaching_service

            coaching = coaching_service
            self._coaching = coaching
        return coaching


def recent_intents(athlete_id: str, db: Session) -> list[str]:
    """Return the athlete's last few classified intents, most recent last."""
    rows = (
        db.query(ChatMessageModel.intent_decision)
        .filter(
            ChatMessageModel.athlete_id == athlete_id,
            ChatMessageModel.intent_decision.is_not(None),
        )
        .order_by(desc(ChatMessageModel.created_at))
        .limit(_RECENT_INTENT_LIMIT)
        .all()
    )
    return [row[0] for row in reversed(rows) if row[0]]


def _message_of(payload: dict[str, Any]) -> str | None:
    message = payload.get("message")
    if isinstance(message, str) and message.strip():
        return message
    return None


def build_live_coordinator(
    *,
    coaching: PlanCreator | None = None,
) -> CoordinatorService:
    """Return a coordinator that actually runs graphs.

    The module-level ``coordinator_service`` singleton stays inert on purpose so
    routing can be unit-tested without an LLM; live surfaces build their own.
    """
    return CoordinatorService(
        graph_invoker=DefaultGraphInvoker(coaching=coaching),
        auto_advance_signup=True,
    )
