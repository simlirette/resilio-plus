"""Onboarding graph — Phase D (D7 + D8).

HITL (Human-in-the-Loop) conversation graph for the onboarding journey phase.
Thread state persisted in-memory (_thread_states dict); production-grade
persistence can use SqliteSaver or a DB-backed table.

Blocs 1-3 (D7):
  1 — Accueil + présentation Head Coach
  2 — Profil de base (âge, sexe, poids, taille) — interrupt HITL
  3 — Objectif principal + horizon — interrupt HITL

Blocs 4-6 (D8):
  4 — Historique sportif + disciplines actives — interrupt HITL
  5 — Préférences entraînement (methodology_preferences) — DEP-C4-002
  6 — Confirmation scope + lancement plan → handoff

Injury mid-onboarding (D8, DEP-C3-003):
  suspend_onboarding_for_injury() — stores suspended block
  resume_onboarding_after_recovery() — resumes at suspended block

Thread ID format: ``{athlete_id}:onboarding:{uuid4}``
Stored on ``AthleteModel.active_onboarding_thread_id``.
"""
from __future__ import annotations

import dataclasses
import json
import logging
import os
import uuid
from typing import Any

import anthropic

from ..agents.prompts import HEAD_COACH_PROMPT
from ..core.head_coach_view_builder import build_head_coach_view
from ..db.models import AthleteModel
from ..schemas.head_coach_view import HeadCoachView
from ..services.conversation import (
    Turn,
    build_messages,
    recent_turns,
    record_message,
)
from ..services.onboarding_goal import (
    describe_gaps,
    describe_optional,
    optional_gaps,
    profile_gaps,
    ready_to_confirm,
)
from ..services.reply import OUTPUT_CONTRACT, athlete_facing

# ─── Constants ────────────────────────────────────────────────────────────────

_MODEL_CHAT = "claude-sonnet-4-6"
_MAX_TOKENS = 1024

# Total onboarding blocks (D7: 1-3, D8: 4-6)
#: Hard ceiling on questions. `ready_to_confirm` normally ends the
#: conversation earlier, as soon as the profile can support a plan.
_MAX_BLOCK = 12


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

logger = logging.getLogger(__name__)


# ─── Block definitions ────────────────────────────────────────────────────────

