"""RecoveryCoachView schema — Phase D (D6), DEP-C3-001."""
from __future__ import annotations

from pydantic import BaseModel, Field


class RecoveryCoachView(BaseModel):
    """Athlete recovery context for Recovery Coach chat consultations.

    Built by recovery_view_builder.build_recovery_view().
    Consumed by chat_turn handle_injury_report node (DEP-C3-001).
    """

    athlete_id: str
    journey_phase: str

    # Duration delta over last 7 days (actual - prescribed), in minutes
    # Null when no session logs with duration data exist
    mean_vs_prescribed_delta_7d: float | None = None
    """Mean (actual_duration_min - prescribed_duration_min) over last 7 days.
    Positive = athlete trains longer than prescribed; negative = shorter."""

    recent_rpe_avg: float | None = None
    """Average RPE over last 7 days of session logs (1-10 scale)."""

    sessions_logged_last_7d: int = Field(default=0, ge=0)
    """Number of sessions logged in the last 7 days."""
