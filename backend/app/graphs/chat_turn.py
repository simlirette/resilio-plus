"""chat_turn graph — Phase D (D4).

Ephemeral (no persistent thread) conversational routing graph for steady_state.
Invoked by CoordinatorService on CHAT_FREE_MESSAGE events.

Routes:
  HEAD_COACH_DIRECT     → Head Coach responds directly (1 LLM call)
  SPECIALIST_TECHNICAL  → Specialist → Head Coach synthesizes (2 LLM calls for single)
  handle_session_log    → DEP-C4-001: Lifting consulted when RPE delta ≥ 1.5 or
                          recent_elevated_rpe_count ≥ 2; else Head Coach direct.

D5 extends this graph with:
  - SPECIALIST_TECHNICAL chain (max 3)
  - CLINICAL_ESCALATION_IMMEDIATE
  - OUT_OF_SCOPE
  - CLARIFICATION_NEEDED
  - CrossDisciplineInterferenceService (DEP-C4-004)
"""
from __future__ import annotations

import json
import os
import uuid
from typing import Any

import anthropic

from ..agents.prompts import (
    ENERGY_COACH_PROMPT,
    HEAD_COACH_PROMPT,
    LIFTING_COACH_PROMPT,
    NUTRITION_COACH_PROMPT,
    RECOVERY_COACH_PROMPT,
    RUNNING_COACH_PROMPT,
)
from ..core.classify_intent_builder import build_classify_intent_request
from ..core.head_coach_view_builder import build_head_coach_view
from ..db.models import AthleteModel, ChatMessageModel
from ..schemas.head_coach_view import HeadCoachView
from ..schemas.intent import IntentClassification
from ..services.classify_intent_service import classify_intent

# ─── Constants ────────────────────────────────────────────────────────────────

_MODEL_CHAT = "claude-sonnet-4-6"
"""Chat responses use Sonnet 4.6 for quality; classify_intent uses Haiku 4.5."""

_MAX_TOKENS_CHAT = 1024

# Map specialist name → system prompt
_SPECIALIST_PROMPTS: dict[str, str] = {
    "running": RUNNING_COACH_PROMPT,
    "lifting": LIFTING_COACH_PROMPT,
    "recovery": RECOVERY_COACH_PROMPT,
    "nutrition": NUTRITION_COACH_PROMPT,
    "energy": ENERGY_COACH_PROMPT,
    # swimming + biking use a generic fallback (prompts not yet in prompts.py)
    "swimming": (
        "Tu es le Swimming Coach de Resilio+. "
        "Réponds uniquement aux questions de natation."
    ),
    "biking": (
        "Tu es le Biking Coach de Resilio+. "
        "Réponds uniquement aux questions de cyclisme."
    ),
}

# RPE deviation threshold triggering Lifting consultation (DEP-C4-001)
_RPE_DEVIATION_THRESHOLD = 1.5
# Minimum recent elevated RPE session count triggering Lifting consultation (DEP-C4-001)
_RPE_PATTERN_SESSION_COUNT = 2


# ─── DB helpers (injectable for tests via patch) ─────────────────────────────

def _get_athlete(athlete_id: str, db: Any) -> AthleteModel:
    athlete: AthleteModel | None = (
        db.query(AthleteModel).filter(AthleteModel.id == athlete_id).first()
    )
    if athlete is None:
        raise ValueError(f"Athlete {athlete_id!r} not found")
    return athlete


def _persist_messages(
    athlete_id: str,
    user_message: str,
    assistant_response: str,
    intent_decision: str,
    specialists_consulted: list[str],
    db: Any,
) -> None:
    """Persist user + assistant messages for the chat history endpoint."""
    user_msg = ChatMessageModel(
        id=str(uuid.uuid4()),
        athlete_id=athlete_id,
        role="user",
        content=user_message,
        intent_decision=None,
        specialists_consulted=None,
    )
    assistant_msg = ChatMessageModel(
        id=str(uuid.uuid4()),
        athlete_id=athlete_id,
        role="assistant",
        content=assistant_response,
        intent_decision=intent_decision,
        specialists_consulted=json.dumps(specialists_consulted),
    )
    db.add(user_msg)
    db.add(assistant_msg)
    db.commit()


# ─── LLM invocation helpers ───────────────────────────────────────────────────

def _make_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY", "")
    return anthropic.Anthropic(api_key=api_key)


def _call_agent(
    system_prompt: str,
    user_content: str,
) -> str:
    """Call Anthropic with a given system prompt and user content, return text."""
    client = _make_client()
    message = client.messages.create(
        model=_MODEL_CHAT,
        max_tokens=_MAX_TOKENS_CHAT,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
    )
    return getattr(message.content[0], "text", "")


def _format_head_coach_user_content(
    view: HeadCoachView,
    user_message: str,
    specialist_notes: str | None = None,
) -> str:
    """Build user-turn content for Head Coach (direct or synthesis)."""
    lines = [
        f"athlete_id: {view.athlete_id}",
        f"journey_phase: {view.journey_phase}",
        f"sports: {view.sports}",
        f"hours_per_week: {view.hours_per_week}",
        f"coaching_mode: {view.coaching_mode}",
    ]
    if specialist_notes:
        lines.append(f"\nSpecialist notes:\n{specialist_notes}")
    lines.append(f"\nUser message: {user_message}")
    return "\n".join(lines)


