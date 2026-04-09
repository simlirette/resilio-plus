"""
Scheduler de synchronisation périodique — Resilio+.
Lance sync_all_strava et sync_all_hevy toutes les 6h pour tous les athlètes connectés.
Uses APScheduler AsyncIOScheduler (in-process, compatible FastAPI lifespan).
"""
import logging
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from connectors.hevy import HevyConnector
from connectors.strava import StravaConnector
from models.database import ConnectorCredential
from models.db_session import AsyncSessionFactory

logger = logging.getLogger(__name__)

_strava = StravaConnector()
_hevy = HevyConnector()


async def sync_all_strava() -> None:
    """Sync Strava pour tous les athlètes avec credential Strava valide."""
    async with AsyncSessionFactory() as db:
        try:
            result = await db.execute(
                select(ConnectorCredential).where(ConnectorCredential.provider == "strava")
            )
            creds = result.scalars().all()
            for cred in creds:
                try:
                    cred = await _strava.refresh_token_if_expired(cred, db)
                    since = datetime.now(tz=UTC) - timedelta(days=7)
                    activities = await _strava.fetch_activities(cred, since)
                    count = await _strava.ingest_activities(cred.athlete_id, activities, db)
                    logger.info("Strava sync OK: athlete=%s ingested=%d", cred.athlete_id, count)
                except Exception:
                    logger.warning(
                        "Strava sync failed: athlete=%s", cred.athlete_id, exc_info=True
                    )
            await db.commit()
        except Exception:
            logger.error("sync_all_strava: DB error", exc_info=True)
            await db.rollback()


async def sync_all_hevy() -> None:
    """Sync Hevy pour tous les athlètes avec credential Hevy et api_key valide."""
    async with AsyncSessionFactory() as db:
        try:
            result = await db.execute(
                select(ConnectorCredential).where(
                    ConnectorCredential.provider == "hevy",
                    ConnectorCredential.api_key.is_not(None),
                )
            )
            creds = result.scalars().all()
            for cred in creds:
                try:
                    since = datetime.now(tz=UTC) - timedelta(days=7)
                    workouts = await _hevy.fetch_all_since(cred.api_key, since)
                    count = await _hevy.ingest_workouts(cred.athlete_id, workouts, db)
                    logger.info("Hevy sync OK: athlete=%s ingested=%d", cred.athlete_id, count)
                except Exception:
                    logger.warning(
                        "Hevy sync failed: athlete=%s", cred.athlete_id, exc_info=True
                    )
            await db.commit()
        except Exception:
            logger.error("sync_all_hevy: DB error", exc_info=True)
            await db.rollback()


def setup_scheduler() -> AsyncIOScheduler:
    """Configure et retourne l'AsyncIOScheduler (non démarré)."""
    scheduler = AsyncIOScheduler()
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
    return scheduler