# Key used to store each block's response in collected_data
_BLOCK_DATA_KEYS: dict[int, str] = {
    1: "intro_response",
    2: "basic_profile",
    3: "goal_and_horizon",
    4: "sport_history",
    5: "methodology_preferences",
    6: "scope_confirmation",
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


def _call_head_coach(
    instruction: str,
    context: str,
    history: list[Turn] | None = None,
) -> str:
    client = _make_client()
    message = client.messages.create(
        model=_MODEL_CHAT,
        max_tokens=_MAX_TOKENS,
        system=HEAD_COACH_PROMPT,
        messages=build_messages(
            history, f"{context}\n\nInstruction: {instruction}"
        ),
    )
    return getattr(message.content[0], "text", "")


# ─── Thread state persistence ─────────────────────────────────────────────────
#
# `_thread_states` is the hot path and stays a plain dict. It is a *cache* in
# front of `athletes.onboarding_state_json`: a restart empties the dict, and
# without the column the athlete was silently sent back to block 1 with the
# coach asking everything again.


def _save_state(state: _OnboardingThread, db: Any) -> None:
    """Mirror one thread's state onto its athlete row."""
    athlete = db.get(AthleteModel, state.athlete_id)
    if athlete is None:
        return
    athlete.onboarding_state_json = json.dumps(
        {
            "thread_id": state.thread_id,
            "athlete_id": state.athlete_id,
            "current_block": state.current_block,
            "collected_data": state.collected_data,
            "status": state.status,
        },
        ensure_ascii=False,
    )
    db.commit()


def _restore_state(thread_id: str, db: Any) -> _OnboardingThread | None:
    """Rebuild a cached thread from the database, or return None.

    Corrupt or mismatched state yields None rather than raising: a restart is
    not the moment to start throwing errors at the athlete. They restart the
    conversation, which is bad; they do not get an exception, which is worse.
    """
    cached = _thread_states.get(thread_id)
    if cached is not None:
        return cached

    athlete_id = thread_id.split(":", 1)[0]
    athlete = db.get(AthleteModel, athlete_id)
    if athlete is None:
        return None

    raw = getattr(athlete, "onboarding_state_json", None)
    if not raw:
        return None

    try:
        stored = json.loads(raw)
        if stored.get("thread_id") != thread_id:
            return None
        state = _OnboardingThread(
            thread_id=str(stored["thread_id"]),
            athlete_id=str(stored["athlete_id"]),
            current_block=int(stored["current_block"]),
            collected_data=dict(stored.get("collected_data") or {}),
            status=str(stored["status"]),
        )
    except (ValueError, KeyError, TypeError):
        logger.warning(
            "onboarding_state_unreadable",
            extra={"athlete_id": athlete_id, "thread_id": thread_id},
            exc_info=True,
        )
        return None

    _thread_states[thread_id] = state
    return state


def _persist_block_answer(
    athlete: Any,
    block: int,
    db: Any,
) -> None:
    """Re-read the whole conversation and write what it says about the athlete.

    Per-block extraction only ever looked at one answer, against a field list
    written separately from the question the coach actually asked. The two
    drifted, and two stated race times -- given while the athlete was being
    asked for their weight -- were discarded, leaving `vdot` NULL after an
    onboarding whose entire purpose was to establish it.

    Re-extracting from the transcript each turn costs one Haiku call and makes
    the position of a fact in the conversation irrelevant.

    Best-effort by design. A failed extraction costs one pass and the next turn
    tries again; letting it raise would end the conversation.
    """
    from ..services.onboarding_extraction import apply_extraction, extract_profile

    try:
        data = extract_profile(recent_turns(db, athlete.id, limit=40))
        if not data:
            return
        changed = apply_extraction(athlete, data, db)
        if changed:
            logger.info(
                "onboarding_profile_updated",
                extra={"athlete_id": athlete.id, "block": block, "fields": changed},
            )
    except Exception:
        logger.warning(
            "onboarding_persist_failed",
            extra={"athlete_id": getattr(athlete, "id", None), "block": block},
            exc_info=True,
        )


def _onboarding_instruction(athlete: Any, turns_taken: int) -> str:
    """Tell the coach what the profile still lacks, not which form field to fill.

    Six fixed instructions used to drive this. Block 4 said "collecte
    l'historique sportif" and block 5 said "fréquence souhaitée par discipline",
    so the coach asked for running volume in blocks 3, 4 *and* 5 -- after Phase
    A had handed it the whole conversation and it visibly read it. It was not
    forgetting; it was obeying.
    """
    gaps = profile_gaps(athlete)

    if ready_to_confirm(athlete, turns_taken):
        return (
            "Tu as ce qu'il faut pour construire un plan. Résume à l'athlète ce "
            "que tu as retenu de lui — profil, sports, objectif, fréquence, "
            "contraintes — et demande-lui de confirmer ou de corriger avant que "
            "tu génères la semaine. Ne repose aucune question déjà répondue."
        )

    return (
        f"{describe_gaps(gaps)}. Demande à l'athlète uniquement ce qui manque, "
        "avec tes mots, en une ou deux questions maximum. Tu as l'historique "
        "complet de la conversation : ne repose jamais quelque chose qu'il a "
        "déjà dit, et appuie-toi sur ce qu'il vient de te donner. "
        f"{describe_optional(optional_gaps(athlete))}"
    )


def _onboarding_question(
    athlete: Any,
    view: HeadCoachView,
    history: list[Turn] | None,
    turns_taken: int,
) -> str:
    """Compose the coach's next message from the conversation and the gaps."""
    context = f"Athlete context (onboarding):\n{view.model_dump_json()}"
    raw = _call_head_coach(
        _onboarding_instruction(athlete, turns_taken) + OUTPUT_CONTRACT,
        context,
        history,
    )
    return athlete_facing(raw)


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

    restored = (
        _restore_state(existing_thread_id, db) if existing_thread_id else None
    )
    if restored is not None:
        # Resume existing thread at its current block, even across a restart
        state = restored
        question = _onboarding_question(
            athlete, view, recent_turns(db, athlete_id), state.current_block
        )
        record_message(db, athlete_id, "assistant", question)
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
    _save_state(state, db)

    question = _onboarding_question(athlete, view, recent_turns(db, athlete_id), 0)
    record_message(db, athlete_id, "assistant", question)
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
    state = _restore_state(thread_id, db)
    if state is None:
        raise ValueError(f"Onboarding thread {thread_id!r} not found")
    athlete = _get_athlete(state.athlete_id, db)
    view = build_head_coach_view(athlete)

    # Store current block response
    key = _BLOCK_DATA_KEYS.get(state.current_block, f"block_{state.current_block}")
    state.collected_data[key] = user_response
    # Recorded *before* the next question is composed, so the coach can see
    # the answer it is about to follow up on.
    record_message(db, state.athlete_id, "user", user_response)
    _persist_block_answer(athlete, state.current_block, db)

    next_block = state.current_block + 1

    # Onboarding ends when the profile can support a plan and the athlete has
    # confirmed the summary -- not after a fixed number of questions. The turn
    # ceiling inside `ready_to_confirm` is what stops a stubborn extraction
    # failure turning this into an interrogation with no exit.
    was_confirming = state.status == "confirming"
    if was_confirming or next_block > _MAX_BLOCK:
        state.status = "completed"
        state.current_block = next_block
        athlete.journey_phase = "baseline_pending_confirmation"
        db.commit()
        _save_state(state, db)
        return {
            "thread_id": thread_id,
            "current_block": next_block,
            "question": None,
            "status": "completed",
            "journey_phase": "baseline_pending_confirmation",
            "collected_data": dict(state.collected_data),
        }

    state.current_block = next_block
    state.status = (
        "confirming" if ready_to_confirm(athlete, next_block) else "in_progress"
    )
    _save_state(state, db)
    question = _onboarding_question(
        athlete, view, recent_turns(db, state.athlete_id), next_block
    )
    record_message(db, state.athlete_id, "assistant", question)

    return {
        "thread_id": thread_id,
        "current_block": next_block,
        "question": question,
        "status": "in_progress",
        "collected_data": dict(state.collected_data),
    }


# ─── Injury mid-onboarding (DEP-C3-003) ──────────────────────────────────────


def suspend_onboarding_for_injury(thread_id: str, db: Any) -> None:
    """Suspend current onboarding session due to an injury event.

    Stores the current block number on the athlete record as
    ``suspended_onboarding_block`` so recovery_takeover can hand back
    control to the correct block afterward (DEP-C3-003).

    Args:
        thread_id: Active onboarding thread identifier.
        db: SQLAlchemy session.
    """
    if thread_id not in _thread_states:
        return  # thread not found — no-op

    state = _thread_states[thread_id]
    athlete = _get_athlete(state.athlete_id, db)
    # suspended_onboarding_block may not be a DB column yet — set via object attr
    object.__setattr__(athlete, "suspended_onboarding_block", state.current_block)
    state.status = "suspended"
    db.commit()


def resume_onboarding_after_recovery(
    athlete_id: str,
    db: Any,
) -> dict[str, Any] | None:
    """Resume a suspended onboarding session after a recovery takeover.

    Called by CoordinatorService when ``previous_journey_phase == "onboarding"``.
    If ``suspended_onboarding_block`` is set, resumes at that block.
    If not set (injury happened from another phase), returns None — caller
    should route to baseline_pending_confirmation instead.

    Args:
        athlete_id: Athlete identifier.
        db: SQLAlchemy session.

    Returns:
        Block response dict if resumed, or None if no suspended block.
    """
    athlete = _get_athlete(athlete_id, db)
    suspended_block: int | None = getattr(athlete, "suspended_onboarding_block", None)

    if suspended_block is None:
        return None

    thread_id: str | None = getattr(athlete, "active_onboarding_thread_id", None)

    if thread_id and thread_id in _thread_states:
        state = _thread_states[thread_id]
        state.current_block = suspended_block
        state.status = "in_progress"
        object.__setattr__(athlete, "suspended_onboarding_block", None)
        db.commit()

        view = build_head_coach_view(athlete)
        question = _onboarding_question(
            athlete, view, recent_turns(db, athlete.id), suspended_block
        )
        record_message(db, athlete.id, "assistant", question)
        return {
            "thread_id": thread_id,
            "current_block": suspended_block,
            "question": question,
            "status": "in_progress",
            "collected_data": dict(state.collected_data),
        }

    return None
