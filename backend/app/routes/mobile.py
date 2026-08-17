from __future__ import annotations

import json
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..core.nutrition_logic import compute_nutrition_directives
from ..db.models import AthleteModel, ConnectorCredentialModel, SessionLogModel, TrainingPlanModel
from ..dependencies import get_current_athlete_id, get_db
from ..routes.athletes import athlete_model_to_response
from ..schemas.athlete import DayType, Sport
from ..schemas.plan import WorkoutSlot
from ..services.energy_cycle_service import EnergyCycleService

router = APIRouter(prefix="/mobile", tags=["mobile"])

DB = Annotated[Session, Depends(get_db)]
AuthedId = Annotated[str, Depends(get_current_athlete_id)]

MetricState = Literal["green", "yellow", "red", "unknown"]
MetricStatus = Literal["measured", "estimated", "unavailable"]
AcwrStatus = Literal["safe", "caution", "danger", "unknown"]


class MobileMetric(BaseModel):
    value: float | None = None
    state: MetricState
    status: MetricStatus


class MobileReadinessMetric(MobileMetric):
    trend: Literal["improving", "stable", "declining"] = "stable"
    objective_score: float | None = None
    subjective_score: float | None = None
    allostatic_score: float | None = None


class MobileNutritionMetric(MobileMetric):
    day_type: str | None = None
    calories_target: int | None = None
    protein_g_per_kg: float | None = None
    carbs_g_per_kg: float | None = None
    fat_g_per_kg: float | None = None


class MobileSleepMetric(MobileMetric):
    sleep_hours: float | None = None


class MobileWorkoutSummary(BaseModel):
    session_id: str
    plan_id: str
    sport: str
    title: str
    duration_min: int
    zone: str
    is_rest_day: bool = False
    logged: bool = False


class MobileHomeDataQuality(BaseModel):
    readiness: MetricStatus
    nutrition: MetricStatus
    strain: MetricStatus
    sleep: MetricStatus
    sessions: MetricStatus


class MobileHomeResponse(BaseModel):
    athlete_id: str
    date: date
    readiness: MobileReadinessMetric
    nutrition: MobileNutritionMetric
    strain: MobileMetric
    sleep: MobileSleepMetric
    cognitive_load: MobileMetric = Field(serialization_alias="cognitiveLoad")
    acwr_status: AcwrStatus = Field(serialization_alias="acwrStatus")
    todays_sessions: list[MobileWorkoutSummary] | None = Field(serialization_alias="todaysSessions")
    data_quality: MobileHomeDataQuality = Field(serialization_alias="dataQuality")


def _state_from_readiness(value: float | None) -> MetricState:
    if value is None:
        return "unknown"
    if value >= 65:
        return "green"
    if value >= 40:
        return "yellow"
    return "red"


def _state_from_load(value: float | None) -> MetricState:
    if value is None:
        return "unknown"
    if value < 40:
        return "green"
    if value <= 70:
        return "yellow"
    return "red"


def _acwr_status(acwr: float | None) -> AcwrStatus:
    if acwr is None:
        return "unknown"
    if 0.8 <= acwr <= 1.3:
        return "safe"
    if 0.6 <= acwr <= 1.5:
        return "caution"
    return "danger"


def _sport_for_mobile(sport: Sport) -> str:
    if sport == Sport.BIKING:
        return "cycling"
    return sport.value


def _day_type_from_slots(slots: list[WorkoutSlot]) -> DayType:
    if not slots:
        return DayType.REST
    if any(slot.sport == Sport.LIFTING for slot in slots):
        return DayType.STRENGTH
    if any(slot.duration_min > 60 for slot in slots):
        return DayType.ENDURANCE_LONG
    return DayType.ENDURANCE_SHORT


def _latest_plan(athlete_id: str, db: Session) -> TrainingPlanModel | None:
    return (
        db.query(TrainingPlanModel)
        .filter(TrainingPlanModel.athlete_id == athlete_id)
        .order_by(desc(TrainingPlanModel.created_at))
        .first()
    )


def _today_slots(plan: TrainingPlanModel | None, target_date: date) -> list[WorkoutSlot]:
    if plan is None:
        return []
    slots = [WorkoutSlot.model_validate(slot) for slot in json.loads(plan.weekly_slots_json)]
    return [slot for slot in slots if slot.date == target_date]


