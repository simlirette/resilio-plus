from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from .fatigue import FatigueScore
from .athlete import Sport


class SessionLogRequest(BaseModel):
    actual_duration_min: int | None = Field(default=None, ge=1)
    skipped: bool = False
    rpe: int | None = Field(default=None, ge=1, le=10)
    notes: str = ""
    actual_data: dict[str, Any] = Field(default_factory=dict)


class SessionLogResponse(BaseModel):
    id: str
    session_id: str
    actual_duration_min: int | None
    skipped: bool
    rpe: int | None
    notes: str
    actual_data: dict[str, Any]
    logged_at: datetime


class SessionDetailResponse(BaseModel):
    session_id: str
    plan_id: str
    date: date
    sport: Sport
    workout_type: str
    duration_min: int
    fatigue_score: FatigueScore
    notes: str
    log: SessionLogResponse | None = None


class WeekSummary(BaseModel):
    plan_id: str
    week_number: int
    start_date: date
    end_date: date
    phase: str
    planned_hours: float
    sessions_total: int
    sessions_logged: int
    completion_pct: float
