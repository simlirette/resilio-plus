"""followup_transition graph — Phase D (D9).

Conversation graph for the baseline_active → steady_state transition.
Two HITL interrupts:
  1. present_baseline  — Head Coach presents baseline results, asks for feedback
  2. confirm_first_plan — Head Coach confirms first plan before launch

If the athlete signals an objective adjustment, sets onboarding_reentry_active=True
and returns control to CoordinatorService for re-entry into Onboarding blocs.

Thread ID format: ``{athlete_id}:followup:{uuid4}``
Stored on ``AthleteModel.active_followup_thread_id``.
"""
from __future__ import annotations

import dataclasses
import os
import uuid
from typing import Any

import anthropic

from ..agents.prompts import HEAD_COACH_PROMPT
from ..core.head_coach_view_builder import build_head_coach_view
from ..db.models import AthleteModel

# ─── Constants ────────────────────────────────────────────────────────────────

_MODEL_CHAT = "claude-sonnet-4-6"
_MAX_TOKENS = 1024

# Steps in order
_STEPS = ["present_baseline", "confirm_first_plan"]


# ─── Thread state ─────────────────────────────────────────────────────────────


@dataclasses.dataclass
class _FollowupThread:
    thread_id: str
    athlete_id: str
    step: str  # current step name
    onboarding_reentry_active: bool
    status: str  # "in_progress" | "completed"


_thread_states: dict[str, _FollowupThread] = {}


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _get_athlete(athlete_id: str, db: Any) -> AthleteModel:
    athlete: AthleteModel | None = (
        db.query(AthleteModel).filter(AthleteModel.id == athlete_id).first()
    )
    if athlete is None:
        raise ValueError(f"Athlete {athlete_id!r} not found")
    return athlete


def _make_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY", "")
    return anthropic.Anthropic(api_key=api_key)


def _call_head_coach(instruction: str, context: str) -> str:
    client = _make_client()
    message = client.messages.create(
        model=_MODEL_CHAT,
        max_tokens=_MAX_TOKENS,
        system=HEAD_COACH_PROMPT,
        messages=[{
            "role": "user",
            "content": f"{context}\n\nInstruction: {instruction}",
        }],
    )
    return getattr(message.content[0], "text", "")


_STEP_INSTRUCTIONS: dict[str, str] = {
    "present_baseline": (
        "Présente les résultats du bloc de base à l'athlète : "
        "performances observées, zones identifiées, constats clés. "
        "Demande un retour sur les ressentis et si l'objectif reste valide."
    ),
    "confirm_first_plan": (
        "Propose de lancer le premier plan de coaching adapté. "
        "Demande confirmation avant de procéder."
    ),
}


# ─── Public entry points ──────────────────────────────────────────────────────


def run_followup_start(
    athlete_id: str,
    db: Any,
) -> dict[str, Any]:
    """Start the followup_transition conversation.

    Creates a new thread at the 'present_baseline' step.

    Args:
        athlete_id: Athlete identifier.
        db: SQLAlchemy session.

    Returns:
        {
            "thread_id": str,
            "step": "present_baseline",
            "question": str,
            "status": "in_progress",
        }
    """
    athlete = _get_athlete(athlete_id, db)
    view = build_head_coach_view(athlete)

    thread_id = f"{athlete_id}:followup:{uuid.uuid4()}"
    state = _FollowupThread(
        thread_id=thread_id,
        athlete_id=athlete_id,
        step="present_baseline",
        onboarding_reentry_active=False,
        status="in_progress",
    )
    _thread_states[thread_id] = state

    athlete.active_followup_thread_id = thread_id
    db.commit()

    instruction = _STEP_INSTRUCTIONS["present_baseline"]
    context = f"Athlete context:\n{view.model_dump_json()}"
    question = _call_head_coach(instruction, context)

    return {
        "thread_id": thread_id,
        "step": "present_baseline",
        "question": question,
        "status": "in_progress",
    }


def run_followup_respond(
    thread_id: str,
    user_response: str,
    db: Any,
    adjust_objective: bool = False,
) -> dict[str, Any]:
    """Process athlete response and advance to the next followup step.

    Step flow:
      present_baseline → (adjust_objective?) → confirm_first_plan → [complete]

    If ``adjust_objective=True`` at the feedback step, sets
    ``onboarding_reentry_active=True`` and returns immediately (no more steps).

    Args:
        thread_id: Followup thread identifier.
        user_response: Athlete's response to the current step.
        db: SQLAlchemy session.
        adjust_objective: Explicit flag for objective adjustment (for testing;
            production would infer from user_response content).

    Returns:
        Step response dict with next step or completion marker.

    Raises:
        ValueError: If thread_id not found.
    """
    if thread_id not in _thread_states:
        raise ValueError(f"Followup thread {thread_id!r} not found")

    state = _thread_states[thread_id]
    athlete = _get_athlete(state.athlete_id, db)
    view = build_head_coach_view(athlete)

    if state.step == "present_baseline":
        if adjust_objective:
            state.onboarding_reentry_active = True
            return {
                "thread_id": thread_id,
                "step": "adjust_objective",
                "question": None,
                "status": "in_progress",
                "onboarding_reentry_active": True,
            }
        # Advance to confirm_first_plan
        state.step = "confirm_first_plan"
        instruction = _STEP_INSTRUCTIONS["confirm_first_plan"]
        context = f"Athlete context:\n{view.model_dump_json()}"
        question = _call_head_coach(instruction, context)
        return {
            "thread_id": thread_id,
            "step": "confirm_first_plan",
            "question": question,
            "status": "in_progress",
        }

    if state.step == "confirm_first_plan":
        # Handoff: transition to steady_state
        state.status = "completed"
        athlete.journey_phase = "steady_state"
        db.commit()
        return {
            "thread_id": thread_id,
            "step": "completed",
            "question": None,
            "status": "completed",
            "journey_phase": "steady_state",
        }

    # Fallback for any other step
    return {
        "thread_id": thread_id,
        "step": state.step,
        "question": None,
        "status": state.status,
    }
