"""ModeGuard — FastAPI dependencies that enforce coaching_mode on routes.

Usage:
    @router.post("/create-plan")
    def create_plan(athlete: AthleteModel = Depends(require_full_mode)):
        ...

Both guards:
  1. Verify the JWT belongs to the requested athlete (ownership check)
  2. Verify the athlete is in the required mode
"""
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db.models import AthleteModel
from . import get_db, get_current_athlete_id


def require_full_mode(
    athlete_id: str,
    current_id: Annotated[str, Depends(get_current_athlete_id)],
    db: Annotated[Session, Depends(get_db)],
) -> AthleteModel:
    """Return the AthleteModel if the caller owns it and is in 'full' mode.

    Raises 403 if mode is 'tracking_only'.
    Raises 403 if the JWT athlete_id doesn't match the path athlete_id.
    """
    athlete = db.get(AthleteModel, athlete_id)
    if not athlete or athlete.id != current_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if athlete.coaching_mode != "full":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires Full Coaching mode",
        )
    return athlete


def require_tracking_mode(
    athlete_id: str,
    current_id: Annotated[str, Depends(get_current_athlete_id)],
    db: Annotated[Session, Depends(get_db)],
) -> AthleteModel:
    """Return the AthleteModel if the caller owns it and is in 'tracking_only' mode.

    Raises 403 if mode is 'full'.
    """
    athlete = db.get(AthleteModel, athlete_id)
    if not athlete or athlete.id != current_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if athlete.coaching_mode != "tracking_only":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires Tracking Only mode",
        )
    return athlete
