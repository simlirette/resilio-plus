"""ExternalPlan routes — Tracking Only mode only.

All endpoints require require_tracking_mode (403 if athlete is in 'full' mode).

Endpoints:
  POST   /athletes/{id}/external-plan                          → create plan
  GET    /athletes/{id}/external-plan                          → get active plan
  POST   /athletes/{id}/external-plan/sessions                 → add session
  PATCH  /athletes/{id}/external-plan/sessions/{session_id}    → update session
  DELETE /athletes/{id}/external-plan/sessions/{session_id}    → delete session
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from ..db.models import AthleteModel
from ..dependencies import get_db
from ..dependencies.mode_guard import require_tracking_mode
from ..schemas.external_plan import (
    ExternalPlanCreate,
    ExternalPlanDraft,
    ExternalPlanOut,
    ExternalSessionCreate,
    ExternalSessionOut,
    ExternalSessionUpdate,
)
from ..services.external_plan_service import ExternalPlanService
from ..services.plan_import_service import PlanImportService

router = APIRouter(prefix="/athletes", tags=["external-plan"])

DB = Annotated[Session, Depends(get_db)]
TrackingAthlete = Annotated[AthleteModel, Depends(require_tracking_mode)]


@router.post(
    "/{athlete_id}/external-plan",
    response_model=ExternalPlanOut,
    status_code=status.HTTP_201_CREATED,
)
def create_external_plan(
    athlete_id: str,
    body: ExternalPlanCreate,
    athlete: TrackingAthlete,
    db: DB,
) -> ExternalPlanOut:
    """Create a new external plan (archives any previous active plan)."""
    plan = ExternalPlanService.create_plan(
        athlete_id=athlete_id,
        title=body.title,
        start_date=body.start_date,
        end_date=body.end_date,
        db=db,
    )
    db.refresh(plan)
    return ExternalPlanOut.model_validate(plan)


@router.get(
    "/{athlete_id}/external-plan",
    response_model=ExternalPlanOut,
)
def get_active_external_plan(
    athlete_id: str,
    athlete: TrackingAthlete,
    db: DB,
) -> ExternalPlanOut:
    """Get the athlete's active external plan with all sessions."""
    plan = ExternalPlanService.get_active_plan(athlete_id=athlete_id, db=db)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active external plan found",
        )
    return ExternalPlanOut.model_validate(plan)


@router.post(
    "/{athlete_id}/external-plan/sessions",
    response_model=ExternalSessionOut,
    status_code=status.HTTP_201_CREATED,
)
def add_external_session(
    athlete_id: str,
    body: ExternalSessionCreate,
    athlete: TrackingAthlete,
    db: DB,
) -> ExternalSessionOut:
    """Add a session to the athlete's active external plan."""
    plan = ExternalPlanService.get_active_plan(athlete_id=athlete_id, db=db)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active external plan. Create a plan first.",
        )
    session_obj = ExternalPlanService.add_session(
        plan_id=plan.id,
        athlete_id=athlete_id,
        session_date=body.session_date,
        sport=body.sport,
        title=body.title,
        description=body.description,
        duration_min=body.duration_min,
        db=db,
    )
    return ExternalSessionOut.model_validate(session_obj)


@router.patch(
    "/{athlete_id}/external-plan/sessions/{session_id}",
    response_model=ExternalSessionOut,
)
def update_external_session(
    athlete_id: str,
    session_id: str,
    body: ExternalSessionUpdate,
    athlete: TrackingAthlete,
    db: DB,
) -> ExternalSessionOut:
    """Partially update an external session."""
    updates = body.model_dump(exclude_none=True)
    session_obj = ExternalPlanService.update_session(
        session_id=session_id,
        athlete_id=athlete_id,
        updates=updates,
        db=db,
    )
    return ExternalSessionOut.model_validate(session_obj)


@router.delete(
    "/{athlete_id}/external-plan/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_external_session(
    athlete_id: str,
    session_id: str,
    athlete: TrackingAthlete,
    db: DB,
) -> None:
    """Hard-delete an external session."""
    ExternalPlanService.delete_session(
        session_id=session_id,
        athlete_id=athlete_id,
        db=db,
    )


@router.post(
    "/{athlete_id}/external-plan/import",
    response_model=ExternalPlanDraft,
    status_code=200,
)
async def import_plan_file(
    athlete_id: str,
    athlete: TrackingAthlete,
    db: DB,
    file: UploadFile = File(...),
) -> ExternalPlanDraft:
    """Upload a plan file; Claude Haiku parses it into an ExternalPlanDraft.

    No DB write — the athlete reviews the draft and calls /import/confirm to persist.
    """
    raw = await file.read()
    content = raw.decode("utf-8", errors="replace")
    filename = file.filename or "upload"
    return PlanImportService.parse_file(content=content, filename=filename)


@router.post(
    "/{athlete_id}/external-plan/import/confirm",
    response_model=ExternalPlanOut,
    status_code=201,
)
def confirm_plan_import(
    athlete_id: str,
    body: ExternalPlanDraft,
    athlete: TrackingAthlete,
    db: DB,
) -> ExternalPlanOut:
    """Persist a reviewed ExternalPlanDraft as the athlete's active ExternalPlan."""
    plan = PlanImportService.confirm_import(
        athlete_id=athlete_id,
        draft=body,
        db=db,
    )
    return ExternalPlanOut.model_validate(plan)
