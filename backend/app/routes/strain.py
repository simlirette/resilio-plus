# backend/app/routes/strain.py
from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.strain import MUSCLES, compute_muscle_strain
from ..db.models import AthleteModel
from ..dependencies import get_current_athlete_id, get_db
from ..services.connector_service import fetch_connector_data

router = APIRouter(prefix="/athletes", tags=["strain"])

DB = Annotated[Session, Depends(get_db)]


class MuscleStrainResponse(BaseModel):
    computed_at: date
    scores: dict[str, float]
    peak_group: str
    peak_score: float


def _require_own(
    athlete_id: str,
    current_id: Annotated[str, Depends(get_current_athlete_id)],
) -> str:
    if current_id != athlete_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return athlete_id


@router.get("/{athlete_id}/strain", response_model=MuscleStrainResponse)
def get_strain(
    athlete_id: str,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> MuscleStrainResponse:
    if db.get(AthleteModel, athlete_id) is None:
        raise HTTPException(status_code=404, detail="Athlete not found")

    connector_data = fetch_connector_data(athlete_id, db)
    strain = compute_muscle_strain(
        strava_activities=connector_data["strava_activities"],
        hevy_workouts=connector_data["hevy_workouts"],
    )

    scores = {m: getattr(strain, m) for m in MUSCLES}
    peak_group = max(scores, key=lambda k: scores[k])

    return MuscleStrainResponse(
        computed_at=strain.computed_at.date(),
        scores=scores,
        peak_group=peak_group,
        peak_score=scores[peak_group],
    )
