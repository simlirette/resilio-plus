"""Cross-discipline load schemas — Phase D (D2), DEP-C4-004.

CrossDisciplineLoadV1 and CrossDisciplineLoadV2 represent aggregated weekly
load across endurance disciplines (running, biking, swimming) for use by the
Head Coach when evaluating inter-sport fatigue interactions.

V1 is the lightweight count-only version already used in existing plan_generation
contexts. V2 adds z-score normalisation, leg-impact index, and key session-day
flags for the Phase D chat flows.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class DisciplineLoadDetail(BaseModel):
    """Per-discipline load detail for CrossDisciplineLoadV2."""

    weekly_sessions_count: int = Field(..., ge=0)
    weekly_volume_zscore: float
    """Z-score of weekly volume relative to the athlete's 8-week baseline.
    Positive = above baseline, negative = below."""

    has_long_session_day: str | None = None
    """ISO date (YYYY-MM-DD) of the long session day this week, if any."""

    has_intensity_day: str | None = None
    """ISO date (YYYY-MM-DD) of the intensity/interval session day, if any."""

    leg_impact_index: float = Field(..., ge=0.0, le=1.0)
    """Composite leg-impact score for this discipline (0 = no impact, 1 = maximum).
    Running ≈ 1.0, Biking ≈ 0.4, Swimming ≈ 0.0."""


class CrossDisciplineLoadV1(BaseModel):
    """Lightweight cross-discipline session count (V1 — used in plan_generation).

    DEP-C4-004: retained for backwards compatibility with existing plan_generation
    graph nodes. V2 adds richer context for Phase D chat flows.
    """

    weekly_running_sessions: int = Field(default=0, ge=0)
    weekly_biking_sessions: int = Field(default=0, ge=0)
    weekly_swimming_sessions: int = Field(default=0, ge=0)


class CrossDisciplineLoadV2(BaseModel):
    """Rich cross-discipline load view (V2 — used in Phase D chat flows).

    DEP-C4-004: extended context for Head Coach and specialist agents during
    chat_turn consultations. Null discipline = not active for the athlete.
    """

    running: DisciplineLoadDetail | None = None
    biking: DisciplineLoadDetail | None = None
    swimming: DisciplineLoadDetail | None = None
