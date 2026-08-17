"""Followup transition routes — Phase D (D9).

Endpoints:
  POST /followup/respond — Submit response to current followup step.
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..dependencies import get_current_athlete_id, get_db
from ..graphs.followup_transition import run_followup_respond, run_followup_start

router = APIRouter(prefix="/followup", tags=["followup"])

AuthAthleteId = Annotated[str, Depends(get_current_athlete_id)]


class FollowupStartRequest(BaseModel):
    athlete_id: str


class FollowupRespondRequest(BaseModel):
    thread_id: str
    user_response: str
    adjust_objective: bool = False


class FollowupStepResponse(BaseModel):
    thread_id: str
    step: str
    question: str | None
    status: str
    journey_phase: str | None = None
    onboarding_reentry_active: bool | None = None


@router.post("/start", response_model=FollowupStepResponse, status_code=status.HTTP_200_OK)
def start_followup(
    body: FollowupStartRequest,
    current_athlete_id: AuthAthleteId,
    db: Any = Depends(get_db),
) -> FollowupStepResponse:
    """Start the followup_transition conversation."""
    if current_athlete_id != body.athlete_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot start followup for another athlete",
        )
    result = run_followup_start(athlete_id=body.athlete_id, db=db)
    return FollowupStepResponse(**result)


@router.post("/respond", response_model=FollowupStepResponse, status_code=status.HTTP_200_OK)
def respond_followup(
    body: FollowupRespondRequest,
    _: AuthAthleteId,
    db: Any = Depends(get_db),
) -> FollowupStepResponse:
    """Submit a response to the current followup step."""
    try:
        result = run_followup_respond(
            thread_id=body.thread_id,
            user_response=body.user_response,
            db=db,
            adjust_objective=body.adjust_objective,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return FollowupStepResponse(**result)
