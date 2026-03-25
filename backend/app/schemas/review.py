from datetime import date
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .athlete import Sport


class ActivityResult(BaseModel):
    date: date
    sport: Sport
    planned_duration_min: int = Field(..., gt=0)
    actual_duration_min: int | None = None
    rpe_actual: int | None = Field(None, ge=1, le=10)
    notes: str = ""


class WeeklyReview(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    athlete_id: UUID
    plan_id: UUID
    week_start: date
    results: list[ActivityResult] = Field(default_factory=list)
    readiness_score: float | None = None
    hrv_rmssd: float | None = None
    sleep_hours_avg: float | None = None
    athlete_comment: str = ""
