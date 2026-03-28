import json
from datetime import date
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .athlete import Sport
from .fatigue import FatigueScore


class WorkoutSlot(BaseModel):
    date: date
    sport: Sport
    workout_type: str
    duration_min: int = Field(..., gt=0)
    fatigue_score: FatigueScore
    notes: str = ""


class TrainingPlan(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    athlete_id: UUID
    start_date: date
    end_date: date
    phase: Literal["base", "build", "peak", "taper", "recovery"]
    weekly_slots: dict[str, list[WorkoutSlot]] = Field(default_factory=dict)
    total_weekly_hours: float = Field(..., ge=0)
    acwr: float = Field(..., ge=0, description="Acute:Chronic Workload Ratio — safe zone 0.8–1.3")


class TrainingPlanResponse(BaseModel):
    id: str
    athlete_id: str
    start_date: date
    end_date: date
    phase: str
    total_weekly_hours: float
    acwr: float
    sessions: list[WorkoutSlot]

    @classmethod
    def from_model(cls, m: object) -> "TrainingPlanResponse":
        sessions = [WorkoutSlot.model_validate(s) for s in json.loads(m.weekly_slots_json)]
        return cls(
            id=m.id,
            athlete_id=m.athlete_id,
            start_date=m.start_date,
            end_date=m.end_date,
            phase=m.phase,
            total_weekly_hours=m.total_weekly_hours,
            acwr=m.acwr,
            sessions=sessions,
        )
