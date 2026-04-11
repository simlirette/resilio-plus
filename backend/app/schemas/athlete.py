from enum import Enum
from datetime import date
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Sport(str, Enum):
    RUNNING = "running"
    LIFTING = "lifting"
    SWIMMING = "swimming"
    BIKING = "biking"


class DayType(str, Enum):
    REST = "rest"
    STRENGTH = "strength"
    ENDURANCE_SHORT = "endurance_short"
    ENDURANCE_LONG = "endurance_long"
    RACE = "race"


class AthleteProfile(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    age: int = Field(..., ge=14, le=100)
    sex: Literal["M", "F", "other"]
    weight_kg: float = Field(..., gt=0)
    height_cm: float = Field(..., gt=0)
    sports: list[Sport]
    primary_sport: Sport
    goals: list[str]
    target_race_date: date | None = None
    available_days: list[int] = Field(..., description="0=Mon … 6=Sun")
    hours_per_week: float = Field(..., gt=0)
    equipment: list[str] = Field(default_factory=list)
    # Fitness markers (optional — filled progressively)
    max_hr: int | None = None
    resting_hr: int | None = None
    ftp_watts: int | None = None
    vdot: float | None = None
    css_per_100m: float | None = None
    # Lifestyle
    sleep_hours_typical: float = Field(default=7.0)
    stress_level: int = Field(default=5, ge=1, le=10)
    job_physical: bool = False
    coaching_mode: Literal["full", "tracking_only"] = "full"


class AthleteCreate(BaseModel):
    name: str
    age: int = Field(..., ge=14, le=100)
    sex: Literal["M", "F", "other"]
    weight_kg: float = Field(..., gt=0)
    height_cm: float = Field(..., gt=0)
    sports: list[Sport]
    primary_sport: Sport
    goals: list[str]
    target_race_date: date | None = None
    available_days: list[int] = Field(..., description="0=Mon … 6=Sun")
    hours_per_week: float = Field(..., gt=0)
    equipment: list[str] = Field(default_factory=list)
    max_hr: int | None = None
    resting_hr: int | None = None
    ftp_watts: int | None = None
    vdot: float | None = None
    css_per_100m: float | None = None
    sleep_hours_typical: float = Field(default=7.0)
    stress_level: int = Field(default=5, ge=1, le=10)
    job_physical: bool = False
    coaching_mode: Literal["full", "tracking_only"] = "full"


class AthleteUpdate(BaseModel):
    name: str | None = None
    age: int | None = Field(default=None, ge=14, le=100)
    sex: Literal["M", "F", "other"] | None = None
    weight_kg: float | None = Field(default=None, gt=0)
    height_cm: float | None = Field(default=None, gt=0)
    sports: list[Sport] | None = None
    primary_sport: Sport | None = None
    goals: list[str] | None = None
    target_race_date: date | None = None
    available_days: list[int] | None = None
    hours_per_week: float | None = None
    equipment: list[str] | None = None
    max_hr: int | None = None
    resting_hr: int | None = None
    ftp_watts: int | None = None
    vdot: float | None = None
    css_per_100m: float | None = None
    sleep_hours_typical: float | None = None
    stress_level: int | None = Field(default=None, ge=1, le=10)
    job_physical: bool | None = None
    coaching_mode: Literal["full", "tracking_only"] | None = None


AthleteResponse = AthleteProfile
