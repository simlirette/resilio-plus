"""
Sync scheduler — APScheduler BackgroundScheduler.
Runs sync_all_strava and sync_all_hevy every 6 hours for all connected athletes.
Each function creates its own DB session (thread-safe, independent of request sessions).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from ..db.database import SessionLocal
from ..db.models import ConnectorCredentialModel

logger = logging.getLogger(__name__)


def sync_all_strava() -> None:
    """Sync Strava for all athletes with active Strava credentials."""
    from ..connectors.strava import StravaConnector
    from ..schemas.connector import ConnectorCredential
    import os

    client_id = os.getenv("STRAVA_CLIENT_ID", "")
    client_secret = os.getenv("STRAVA_CLIENT_SECRET", "")

    with SessionLocal() as db:
        creds = (
            db.query(ConnectorCredentialModel)
            .filter_by(provider="strava")
            .all()
        )
        for cred_model in creds:
            try:
                cred = ConnectorCredential(
                    athlete_id=cred_model.athlete_id,  # type: ignore[arg-type]
                    provider="strava",
                    access_token=cred_model.access_token,
                    refresh_token=cred_model.refresh_token,
                    expires_at=cred_model.expires_at,
                )
                since = datetime.now(timezone.utc) - timedelta(days=7)
                until = datetime.now(timezone.utc)
                with StravaConnector(cred, client_id=client_id, client_secret=client_secret) as connector:
                    activities = connector.fetch_activities(since, until)
                logger.info(
                    "Strava sync OK: athlete=%s activities=%d",
                    cred_model.athlete_id,
                    len(activities),
                )
            except Exception:
                logger.warning(
                    "Strava sync failed: athlete=%s",
                    cred_model.athlete_id,
                    exc_info=True,
                )


def sync_all_hevy() -> None:
    """Sync Hevy for all athletes with active Hevy API key."""
    from ..connectors.hevy import HevyConnector
    from ..schemas.connector import ConnectorCredential

    with SessionLocal() as db:
        creds = (
            db.query(ConnectorCredentialModel)
            .filter_by(provider="hevy")
            .all()
        )
        for cred_model in creds:
            try:
                extra = json.loads(cred_model.extra_json or "{}")
                api_key = extra.get("api_key", "")
                if not api_key:
                    continue

                cred = ConnectorCredential(
                    athlete_id=cred_model.athlete_id,  # type: ignore[arg-type]
                    provider="hevy",
                    extra={"api_key": api_key},
                )
                since = datetime.now(timezone.utc) - timedelta(days=7)
                until = datetime.now(timezone.utc)
                with HevyConnector(cred, client_id=api_key, client_secret="") as connector:
                    workouts = connector.fetch_workouts(since, until)
                logger.info(
                    "Hevy sync OK: athlete=%s workouts=%d",
                    cred_model.athlete_id,
                    len(workouts),
                )
            except Exception:
                logger.warning(
                    "Hevy sync failed: athlete=%s",
                    cred_model.athlete_id,
                    exc_info=True,
                )


def setup_scheduler() -> BackgroundScheduler:
    """Create, configure, and start the BackgroundScheduler."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        sync_all_strava,
        trigger="interval",
        hours=6,
        id="strava_sync",
        replace_existing=True,
        misfire_grace_time=300,
    )
    scheduler.add_job(
        sync_all_hevy,
        trigger="interval",
        hours=6,
        id="hevy_sync",
        replace_existing=True,
        misfire_grace_time=300,
    )
    scheduler.start()
    return scheduler
