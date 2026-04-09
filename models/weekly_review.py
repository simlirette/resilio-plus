# models/weekly_review.py
"""
WeeklyReviewState — état LangGraph pour le weekly review graph (H1-H4).
Distinct de AthleteState : composition, pas héritage.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from models.athlete_state import AthleteState


class ActualWorkout(BaseModel):
    """One completed (or missed) session from the past week."""

    sport: Literal["running", "lifting"]
    date: str  # "YYYY-MM-DD"
    completed: bool
    actual_data: dict = {}
    # Running actual_data keys: duration_min, avg_hr, type ("easy"|"tempo"|"interval")
    # Lifting actual_data keys: duration_min, session_type ("hypertrophy"|"strength"|"power")


class WeeklyReviewState(BaseModel):
    """LangGraph state for the weekly review graph."""

    model_config = ConfigDict(frozen=False)

    athlete_state: AthleteState
    actual_workouts: list[ActualWorkout] = Field(default_factory=list)

    # Written by graph nodes
    analysis: dict | None = None          # WeeklyAnalyzer output
    adjustments: list[dict] = Field(default_factory=list)  # WeeklyAdjuster output
    acwr_before: float | None = None      # ACWR captured before node_wr_adjust overwrites it
    acwr_after: float | None = None       # Recalculated ACWR
    report: dict | None = None            # Final report
