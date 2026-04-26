"""HeadCoachView schema — Phase D (D4).

Minimal athlete context consumed by Head Coach during chat_turn invocations.
Expanded in D6 with Recovery and Energy view integration.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HeadCoachView(BaseModel):
    """Athlete context snapshot for Head Coach chat responses.

    Built by head_coach_view_builder.build_head_coach_view().
    Consumed by chat_turn graph nodes invoke_head_coach and synthesize_response.
    """

    athlete_id: str
    journey_phase: str
    sports: list[str] = Field(default_factory=list)
    primary_sport: str
    hours_per_week: float

    # Coaching mode (full | tracking_only | manual)
    coaching_mode: str = "full"

    # Recent plan summary — null if no active plan
    active_plan_summary: dict[str, Any] | None = None

    # Clinical context flag (propagated from athlete record)
    clinical_context_flag: str | None = None
