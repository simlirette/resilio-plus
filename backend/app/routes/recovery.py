from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.recovery_logic import compute_recovery_status
from ..db.models import AthleteModel
from ..dependencies import get_db, get_current_athlete_id
from ..routes.athletes import athlete_model_to_response

router = APIRouter(prefix="/athletes", tags=["recovery"])

DB = Annotated[Session, Depends(get_db)]


def _require_own(
    athlete_id: str,
    current_id: Annotated[str, Depends(get_current_athlete_id)],
) -> str:
    if current_id != athlete_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return athlete_id


class RecoveryStatusResponse(BaseModel):
    readiness_modifier: float
    hrv_trend: str
    sleep_avg_hours: float | None
    sleep_banking_active: bool
    recommendation: str


@router.get("/{athlete_id}/recovery-status", response_model=RecoveryStatusResponse)
def get_recovery_status(
    athlete_id: str,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> RecoveryStatusResponse:
    """Return current recovery status based on Terra/HRV data."""
    from datetime import date
    from ..services.connector_service import fetch_connector_data

    athlete_model = db.get(AthleteModel, athlete_id)
    if athlete_model is None:
        raise HTTPException(status_code=404, detail="Athlete not found")
    athlete = athlete_model_to_response(athlete_model)
    connector_data = fetch_connector_data(athlete_id, db)

    status = compute_recovery_status(
        terra_data=connector_data.get("terra_health", []),
        target_race_date=athlete.target_race_date,
        week_start=date.today(),
    )

    return RecoveryStatusResponse(
        readiness_modifier=status.readiness_modifier,
        hrv_trend=status.hrv_trend,
        sleep_avg_hours=status.sleep_avg_hours,
        sleep_banking_active=status.sleep_banking_active,
        recommendation=status.recommendation,
    )
