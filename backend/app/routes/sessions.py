from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..db.models import AthleteModel, SessionLogModel, TrainingPlanModel
from ..dependencies import get_db, get_current_athlete_id
from ..schemas.plan import WorkoutSlot
from ..schemas.session_log import (
    SessionDetailResponse,
    SessionLogRequest,
    SessionLogResponse,
    WeekSummary,
)

router = APIRouter(prefix="/athletes", tags=["sessions"])

DB = Annotated[Session, Depends(get_db)]


def _require_own(
    athlete_id: str,
    current_id: Annotated[str, Depends(get_current_athlete_id)],
) -> str:
    if current_id != athlete_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return athlete_id


def _get_latest_plan(athlete_id: str, db: Session) -> TrainingPlanModel:
    plan = (
        db.query(TrainingPlanModel)
        .filter(TrainingPlanModel.athlete_id == athlete_id)
        .order_by(desc(TrainingPlanModel.created_at))
        .first()
    )
    if plan is None:
        raise HTTPException(status_code=404, detail="No plan found")
    return plan


def _find_session(plan: TrainingPlanModel, session_id: str) -> WorkoutSlot | None:
    slots = [WorkoutSlot.model_validate(s) for s in json.loads(plan.weekly_slots_json)]
    for slot in slots:
        if slot.id == session_id:
            return slot
    return None


def _log_to_response(log: SessionLogModel) -> SessionLogResponse:
    return SessionLogResponse(
        id=log.id,
        session_id=log.session_id,
        actual_duration_min=log.actual_duration_min,
        skipped=log.skipped,
        rpe=log.rpe,
        notes=log.notes,
        actual_data=json.loads(log.actual_data_json),
        logged_at=log.logged_at,
    )


@router.get("/{athlete_id}/sessions/{session_id}", response_model=SessionDetailResponse)
def get_session_detail(
    athlete_id: str,
    session_id: str,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> SessionDetailResponse:
    plan = _get_latest_plan(athlete_id, db)
    slot = _find_session(plan, session_id)
    if slot is None:
        raise HTTPException(status_code=404, detail="Session not found in current plan")

    log_model = (
        db.query(SessionLogModel)
        .filter(
            SessionLogModel.athlete_id == athlete_id,
            SessionLogModel.session_id == session_id,
        )
        .first()
    )

    return SessionDetailResponse(
        session_id=slot.id,
        plan_id=plan.id,
        date=slot.date,
        sport=slot.sport,
        workout_type=slot.workout_type,
        duration_min=slot.duration_min,
        fatigue_score=slot.fatigue_score,
        notes=slot.notes,
        log=_log_to_response(log_model) if log_model else None,
    )


@router.post(
    "/{athlete_id}/sessions/{session_id}/log",
    response_model=SessionLogResponse,
    status_code=201,
)
def log_session(
    athlete_id: str,
    session_id: str,
    req: SessionLogRequest,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> SessionLogResponse:
    # Verify session exists in latest plan
    plan = _get_latest_plan(athlete_id, db)
    slot = _find_session(plan, session_id)
    if slot is None:
        raise HTTPException(status_code=404, detail="Session not found in current plan")

    # Upsert
    existing = (
        db.query(SessionLogModel)
        .filter(
            SessionLogModel.athlete_id == athlete_id,
            SessionLogModel.session_id == session_id,
        )
        .first()
    )

    if existing:
        existing.actual_duration_min = req.actual_duration_min
        existing.skipped = req.skipped
        existing.rpe = req.rpe
        existing.notes = req.notes
        existing.actual_data_json = json.dumps(req.actual_data)
        existing.logged_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        return _log_to_response(existing)

    log = SessionLogModel(
        id=str(uuid.uuid4()),
        athlete_id=athlete_id,
        plan_id=plan.id,
        session_id=session_id,
        actual_duration_min=req.actual_duration_min,
        skipped=req.skipped,
        rpe=req.rpe,
        notes=req.notes,
        actual_data_json=json.dumps(req.actual_data),
        logged_at=datetime.now(timezone.utc),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return _log_to_response(log)


@router.get("/{athlete_id}/sessions/{session_id}/log", response_model=SessionLogResponse)
def get_session_log(
    athlete_id: str,
    session_id: str,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> SessionLogResponse:
    log = (
        db.query(SessionLogModel)
        .filter(
            SessionLogModel.athlete_id == athlete_id,
            SessionLogModel.session_id == session_id,
        )
        .first()
    )
    if log is None:
        raise HTTPException(status_code=404, detail="No log found for this session")
    return _log_to_response(log)


@router.get("/{athlete_id}/history", response_model=list[WeekSummary])
def get_history(
    athlete_id: str,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> list[WeekSummary]:
    plans = (
        db.query(TrainingPlanModel)
        .filter(TrainingPlanModel.athlete_id == athlete_id)
        .order_by(desc(TrainingPlanModel.created_at))
        .all()
    )

    summaries: list[WeekSummary] = []
    for i, plan in enumerate(plans):
        slots = json.loads(plan.weekly_slots_json)
        sessions_total = len(slots)
        sessions_logged = (
            db.query(SessionLogModel)
            .filter(
                SessionLogModel.athlete_id == athlete_id,
                SessionLogModel.plan_id == plan.id,
            )
            .count()
        )
        completion_pct = (
            round(sessions_logged / sessions_total * 100, 1)
            if sessions_total > 0
            else 0.0
        )
        week_number = len(plans) - i  # oldest = 1
        summaries.append(
            WeekSummary(
                plan_id=plan.id,
                week_number=week_number,
                start_date=plan.start_date,
                end_date=plan.end_date,
                phase=plan.phase,
                planned_hours=round(plan.total_weekly_hours, 2),
                sessions_total=sessions_total,
                sessions_logged=sessions_logged,
                completion_pct=completion_pct,
            )
        )
    return summaries