# ─── Session log RPE routing (DEP-C4-001) ────────────────────────────────────

def _should_consult_lifting_for_session_log(
    session_log_context: dict[str, Any] | None,
) -> bool:
    """Return True if Lifting should be consulted based on session log RPE data.

    Conditions (DEP-C4-001):
    - rpe_actual ≥ rpe_prescribed + _RPE_DEVIATION_THRESHOLD (≥ 1.5), OR
    - recent_elevated_rpe_count ≥ _RPE_PATTERN_SESSION_COUNT (≥ 2 sessions)
    """
    if not session_log_context:
        return False
    rpe_actual = session_log_context.get("rpe_actual")
    rpe_prescribed = session_log_context.get("rpe_prescribed")
    recent_count = session_log_context.get("recent_elevated_rpe_count", 0)

    if rpe_actual is not None and rpe_prescribed is not None:
        if (rpe_actual - rpe_prescribed) >= _RPE_DEVIATION_THRESHOLD:
            return True

    if recent_count >= _RPE_PATTERN_SESSION_COUNT:
        return True

    return False


# ─── Public entry point ───────────────────────────────────────────────────────

def run_chat_turn(
    athlete_id: str,
    user_message: str,
    db: Any,
    last_3_intents: list[str],
    last_user_message: str | None = None,
    session_log_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute one ephemeral chat_turn and return the result dict.

    D4 routes:
    - HEAD_COACH_DIRECT   → 1 LLM call (Head Coach)
    - SPECIALIST_TECHNICAL (single) → 2 LLM calls (specialist + HC synthesis)
    - handle_session_log RPE check → conditionally upgrades to Lifting consult

    Returns:
        {
            "final_response": str,
            "intent_decision": str,
            "specialists_consulted": list[str],
            "thread_id": None,  # ephemeral — no persistent thread
        }
    """
    # 1. Load athlete + build view
    athlete = _get_athlete(athlete_id, db)
    view = build_head_coach_view(athlete)

    # 2. Classify intent
    from_request = build_classify_intent_request(
        athlete=athlete,
        user_message=user_message,
        last_3_intents=last_3_intents,
        last_user_message=last_user_message,
    )
    intent: IntentClassification = classify_intent(from_request)

    # 3. Apply session_log RPE override (DEP-C4-001)
    specialists_consulted: list[str] = []
    final_response: str

    # Determine if session_log RPE check upgrades to Lifting consultation
    rpe_requires_lifting = _should_consult_lifting_for_session_log(session_log_context)

    if intent.decision == "SPECIALIST_TECHNICAL" and intent.specialist_chain:
        # D4 handles single specialist only; D5 handles chain
        first_specialist = intent.specialist_chain[0].specialist

        # 4a. Invoke specialist
        specialist_prompt = _SPECIALIST_PROMPTS.get(
            first_specialist,
            f"Tu es le {first_specialist.title()} Coach de Resilio+.",
        )
        specialist_response = _call_agent(
            system_prompt=specialist_prompt,
            user_content=f"Athlete context:\n{view.model_dump_json()}\n\nUser: {user_message}",
        )
        specialists_consulted.append(first_specialist)

        # 4b. Head Coach synthesizes
        hc_content = _format_head_coach_user_content(
            view=view,
            user_message=user_message,
            specialist_notes=f"{first_specialist.title()} Coach:\n{specialist_response}",
        )
        final_response = _call_agent(
            system_prompt=HEAD_COACH_PROMPT,
            user_content=hc_content,
        )

    elif rpe_requires_lifting:
        # Session log RPE threshold exceeded → consult Lifting, HC synthesizes
        rpe_ctx_str = json.dumps(session_log_context)
        lifting_response = _call_agent(
            system_prompt=LIFTING_COACH_PROMPT,
            user_content=(
                f"Athlete context:\n{view.model_dump_json()}\n\n"
                f"User: {user_message}\nRPE context: {rpe_ctx_str}"
            ),
        )
        specialists_consulted.append("lifting")

        hc_content = _format_head_coach_user_content(
            view=view,
            user_message=user_message,
            specialist_notes=f"Lifting Coach (RPE alert):\n{lifting_response}",
        )
        final_response = _call_agent(
            system_prompt=HEAD_COACH_PROMPT,
            user_content=hc_content,
        )

    else:
        # HEAD_COACH_DIRECT (or unrecognised D5+ routes defaulting to HC)
        hc_content = _format_head_coach_user_content(view=view, user_message=user_message)
        final_response = _call_agent(
            system_prompt=HEAD_COACH_PROMPT,
            user_content=hc_content,
        )

    # 5. Persist messages
    _persist_messages(
        athlete_id=athlete_id,
        user_message=user_message,
        assistant_response=final_response,
        intent_decision=intent.decision,
        specialists_consulted=specialists_consulted,
        db=db,
    )

    return {
        "final_response": final_response,
        "intent_decision": intent.decision,
        "specialists_consulted": specialists_consulted,
        "thread_id": None,
    }
