from datetime import date
from typing import Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class ConnectorCredential(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    athlete_id: UUID
    provider: str
    access_token: str | None = None
    refresh_token: str | None = None
    expires_at: int | None = None  # Unix timestamp
    extra: dict[str, Any] = Field(default_factory=dict)


class StravaLap(BaseModel):
    lap_index: int
    elapsed_time_seconds: int
    distance_meters: float
    average_hr: float | None = None
    pace_per_km: str | None = None  # "5:23"


class StravaActivity(BaseModel):
    id: str  # "strava_{strava_id}"
    name: str
    sport_type: str
    date: date
    duration_seconds: int
    distance_meters: float | None = None
    elevation_gain_meters: float | None = None
    average_hr: float | None = None
    max_hr: float | None = None
    perceived_exertion: int | None = Field(default=None, ge=1, le=10)  # RPE 1-10
    laps: list[StravaLap] = Field(default_factory=list)


class HevySet(BaseModel):
    reps: int | None = None
    weight_kg: float | None = None
    rpe: float | None = Field(default=None, ge=1, le=10)  # 1-10
    set_type: str  # "normal", "warmup", "dropset", "failure"


class HevyExercise(BaseModel):
    name: str
    sets: list[HevySet]


class HevyWorkout(BaseModel):
    id: str
    title: str
    date: date
    duration_seconds: int
    exercises: list[HevyExercise]


class FatSecretMeal(BaseModel):
    name: str  # "Breakfast", "Lunch", "Dinner", "Other"
    calories: float
    carbs_g: float
    protein_g: float
    fat_g: float


class FatSecretDay(BaseModel):
    date: date
    calories_total: float
    carbs_g: float
    protein_g: float
    fat_g: float
    meals: list[FatSecretMeal]


class TerraHealthData(BaseModel):
    date: date
    hrv_rmssd: float | None = None  # ms
    sleep_duration_hours: float | None = None
    sleep_score: float | None = Field(default=None, ge=0, le=100)  # 0-100
    steps: int | None = None
    active_energy_kcal: float | None = None