def _session_summaries(
    plan: TrainingPlanModel | None,
    slots: list[WorkoutSlot],
    athlete_id: str,
    db: Session,
) -> list[MobileWorkoutSummary] | None:
    if plan is None or not slots:
        return None

    session_ids = [slot.id for slot in slots]
    logged_ids = {
        row[0]
        for row in db.query(SessionLogModel.session_id)
        .filter(
            SessionLogModel.athlete_id == athlete_id,
            SessionLogModel.session_id.in_(session_ids),
        )
        .all()
    }

    return [
        MobileWorkoutSummary(
            session_id=slot.id,
            plan_id=plan.id,
            sport=_sport_for_mobile(slot.sport),
            title=slot.workout_type,
            duration_min=slot.duration_min,
            zone=slot.notes or "Planifiee",
            logged=slot.id in logged_ids,
        )
        for slot in slots
    ]


def _readiness_metric(athlete_id: str, db: Session) -> MobileReadinessMetric:
    try:
        readiness = EnergyCycleService().get_readiness(athlete_id, db)
    except HTTPException as exc:
        if exc.status_code != 404:
            raise
        return MobileReadinessMetric(state="unknown", status="unavailable")

    return MobileReadinessMetric(
        value=round(readiness.final_readiness, 2),
        state=readiness.traffic_light,
        status="measured",
        objective_score=round(readiness.objective_score, 2),
        subjective_score=round(readiness.subjective_score, 2),
        allostatic_score=round(readiness.allostatic_score, 2),
    )


def _nutrition_metric(
    athlete: AthleteModel,
    slots: list[WorkoutSlot],
) -> MobileNutritionMetric:
    athlete_response = athlete_model_to_response(athlete)
    plan = compute_nutrition_directives(athlete_response)
    day_type = _day_type_from_slots(slots)
    target = plan.targets_by_day_type.get(day_type) or plan.targets_by_day_type[DayType.REST]

    return MobileNutritionMetric(
        value=None,
        state="unknown",
        status="estimated",
        day_type=target.day_type.value,
        calories_target=target.macro_target.calories_total,
        protein_g_per_kg=target.macro_target.protein_g_per_kg,
        carbs_g_per_kg=target.macro_target.carbs_g_per_kg,
        fat_g_per_kg=target.macro_target.fat_g_per_kg,
    )


def _sleep_metric(athlete_id: str, db: Session) -> MobileSleepMetric:
    terra = (
        db.query(ConnectorCredentialModel)
        .filter_by(athlete_id=athlete_id, provider="terra")
        .first()
    )
    if terra is None:
        return MobileSleepMetric(state="unknown", status="unavailable")

    extra = json.loads(terra.extra_json or "{}")
    sleep_hours = extra.get("last_sleep_hours")
    if sleep_hours is None:
        return MobileSleepMetric(state="unknown", status="unavailable")

    value = min(100.0, max(0.0, float(sleep_hours) / 8.0 * 100.0))
    return MobileSleepMetric(
        value=round(value, 2),
        state=_state_from_readiness(value),
        status="measured",
        sleep_hours=float(sleep_hours),
    )


@router.get("/home", response_model=MobileHomeResponse)
def get_mobile_home(current_athlete_id: AuthedId, db: DB) -> MobileHomeResponse:
    athlete = db.get(AthleteModel, current_athlete_id)
    if athlete is None:
        raise HTTPException(status_code=404, detail="Athlete not found")

    today = date.today()
    plan = _latest_plan(current_athlete_id, db)
    slots = _today_slots(plan, today)
    readiness = _readiness_metric(current_athlete_id, db)
    nutrition = _nutrition_metric(athlete, slots)
    sleep = _sleep_metric(current_athlete_id, db)
    cognitive_load = MobileMetric(
        value=readiness.allostatic_score,
        state=_state_from_load(readiness.allostatic_score),
        status=readiness.status,
    )

    return MobileHomeResponse(
        athlete_id=current_athlete_id,
        date=today,
        readiness=readiness,
        nutrition=nutrition,
        strain=MobileMetric(state="unknown", status="unavailable"),
        sleep=sleep,
        cognitive_load=cognitive_load,
        acwr_status=_acwr_status(plan.acwr if plan else None),
        todays_sessions=_session_summaries(plan, slots, current_athlete_id, db),
        data_quality=MobileHomeDataQuality(
            readiness=readiness.status,
            nutrition=nutrition.status,
            strain="unavailable",
            sleep=sleep.status,
            sessions="measured" if plan else "unavailable",
        ),
    )

