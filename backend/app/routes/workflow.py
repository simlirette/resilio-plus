"""
Workflow orchestration routes — Head Coach creation and weekly review loops.

Implements the 9-step plan creation workflow (section 8.1 of resilio-master-v2.md)
and the 5-step weekly review cycle (H1-H5).

These endpoints are intentionally synchronous — plan generation is fast enough
to run within a single HTTP request. For multi-minute jobs, consider background tasks.

Endpoints:
  GET  /athletes/{id}/workflow/status                        — current workflow phase + readiness
  POST /athletes/{id}/workflow/create-plan                   — trigger full plan creation (steps 1-9)
  POST /athletes/{id}/workflow/weekly-sync                   — trigger weekly review cycle (H1-H5)
  POST /athletes/{id}/workflow/plans/{thread_id}/approve     — approve proposed plan
  POST /athletes/{id}/workflow/plans/{thread_id}/revise      — reject and revise plan
"""
from __future__ import annotations

import json
import uuid
from datetime import date, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..db.models import AthleteModel, TrainingPlanModel, WeeklyReviewModel, SessionLogModel
from ..dependencies import get_db, get_current_athlete_id
from ..dependencies.mode_guard import require_full_mode
from ..services.coaching_service import CoachingService

router = APIRouter(prefix="/athletes", tags=["workflow"])

DB = Annotated[Session, Depends(get_db)]


def _validate_thread_ownership(thread_id: str, athlete_id: str) -> None:
    """Verify the thread_id was created for this athlete.

    Thread IDs are prefixed with athlete_id (e.g. 'a1:uuid4').
    Raises HTTPException 403 if the prefix doesn't match.
    """
    if not thread_id.startswith(f"{athlete_id}:"):
        raise HTTPException(status_code=403, detail="Thread does not belong to this athlete")


def _require_own(
    athlete_id: str,
    current_id: Annotated[str, Depends(get_current_athlete_id)],
    db: DB,
) -> AthleteModel:
    athlete = db.get(AthleteModel, athlete_id)
    if not athlete or athlete.id != current_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return athlete


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class WorkflowStatus(BaseModel):
    athlete_id: str
    phase: Literal["onboarding", "no_plan", "active", "weekly_review_due"]
    has_plan: bool
    plan_id: str | None
    plan_start_date: date | None
    plan_end_date: date | None
    weeks_completed: int
    sessions_logged_this_week: int
    weekly_review_due: bool
    acwr: float | None
    readiness: Literal["green", "yellow", "red"] | None


class PlanCreateRequest(BaseModel):
    start_date: date
    weeks: int = 8


class PlanCreateResponse(BaseModel):
    success: bool
    plan_id: str | None = None
    phase: str | None = None
    weeks: int | None = None
    sessions_total: int | None = None
    message: str = ""
    thread_id: str | None = None
    requires_approval: bool = False


class PlanApproveResponse(BaseModel):
    success: bool
    plan_id: str | None = None
    message: str = ""


class PlanReviseRequest(BaseModel):
    feedback: str
    weeks: int | None = None


