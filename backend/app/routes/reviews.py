import uuid
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.acwr import compute_acwr
from app.db.models import AthleteModel, TrainingPlanModel, WeeklyReviewModel
from app.dependencies import get_db, get_current_athlete_id
from app.schemas.plan import TrainingPlanResponse
from app.schemas.review import WeekStatusResponse, WeeklyReviewRequest, WeeklyReviewResponse
from app.services.connector_service import fetch_connector_data

router = APIRouter(prefix="/athletes", tags=["reviews"])

DB = Annotated[Session, Depends(get_db)]


def _require_own(
    athlete_id: str,
    current_id: Annotated[str, Depends(get_current_athlete_id)],
) -> str:
    if current_id != athlete_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return athlete_id


def _get_latest_plan(athlete_id: str, db: Session) -> TrainingPlanModel:
    plan = (
        db.query(TrainingPlanModel)
        .filter(TrainingPlanModel.athlete_id == athlete_id)
        .order_by(desc(TrainingPlanModel.created_at))
        .first()
    )
    if plan is None:
        raise HTTPException(status_code=404, detail="No plan found for this athlete")
    return plan


def _compute_actual_hours(activities: list, workouts: list, start: date, end: date) -> float:
    """Sum duration_seconds for activities/workouts within [start, end] date range."""
    total = 0
    for act in activities:
        act_date = act.date if hasattr(act, "date") else date.fromisoformat(str(act.get("date", "")))
        if start <= act_date <= end:
            duration = act.duration_seconds if hasattr(act, "duration_seconds") else act.get("duration_seconds", 0)
            total += duration
    for w in workouts:
        w_date = w.date if hasattr(w, "date") else date.fromisoformat(str(w.get("date", "")))
        if start <= w_date <= end:
            duration = w.duration_seconds if hasattr(w, "duration_seconds") else w.get("duration_seconds", 0)
            total += duration
    return round(total / 3600, 2)


def _build_daily_loads(activities: list, days: int = 28) -> list[float]:
    """Oldest-first list of daily load (hours) for the last `days` days."""
    today = date.today()
    daily: dict[date, float] = {}
    for act in activities:
        act_date = act.date if hasattr(act, "date") else date.fromisoformat(str(act.get("date", "")))
        duration = act.duration_seconds if hasattr(act, "duration_seconds") else act.get("duration_seconds", 0)
        daily[act_date] = daily.get(act_date, 0.0) + duration / 3600

    return [daily.get(today - timedelta(days=i), 0.0) for i in range(days - 1, -1, -1)]


def _adjustment_message(acwr: float, adjustment: float) -> str:
    if adjustment < 1.0:
        return f"Volume réduit de {round((1 - adjustment) * 100)}% (ACWR élevé : {acwr:.2f})"
    if adjustment > 1.0:
        return f"Volume augmenté de {round((adjustment - 1) * 100)}% (sous-entraînement : ACWR {acwr:.2f})"
    return f"Volume maintenu (ACWR dans la zone sûre : {acwr:.2f})"


@router.get("/{athlete_id}/week-status", response_model=WeekStatusResponse)
def get_week_status(
    athlete_id: str,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> WeekStatusResponse:
    plan = _get_latest_plan(athlete_id, db)

    connector_data = fetch_connector_data(athlete_id, db)
    actual_hours = _compute_actual_hours(
        connector_data["strava_activities"],
        connector_data["hevy_workouts"],
        plan.start_date,
        date.today(),
    )

    daily_loads = _build_daily_loads(connector_data["strava_activities"])
    acwr_result = compute_acwr(daily_loads)

    week_number = (
        db.query(TrainingPlanModel)
        .filter(TrainingPlanModel.athlete_id == athlete_id)
        .count()
    )

    completion_pct = (
        round(actual_hours / plan.total_weekly_hours * 100, 1)
        if plan.total_weekly_hours > 0
        else 0.0
    )

    return WeekStatusResponse(
        week_number=week_number,
        plan=TrainingPlanResponse.from_model(plan),
        planned_hours=round(plan.total_weekly_hours, 2),
        actual_hours=actual_hours,
        completion_pct=completion_pct,
        acwr=acwr_result.ratio if acwr_result.ratio > 0 else None,
    )


@router.post("/{athlete_id}/review", response_model=WeeklyReviewResponse, status_code=201)
def submit_weekly_review(
    athlete_id: str,
    req: WeeklyReviewRequest,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> WeeklyReviewResponse:
    plan = _get_latest_plan(athlete_id, db)

    week_end = date.fromisoformat(req.week_end_date)
    week_start = week_end - timedelta(days=6)

    connector_data = fetch_connector_data(athlete_id, db)
    actual_hours = _compute_actual_hours(
        connector_data["strava_activities"],
        connector_data["hevy_workouts"],
        week_start,
        week_end,
    )

    daily_loads = _build_daily_loads(connector_data["strava_activities"])
    acwr_result = compute_acwr(daily_loads)

    if acwr_result.ratio > 1.3:
        adjustment = 0.9
    elif 0 < acwr_result.ratio < 0.8:
        adjustment = 1.1
    else:
        adjustment = 1.0

    week_number = (
        db.query(TrainingPlanModel)
        .filter(TrainingPlanModel.athlete_id == athlete_id)
        .count()
    )

    review = WeeklyReviewModel(
        id=str(uuid.uuid4()),
        athlete_id=athlete_id,
        plan_id=plan.id,
        week_start=week_start,
        week_number=week_number,
        planned_hours=plan.total_weekly_hours,
        actual_hours=actual_hours,
        acwr=acwr_result.ratio,
        adjustment_applied=adjustment,
        readiness_score=req.readiness_score,
        hrv_rmssd=req.hrv_rmssd,
        sleep_hours_avg=req.sleep_hours_avg,
        athlete_comment=req.comment,
        results_json="{}",
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    return WeeklyReviewResponse(
        review_id=review.id,
        week_number=week_number,
        planned_hours=round(plan.total_weekly_hours, 2),
        actual_hours=actual_hours,
        acwr=round(acwr_result.ratio, 4),
        adjustment_applied=adjustment,
        next_week_suggestion=_adjustment_message(acwr_result.ratio, adjustment),
    )
