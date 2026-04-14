from __future__ import annotations

import json
from datetime import date as date_type
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..core.nutrition_logic import compute_nutrition_directives
from ..db.models import AthleteModel, TrainingPlanModel
from ..dependencies import get_db, get_current_athlete_id
from ..routes.athletes import athlete_model_to_response
from ..schemas.athlete import DayType, Sport
from ..schemas.nutrition import NutritionPlan, NutritionTodayResponse
from ..schemas.plan import WorkoutSlot

router = APIRouter(prefix="/athletes", tags=["nutrition"])

DB = Annotated[Session, Depends(get_db)]


def _require_own(
    athlete_id: str,
    current_id: Annotated[str, Depends(get_current_athlete_id)],
) -> str:
    if current_id != athlete_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return athlete_id


@router.get("/{athlete_id}/nutrition-directives", response_model=NutritionPlan)
def get_nutrition_directives(
    athlete_id: str,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> NutritionPlan:
    """Return per-day-type macro targets for the athlete."""
    athlete_model = db.get(AthleteModel, athlete_id)
    if athlete_model is None:
        raise HTTPException(status_code=404, detail="Athlete not found")
    athlete = athlete_model_to_response(athlete_model)
    return compute_nutrition_directives(athlete)


_DAY_TYPE_PRIORITY: dict[DayType, int] = {
    DayType.RACE: 5,
    DayType.ENDURANCE_LONG: 4,
    DayType.ENDURANCE_SHORT: 3,
    DayType.STRENGTH: 2,
    DayType.REST: 1,
}


def _slot_to_day_type(slot: WorkoutSlot) -> DayType:
    if "race" in slot.workout_type.lower():
        return DayType.RACE
    if slot.sport == Sport.LIFTING:
        return DayType.STRENGTH
    if slot.duration_min > 60:
        return DayType.ENDURANCE_LONG
    return DayType.ENDURANCE_SHORT


def _resolve_day_type(plan: TrainingPlanModel | None, target: date_type) -> DayType:
    if plan is None:
        return DayType.REST
    slots = [WorkoutSlot.model_validate(s) for s in json.loads(plan.weekly_slots_json)]
    today_slots = [s for s in slots if s.date == target]
    if not today_slots:
        return DayType.REST
    best = DayType.REST
    for slot in today_slots:
        candidate = _slot_to_day_type(slot)
        if _DAY_TYPE_PRIORITY[candidate] > _DAY_TYPE_PRIORITY[best]:
            best = candidate
    return best


@router.get("/{athlete_id}/nutrition-today", response_model=NutritionTodayResponse)
def get_nutrition_today(
    athlete_id: str,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
    target_date: date_type | None = Query(default=None),
) -> NutritionTodayResponse:
    athlete_model = db.get(AthleteModel, athlete_id)
    if athlete_model is None:
        raise HTTPException(status_code=404, detail="Athlete not found")
    athlete = athlete_model_to_response(athlete_model)

    today = target_date or date_type.today()

    plan = (
        db.query(TrainingPlanModel)
        .filter(TrainingPlanModel.athlete_id == athlete_id)
        .order_by(desc(TrainingPlanModel.created_at))
        .first()
    )

    day_type = _resolve_day_type(plan, today)
    nutrition_plan = compute_nutrition_directives(athlete)
    day_nutrition = nutrition_plan.targets_by_day_type.get(day_type)
    if day_nutrition is None:
        day_nutrition = nutrition_plan.targets_by_day_type[DayType.REST]

    return NutritionTodayResponse(
        date=today,
        day_type=day_type,
        macro_target=day_nutrition.macro_target,
        intra_effort_carbs_g_per_h=day_nutrition.intra_effort_carbs_g_per_h,
        sodium_mg_per_h=day_nutrition.sodium_mg_per_h,
    )
