from datetime import date
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class ConnectorCredential(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    athlete_id: UUID
    provider: str
    access_token: str | None = None
    refresh_token: str | None = None
    expires_at: int | None = None  # Unix timestamp
    extra: dict = Field(default_factory=dict)


class StravaLap(BaseModel):
    lap_index: int
    elapsed_time_seconds: int
    distance_meters: float
    average_hr: float | None
    pace_per_km: str | None  # "5:23"


class StravaActivity(BaseModel):
    id: str  # "strava_{strava_id}"
    name: str
    sport_type: str
    date: date
    duration_seconds: int
    distance_meters: float | None
    elevation_gain_meters: float | None
    average_hr: float | None
    max_hr: float | None
    perceived_exertion: int | None  # RPE 1-10
    laps: list[StravaLap] = Field(default_factory=list)


class HevySet(BaseModel):
    reps: int | None
    weight_kg: float | None
    rpe: float | None  # 1-10
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
    hrv_rmssd: float | None  # ms
    sleep_duration_hours: float | None
    sleep_score: float | None  # 0-100
    steps: int | None
    active_energy_kcal: float | None
