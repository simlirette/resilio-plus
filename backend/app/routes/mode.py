"""Mode switch endpoint — PATCH /athletes/{athlete_id}/mode

Allows an authenticated athlete to switch between 'full' and 'tracking_only'.

Side effects:
- full → tracking_only : archives all active TrainingPlan records
- tracking_only → full : no destructive action (data preserved)
"""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db.models import AthleteModel, TrainingPlanModel
from ..dependencies import get_current_athlete_id, get_db

router = APIRouter(prefix="/athletes", tags=["mode"])

DB = Annotated[Session, Depends(get_db)]


class ModeSwitchRequest(BaseModel):
    coaching_mode: Literal["full", "tracking_only"]


class ModeSwitchResponse(BaseModel):
    athlete_id: str
    coaching_mode: str
    message: str


@router.patch("/{athlete_id}/mode", response_model=ModeSwitchResponse)
def switch_mode(
    athlete_id: str,
    req: ModeSwitchRequest,
    db: DB,
    current_id: Annotated[str, Depends(get_current_athlete_id)],
) -> ModeSwitchResponse:
    athlete = db.get(AthleteModel, athlete_id)
    if not athlete or athlete.id != current_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    previous_mode = athlete.coaching_mode
    athlete.coaching_mode = req.coaching_mode

    # Side effect: archive active plans when switching away from full coaching
    if previous_mode == "full" and req.coaching_mode == "tracking_only":
        active_plans = (
            db.query(TrainingPlanModel)
            .filter(
                TrainingPlanModel.athlete_id == athlete_id,
                TrainingPlanModel.status == "active",
            )
            .all()
        )
        for plan in active_plans:
            plan.status = "archived"

    db.commit()
    db.refresh(athlete)

    return ModeSwitchResponse(
        athlete_id=athlete.id,
        coaching_mode=athlete.coaching_mode,
        message=f"Mode switched to {athlete.coaching_mode}",
    )
