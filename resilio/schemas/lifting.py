"""
Lifting schemas — Hevy workouts, exercise catalog, lifting profile, analysis reports,
and strength-session prescriptions.

Hevy is the system of record for what was lifted; these models mirror the fields of
the Hevy public API (weights always in kg) and add the coaching layer on top.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ============================================================
# HEVY DATA (stored under data/lifting/)
# ============================================================


class HevySetType(str, Enum):
    WARMUP = "warmup"
    NORMAL = "normal"
    FAILURE = "failure"
    DROPSET = "dropset"


class HevySet(BaseModel):
    index: int = 0
    type: str = HevySetType.NORMAL.value
    weight_kg: Optional[float] = None
    reps: Optional[int] = None
    distance_meters: Optional[float] = None
    duration_seconds: Optional[float] = None
    rpe: Optional[float] = None
    custom_metric: Optional[float] = None

    @property
    def is_working(self) -> bool:
        """Hard set: anything except a warm-up."""
        return self.type != HevySetType.WARMUP.value


class HevyExercise(BaseModel):
    index: int = 0
    title: str
    exercise_template_id: str
    notes: Optional[str] = None
    superset_id: Optional[int] = None
    sets: list[HevySet] = Field(default_factory=list)


class HevyWorkout(BaseModel):
    id: str
    title: str = ""
    routine_id: Optional[str] = None
    description: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    exercises: list[HevyExercise] = Field(default_factory=list)

    @property
    def local_date(self) -> date:
        return self.start_time.date()


class ExerciseTemplate(BaseModel):
    id: str
    title: str
    type: str = "weight_reps"
    primary_muscle_group: Optional[str] = None
    secondary_muscle_groups: list[str] = Field(default_factory=list)
    equipment: Optional[str] = None
    is_custom: bool = False


class LiftingSyncState(BaseModel):
    last_sync_at: Optional[datetime] = None
    templates_synced_at: Optional[datetime] = None
    workout_count: int = 0


class LiftingSyncSummary(BaseModel):
    mode: str  # "full" | "incremental"
    added: int = 0
    updated: int = 0
    deleted: int = 0
    total_stored: int = 0
    last_sync_at: Optional[datetime] = None


# ============================================================
# CATALOG (derived from templates)
# ============================================================


class MovementPattern(str, Enum):
    SQUAT = "squat"
    HINGE = "hinge"
    LUNGE = "lunge"
    PUSH = "push"
    PULL = "pull"
    CORE = "core"
    PLYO = "plyo"
    CARRY = "carry"
    ISOLATION = "isolation"


class CatalogEntry(BaseModel):
    template_id: str
    title: str
    template_type: str = "weight_reps"
    primary_group: Optional[str] = None  # landmark group (quads, back, ...) or None if not counted
    secondary_groups: list[str] = Field(default_factory=list)
    pattern: MovementPattern = MovementPattern.ISOLATION
    lower_body: bool = False
    sfr_tier: Optional[int] = None
    equipment: Optional[str] = None

    model_config = ConfigDict(use_enum_values=True)


# ============================================================
# LIFTING PROFILE (profile.yaml → lifting:)
# ============================================================


class LiftingGoal(str, Enum):
    HYPERTROPHY_ATHLETIC = "hypertrophy_athletic"
    HYPERTROPHY = "hypertrophy"
    MAINTENANCE = "maintenance"
    STRENGTH = "strength"


WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


class LiftingProfile(BaseModel):
    goal: LiftingGoal = LiftingGoal.HYPERTROPHY_ATHLETIC
    gym_days: list[str] = Field(default_factory=list, description="Weekdays the gym is available")
    optional_days: list[str] = Field(
        default_factory=list, description="Gym days used only if needed"
    )
    split: list[str] = Field(
        default_factory=list, description="Session labels, e.g. ['Upper A', 'Legs']"
    )
    compound_rep_range: list[int] = Field(default_factory=lambda: [6, 10])
    accessory_rep_range: list[int] = Field(default_factory=lambda: [10, 15])
    rir_target: list[int] = Field(default_factory=lambda: [1, 3])
    min_reps: int = Field(
        default=5, ge=1, description="No working sets below this (non-power work)"
    )
    include_power: bool = True
    protected_exercises: list[str] = Field(default_factory=list)
    blacklist: list[str] = Field(default_factory=list)
    increment_kg: dict[str, float] = Field(default_factory=lambda: {"upper": 2.5, "lower": 5.0})
    notes: Optional[str] = None

    model_config = ConfigDict(use_enum_values=True)

    @field_validator("gym_days", "optional_days")
    @classmethod
    def _valid_days(cls, v: list[str]) -> list[str]:
        out = [d.strip().lower() for d in v]
        bad = [d for d in out if d not in WEEKDAYS]
        if bad:
            raise ValueError(f"Invalid weekday(s): {bad}")
        return out

    @field_validator("compound_rep_range", "accessory_rep_range", "rir_target")
    @classmethod
    def _valid_range(cls, v: list[int]) -> list[int]:
        if len(v) != 2 or v[0] > v[1] or v[0] < 0:
            raise ValueError(f"Range must be [low, high] with low <= high, got {v}")
        return v


# ============================================================
# ANALYSIS REPORTS
# ============================================================


class ExerciseSessionSummary(BaseModel):
    date: date
    workout_id: str
    workout_title: str
    working_sets: int
    total_reps: int
    top_weight_kg: Optional[float] = None
    top_set_reps: Optional[int] = None
    best_e1rm_kg: Optional[float] = None
    sets: list[HevySet] = Field(default_factory=list)


class ExerciseHistory(BaseModel):
    template_id: str
    title: str
    weeks: int
    sessions: list[ExerciseSessionSummary] = Field(default_factory=list)
    e1rm_trend_kg: Optional[float] = Field(
        default=None, description="Best e1RM of the latest session minus the first, if both exist"
    )


class MuscleVolume(BaseModel):
    group: str
    hard_sets: float
    mev: int
    mav: int
    mrv: float
    status: str  # below_mev | productive | above_mav | above_mrv


class VolumeReport(BaseModel):
    week_start: date
    week_end: date
    hybrid_adjusted: bool
    workouts_counted: int
    groups: list[MuscleVolume] = Field(default_factory=list)
    unmapped_exercises: list[str] = Field(default_factory=list)


class ProgressionSuggestion(BaseModel):
    template_id: str
    title: str
    rep_range: list[int]
    last_session_date: Optional[date] = None
    last_load_kg: Optional[float] = None
    last_reps: list[int] = Field(default_factory=list)
    suggested_load_kg: Optional[float] = None
    suggested_sets: Optional[int] = None
    target_reps: Optional[int] = None
    action: str  # increase_load | add_reps | hold | deload | no_recent_history | bodyweight
    reason: str


# ============================================================
# PRESCRIPTION (SP3) — embedded in StrengthSession
# ============================================================


class ExerciseKind(str, Enum):
    HYPERTROPHY = "hypertrophy"
    POWER = "power"
    PREHAB = "prehab"
    CORE = "core"
    MOBILITY = "mobility"


class ExercisePrescription(BaseModel):
    exercise_template_id: str = Field(..., description="Hevy exercise template id")
    title: str
    kind: ExerciseKind = ExerciseKind.HYPERTROPHY
    sets: int = Field(..., ge=1, le=10)
    warmup_sets: int = Field(default=0, ge=0, le=5)
    rep_range: Optional[list[int]] = Field(default=None, description="[low, high] reps per set")
    duration_seconds: Optional[int] = Field(default=None, gt=0)
    target_rir: Optional[int] = Field(default=None, ge=0, le=5)
    load_kg: Optional[float] = Field(default=None, ge=0)
    rest_seconds: int = Field(default=90, ge=0, le=600)
    superset_group: Optional[int] = None
    notes: Optional[str] = None

    model_config = ConfigDict(use_enum_values=True)

    @model_validator(mode="after")
    def _reps_or_duration(self) -> "ExercisePrescription":
        if self.rep_range is None and self.duration_seconds is None:
            raise ValueError(f"{self.title}: set rep_range or duration_seconds")
        if self.rep_range is not None and (
            len(self.rep_range) != 2
            or self.rep_range[0] < 1
            or self.rep_range[0] > self.rep_range[1]
        ):
            raise ValueError(f"{self.title}: rep_range must be [low, high], got {self.rep_range}")
        return self


class LiftingBlock(BaseModel):
    start_week: int = Field(..., ge=1)
    end_week: int = Field(..., ge=1)
    focus: str = Field(..., description="hypertrophy | maintenance | deload | power")
    sessions_per_week: int = Field(..., ge=0, le=7)
    weekly_sets: dict[str, int] = Field(
        default_factory=dict, description="Target hard sets per group"
    )
    notes: Optional[str] = None

    @model_validator(mode="after")
    def _ordered(self) -> "LiftingBlock":
        if self.end_week < self.start_week:
            raise ValueError("end_week must be >= start_week")
        return self
