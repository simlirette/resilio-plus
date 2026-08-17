"""Onboarding routes — Phase D (D7).

Endpoints:
  POST /onboarding/start   — Start or resume an onboarding session.
  POST /onboarding/respond — Submit response to current onboarding block.
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..dependencies import get_current_athlete_id, get_db
from ..graphs.onboarding import run_onboarding_respond, run_onboarding_start

router = APIRouter(prefix="/onboarding", tags=["onboarding-d7"])

AuthAthleteId = Annotated[str, Depends(get_current_athlete_id)]


# ─── Request / response schemas ───────────────────────────────────────────────


class OnboardingStartRequest(BaseModel):
    athlete_id: str


class OnboardingRespondRequest(BaseModel):
    thread_id: str
    user_response: str


class OnboardingBlockResponse(BaseModel):
    thread_id: str
    current_block: int
    question: str | None
    status: str
    collected_data: dict[str, str] | None = None


# ─── Endpoints ────────────────────────────────────────────────────────────────


@router.post(
    "/start",
    response_model=OnboardingBlockResponse,
    status_code=status.HTTP_200_OK,
)
def start_onboarding(
    body: OnboardingStartRequest,
    current_athlete_id: AuthAthleteId,
    db: Any = Depends(get_db),
) -> OnboardingBlockResponse:
    """Start or resume an onboarding session.

    If the athlete has an existing active onboarding thread, resumes at the
    current block. Otherwise creates a new thread at block 1.
    """
    if current_athlete_id != body.athlete_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot start onboarding for another athlete",
        )
    result = run_onboarding_start(athlete_id=body.athlete_id, db=db)
    return OnboardingBlockResponse(**result)


@router.post(
    "/respond",
    response_model=OnboardingBlockResponse,
    status_code=status.HTTP_200_OK,
)
def respond_onboarding(
    body: OnboardingRespondRequest,
    _: AuthAthleteId,  # auth guard — no ownership check needed (thread_id is opaque)
    db: Any = Depends(get_db),
) -> OnboardingBlockResponse:
    """Submit a response to the current onboarding block.

    Advances to the next block; returns null question and status=completed
    after the final D7 block.
    """
    try:
        result = run_onboarding_respond(
            thread_id=body.thread_id,
            user_response=body.user_response,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return OnboardingBlockResponse(**result)
