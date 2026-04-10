from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.nutrition_logic import compute_nutrition_directives
from ..db.models import AthleteModel
from ..dependencies import get_db, get_current_athlete_id
from ..routes.athletes import athlete_model_to_response
from ..schemas.nutrition import NutritionPlan

router = APIRouter(prefix="/athletes", tags=["nutrition"])

DB = Annotated[Session, Depends(get_db)]


def _require_own(
    athlete_id: str,
    current_id: Annotated[str, Depends(get_current_athlete_id)],
) -> str:
    if current_id != athlete_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return athlete_id


@router.get("/{athlete_id}/nutrition-directives", response_model=NutritionPlan)
def get_nutrition_directives(
    athlete_id: str,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> NutritionPlan:
    """Return per-day-type macro targets for the athlete."""
    athlete_model = db.get(AthleteModel, athlete_id)
    if athlete_model is None:
        raise HTTPException(status_code=404, detail="Athlete not found")
    athlete = athlete_model_to_response(athlete_model)
    return compute_nutrition_directives(athlete)
