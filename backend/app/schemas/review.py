from datetime import date
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .athlete import Sport
from .plan import TrainingPlanResponse


class ActivityResult(BaseModel):
    date: date
    sport: Sport
    planned_duration_min: int = Field(..., gt=0)
    actual_duration_min: int | None = Field(default=None, ge=0)
    rpe_actual: int | None = Field(None, ge=1, le=10)
    notes: str = ""


class WeeklyReview(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    athlete_id: UUID
    plan_id: UUID
    week_start: date
    results: list[ActivityResult] = Field(default_factory=list)
    readiness_score: float | None = Field(default=None, ge=0, le=100)
    hrv_rmssd: float | None = Field(default=None, ge=0)
    sleep_hours_avg: float | None = Field(default=None, ge=0)
    athlete_comment: str = ""


class WeekStatusResponse(BaseModel):
    week_number: int
    plan: TrainingPlanResponse
    planned_hours: float
    actual_hours: float
    completion_pct: float
    acwr: float | None


class WeeklyReviewRequest(BaseModel):
    week_end_date: str  # ISO date string e.g. "2026-04-09"
    readiness_score: float | None = Field(default=None, ge=1.0, le=10.0)
    hrv_rmssd: float | None = None
    sleep_hours_avg: float | None = None
    comment: str = ""


class WeeklyReviewResponse(BaseModel):
    review_id: str
    week_number: int
    planned_hours: float
    actual_hours: float
    acwr: float
    adjustment_applied: float
    next_week_suggestion: str
