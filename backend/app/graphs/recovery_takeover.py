"""recovery_takeover graph — Phase D (D10).

Overlay graph for clinical Recovery takeovers. Activated when an injury is
reported and ``takeover_requested=True`` from ``run_injury_report()``.

Steps:
  assess_injury       — Recovery assesses the injury (interrupt HITL)
  monitor_recovery    — Recovery monitors progress (loop, interrupt per check-in)
  evaluate_and_return — Fused evaluate_readiness + propose_return_plan (DEP-C3-002)
  [complete]          — Handoff back to baseline flow

Overlay lifecycle:
  - Entry: ``recovery_takeover_active=True``, stores ``previous_journey_phase``
  - Exit:
    - previous_phase != "onboarding" → ``journey_phase=baseline_pending_confirmation``
    - previous_phase == "onboarding" → returns ``previous_journey_phase=onboarding``
      for CoordinatorService to route to suspended onboarding bloc

Thread ID format: ``{athlete_id}:recovery:{uuid4}``
Stored on ``AthleteModel.active_recovery_thread_id``.
"""
from __future__ import annotations

import dataclasses
import os
import uuid
from typing import Any

import anthropic

from ..agents.prompts import RECOVERY_COACH_PROMPT
from ..core.head_coach_view_builder import build_head_coach_view
from ..db.models import AthleteModel

# ─── Constants ────────────────────────────────────────────────────────────────

_MODEL_CHAT = "claude-sonnet-4-6"
_MAX_TOKENS = 1024


# ─── Thread state ─────────────────────────────────────────────────────────────


@dataclasses.dataclass
class _RecoveryThread:
    thread_id: str
    athlete_id: str
    step: str  # "assess_injury" | "monitor_recovery" | "evaluate_and_return" | "completed"
    previous_journey_phase: str
    status: str  # "in_progress" | "completed"


_thread_states: dict[str, _RecoveryThread] = {}


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


def _call_coach(system_prompt: str, instruction: str, context: str) -> str:
    client = _make_client()
    message = client.messages.create(
        model=_MODEL_CHAT,
        max_tokens=_MAX_TOKENS,
        system=system_prompt,
        messages=[{
            "role": "user",
            "content": f"{context}\n\nInstruction: {instruction}",
        }],
    )
    return getattr(message.content[0], "text", "")


# ─── Public entry points ──────────────────────────────────────────────────────


def run_recovery_takeover_start(
    athlete_id: str,
    injury_message: str,
    db: Any,
) -> dict[str, Any]:
    """Activate the recovery_takeover overlay and start injury assessment.

    - Sets ``recovery_takeover_active=True`` on the athlete record.
    - Stores ``previous_journey_phase`` for post-takeover routing.
    - Suspends active plan if one is present.
    - Creates a new recovery thread at the ``assess_injury`` step.

    Args:
        athlete_id: Athlete identifier.
        injury_message: Initial injury description.
        db: SQLAlchemy session.

    Returns:
        {
            "thread_id": str,
            "step": "assess_injury",
            "question": str,
            "status": "in_progress",
            "recovery_takeover_active": True,
        }
    """
    athlete = _get_athlete(athlete_id, db)
    view = build_head_coach_view(athlete)

    # Store previous phase and activate overlay
    prev_phase = athlete.journey_phase
    object.__setattr__(athlete, "previous_journey_phase", prev_phase)
    athlete.recovery_takeover_active = True

    # Suspend active plan if present
    active_plan_id: str | None = getattr(athlete, "active_plan_id", None)
    if active_plan_id:
        object.__setattr__(athlete, "suspended_active_plan_id", active_plan_id)

    thread_id = f"{athlete_id}:recovery:{uuid.uuid4()}"
    state = _RecoveryThread(
        thread_id=thread_id,
        athlete_id=athlete_id,
        step="assess_injury",
        previous_journey_phase=prev_phase,
        status="in_progress",
    )
    _thread_states[thread_id] = state

    athlete.active_recovery_thread_id = thread_id
    db.commit()

    context = f"Athlete context:\n{view.model_dump_json()}\nInjury report: {injury_message}"
    question = _call_coach(
        system_prompt=RECOVERY_COACH_PROMPT,
        instruction="Évalue cette blessure. Propose un protocole de gestion initial.",
        context=context,
    )

    return {
        "thread_id": thread_id,
        "step": "assess_injury",
        "question": question,
        "status": "in_progress",
        "recovery_takeover_active": True,
    }


