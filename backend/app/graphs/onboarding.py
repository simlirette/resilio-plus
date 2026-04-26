"""Onboarding graph — Phase D (D7).

HITL (Human-in-the-Loop) conversation graph for the onboarding journey phase.
Thread state persisted in-memory (_thread_states dict) for D7; production-grade
persistence can use SqliteSaver or a DB-backed table.

Blocs 1-3 (D7):
  1 — Accueil + présentation Head Coach
  2 — Profil de base (âge, sexe, poids, taille) — interrupt HITL
  3 — Objectif principal + horizon — interrupt HITL

Thread ID format: ``{athlete_id}:onboarding:{uuid4}``
Stored on ``AthleteModel.active_onboarding_thread_id``.
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
from ..schemas.head_coach_view import HeadCoachView

# ─── Constants ────────────────────────────────────────────────────────────────

_MODEL_CHAT = "claude-sonnet-4-6"
_MAX_TOKENS = 1024

# D7 covers blocs 1-3; D8 will extend to 6
_MAX_BLOCK_D7 = 3


# ─── Thread state ─────────────────────────────────────────────────────────────


@dataclasses.dataclass
class _OnboardingThread:
    thread_id: str
    athlete_id: str
    current_block: int
    collected_data: dict[str, str]
    status: str  # "in_progress" | "completed"


# Module-level state (MemorySaver equivalent for D7)
_thread_states: dict[str, _OnboardingThread] = {}


# ─── Block definitions ────────────────────────────────────────────────────────

_BLOCK_INSTRUCTIONS: dict[int, str] = {
    1: (
        "Tu lances un onboarding pour un nouvel athlète. "
        "Présente-toi brièvement comme Head Coach Resilio+ et "
        "demande à l'athlète de se décrire en quelques mots "
        "(sport principal, niveau, objectif général)."
    ),
    2: (
        "Collecte le profil de base de l'athlète : âge, sexe biologique, "
        "poids (kg) et taille (cm). Pose les questions de façon conversationnelle."
    ),
    3: (
        "Demande l'objectif principal de l'athlète et l'horizon temporel "
        "(ex: finir un semi-marathon en 6 mois). Sois précis et direct."
    ),
}

# Key used to store each block's response in collected_data
_BLOCK_DATA_KEYS: dict[int, str] = {
    1: "intro_response",
    2: "basic_profile",
    3: "goal_and_horizon",
}


# ─── DB + LLM helpers ─────────────────────────────────────────────────────────


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


def _block_question(block: int, view: HeadCoachView) -> str:
    """Generate Head Coach question for the given onboarding block."""
    instruction = _BLOCK_INSTRUCTIONS.get(
        block, f"Continue l'onboarding au bloc {block}."
    )
    context = f"Athlete context (onboarding):\n{view.model_dump_json()}"
    return _call_head_coach(instruction, context)


# ─── Public entry points ──────────────────────────────────────────────────────


def run_onboarding_start(
    athlete_id: str,
    db: Any,
) -> dict[str, Any]:
    """Start a new onboarding session or resume an existing one.

    If the athlete's ``active_onboarding_thread_id`` points to a live thread,
    resumes at the current block. Otherwise creates a new thread at block 1.

    Args:
        athlete_id: Athlete identifier.
        db: SQLAlchemy session.

    Returns:
        {
            "thread_id": str,
            "current_block": int,
            "question": str,
            "status": "in_progress",
        }
    """
    athlete = _get_athlete(athlete_id, db)
    view = build_head_coach_view(athlete)

    existing_thread_id: str | None = getattr(athlete, "active_onboarding_thread_id", None)

    if existing_thread_id and existing_thread_id in _thread_states:
        # Resume existing thread at its current block
        state = _thread_states[existing_thread_id]
        question = _block_question(state.current_block, view)
        return {
            "thread_id": state.thread_id,
            "current_block": state.current_block,
            "question": question,
            "status": state.status,
        }

    # Create new thread
    thread_id = f"{athlete_id}:onboarding:{uuid.uuid4()}"
    state = _OnboardingThread(
        thread_id=thread_id,
        athlete_id=athlete_id,
        current_block=1,
        collected_data={},
        status="in_progress",
    )
    _thread_states[thread_id] = state

    # Persist thread_id on athlete record
    athlete.active_onboarding_thread_id = thread_id
    db.commit()

    question = _block_question(1, view)
    return {
        "thread_id": thread_id,
        "current_block": 1,
        "question": question,
        "status": "in_progress",
    }


def run_onboarding_respond(
    thread_id: str,
    user_response: str,
    db: Any,
) -> dict[str, Any]:
    """Process athlete response and advance to the next onboarding block.

    Stores the response in ``collected_data`` and increments ``current_block``.
    After the last D7 block (3), marks the thread as ``completed``.

    Args:
        thread_id: Onboarding thread identifier.
        user_response: Athlete's response to the current block question.
        db: SQLAlchemy session.

    Returns:
        {
            "thread_id": str,
            "current_block": int,
            "question": str | None,  # None when completed
            "status": "in_progress" | "completed",
            "collected_data": dict,
        }

    Raises:
        ValueError: If thread_id is not found in active thread states.
    """
    if thread_id not in _thread_states:
        raise ValueError(f"Onboarding thread {thread_id!r} not found")

    state = _thread_states[thread_id]
    athlete = _get_athlete(state.athlete_id, db)
    view = build_head_coach_view(athlete)

    # Store current block response
    key = _BLOCK_DATA_KEYS.get(state.current_block, f"block_{state.current_block}")
    state.collected_data[key] = user_response

    next_block = state.current_block + 1

    if next_block > _MAX_BLOCK_D7:
        state.status = "completed"
        state.current_block = next_block
        return {
            "thread_id": thread_id,
            "current_block": next_block,
            "question": None,
            "status": "completed",
            "collected_data": dict(state.collected_data),
        }

    state.current_block = next_block
    question = _block_question(next_block, view)

    return {
        "thread_id": thread_id,
        "current_block": next_block,
        "question": question,
        "status": "in_progress",
        "collected_data": dict(state.collected_data),
    }
