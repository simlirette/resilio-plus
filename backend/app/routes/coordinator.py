"""Coordinator routes — dispatch events and read journey state.

Endpoints:
  POST /coordinator/dispatch                — route event to target graph
  GET  /coordinator/state/{athlete_id}      — journey_phase + overlays + thread IDs
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db.models import AthleteModel
from ..dependencies import get_current_athlete_id, get_db
from ..services.coordinator_service import coordinator_service

router = APIRouter(prefix="/coordinator", tags=["coordinator"])

DB = Annotated[Session, Depends(get_db)]
AuthAthleteId = Annotated[str, Depends(get_current_athlete_id)]


class DispatchRequest(BaseModel):
    event_type: str
    payload: dict[str, Any] = {}


class DispatchResponse(BaseModel):
    graph_invoked: str | None
    thread_id: str | None
    output: dict[str, Any] | None
    pending: bool


class CoordinatorStateResponse(BaseModel):
    athlete_id: str
    journey_phase: str
    overlays: dict[str, bool]
    active_threads: dict[str, str | None]


@router.post("/dispatch", response_model=DispatchResponse)
def dispatch_event(
    req: DispatchRequest,
    athlete_id: AuthAthleteId,
    db: DB,
) -> DispatchResponse:
    """Route un événement utilisateur ou système vers le graphe approprié."""
    try:
        result = coordinator_service.dispatch(
            athlete_id, req.event_type, req.payload, db
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return DispatchResponse(
        graph_invoked=result.graph_invoked,
        thread_id=result.thread_id,
        output=result.output,
        pending=result.pending,
    )


@router.get("/state/{target_athlete_id}", response_model=CoordinatorStateResponse)
def get_coordinator_state(
    target_athlete_id: str,
    current_athlete_id: AuthAthleteId,
    db: DB,
) -> CoordinatorStateResponse:
    """Retourne journey_phase, overlays actifs et thread IDs persistents."""
    if target_athlete_id != current_athlete_id:
        raise HTTPException(
            status_code=403,
            detail="Cannot access another athlete's coordinator state",
        )

    athlete = db.query(AthleteModel).filter(AthleteModel.id == target_athlete_id).first()
    if athlete is None:
        raise HTTPException(status_code=404, detail="Athlete not found")

    return CoordinatorStateResponse(
        athlete_id=athlete.id,
        journey_phase=athlete.journey_phase,
        overlays={
            "recovery_takeover_active": bool(athlete.recovery_takeover_active),
            "onboarding_reentry_active": bool(athlete.onboarding_reentry_active),
        },
        active_threads={
            "onboarding": athlete.active_onboarding_thread_id,
            "recovery_takeover": athlete.active_recovery_thread_id,
            "followup_transition": athlete.active_followup_thread_id,
        },
    )
