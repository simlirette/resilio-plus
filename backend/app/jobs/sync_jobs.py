"""Per-athlete sync job wrappers. Each creates its own DB session."""
from __future__ import annotations

import logging

from ..db.database import SessionLocal
from ..integrations.strava.sync_service import sync as strava_sync
from ..services.sync_service import SyncService
from .runner import run_job

logger = logging.getLogger(__name__)


def sync_strava_for_athlete(athlete_id: str) -> None:
    with SessionLocal() as db:
        run_job(
            job_id=f"strava_sync_{athlete_id}",
            job_type="strava_sync",
            athlete_id=athlete_id,
            fn=lambda: strava_sync(athlete_id, db),
            db=db,
            timeout_s=60,
        )


def sync_hevy_for_athlete(athlete_id: str) -> None:
    with SessionLocal() as db:
        run_job(
            job_id=f"hevy_sync_{athlete_id}",
            job_type="hevy_sync",
            athlete_id=athlete_id,
            fn=lambda: SyncService.sync_hevy(athlete_id, db),
            db=db,
            timeout_s=60,
        )


def sync_terra_for_athlete(athlete_id: str) -> None:
    with SessionLocal() as db:
        run_job(
            job_id=f"terra_sync_{athlete_id}",
            job_type="terra_sync",
            athlete_id=athlete_id,
            fn=lambda: SyncService.sync_terra(athlete_id, db),
            db=db,
            timeout_s=60,
        )
