"""One turn of conversation, driven by the model.

The loop this replaces sent an imperative every turn — "Demande à l'athlète
uniquement ce qui manque" — and the model obeyed it instead of listening. On
2026-08-21 the athlete asked "quand t'ai-je dit 8h ?" and said "je veux
recommencer l'onboarding"; both were ignored and the same question came back
three times. The model was never asked to answer, so it never did.

Nothing here tells the model what to say. It receives:

  - the conversation so far,
  - the facts, each carrying where it came from,
  - the tools it may call.

What the turn *is* — an answer, an acknowledgement, a question, a plan — is its
decision. That is the difference between a coach and a narrator.

Two ceilings keep it honest: a bounded number of tool rounds, and a reply that
always exists. An athlete who gets silence has been failed more thoroughly than
one who gets an imperfect sentence.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, cast

import anthropic
from anthropic.types import ToolParam

from .coach_tools import TOOL_SCHEMAS, ToolContext, run_tool
from .conversation import build_messages, recent_turns

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 2048

#: How many times the model may call tools before it must speak. A tool-happy
#: model would otherwise keep working while the athlete waits.
MAX_ITERATIONS = 5

_FALLBACK_REPLY = (
    "Je n'arrive pas à répondre correctement là, tout de suite. Réessaie dans "
    "un instant."
)


@dataclass
class TurnResult:
    reply: str
    ok: bool = True
    tools_used: list[str] = field(default_factory=list)


def _make_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get(
        "CLAUDE_API_KEY", ""
    )
    return anthropic.Anthropic(api_key=api_key)


def _facts(athlete_id: str, db: Any) -> str:
    """Everything known about the athlete, with provenance.

    Provenance is not decoration. Without it the coach told the athlete "tu m'as
    indiqué 8 heures par semaine" about a value that came from a bootstrap
    script. A coach that cannot tell what it was told from what it assumed will
    eventually put words in the athlete's mouth.
    """
    try:
        from ..core.head_coach_view_builder import build_head_coach_view
        from ..db.models import AthleteModel

        athlete = db.get(AthleteModel, athlete_id)
        if athlete is None:
            return "Profil introuvable."
        view = build_head_coach_view(athlete, db)
    except Exception:
        logger.warning("facts_unavailable", extra={"athlete_id": athlete_id})
        return "Profil momentanément illisible."

    from .profile_provenance import describe_profile

    return describe_profile(view, db, athlete_id)


def _text_of(message: Any) -> str:
    parts = [
        getattr(block, "text", "")
        for block in getattr(message, "content", []) or []
        if getattr(block, "type", "") == "text"
    ]
    return "\n".join(part for part in parts if part).strip()


def _tool_calls(message: Any) -> list[Any]:
    return [
        block
        for block in getattr(message, "content", []) or []
        if getattr(block, "type", "") == "tool_use"
    ]


def run_coach_turn(athlete_id: str, user_message: str, db: Any) -> TurnResult:
    """Answer one athlete message. Never raises."""
    from ..agents.prompts import HEAD_COACH_PROMPT
    from .reply import athlete_facing

    context = ToolContext(athlete_id=athlete_id, db=db)
    used: list[str] = []

    try:
        client = _make_client()
        history = recent_turns(db, athlete_id)
        messages: list[Any] = list(
            build_messages(
                history,
                f"{_facts(athlete_id, db)}\n\nMessage de l'athlète : {user_message}",
            )
        )

        # At most MAX_ITERATIONS tool rounds, then one call that must speak.
        for _ in range(MAX_ITERATIONS):
            message = client.messages.create(
                model=_MODEL,
                max_tokens=_MAX_TOKENS,
                system=HEAD_COACH_PROMPT,
                # cast: the schemas are hand-written dicts in coach_tools, which
                # mypy cannot narrow to the SDK's TypedDict.
                tools=cast(list[ToolParam], TOOL_SCHEMAS),
                messages=messages,
            )
            calls = _tool_calls(message)
            if not calls:
                reply = athlete_facing(_text_of(message)) or _FALLBACK_REPLY
                return TurnResult(reply=reply, tools_used=used)

            messages.append({"role": "assistant", "content": message.content})
            results = []
            for call in calls:
                outcome = run_tool(call.name, dict(call.input or {}), context)
                used.append(call.name)
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": call.id,
                        "content": outcome.content,
                        "is_error": not outcome.ok,
                    }
                )
            messages.append({"role": "user", "content": results})

        # Ceiling reached: ask once for a sentence, with no tools on the table.
        closing = client.messages.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            system=HEAD_COACH_PROMPT,
            messages=messages,
        )
        reply = athlete_facing(_text_of(closing)) or _FALLBACK_REPLY
        return TurnResult(reply=reply, tools_used=used)

    except Exception:
        logger.warning("coach_turn_failed", extra={"athlete_id": athlete_id}, exc_info=True)
        return TurnResult(reply=_FALLBACK_REPLY, ok=False, tools_used=used)
