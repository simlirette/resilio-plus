"""Intent classification schemas — Phase D (D2).

Contracts for classify_intent service (D3) and chat_turn graph (D4).
DEP-C10-003.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .clinical import ClinicalContextFlag


class SpecialistTarget(BaseModel):
    """One specialist in a chain, produced by classify_intent."""

    specialist: Literal[
        "running", "lifting", "swimming", "biking", "nutrition", "recovery", "energy"
    ]
    reason: str = Field(..., max_length=100)


class ConversationContextMinimal(BaseModel):
    """Minimal conversation context passed to classify_intent.

    Intentionally small — only last 3 intents and last user message
    to keep classify_intent latency < 500ms.
    """

    last_3_intents: list[str] = Field(default_factory=list)
    """Last 3 classify_intent decision values (most recent last)."""

    last_user_message: str | None = None
    """Previous user message, for disambiguation."""


class UserProfileMinimal(BaseModel):
    """Minimal athlete profile passed to classify_intent."""

    athlete_id: str
    journey_phase: str
    sports: list[str] = Field(default_factory=list)
    clinical_context_flag: ClinicalContextFlag = None
    """Active clinical sensitivity flag — informs routing to CLINICAL_ESCALATION_IMMEDIATE."""


class IntentClassificationRequest(BaseModel):
    """Input to classify_intent service.

    Built by classify_intent_builder.build_classify_intent_request().
    """

    user_message: str
    conversation_context_minimal: ConversationContextMinimal
    user_profile_minimal: UserProfileMinimal


class IntentClassification(BaseModel):
    """Output of classify_intent service.

    Produced by Haiku 4.5 LLM call (D3) from structured XML output.
    Consumed by chat_turn graph route_intent node (D4).
    """

    decision: Literal[
        "HEAD_COACH_DIRECT",
        "SPECIALIST_TECHNICAL",
        "CLINICAL_ESCALATION_IMMEDIATE",
        "OUT_OF_SCOPE",
        "CLARIFICATION_NEEDED",
    ]

    specialist_chain: list[SpecialistTarget] | None = None
    """Ordered specialist chain (max 3). Only for SPECIALIST_TECHNICAL."""

    clinical_escalation_type: Literal["tca_declared", "self_harm_signal"] | None = None
    """Type of clinical escalation. Only for CLINICAL_ESCALATION_IMMEDIATE."""

    clarification_axes: list[str] | None = None
    """Tappable clarification options (2–4 items). Only for CLARIFICATION_NEEDED."""

    confidence: float = Field(..., ge=0.0, le=1.0)
    """Model confidence in the decision, 0–1."""

    reasoning: str = Field(..., max_length=200)
    """One-sentence rationale for the routing decision (≤200 chars)."""

    language_detected: Literal["fr", "en", "fr-en-mixed"]
    """Detected language of the user message."""

    clinical_context_active_acknowledged: bool
    """True when the model acknowledged an active clinical flag in its routing decision."""

    @field_validator("specialist_chain")
    @classmethod
    def _max_3_specialists(
        cls, v: list[SpecialistTarget] | None
    ) -> list[SpecialistTarget] | None:
        if v is not None and len(v) > 3:
            raise ValueError("specialist_chain must contain at most 3 specialists")
        return v
