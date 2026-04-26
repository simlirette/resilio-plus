"""Energy Coach view schema — Phase D (D2), DEP-C9-008 (partial: schema only).

EnergyCoachView is the structured input consumed by the Energy Coach agent
when invoked from the chat_turn graph (D6). Contains aggregated load metrics,
energy availability data, and recent check-ins.

The view builder (build_energy_view) is implemented in D6.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class DisciplineLoadSummary(BaseModel):
    """Weekly aggregated load for one discipline."""

    discipline: str
    weekly_sessions: int = Field(..., ge=0)
    weekly_volume_hours: float = Field(..., ge=0.0)
    acwr: float | None = None
    """Acute:Chronic Workload Ratio for this discipline, if computable."""


class CheckInSummaryEntry(BaseModel):
    """Single check-in summary for EnergyCoachView (last 14 days)."""

    check_in_date: date
    energy_global: str
    work_intensity: str
    stress_level: str
    legs_feeling: str
    final_readiness: float | None = None
    energy_availability: float | None = None


class EnergyCoachView(BaseModel):
    """Aggregated energy and load view for the Energy Coach agent.

    Consumed by Energy Coach in consultation mode from chat_turn (D6).
    DEP-C9-008: schema only in D2 — view builder implemented in D6.
    """

    athlete_id: str

    # Aggregated loads across all active disciplines
    discipline_loads: list[DisciplineLoadSummary] = Field(default_factory=list)
    """Per-discipline load summary for the current week."""

    total_weekly_hours: float = Field(default=0.0, ge=0.0)
    """Sum of hours across all disciplines this week."""

    # Energy metrics (from EnergyCycleService / check-ins)
    current_energy_availability: float | None = None
    """Energy availability kcal/kg/day (null if no nutrition data)."""

    allostatic_score: float | None = Field(default=None, ge=0.0, le=100.0)
    """Composite allostatic load score (0–100)."""

    intensity_cap: float | None = Field(default=None, ge=0.0, le=1.0)
    """Current training intensity cap from EnergyCycleService (0–1)."""

    # Recent check-ins (last 14 days)
    recent_checkins: list[CheckInSummaryEntry] = Field(default_factory=list)
    """Last 14 days of check-in data for trend analysis."""

    # Nutrition snapshot (optional — from NutritionLoadPayload if available)
    nutrition_snapshot: dict[str, Any] | None = None
    """Partial NutritionLoadPayload for energy context (calories_reported, macros)."""

    # Flags
    energy_pattern_flags: list[str] = Field(default_factory=list)
    """Active energy pattern flags (from detect_energy_patterns)."""
