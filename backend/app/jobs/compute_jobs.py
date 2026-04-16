"""Global compute jobs: daily snapshot + energy patterns."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import date, datetime, timezone

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


def _snapshot_all_athletes(db: Session) -> None:
    """Compute readiness + strain for all athletes and upsert snapshots."""
    athletes = db.query(AthleteModel).all()
    today = date.today()

    for athlete in athletes:
        try:
            data = fetch_connector_data(athlete.id, db)
            readiness = compute_readiness(
                [data["terra_health"]] if data["terra_health"] else [],
            )
            strain = compute_muscle_strain(
                data["strava_activities"],
                data["hevy_workouts"],
            )

            existing = (
                db.query(AthleteStateSnapshotModel)
                .filter_by(athlete_id=athlete.id, snapshot_date=today)
                .first()
            )
            if existing:
                existing.readiness = readiness
                existing.strain_json = json.dumps(strain.model_dump())
            else:
                db.add(AthleteStateSnapshotModel(
                    id=str(uuid.uuid4()),
                    athlete_id=athlete.id,
                    snapshot_date=today,
                    readiness=readiness,
                    strain_json=json.dumps(strain.model_dump()),
                ))
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
