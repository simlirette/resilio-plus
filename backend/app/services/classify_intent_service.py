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
import os
import re
from pathlib import Path

import anthropic

from ..observability.metrics import track_agent_call
from ..schemas.intent import IntentClassification, IntentClassificationRequest

# ─── Constants ────────────────────────────────────────────────────────────────

_MODEL = "claude-haiku-4-5-20251001"
_MAX_TOKENS = 1024
_TIMEOUT_SECONDS = 0.8  # 800ms hard limit

# Load prompt from docs/prompts/classify-intent.md (relative to repo root)
_PROMPT_PATH = Path(__file__).parents[4] / "docs" / "prompts" / "classify-intent.md"


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


def _parse_response(raw_text: str) -> IntentClassification:
    """Extract <contract_payload> JSON block from Haiku XML output and parse it."""
    match = _CONTRACT_PAYLOAD_RE.search(raw_text)
    if not match:
        raise ValueError(
            f"classify_intent: no <contract_payload> found in model output. "
            f"Raw (first 500 chars): {raw_text[:500]!r}"
        )
    payload_json = match.group(1)
    try:
        data = json.loads(payload_json)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"classify_intent: could not parse <contract_payload> as JSON: {exc}. "
            f"Payload: {payload_json[:300]!r}"
        ) from exc

    return IntentClassification(**data)


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
            timeout=_TIMEOUT_SECONDS,
        )
        raw: str = getattr(message.content[0], "text", "")
        return _parse_response(raw)

    with track_agent_call("classify_intent"):
        try:
            return _call()
        except anthropic.APITimeoutError:
            # Retry once on timeout (plan D3 spec: retry 1× on timeout)
            return _call()
