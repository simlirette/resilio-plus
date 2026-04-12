"""
Sync scheduler — APScheduler BackgroundScheduler.
Runs sync_all_strava, sync_all_hevy, sync_all_terra every 6 hours for all connected athletes.
Each function creates its own DB session (thread-safe, independent of request sessions).
Delegates all sync logic to SyncService.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from ..db.database import SessionLocal
from ..db.models import ConnectorCredentialModel
from ..services.sync_service import ConnectorNotFoundError, SyncService

logger = logging.getLogger(__name__)


def sync_all_strava() -> None:
    """Auto-sync Strava for all athletes with active Strava credentials."""
    with SessionLocal() as db:
        creds = db.query(ConnectorCredentialModel).filter_by(provider="strava").all()
        for cred_model in creds:
            try:
                result = SyncService.sync_strava(cred_model.athlete_id, db)
                logger.info(
                    "Strava sync OK: athlete=%s synced=%d skipped=%d",
                    cred_model.athlete_id, result["synced"], result.get("skipped", 0),
                )
            except ConnectorNotFoundError:
                pass
            except Exception:
                logger.warning(
                    "Strava sync failed: athlete=%s", cred_model.athlete_id, exc_info=True
                )


def sync_all_hevy() -> None:
    """Auto-sync Hevy for all athletes with active Hevy API key."""
    with SessionLocal() as db:
        creds = db.query(ConnectorCredentialModel).filter_by(provider="hevy").all()
        for cred_model in creds:
            try:
                result = SyncService.sync_hevy(cred_model.athlete_id, db)
                logger.info(
                    "Hevy sync OK: athlete=%s synced=%d skipped=%d",
                    cred_model.athlete_id, result["synced"], result.get("skipped", 0),
                )
            except ConnectorNotFoundError:
                pass
            except Exception:
                logger.warning(
                    "Hevy sync failed: athlete=%s", cred_model.athlete_id, exc_info=True
                )


def sync_all_terra() -> None:
    """Auto-sync Terra HRV/sleep for all athletes with active Terra credentials."""
    with SessionLocal() as db:
        creds = db.query(ConnectorCredentialModel).filter_by(provider="terra").all()
        for cred_model in creds:
            try:
                result = SyncService.sync_terra(cred_model.athlete_id, db)
                logger.info(
                    "Terra sync OK: athlete=%s hrv=%s sleep=%s",
                    cred_model.athlete_id, result["hrv_rmssd"], result["sleep_hours"],
                )
            except ConnectorNotFoundError:
                pass
            except Exception:
                logger.warning(
                    "Terra sync failed: athlete=%s", cred_model.athlete_id, exc_info=True
                )


def setup_scheduler() -> BackgroundScheduler:
    """Create, configure, and start the BackgroundScheduler."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        sync_all_strava, trigger="interval", hours=6,
        id="strava_sync", replace_existing=True, misfire_grace_time=300,
    )
    scheduler.add_job(
        sync_all_hevy, trigger="interval", hours=6,
        id="hevy_sync", replace_existing=True, misfire_grace_time=300,
    )
    scheduler.add_job(
        sync_all_terra, trigger="interval", hours=6,
        id="terra_sync", replace_existing=True, misfire_grace_time=300,
    )
    scheduler.start()
    return scheduler
