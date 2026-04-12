from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class ExternalPlanCreate(BaseModel):
    title: str
    start_date: date | None = None
    end_date: date | None = None


class ExternalSessionCreate(BaseModel):
    session_date: date
    sport: str
    title: str
    description: str | None = None
    duration_min: int | None = None


class ExternalSessionUpdate(BaseModel):
    session_date: date | None = None
    sport: str | None = None
    title: str | None = None
    description: str | None = None
    duration_min: int | None = None
    status: Literal["planned", "completed", "skipped"] | None = None


class ExternalSessionOut(BaseModel):
    id: str
    plan_id: str
    athlete_id: str
    session_date: date
    sport: str
    title: str
    description: str | None
    duration_min: int | None
    status: str

    model_config = {"from_attributes": True}


class ExternalPlanOut(BaseModel):
    id: str
    athlete_id: str
    title: str
    source: str
    status: str
    start_date: date | None
    end_date: date | None
    created_at: datetime
    sessions: list[ExternalSessionOut]

    model_config = {"from_attributes": True}