def run_recovery_takeover_respond(
    thread_id: str,
    user_response: str,
    db: Any,
    ready_to_return: bool = False,
) -> dict[str, Any]:
    """Process athlete response within the recovery takeover overlay.

    Step transitions:
      assess_injury → monitor_recovery
      monitor_recovery (ready_to_return=False) → monitor_recovery (loop)
      monitor_recovery (ready_to_return=True) → evaluate_and_return
      evaluate_and_return → [complete, handoff]

    At handoff:
      - previous_phase != "onboarding" → ``journey_phase=baseline_pending_confirmation``
      - previous_phase == "onboarding" → return ``previous_journey_phase`` for Coordinator

    Args:
        thread_id: Recovery thread identifier.
        user_response: Athlete's response to the current step.
        db: SQLAlchemy session.
        ready_to_return: Signal athlete is ready to resume training (for testing
            and explicit API calls; production infers from user_response).

    Returns:
        Step response dict.

    Raises:
        ValueError: If thread_id not found.
    """
    if thread_id not in _thread_states:
        raise ValueError(f"Recovery thread {thread_id!r} not found")

    state = _thread_states[thread_id]
    athlete = _get_athlete(state.athlete_id, db)
    view = build_head_coach_view(athlete)
    context = f"Athlete context:\n{view.model_dump_json()}\nAthlète: {user_response}"

    if state.step == "assess_injury":
        state.step = "monitor_recovery"
        question = _call_coach(
            system_prompt=RECOVERY_COACH_PROMPT,
            instruction=(
                "Protocole accepté. Commence le suivi de récupération. "
                "Demande un check-in de l'état actuel."
            ),
            context=context,
        )
        return {
            "thread_id": thread_id,
            "step": "monitor_recovery",
            "question": question,
            "status": "in_progress",
        }

    if state.step == "monitor_recovery":
        if not ready_to_return:
            # Stay in monitor loop
            question = _call_coach(
                system_prompt=RECOVERY_COACH_PROMPT,
                instruction="Continue le monitoring. Évalue les symptômes actuels.",
                context=context,
            )
            return {
                "thread_id": thread_id,
                "step": "monitor_recovery",
                "question": question,
                "status": "in_progress",
            }
        # Ready → evaluate + propose return (DEP-C3-002 fused node)
        state.step = "evaluate_and_return"
        question = _call_coach(
            system_prompt=RECOVERY_COACH_PROMPT,
            instruction=(
                "L'athlète signale être prêt. Évalue la capacité de retour et "
                "propose un plan de retour progressif."
            ),
            context=context,
        )
        return {
            "thread_id": thread_id,
            "step": "evaluate_and_return",
            "question": question,
            "status": "in_progress",
        }

    if state.step == "evaluate_and_return":
        # Handoff
        state.step = "completed"
        state.status = "completed"
        athlete.recovery_takeover_active = False
        prev_phase = state.previous_journey_phase

        if prev_phase == "onboarding":
            db.commit()
            return {
                "thread_id": thread_id,
                "step": "completed",
                "question": None,
                "status": "completed",
                "recovery_takeover_active": False,
                "previous_journey_phase": "onboarding",
            }

        # All other phases → baseline_pending_confirmation
        athlete.journey_phase = "baseline_pending_confirmation"
        db.commit()
        return {
            "thread_id": thread_id,
            "step": "completed",
            "question": None,
            "status": "completed",
            "recovery_takeover_active": False,
            "journey_phase": "baseline_pending_confirmation",
        }

    # Fallback
    return {
        "thread_id": thread_id,
        "step": state.step,
        "question": None,
        "status": state.status,
    }
