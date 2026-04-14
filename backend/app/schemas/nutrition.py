from datetime import date
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .athlete import DayType


class MacroTarget(BaseModel):
    carbs_g_per_kg: float = Field(..., ge=0)
    protein_g_per_kg: float = Field(..., ge=0)
    fat_g_per_kg: float = Field(..., ge=0)
    calories_total: int = Field(..., gt=0)


class DayNutrition(BaseModel):
    day_type: DayType
    macro_target: MacroTarget
    intra_effort_carbs_g_per_h: float | None = Field(default=None, ge=0)
    sodium_mg_per_h: float | None = Field(default=None, ge=0)


class NutritionPlan(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    athlete_id: UUID
    weight_kg: float = Field(..., gt=0)
    targets_by_day_type: dict[DayType, DayNutrition] = Field(default_factory=dict)


class NutritionTodayResponse(BaseModel):
    date: date
    day_type: DayType
    macro_target: MacroTarget
    intra_effort_carbs_g_per_h: float | None = Field(default=None, ge=0)
    sodium_mg_per_h: float | None = Field(default=None, ge=0)
