"""Per-athlete job lifecycle: register on connect, unregister on disconnect."""
from __future__ import annotations

import logging

from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from ..db.models import ConnectorCredentialModel

logger = logging.getLogger(__name__)

# Provider → (job module function path, interval hours)
_PROVIDER_CONFIG: dict[str, tuple[str, int]] = {
    "strava": ("app.jobs.sync_jobs:sync_strava_for_athlete", 1),
    "hevy": ("app.jobs.sync_jobs:sync_hevy_for_athlete", 6),
    "terra": ("app.jobs.sync_jobs:sync_terra_for_athlete", 6),
}


def _job_id(provider: str, athlete_id: str) -> str:
    return f"{provider}_sync_{athlete_id}"


def register_athlete_jobs(
    athlete_id: str,
    provider: str,
    scheduler: BackgroundScheduler,
) -> None:
    """Add a sync job for the given athlete+provider."""
    config = _PROVIDER_CONFIG.get(provider)
    if config is None:
        return
    func_ref, interval_hours = config
    jid = _job_id(provider, athlete_id)
    scheduler.add_job(
        func_ref,
        trigger="interval",
        hours=interval_hours,
        id=jid,
        replace_existing=True,
        misfire_grace_time=300,
        kwargs={"athlete_id": athlete_id},
    )
    logger.info("Registered job %s (every %dh)", jid, interval_hours)


def unregister_athlete_jobs(
    athlete_id: str,
    provider: str,
    scheduler: BackgroundScheduler,
) -> None:
    """Remove a sync job for the given athlete+provider."""
    jid = _job_id(provider, athlete_id)
    try:
        scheduler.remove_job(jid)
        logger.info("Unregistered job %s", jid)
    except JobLookupError:
        logger.debug("Job %s not found (already removed)", jid)


def restore_all_jobs(scheduler: BackgroundScheduler, db: Session) -> None:
    """Re-register jobs for all connected athletes. Called at startup."""
    creds = db.query(ConnectorCredentialModel).all()
    for cred in creds:
        register_athlete_jobs(cred.athlete_id, cred.provider, scheduler)
