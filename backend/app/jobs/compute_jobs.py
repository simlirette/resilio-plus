"""Global compute jobs: daily snapshot + energy patterns."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session

from ..core.energy_patterns import detect_energy_patterns
from ..core.readiness import compute_readiness
from ..core.strain import compute_muscle_strain
from ..db.database import SessionLocal
from ..db.models import AthleteModel
from ..services.connector_service import fetch_connector_data
from .models import AthleteStateSnapshotModel
from .runner import run_job

logger = logging.getLogger(__name__)


#: A baseline built from last winter says nothing about this week.
_RECOVERY_WINDOW_DAYS = 30


def _recovery_records(
    athlete_id: str,
    db: Session,
    terra: Any,
) -> list[Any]:
    """Recovery signal for readiness: Terra if present, else Apple Health.

    The goal document names Apple Health as a data source. Its parser, its
    aggregator and its table all shipped in V3-X -- and nothing ever read the
    table, so an athlete could import a full export and readiness stayed None.

    The two are never mixed. Terra reports RMSSD, Apple Health reports SDNN:
    different measurements on different scales. Readiness is a delta against a
    baseline, so a window that switches between them produces a swing that
    looks like fatigue and is arithmetic.
    """
    if terra is not None:
        return [terra]

    try:
        from ..db.models import AppleHealthDailyModel
        from ..schemas.connector import TerraHealthData

        cutoff = date.today() - timedelta(days=_RECOVERY_WINDOW_DAYS)
        rows = (
            db.query(AppleHealthDailyModel)
            .filter(
                AppleHealthDailyModel.athlete_id == athlete_id,
                AppleHealthDailyModel.record_date >= cutoff,
            )
            .all()
        )
    except Exception:
        logger.warning("apple_health_unreadable", extra={"athlete_id": athlete_id})
        return []

    records: list[Any] = []
    for row in rows:
        if row.hrv_sdnn_avg is None and row.sleep_hours is None:
            continue
        records.append(
            TerraHealthData(
                date=row.record_date,
                # SDNN carried in the RMSSD field on purpose: readiness only
                # ever compares this series to itself, and mixing is prevented
                # above. `AthleteMetrics.hrv_sdnn` stays the field of record.
                hrv_rmssd=row.hrv_sdnn_avg,
                sleep_duration_hours=row.sleep_hours,
                active_energy_kcal=row.active_energy_kcal,
            )
        )
    return records


def snapshot_athlete(athlete_id: str, db: Session) -> None:
    """Compute readiness + strain for one athlete and upsert today's snapshot.

    Does not commit — the caller owns the transaction boundary.
    """
    today = date.today()
    data = fetch_connector_data(athlete_id, db)
    records = _recovery_records(athlete_id, db, data["terra_health"])
    readiness = compute_readiness(records)
    # Distinguishes a neutral modifier from an absent signal -- see
    # AthleteStateSnapshotModel.readiness_source.
    readiness_source = "measured" if records else None
    strain = compute_muscle_strain(
        data["strava_activities"],
        data["hevy_workouts"],
    )

    existing = (
        db.query(AthleteStateSnapshotModel)
        .filter_by(athlete_id=athlete_id, snapshot_date=today)
        .first()
    )
    if existing:
        existing.readiness = readiness
        existing.readiness_source = readiness_source
        existing.strain_json = json.dumps(strain.model_dump(mode="json"))
    else:
        db.add(
            AthleteStateSnapshotModel(
                id=str(uuid.uuid4()),
                athlete_id=athlete_id,
                snapshot_date=today,
                readiness=readiness,
                readiness_source=readiness_source,
                strain_json=json.dumps(strain.model_dump(mode="json")),
            )
        )


def _snapshot_all_athletes(db: Session) -> None:
    """Compute readiness + strain for all athletes and upsert snapshots."""
    athletes = db.query(AthleteModel).all()

    for athlete in athletes:
        try:
            snapshot_athlete(athlete.id, db)
        except Exception:
            logger.warning("Snapshot failed for athlete %s", athlete.id, exc_info=True)

    db.commit()


def run_daily_snapshot() -> None:
    """Daily job: compute readiness + strain snapshots for all athletes."""
    with SessionLocal() as db:
        run_job(
            job_id="daily_snapshot",
            job_type="daily_snapshot",
            athlete_id=None,
            fn=lambda: _snapshot_all_athletes(db),
            db=db,
            timeout_s=300,
        )


def _energy_patterns_inner(db: Session) -> None:
    detect_energy_patterns(db)


def run_energy_patterns() -> None:
    """Weekly job: detect energy patterns for all athletes."""
    with SessionLocal() as db:
        run_job(
            job_id="energy_patterns",
            job_type="energy_patterns",
            athlete_id=None,
            fn=lambda: _energy_patterns_inner(db),
            db=db,
            timeout_s=300,
        )
