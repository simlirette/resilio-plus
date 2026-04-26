"""EnergyCoachView builder — Phase D (D6), DEP-C9-008 (view builder).

Completes the DEP-C9-008 delivery: schema was in D2, this is the view builder.
Builds EnergyCoachView from AthleteModel + DB energy snapshots + check-ins.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from ..db.models import AthleteModel, EnergySnapshotModel
from ..schemas.energy import CheckInSummaryEntry, EnergyCoachView

_CHECKIN_LOOKBACK_DAYS = 14


def build_energy_view(athlete: AthleteModel, db: Any) -> EnergyCoachView:
    """Build an EnergyCoachView from the athlete record and recent energy data.

    Graceful degradation: all fields are optional/nullable; returns empty view
    if no energy data exists.

    Args:
        athlete: ORM model.
        db: SQLAlchemy session.

    Returns:
        EnergyCoachView with current energy metrics and recent check-in history.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=_CHECKIN_LOOKBACK_DAYS)

    # Load recent energy snapshots (used as check-in proxies)
    snapshots: list[EnergySnapshotModel] = (
        db.query(EnergySnapshotModel)
        .filter(EnergySnapshotModel.athlete_id == athlete.id)
        .order_by(EnergySnapshotModel.timestamp.desc())
        .limit(14)
        .all()
    )

    # Latest snapshot → current energy metrics
    latest = snapshots[0] if snapshots else None
    current_ea: float | None = latest.energy_availability if latest else None
    allostatic: float | None = latest.allostatic_score if latest else None
    intensity_cap: float | None = latest.recommended_intensity_cap if latest else None

    # Build check-in summaries from snapshots
    recent_checkins: list[CheckInSummaryEntry] = []
    for snap in snapshots:
        if snap.timestamp < cutoff:
            continue
        entry = CheckInSummaryEntry(
            check_in_date=snap.timestamp.date(),
            energy_global=snap.legs_feeling or "unknown",
            work_intensity="unknown",
            stress_level=snap.stress_level or "unknown",
            legs_feeling=snap.legs_feeling or "unknown",
            final_readiness=snap.objective_score,
            energy_availability=snap.energy_availability,
        )
        recent_checkins.append(entry)

    return EnergyCoachView(
        athlete_id=athlete.id,
        discipline_loads=[],  # D6 stub — full computation deferred to later sessions
        total_weekly_hours=athlete.hours_per_week,
        current_energy_availability=current_ea,
        allostatic_score=allostatic,
        intensity_cap=intensity_cap,
        recent_checkins=recent_checkins,
        nutrition_snapshot=None,
        energy_pattern_flags=[],
    )
