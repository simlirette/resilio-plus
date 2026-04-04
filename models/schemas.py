"""
SCHEMAS PYDANTIC — Resilio+
Couche de validation au-dessus des SQLAlchemy models.
Utilisé pour valider les données JSONB et filtrer l'AthleteState par agent via get_agent_view().
"""
from __future__ import annotations

import uuid
from datetime import datetime, date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TrainingHistory(BaseModel):
    total_years_training: float
    years_running: float
    years_lifting: float
    years_swimming: float
    current_weekly_volume_hours: float
    longest_run_ever_km: float | None = None
    current_5k_time_min: float | None = None
    current_10k_time_min: float | None = None
    current_half_marathon_min: float | None = None
    estimated_1rm: dict[str, float] = {}


class Injury(BaseModel):
    type: str
    year: int
    duration_weeks: int
    side: str | None = None
    recurrent: bool = False
    notes: str | None = None


class Lifestyle(BaseModel):
    work_type: str
    work_hours_per_day: float
    commute_active: bool
    sleep_avg_hours: float
    stress_level: str
    alcohol_per_week: int = 0
    smoking: bool = False


class Goals(BaseModel):
    primary: str
    secondary: str | None = None
    tertiary: str | None = None
    timeline_weeks: int
    priority_hierarchy: list[str] = []


class Equipment(BaseModel):
    gym_access: bool
    gym_equipment: list[str] = []
    pool_access: bool = False
    pool_type: str | None = None
    outdoor_running: bool = True
    treadmill: bool = False
    heart_rate_monitor: bool = False
    gps_watch: str | None = None
    power_meter_bike: bool = False


class DayAvailability(BaseModel):
    available: bool
    max_hours: float
    preferred_time: str | None = None


class AthleteProfile(BaseModel):
    first_name: str
    age: int
    sex: Literal["M", "F"]
    weight_kg: float
    height_cm: float
    body_fat_percent: float | None = None
    resting_hr: int | None = None
    max_hr_measured: int | None = None
    max_hr_formula: int | None = None
    training_history: TrainingHistory
    injuries_history: list[Injury] = []
    lifestyle: Lifestyle
    goals: Goals
    equipment: Equipment
    active_sports: list[str] = []
    available_days: dict[str, DayAvailability] = {}


class CurrentPhase(BaseModel):
    macrocycle: str
    mesocycle_week: int
    mesocycle_length: int = 4
    next_deload: str | None = None
    target_event: str | None = None
    target_event_date: date | None = None


class TrainingPaces(BaseModel):
    easy_min_per_km: str
    easy_max_per_km: str
    marathon_pace_per_km: str | None = None
    threshold_pace_per_km: str
    interval_pace_per_km: str
    repetition_pace_per_km: str
    long_run_pace_per_km: str


class RunningProfile(BaseModel):
    vdot: float
    training_paces: TrainingPaces
    weekly_km_current: float
    weekly_km_target: float
    max_long_run_km: float
    cadence_avg: int | None = None
    preferred_terrain: str = "road"


class VolumeLandmarks(BaseModel):
    mev: int
    mav: int
    mrv_hybrid: int


class LiftingProfile(BaseModel):
    training_split: str
    sessions_per_week: int
    current_volume_per_muscle: dict[str, int] = {}
    volume_landmarks: dict[str, VolumeLandmarks] = {}
    progression_model: str = "double_progression"
    rir_target_range: list[int] = [1, 3]


class SwimmingProfile(BaseModel):
    reference_times: dict[str, float] = {}
    technique_level: str = "beginner"
    weekly_volume_km: float = 0.0


class BikingProfile(BaseModel):
    ftp_watts: float | None = None
    weekly_volume_km: float = 0.0


class MacrosTarget(BaseModel):
    protein_g: float
    carbs_g: float
    fat_g: float


class NutritionProfile(BaseModel):
    tdee_estimated: float
    macros_target: MacrosTarget
    supplements_current: list[str] = []
    dietary_restrictions: list[str] = []
    allergies: list[str] = []


class ACWRBySport(BaseModel):
    running: float | None = None
    lifting: float | None = None
    biking: float | None = None
    swimming: float | None = None


class FatigueState(BaseModel):
    acwr: float | None = None
    acwr_trend: str | None = None
    acwr_by_sport: ACWRBySport = Field(default_factory=ACWRBySport)
    weekly_fatigue_score: float | None = None
    fatigue_by_muscle: dict[str, float] = {}
    cns_load_7day_avg: float | None = None
    recovery_score_today: float | None = None
    hrv_rmssd_today: float | None = None
    hrv_rmssd_baseline: float | None = None
    sleep_hours_last_night: float | None = None
    sleep_quality_subjective: int | None = None
    fatigue_subjective: int | None = None


class Compliance(BaseModel):
    last_4_weeks_completion_rate: float | None = None
    missed_sessions_this_week: list[str] = []
    nutrition_adherence_7day: float | None = None


class WeeklyVolumes(BaseModel):
    running_km: float = 0.0
    lifting_sessions: int = 0
    swimming_km: float = 0.0
    biking_km: float = 0.0
    total_training_hours: float = 0.0


class AthleteStateSchema(BaseModel):
    model_config = ConfigDict(strict=False)

    athlete_id: uuid.UUID
    updated_at: datetime
    profile: AthleteProfile
    current_phase: CurrentPhase
    running_profile: RunningProfile
    lifting_profile: LiftingProfile
    swimming_profile: SwimmingProfile = Field(default_factory=SwimmingProfile)
    biking_profile: BikingProfile = Field(default_factory=BikingProfile)
    nutrition_profile: NutritionProfile
    fatigue: FatigueState = Field(default_factory=FatigueState)
    compliance: Compliance = Field(default_factory=Compliance)
    weekly_volumes: WeeklyVolumes = Field(default_factory=WeeklyVolumes)
