"""EnergyCycleService — V3-C.

Standalone service for the Energy Cycle (Volet 2).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..agents.energy_coach.agent import EnergyCoach, EnergyInput
from ..db.models import AthleteModel, EnergySnapshotModel, HormonalProfileModel
from ..models.athlete_state import EnergyCheckIn
from ..schemas.checkin import CheckInInput, HormonalProfileUpdate, ReadinessResponse

_LEG_SCORES: dict[str, float] = {"fresh": 0.0, "normal": 25.0, "heavy": 60.0, "dead": 90.0}
_ENERGY_SCORES: dict[str, float] = {"great": 0.0, "ok": 20.0, "low": 55.0, "exhausted": 85.0}


def compute_subjective_score(legs_feeling: str, energy_global: str) -> float:
    """Return readiness-direction subjective score (0–100, 100 = fresh)."""
    load = (_LEG_SCORES[legs_feeling] + _ENERGY_SCORES[energy_global]) / 2.0
    return round(100.0 - load, 2)


def classify_divergence(divergence: float) -> Literal["none", "moderate", "high"]:
    if divergence < 15.0:
        return "none"
    if divergence <= 30.0:
        return "moderate"
    return "high"


def traffic_light_from_readiness(final_readiness: float) -> Literal["green", "yellow", "red"]:
    if final_readiness >= 65.0:
        return "green"
    if final_readiness >= 40.0:
        return "yellow"
    return "red"


def _build_insights(
    divergence_flag: str,
    subjective_score: float,
    legs_feeling: str = "normal",
    energy_global: str = "ok",
) -> list[str]:
    insights: list[str] = []
    if divergence_flag == "high" and subjective_score < 40.0:
        insights.append("HRV normale mais jambes à dead. Ton ressenti compte.")
    return insights


def _snapshot_to_readiness(
    snapshot: EnergySnapshotModel,
    legs_feeling: Optional[str] = None,
    energy_global: Optional[str] = None,
) -> ReadinessResponse:
    obj = float(snapshot.objective_score) if snapshot.objective_score is not None else 50.0
    subj = float(snapshot.subjective_score) if snapshot.subjective_score is not None else 50.0

    divergence = abs(obj - subj)
    divergence_flag = classify_divergence(divergence)
    weight_subj = 0.55 if divergence > 25.0 else 0.40
    final = round(obj * (1.0 - weight_subj) + subj * weight_subj, 2)

    return ReadinessResponse(
        date=snapshot.timestamp.date(),
        objective_score=round(obj, 2),
        subjective_score=round(subj, 2),
        final_readiness=final,
        divergence=round(divergence, 2),
        divergence_flag=divergence_flag,
        traffic_light=traffic_light_from_readiness(final),
        allostatic_score=round(snapshot.allostatic_score, 2),
        energy_availability=round(snapshot.energy_availability, 2),
        intensity_cap=round(snapshot.recommended_intensity_cap, 2),
        insights=_build_insights(
            divergence_flag, subj, legs_feeling or "normal", energy_global or "ok"
        ),
    )


class EnergyCycleService:
    _coach = EnergyCoach()

    def submit_checkin(
        self, athlete_id: str, db: Session, checkin: CheckInInput
    ) -> ReadinessResponse:
        athlete = db.get(AthleteModel, athlete_id)
        if not athlete:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Athlete not found")

        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        existing = (
            db.query(EnergySnapshotModel)
            .filter(
                EnergySnapshotModel.athlete_id == athlete_id,
                EnergySnapshotModel.timestamp >= today_start,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Check-in already submitted for today"
            )

        subjective_score = compute_subjective_score(checkin.legs_feeling, checkin.energy_global)

        energy_input = EnergyInput(
            hrv_deviation=0.0,
            sleep_quality=50.0,
            caloric_intake=2000.0,
            exercise_energy=0.0,
            ffm_kg=max(1.0, athlete.weight_kg * 0.80),
            check_in=EnergyCheckIn(
                work_intensity=checkin.work_intensity,
                stress_level=checkin.stress_level,
                cycle_phase=checkin.cycle_phase,
            ),
            sex=athlete.sex,
        )
        energy_snapshot = self._coach.create_snapshot(energy_input)
        objective_score = round(100.0 - energy_snapshot.allostatic_score, 2)

        snap_model = EnergySnapshotModel(
            id=str(uuid.uuid4()),
            athlete_id=athlete_id,
            timestamp=datetime.now(timezone.utc),
            allostatic_score=round(energy_snapshot.allostatic_score, 4),
            cognitive_load=round(energy_snapshot.cognitive_load, 4),
            energy_availability=round(energy_snapshot.energy_availability, 4),
            cycle_phase=checkin.cycle_phase,
            sleep_quality=energy_snapshot.sleep_quality,
            recommended_intensity_cap=energy_snapshot.recommended_intensity_cap,
            veto_triggered=energy_snapshot.veto_triggered,
            veto_reason=energy_snapshot.veto_reason,
            objective_score=objective_score,
            subjective_score=round(subjective_score, 2),
            legs_feeling=checkin.legs_feeling,
            stress_level=checkin.stress_level,
        )
        db.add(snap_model)
        db.commit()
        db.refresh(snap_model)

        return _snapshot_to_readiness(snap_model, checkin.legs_feeling, checkin.energy_global)

    def get_today_snapshot(self, athlete_id: str, db: Session) -> Optional[EnergySnapshotModel]:
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        return (
            db.query(EnergySnapshotModel)
            .filter(
                EnergySnapshotModel.athlete_id == athlete_id,
                EnergySnapshotModel.timestamp >= today_start,
            )
            .first()
        )

    def get_readiness(self, athlete_id: str, db: Session) -> ReadinessResponse:
        snapshot = self.get_today_snapshot(athlete_id, db)
        if snapshot is None:
            snapshot = (
                db.query(EnergySnapshotModel)
                .filter(EnergySnapshotModel.athlete_id == athlete_id)
                .order_by(EnergySnapshotModel.timestamp.desc())
                .first()
            )
        if snapshot is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No check-in data found. Submit a check-in first.",
            )
        return _snapshot_to_readiness(snapshot)

    def get_history(
        self, athlete_id: str, db: Session, days: int = 28
    ) -> list[EnergySnapshotModel]:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        return (
            db.query(EnergySnapshotModel)
            .filter(
                EnergySnapshotModel.athlete_id == athlete_id,
                EnergySnapshotModel.timestamp >= since,
            )
            .order_by(EnergySnapshotModel.timestamp.desc())
            .all()
        )

    def update_hormonal_profile(
        self, athlete_id: str, db: Session, data: HormonalProfileUpdate
    ) -> HormonalProfileModel:
        profile = (
            db.query(HormonalProfileModel)
            .filter(HormonalProfileModel.athlete_id == athlete_id)
            .first()
        )
        if profile is None:
            profile = HormonalProfileModel(id=str(uuid.uuid4()), athlete_id=athlete_id)
            db.add(profile)

        profile.enabled = data.enabled
        profile.cycle_length_days = data.cycle_length_days
        profile.last_period_start = data.last_period_start
        profile.tracking_source = data.tracking_source
        profile.notes = data.notes

        db.commit()
        db.refresh(profile)
        return profile
