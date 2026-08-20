"""classify_intent service — Phase D (D3), DEP-C10-001.

Lightweight gateway component: classifies a free-form user message into one of
5 routing decisions using Haiku 4.5. Invoked by Head Coach on every free chat
message (non-structured trigger).

Contract:
  Input:  IntentClassificationRequest (DEP-C10-003)
  Output: IntentClassification (DEP-C10-003)
  Model:  claude-haiku-4-5-20251001
  Latency target: < 500ms (hard limit: 800ms → 1 retry on timeout)
  Observability: track_agent_call("classify_intent")
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any
from pathlib import Path

import anthropic

from ..observability.metrics import track_agent_call
from ..schemas.intent import IntentClassification, IntentClassificationRequest

# ─── Constants ────────────────────────────────────────────────────────────────

_MODEL = "claude-haiku-4-5-20251001"
_MAX_TOKENS = 1024
logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 8.0
"""Seconds allowed for one classification attempt.

Was 0.8s, chosen as a latency target rather than a failure threshold. A real
round trip - network plus generation - does not fit in it, so two attempts
would exhaust and the raised error took the whole conversation turn with it.
Override with CLASSIFY_INTENT_TIMEOUT_S.
"""

_FALLBACK_DECISION = "HEAD_COACH_DIRECT"
"""Where routing sends a message it could not classify.

