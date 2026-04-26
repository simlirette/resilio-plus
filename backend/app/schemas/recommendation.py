"""Recommendation contract schema — Phase D (D2), DEP-C4-006.

Extends the V1 AgentRecommendation dataclass concept with a Pydantic model
that enforces B3 validators REC1 and REC2, including the new INTERPRETATION mode.

This is a NEW Pydantic contract — does not modify the frozen AgentRecommendation
dataclass in agents/base.py (used by plan_generation graph nodes).
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, model_validator

# ─── Trigger constants ────────────────────────────────────────────────────────

# Valid trigger values and their required mode (B3 v2 REC2 mapping)
_REC2_TRIGGER_TO_MODE: dict[str, str] = {
    "PLAN_GEN_DELEGATE_SPECIALISTS": "planning",
    "CHAT_WEEKLY_REPORT": "review",
    "CHAT_SESSION_LOG_INTERPRETATION": "interpretation",   # DEP-C4-006
    "CHAT_TECHNICAL_QUESTION_LIFTING": "interpretation",   # DEP-C4-006
}

# Fields forbidden in INTERPRETATION mode (REC1 B3 v2)
_INTERPRETATION_FORBIDDEN_FIELDS = frozenset({
    "sessions",
    "block_theme",
    "generation_mode",
    "weekly_volume_target",
    "weekly_intensity_distribution",
    "projected_strain_contribution",
    "block_analysis",
    "proposed_trade_offs",
})


# ─── Enum ────────────────────────────────────────────────────────────────────

class RecommendationMode(str, Enum):
    PLANNING = "planning"
    REVIEW = "review"
    INTERPRETATION = "interpretation"   # DEP-C4-006: new mode for conditional chat consultations


# ─── Pydantic model ──────────────────────────────────────────────────────────

class Recommendation(BaseModel):
    """Structured output contract for specialist agents in Phase D chat flows.

    Validators:
    - REC2: trigger ↔ mode mapping must be consistent (B3 v2).
    - REC1: INTERPRETATION mode requires notes_for_head_coach and forbids
            planning-specific fields (B3 v2).
    """

    agent_name: str
    trigger: str
    mode: RecommendationMode

    # Common optional fields
    notes_for_head_coach: str | None = None
    flag_for_head_coach: str | None = None

    # PLANNING mode fields (all optional, validated via REC1)
    sessions: list[dict[str, Any]] | None = None
    block_theme: str | None = None
    generation_mode: str | None = None
    weekly_volume_target: int | None = None
    weekly_intensity_distribution: dict[str, float] | None = None
    projected_strain_contribution: float | None = None

    # REVIEW mode fields
    block_analysis: str | None = None
    proposed_trade_offs: str | None = None

    @model_validator(mode="after")
    def _validate_rec2_and_rec1(self) -> "Recommendation":
        """REC2: trigger must map to declared mode.
        REC1: INTERPRETATION mode constraints.
        """
        # ── REC2 ──────────────────────────────────────────────────────────────
        expected_mode = _REC2_TRIGGER_TO_MODE.get(self.trigger)
        if expected_mode is None:
            raise ValueError(
                f"REC2 violation: trigger {self.trigger!r} is not admissible. "
                f"Allowed triggers: {sorted(_REC2_TRIGGER_TO_MODE)}"
            )
        if self.mode.value != expected_mode:
            raise ValueError(
                f"REC2 violation: trigger {self.trigger!r} requires mode "
                f"{expected_mode!r}, got {self.mode.value!r}"
            )

        # ── REC1 — INTERPRETATION constraints ─────────────────────────────────
        if self.mode == RecommendationMode.INTERPRETATION:
            if not self.notes_for_head_coach:
                raise ValueError(
                    "REC1 violation: INTERPRETATION mode requires notes_for_head_coach (non-null)"
                )
            for field_name in _INTERPRETATION_FORBIDDEN_FIELDS:
                if getattr(self, field_name, None) is not None:
                    raise ValueError(
                        f"REC1 violation: field {field_name!r} is forbidden in INTERPRETATION mode"
                    )

        return self