class WeeklySyncResponse(BaseModel):
    success: bool
    week_number: int
    sessions_completed: int
    sessions_planned: int
    completion_rate: float
    acwr: float | None
    readiness: Literal["green", "yellow", "red"] | None
    recommendations: list[str]
    next_week_adjusted: bool


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/{athlete_id}/workflow/status", response_model=WorkflowStatus)
def get_workflow_status(
    athlete_id: str,
    athlete: Annotated[AthleteModel, Depends(_require_own)],
    db: DB,
) -> WorkflowStatus:
    """
    Return the athlete's current workflow phase and readiness for next step.

    Phases:
      - onboarding:       athlete created but no plan yet and no target date
      - no_plan:          athlete has target date but no plan generated
      - active:           plan exists and is current
      - weekly_review_due: active plan but this week's review is not done
    """
    plan = (
        db.query(TrainingPlanModel)
        .filter(TrainingPlanModel.athlete_id == athlete_id)
        .order_by(desc(TrainingPlanModel.created_at))
        .first()
    )

    if plan is None:
        phase = "no_plan" if athlete.target_race_date else "onboarding"
        return WorkflowStatus(
            athlete_id=athlete_id,
            phase=phase,
            has_plan=False,
            plan_id=None,
            plan_start_date=None,
            plan_end_date=None,
            weeks_completed=0,
            sessions_logged_this_week=0,
            weekly_review_due=False,
            acwr=None,
            readiness=None,
        )

    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    sessions_this_week = (
        db.query(SessionLogModel)
        .filter(
            SessionLogModel.athlete_id == athlete_id,
            SessionLogModel.actual_duration_min.isnot(None),
        )
        .count()
    )

    latest_review = (
        db.query(WeeklyReviewModel)
        .filter(WeeklyReviewModel.athlete_id == athlete_id)
        .order_by(desc(WeeklyReviewModel.week_start))
        .first()
    )

    review_due = (
        latest_review is None
        or latest_review.week_start < week_start
    )

    weeks_completed = 0
    if plan.start_date:
        delta = today - plan.start_date
        weeks_completed = max(0, delta.days // 7)

    acwr = latest_review.acwr if latest_review else None
    readiness = _readiness_from_acwr(acwr)

    phase: Literal["onboarding", "no_plan", "active", "weekly_review_due"] = (
        "weekly_review_due" if review_due else "active"
    )

    return WorkflowStatus(
        athlete_id=athlete_id,
        phase=phase,
        has_plan=True,
        plan_id=plan.id,
        plan_start_date=plan.start_date,
        plan_end_date=plan.end_date,
        weeks_completed=weeks_completed,
        sessions_logged_this_week=sessions_this_week,
        weekly_review_due=review_due,
        acwr=acwr,
        readiness=readiness,
    )


@router.post("/{athlete_id}/workflow/create-plan", response_model=PlanCreateResponse)
def create_plan_workflow(
    athlete_id: str,
    body: PlanCreateRequest,
    athlete: Annotated[AthleteModel, Depends(require_full_mode)],
    db: DB,
) -> PlanCreateResponse:
    """
    Trigger the LangGraph plan creation workflow (V3-D).

    Runs the coaching graph until the present_to_athlete interrupt, then
    returns the proposed plan with thread_id for approval/revision.
    """
    try:
        sports = json.loads(athlete.sports_json)
        goals = json.loads(athlete.goals_json)
        available_days = json.loads(athlete.available_days_json)
        equipment = json.loads(athlete.equipment_json)
    except Exception:
        sports, goals, available_days, equipment = [], [], [], []

    from ..schemas.athlete import AthleteProfile
    athlete_profile = AthleteProfile(
        id=athlete.id,
        name=athlete.name,
        age=athlete.age,
        sex=athlete.sex,
        weight_kg=athlete.weight_kg,
        height_cm=athlete.height_cm,
        sports=sports,
        primary_sport=athlete.primary_sport,
        goals=goals,
        available_days=available_days,
        hours_per_week=athlete.hours_per_week,
        target_race_date=athlete.target_race_date,
        sleep_hours_typical=athlete.sleep_hours_typical,
        stress_level=athlete.stress_level,
        job_physical=athlete.job_physical,
        max_hr=athlete.max_hr,
        resting_hr=athlete.resting_hr,
        ftp_watts=athlete.ftp_watts,
        vdot=athlete.vdot,
        css_per_100m=athlete.css_per_100m,
        equipment=equipment,
        coaching_mode=athlete.coaching_mode,
    )

    service = CoachingService()
    try:
        thread_id, proposed_dict = service.create_plan(
            athlete_id=athlete_id,
            athlete_dict=athlete_profile.model_dump(mode="json"),
            load_history=[],
            db=db,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Plan generation failed: {exc}") from exc

    sessions_total = len(proposed_dict.get("sessions", [])) if proposed_dict else 0
    phase = proposed_dict.get("phase", "base") if proposed_dict else "base"

    return PlanCreateResponse(
        success=True,
        plan_id=None,
        phase=phase,
        weeks=body.weeks,
        sessions_total=sessions_total,
        message=(
            f"Plan proposé — {body.weeks} semaines phase {phase}. "
            f"{sessions_total} séances. En attente de validation."
        ),
        thread_id=thread_id,
        requires_approval=True,
    )


@router.post("/{athlete_id}/workflow/plans/{thread_id}/approve", response_model=PlanApproveResponse)
def approve_plan(
    athlete_id: str,
    thread_id: str,
    athlete: Annotated[AthleteModel, Depends(require_full_mode)],
    db: DB,
) -> PlanApproveResponse:
    """Approve the proposed plan — finalize and persist to DB."""
    _validate_thread_ownership(thread_id, athlete_id)
    service = CoachingService()
    try:
        final_dict = service.resume_plan(
            thread_id=thread_id,
            approved=True,
            feedback=None,
            db=db,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Plan approval failed: {exc}") from exc

    plan_id = final_dict.get("db_plan_id") if final_dict else None
    return PlanApproveResponse(
        success=True,
        plan_id=plan_id,
        message="Plan approuvé et enregistré." if plan_id else "Plan approuvé.",
    )


@router.post("/{athlete_id}/workflow/plans/{thread_id}/revise", response_model=PlanCreateResponse)
def revise_plan_endpoint(
    athlete_id: str,
    thread_id: str,
    body: PlanReviseRequest,
    athlete: Annotated[AthleteModel, Depends(require_full_mode)],
    db: DB,
) -> PlanCreateResponse:
    """Reject the proposed plan with feedback and request a revision."""
    _validate_thread_ownership(thread_id, athlete_id)
    service = CoachingService()
    try:
        new_proposed = service.resume_plan(
            thread_id=thread_id,
            approved=False,
            feedback=body.feedback,
            db=db,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Plan revision failed: {exc}") from exc

    sessions_total = len(new_proposed.get("sessions", [])) if new_proposed else 0
    phase = new_proposed.get("phase", "base") if new_proposed else "base"

    return PlanCreateResponse(
        success=True,
        plan_id=None,
        phase=phase,
        weeks=body.weeks,
        sessions_total=sessions_total,
        message=f"Plan révisé. {sessions_total} séances proposées.",
        thread_id=thread_id,
        requires_approval=True,
    )


@router.post("/{athlete_id}/workflow/weekly-sync", response_model=WeeklySyncResponse)
def weekly_sync(
    athlete_id: str,
    athlete: Annotated[AthleteModel, Depends(_require_own)],
    db: DB,
) -> WeeklySyncResponse:
    """
    Trigger the H1-H5 weekly review cycle.

    H1: Pull session data from DB (connector syncs happen via /connectors/*)
    H2: Compare planned vs actual sessions
    H3: Compute ACWR, update readiness
    H4: Generate recommendations
    H5: Create WeeklyReview record for the current week
    """
    plan = (
        db.query(TrainingPlanModel)
        .filter(TrainingPlanModel.athlete_id == athlete_id)
        .order_by(desc(TrainingPlanModel.created_at))
        .first()
    )
    if plan is None:
        raise HTTPException(status_code=404, detail="No training plan found. Create a plan first.")

    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    # H1 + H2: Planned vs actual sessions
    try:
        slots_data = json.loads(plan.weekly_slots_json)
    except Exception:
        slots_data = []

    # Find this week's slots
    planned_this_week = 0
    for week_block in slots_data:
        ws = week_block.get("week_start")
        if ws:
            try:
                ws_date = date.fromisoformat(ws)
                if ws_date == week_start:
                    planned_this_week = len(week_block.get("sessions", []))
                    break
            except ValueError:
                pass

    # Count logged sessions (any non-skipped session)
    logged_sessions = (
        db.query(SessionLogModel)
        .filter(
            SessionLogModel.athlete_id == athlete_id,
            SessionLogModel.skipped == False,  # noqa: E712
            SessionLogModel.actual_duration_min.isnot(None),
        )
        .count()
    )

    # H3: Compute ACWR from reviews
    recent_reviews = (
        db.query(WeeklyReviewModel)
        .filter(WeeklyReviewModel.athlete_id == athlete_id)
        .order_by(desc(WeeklyReviewModel.week_start))
        .limit(4)
        .all()
    )

    acwr = _compute_acwr(logged_sessions, recent_reviews)
    readiness = _readiness_from_acwr(acwr)
    completion_rate = logged_sessions / planned_this_week if planned_this_week > 0 else 0.0

    # H4: Recommendations
    recommendations = _build_recommendations(
        acwr=acwr,
        completion_rate=completion_rate,
        readiness=readiness,
    )

    # H5: Persist weekly review
    week_number = max(1, (today - plan.start_date).days // 7 + 1) if plan.start_date else 1

    review = WeeklyReviewModel(
        id=str(uuid.uuid4()),
        athlete_id=athlete_id,
        plan_id=plan.id,
        week_start=week_start,
        week_number=week_number,
        planned_hours=athlete.hours_per_week,
        actual_hours=None,
        acwr=acwr,
        adjustment_applied=None,
        readiness_score=None,
        athlete_comment="",
        results_json=json.dumps({
            "sessions_logged": logged_sessions,
            "sessions_planned": planned_this_week,
            "completion_rate": completion_rate,
            "readiness": readiness,
            "recommendations": recommendations,
        }),
    )
    db.add(review)
    db.commit()

    next_week_adjusted = acwr is not None and (acwr > 1.3 or acwr < 0.8)

    return WeeklySyncResponse(
        success=True,
        week_number=week_number,
        sessions_completed=logged_sessions,
        sessions_planned=planned_this_week,
        completion_rate=round(completion_rate, 2),
        acwr=round(acwr, 2) if acwr is not None else None,
        readiness=readiness,
        recommendations=recommendations,
        next_week_adjusted=next_week_adjusted,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_acwr(
    current_load: int,
    recent_reviews: list[WeeklyReviewModel],
) -> float | None:
    """
    Simplified ACWR: acute (current week sessions) / chronic (avg of last 4 weeks).
    Returns None if no chronic data available.
    """
    if not recent_reviews:
        return None
    chronic_values = []
    for r in recent_reviews:
        try:
            results = json.loads(r.results_json)
            completed = results.get("sessions_logged", 0)
            chronic_values.append(float(completed))
        except Exception:
            pass
    if not chronic_values:
        return None
    chronic_avg = sum(chronic_values) / len(chronic_values)
    if chronic_avg == 0:
        return None
    return current_load / chronic_avg


def _readiness_from_acwr(acwr: float | None) -> Literal["green", "yellow", "red"] | None:
    if acwr is None:
        return None
    if acwr <= 1.3:
        return "green"
    if acwr <= 1.5:
        return "yellow"
    return "red"


def _build_recommendations(
    acwr: float | None,
    completion_rate: float,
    readiness: str | None,
) -> list[str]:
    recs = []
    if readiness == "red":
        recs.append("ACWR > 1.5 — réduire le volume de 20% la semaine prochaine.")
        recs.append("Prioriser le sommeil et la récupération active.")
    elif readiness == "yellow":
        recs.append("ACWR entre 1.3 et 1.5 — maintenir le volume, pas d'augmentation.")
        recs.append("Surveiller les signaux de fatigue (FC repos, humeur, RPE).")
    elif readiness == "green":
        if completion_rate >= 0.9:
            recs.append("Excellente semaine! Tu peux augmenter légèrement le volume (+5-10%).")
        elif completion_rate >= 0.7:
            recs.append("Bonne semaine. Maintenir le volume actuel.")
        else:
            recs.append("Taux de complétion faible — identifier les obstacles et ajuster le planning.")

    if completion_rate < 0.5:
        recs.append("Moins de 50% des séances complétées — envisager de réduire la densité du plan.")

    return recs