Routing is an optimisation - it picks which specialist to consult. Losing it
should cost precision, not the conversation. The Head Coach prompt carries its
own clinical guardrails, so answering from it beats answering nothing.
"""

# Load prompt from docs/prompts/classify-intent.md (relative to repo root)
# parents[3] is the repository root: services -> app -> backend -> repo.
# This was parents[4], one level too high, so the file never resolved and the
# loader fell back to a 277-character stub while the real 82 KB routing prompt
# went unused.
_PROMPT_PATH = Path(__file__).parents[3] / "docs" / "prompts" / "classify-intent.md"


def _load_system_prompt() -> str:
    if _PROMPT_PATH.exists():
        return _PROMPT_PATH.read_text(encoding="utf-8")
    # Fallback: minimal inline prompt when running outside repo context (e.g. Docker)
    return (
        "You are classify_intent, a routing gateway. "
        "Classify the user message and emit a <contract_payload> JSON block "
        "with fields: decision, specialist_chain, clinical_escalation_type, "
        "clarification_axes, confidence, reasoning, language_detected, "
        "clinical_context_active_acknowledged."
    )


_SYSTEM_PROMPT = _load_system_prompt()

# ─── XML → IntentClassification parser ───────────────────────────────────────

_CONTRACT_PAYLOAD_RE = re.compile(
    r"<contract_payload>\s*(.*?)\s*</contract_payload>", re.DOTALL
)


_VALID_DECISIONS = {
    "HEAD_COACH_DIRECT",
    "SPECIALIST_TECHNICAL",
    "CLINICAL_ESCALATION_IMMEDIATE",
    "OUT_OF_SCOPE",
    "CLARIFICATION_NEEDED",
}

_VALID_ESCALATIONS = {"tca_declared", "self_harm_signal"}

_LANGUAGE_ALIASES = {
    "french": "fr",
    "francais": "fr",
    "français": "fr",
    "english": "en",
    "anglais": "en",
    "mixed": "fr-en-mixed",
    "fr-en": "fr-en-mixed",
}

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_BARE_OBJECT_RE = re.compile(r"(\{.*\})", re.DOTALL)


def _extract_payload(raw_text: str) -> dict[str, Any]:
    """Pull the payload out of whatever shape the model produced.

    The contract asks for <contract_payload> tags. Live output has also used a
    ```json fence, a bare object, and a fence wrapping a "contract_payload"
    key, sometimes followed by prose. Being strict here bought nothing: it sent
    every message to the fallback and no specialist was ever consulted.
    """
    candidates: list[str] = []
    tagged = _CONTRACT_PAYLOAD_RE.search(raw_text)
    if tagged:
        candidates.append(tagged.group(1))
    fenced = _JSON_FENCE_RE.search(raw_text)
    if fenced:
        candidates.append(fenced.group(1))
    bare = _BARE_OBJECT_RE.search(raw_text)
    if bare:
        candidates.append(bare.group(1))

    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        inner = data.get("contract_payload")
        return inner if isinstance(inner, dict) else data

    raise ValueError(
        "classify_intent: no usable JSON payload in model output. "
        f"Raw (first 500 chars): {raw_text[:500]!r}"
    )


def _coerce(data: dict[str, Any]) -> dict[str, Any]:
    """Normalise a payload that is close enough, without inventing meaning."""
    out = {k: v for k, v in data.items() if k in IntentClassification.model_fields}

    language = str(out.get("language_detected", "fr")).strip().lower()
    out["language_detected"] = _LANGUAGE_ALIASES.get(language, language)
    if out["language_detected"] not in {"fr", "en", "fr-en-mixed"}:
        out["language_detected"] = "fr"

    chain = out.get("specialist_chain")
    if isinstance(chain, str):
        chain = [{"specialist": chain}]
    if isinstance(chain, list):
        normalised = []
        for item in chain[:3]:
            if isinstance(item, str):
                item = {"specialist": item}
            if not isinstance(item, dict) or "specialist" not in item:
                continue
            # `reason` is required by the schema; the model often omits it.
            item.setdefault("reason", "routed by intent classifier")
            normalised.append(item)
        out["specialist_chain"] = normalised or None
    elif chain is not None:
        out["specialist_chain"] = None

    reasoning = str(out.get("reasoning") or "Routing decision.")
    out["reasoning"] = reasoning[:200]

    out.setdefault("clinical_context_active_acknowledged", False)
    out["clinical_context_active_acknowledged"] = bool(
        out.get("clinical_context_active_acknowledged")
    )

    confidence = out.get("confidence", 0.0)
    try:
        out["confidence"] = min(1.0, max(0.0, float(confidence)))
    except (TypeError, ValueError):
        out["confidence"] = 0.0

    escalation = out.get("clinical_escalation_type")
    if escalation not in _VALID_ESCALATIONS:
        # An invented type must not manufacture an emergency: live output once
        # classified "dead legs" as an acute neuromuscular escalation.
        out["clinical_escalation_type"] = None

    decision = out.get("decision")
    if decision not in _VALID_DECISIONS:
        # Honour an invented decision only when it carries a type we recognise.
        if out.get("clinical_escalation_type") in _VALID_ESCALATIONS:
            out["decision"] = "CLINICAL_ESCALATION_IMMEDIATE"
        else:
            logger.warning(
                "classify_intent_unknown_decision", extra={"decision": str(decision)}
            )
            out["decision"] = "HEAD_COACH_DIRECT"

    return out


def _parse_response(raw_text: str) -> IntentClassification:
    """Parse the model's routing decision, tolerating format drift."""
    return IntentClassification(**_coerce(_extract_payload(raw_text)))


# ─── User message serialiser ─────────────────────────────────────────────────

def _build_user_content(request: IntentClassificationRequest) -> str:
    """Serialise the IntentClassificationRequest as a structured user turn."""
    ctx = request.conversation_context_minimal
    profile = request.user_profile_minimal

    lines = [
        f"user_message: {request.user_message}",
        f"athlete_id: {profile.athlete_id}",
        f"journey_phase: {profile.journey_phase}",
        f"sports: {profile.sports}",
        f"clinical_context_flag: {profile.clinical_context_flag}",
        f"last_3_intents: {ctx.last_3_intents}",
        f"last_user_message: {ctx.last_user_message}",
    ]
    return "\n".join(lines)


# ─── Public entry point ───────────────────────────────────────────────────────

def _timeout_seconds() -> float:
    """Per-attempt budget, overridable via CLASSIFY_INTENT_TIMEOUT_S."""
    raw = os.environ.get("CLASSIFY_INTENT_TIMEOUT_S", "").strip()
    if not raw:
        return _TIMEOUT_SECONDS
    try:
        value = float(raw)
    except ValueError:
        return _TIMEOUT_SECONDS
    return value if value > 0 else _TIMEOUT_SECONDS


def _fallback_classification(reason: str) -> IntentClassification:
    """Route to the Head Coach when classification is unavailable."""
    logger.warning("classify_intent_fallback", extra={"reason": reason})
    return IntentClassification(
        decision="HEAD_COACH_DIRECT",
        specialist_chain=None,
        confidence=0.0,
        reasoning=f"Routing unavailable ({reason}); Head Coach answering directly.",
        language_detected="fr",
        clinical_context_active_acknowledged=False,
    )


def classify_intent(request: IntentClassificationRequest) -> IntentClassification:
    """Classify a free-form user message into a routing decision.

    Calls Haiku 4.5 with a structured system prompt and parses the
    <contract_payload> XML block from the response.

    Timeout: 800ms hard limit. Retries once on APITimeoutError.
    Raises: anthropic.APITimeoutError if both attempts time out.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY", "")
    client = anthropic.Anthropic(api_key=api_key)

    user_content = _build_user_content(request)

    def _call() -> IntentClassification:
        message = client.messages.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
            timeout=_timeout_seconds(),
        )
        raw: str = getattr(message.content[0], "text", "")
        return _parse_response(raw)

    with track_agent_call("classify_intent"):
        try:
            return _call()
        except anthropic.APITimeoutError:
            # Retry once on timeout (plan D3 spec: retry 1x on timeout)
            try:
                return _call()
            except Exception:
                return _fallback_classification("timeout")
        except Exception as exc:
            return _fallback_classification(type(exc).__name__)
