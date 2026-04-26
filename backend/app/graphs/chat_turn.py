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


# ─── Clinical escalation resources (§10.1.1) ─────────────────────────────────

_CLINICAL_RESOURCES = {
    "self_harm_signal": (
        "Je t'encourage à contacter une ligne d'aide immédiatement. "
        "Canada: 1-866-APPELLE (277-3553). "
        "Ton bien-être passe avant tout entraînement."
    ),
    "tca_declared": (
        "Ce sujet mérite un accompagnement spécialisé. "
        "Consulte un professionnel de santé ou un médecin avant de reprendre "
        "toute activité physique intense."
    ),
}
_CLINICAL_FALLBACK = (
    "Ce sujet dépasse le cadre de l'entraînement sportif. "
    "Consulte un professionnel de santé."
)


# ─── Specialist chain helpers (D5) ───────────────────────────────────────────

_NOTES_MAX_CHARS = 500  # prior_chain_specialist_notes cap per §10.1.2


def _build_specialist_content(
    view: HeadCoachView,
    user_message: str,
    prior_chain_notes: list[dict[str, str]] | None,
    clinical_flag: str | None,
) -> str:
    """Build user-turn content for a specialist in the chain."""
    lines = [f"Athlete context:\n{view.model_dump_json()}"]
    if clinical_flag:
        lines.append(f"clinical_context_flag: {clinical_flag}")
    if prior_chain_notes:
        notes_str = "; ".join(
            f"{n['specialist']}: {n['notes'][:_NOTES_MAX_CHARS]}"
            for n in prior_chain_notes
        )
        lines.append(f"prior_chain_specialist_notes: {notes_str}")
    lines.append(f"\nUser: {user_message}")
    return "\n".join(lines)


def _invoke_specialist_chain(
    specialist_chain_items: list[Any],
    view: HeadCoachView,
    user_message: str,
    clinical_flag: str | None,
) -> tuple[list[str], list[dict[str, str]]]:
    """Invoke up to 3 specialists sequentially, passing prior notes forward.

    Returns:
        (specialist_names, accumulated_notes) where accumulated_notes contains
        {specialist, notes} dicts for HC synthesis.
    """
    names: list[str] = []
    accumulated_notes: list[dict[str, str]] = []

    for item in specialist_chain_items[:3]:  # hard cap at 3
        spec_name = item.specialist
        prompt = _SPECIALIST_PROMPTS.get(
            spec_name,
            f"Tu es le {spec_name.title()} Coach de Resilio+.",
        )
        content = _build_specialist_content(
            view=view,
            user_message=user_message,
            prior_chain_notes=accumulated_notes if accumulated_notes else None,
            clinical_flag=clinical_flag,
        )
        response = _call_agent(system_prompt=prompt, user_content=content)
        names.append(spec_name)
        accumulated_notes.append({
            "specialist": spec_name,
            "notes": response[:_NOTES_MAX_CHARS],
        })

    return names, accumulated_notes


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

    Routes (D4+D5):
    - HEAD_COACH_DIRECT          → 1 LLM call (Head Coach)
    - SPECIALIST_TECHNICAL chain → N specialist calls + 1 HC synthesis (max 4 LLM calls)
    - CLINICAL_ESCALATION_IMMEDIATE → 0 LLM calls, hardcoded resources
    - OUT_OF_SCOPE               → 1 LLM call (Head Coach bounded response)
    - CLARIFICATION_NEEDED       → 1 LLM call (Head Coach intro) + tappable axes
    - handle_session_log RPE     → conditionally upgrades to Lifting consult (DEP-C4-001)

    Returns:
        {
            "final_response": str,
            "intent_decision": str,
            "specialists_consulted": list[str],
            "clarification_axes": list[str] | None,
            "thread_id": None,  # ephemeral — no persistent thread
        }
    """
    # 1. Load athlete + build view
    athlete = _get_athlete(athlete_id, db)
    view = build_head_coach_view(athlete)
    clinical_flag: str | None = getattr(athlete, "clinical_context_flag", None)

    # 2. Classify intent
    from_request = build_classify_intent_request(
        athlete=athlete,
        user_message=user_message,
        last_3_intents=last_3_intents,
        last_user_message=last_user_message,
    )
    intent: IntentClassification = classify_intent(from_request)

    specialists_consulted: list[str] = []
    clarification_axes: list[str] | None = None
    final_response: str

    # 3. Route by intent decision

    if intent.decision == "CLINICAL_ESCALATION_IMMEDIATE":
        # Zero LLM calls — return hardcoded clinical resources
        esc_type = intent.clinical_escalation_type or ""
        final_response = _CLINICAL_RESOURCES.get(esc_type, _CLINICAL_FALLBACK)

    elif intent.decision == "CLARIFICATION_NEEDED":
        # Head Coach formulates intro phrase; axes passed through for tappable UI
        clarification_axes = intent.clarification_axes or []
        hc_content = _format_head_coach_user_content(
            view=view,
            user_message=user_message,
        )
        final_response = _call_agent(
            system_prompt=HEAD_COACH_PROMPT,
            user_content=hc_content + "\n\nDecision: CLARIFICATION_NEEDED. "
            f"Generate a short intro phrase only (≤1 sentence). "
            f"Axes: {clarification_axes}",
        )

    elif intent.decision == "OUT_OF_SCOPE":
        hc_content = _format_head_coach_user_content(
            view=view,
            user_message=user_message,
        )
        final_response = _call_agent(
            system_prompt=HEAD_COACH_PROMPT,
            user_content=hc_content + "\n\nDecision: OUT_OF_SCOPE. "
            "Respond briefly: this topic is outside your coaching scope.",
        )

    elif intent.decision == "SPECIALIST_TECHNICAL" and intent.specialist_chain:
        # Chain specialists sequentially (D5), inject clinical_flag if acknowledged
        effective_flag = clinical_flag if intent.clinical_context_active_acknowledged else None

        names, chain_notes = _invoke_specialist_chain(
            specialist_chain_items=intent.specialist_chain,
            view=view,
            user_message=user_message,
            clinical_flag=effective_flag,
        )
        specialists_consulted = names

        # Head Coach synthesizes all specialist notes
        all_notes = "\n".join(
            f"{n['specialist'].title()} Coach:\n{n['notes']}" for n in chain_notes
        )
        hc_content = _format_head_coach_user_content(
            view=view,
            user_message=user_message,
            specialist_notes=all_notes,
        )
        final_response = _call_agent(
            system_prompt=HEAD_COACH_PROMPT,
            user_content=hc_content,
        )

    else:
        # HEAD_COACH_DIRECT (or fallback)
        # Check session_log RPE override first (DEP-C4-001)
        rpe_requires_lifting = _should_consult_lifting_for_session_log(session_log_context)
        if rpe_requires_lifting:
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
        else:
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
        "clarification_axes": clarification_axes,
        "thread_id": None,
    }
