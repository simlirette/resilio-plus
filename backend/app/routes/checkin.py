"""Energy Cycle routes — V3-C.

No mode restriction — available to all athletes.
    POST  /athletes/{id}/checkin         → ReadinessResponse (201)
    GET   /athletes/{id}/readiness       → ReadinessResponse
    GET   /athletes/{id}/energy/history  → list[EnergySnapshotSummary]
    PATCH /athletes/{id}/hormonal-profile → HormonalProfileResponse
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..dependencies import get_current_athlete_id, get_db
from ..schemas.checkin import CheckInInput, HormonalProfileUpdate, ReadinessResponse
from ..services.energy_cycle_service import (
    EnergyCycleService,
    traffic_light_from_readiness,
)

router = APIRouter(prefix="/athletes", tags=["energy"])

DB = Annotated[Session, Depends(get_db)]
_svc = EnergyCycleService()


def _require_own(
    athlete_id: str,
    current_id: Annotated[str, Depends(get_current_athlete_id)],
) -> str:
    if current_id != athlete_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return athlete_id


class HormonalProfileResponse(BaseModel):
    athlete_id: str
    enabled: bool
    cycle_length_days: int
    last_period_start: str | None
    tracking_source: str
    notes: str | None


class EnergySnapshotSummary(BaseModel):
    date: str
    objective_score: float | None
    subjective_score: float | None
    allostatic_score: float
    energy_availability: float
    intensity_cap: float
    veto_triggered: bool
    traffic_light: str


@router.post("/{athlete_id}/checkin", response_model=ReadinessResponse, status_code=201)
def submit_checkin(
    athlete_id: str,
    body: CheckInInput,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> ReadinessResponse:
    return _svc.submit_checkin(athlete_id, db, body)


@router.get("/{athlete_id}/readiness", response_model=ReadinessResponse)
def get_readiness(
    athlete_id: str,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> ReadinessResponse:
    return _svc.get_readiness(athlete_id, db)


@router.get("/{athlete_id}/energy/history", response_model=list[EnergySnapshotSummary])
def get_energy_history(
    athlete_id: str,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
    days: int = Query(default=28, ge=1, le=90),
) -> list[EnergySnapshotSummary]:
    snapshots = _svc.get_history(athlete_id, db, days=days)
    result = []
    for s in snapshots:
        obj = s.objective_score or 50.0
        subj = s.subjective_score or 50.0
        div = abs(obj - subj)
        w = 0.55 if div > 25 else 0.40
        final = obj * (1 - w) + subj * w
        result.append(
            EnergySnapshotSummary(
                date=str(s.timestamp.date()),
                objective_score=s.objective_score,
                subjective_score=s.subjective_score,
                allostatic_score=round(s.allostatic_score, 2),
                energy_availability=round(s.energy_availability, 2),
                intensity_cap=round(s.recommended_intensity_cap, 2),
                veto_triggered=s.veto_triggered,
                traffic_light=traffic_light_from_readiness(final),
            )
        )
    return result


@router.patch("/{athlete_id}/hormonal-profile", response_model=HormonalProfileResponse)
def update_hormonal_profile(
    athlete_id: str,
    body: HormonalProfileUpdate,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> HormonalProfileResponse:
    profile = _svc.update_hormonal_profile(athlete_id, db, body)
    return HormonalProfileResponse(
        athlete_id=profile.athlete_id,
        enabled=profile.enabled,
        cycle_length_days=profile.cycle_length_days,
        last_period_start=(str(profile.last_period_start) if profile.last_period_start else None),
        tracking_source=profile.tracking_source,
        notes=profile.notes,
    )
