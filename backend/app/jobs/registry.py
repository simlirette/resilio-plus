"""Per-athlete job lifecycle: register on connect, unregister on disconnect."""
from __future__ import annotations

import logging

from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from ..db.models import AthleteModel, ConnectorCredentialModel

logger = logging.getLogger(__name__)

WEEKLY_CYCLE_MISFIRE_GRACE_S = 7200
DEFAULT_WEEKLY_CYCLE_DAY = 6  # Sunday, APScheduler counts Monday as 0
DEFAULT_WEEKLY_CYCLE_HOUR = 18
DAILY_REMINDER_HOUR = 6
DAILY_REMINDER_MINUTE = 30
DEFAULT_TIMEZONE = "America/Montreal"

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


def weekly_cycle_job_id(athlete_id: str) -> str:
    return f"weekly_cycle_{athlete_id}"


def daily_reminder_job_id(athlete_id: str) -> str:
    return f"daily_reminder_{athlete_id}"


def register_weekly_cycle(
    athlete_id: str,
    scheduler: BackgroundScheduler,
    db: Session,
) -> None:
    """Schedule the athlete's weekly coaching cycle in their own timezone.

    ``misfire_grace_time`` is generous on purpose: a redeploy over the trigger
    window must delay the week, never skip it.
    """
    athlete = db.get(AthleteModel, athlete_id)
    if athlete is None:
        logger.warning("weekly_cycle_athlete_missing", extra={"athlete_id": athlete_id})
        return

    day = getattr(athlete, "weekly_cycle_day", DEFAULT_WEEKLY_CYCLE_DAY)
    hour = getattr(athlete, "weekly_cycle_hour", DEFAULT_WEEKLY_CYCLE_HOUR)
    tz = getattr(athlete, "timezone", None) or DEFAULT_TIMEZONE

    scheduler.add_job(
        "app.jobs.weekly_jobs:run_weekly_coach_cycle",
        trigger="cron",
        day_of_week=int(day),
        hour=int(hour),
        minute=0,
        timezone=tz,
        id=weekly_cycle_job_id(athlete_id),
        replace_existing=True,
        misfire_grace_time=WEEKLY_CYCLE_MISFIRE_GRACE_S,
        kwargs={"athlete_id": athlete_id},
    )
    logger.info(
        "Registered weekly cycle for %s (day=%s hour=%s tz=%s)",
        athlete_id,
        day,
        hour,
        tz,
    )

    scheduler.add_job(
        "app.jobs.weekly_jobs:run_daily_reminder",
        trigger="cron",
        hour=DAILY_REMINDER_HOUR,
        minute=DAILY_REMINDER_MINUTE,
        timezone=tz,
        id=daily_reminder_job_id(athlete_id),
        replace_existing=True,
        misfire_grace_time=3600,
        kwargs={"athlete_id": athlete_id},
    )


def unregister_weekly_cycle(
    athlete_id: str,
    scheduler: BackgroundScheduler,
) -> None:
    """Remove the weekly cycle and reminder jobs for one athlete."""
    for jid in (weekly_cycle_job_id(athlete_id), daily_reminder_job_id(athlete_id)):
        try:
            scheduler.remove_job(jid)
        except JobLookupError:
            logger.debug("Job %s not found (already removed)", jid)


def restore_all_jobs(scheduler: BackgroundScheduler, db: Session) -> None:
    """Re-register provider sync jobs for all connected athletes. Called at startup."""
    creds = db.query(ConnectorCredentialModel).all()
    for cred in creds:
        register_athlete_jobs(cred.athlete_id, cred.provider, scheduler)


def restore_weekly_cycles(scheduler: BackgroundScheduler, db: Session) -> None:
    """Re-register every athlete's weekly cycle. Called at startup.

    Separate from :func:`restore_all_jobs` because the weekly cycle belongs to
    the athlete, not to a connected provider — an athlete with no connectors
    still gets planned for.
    """
    for (athlete_id,) in db.query(AthleteModel.id).all():
        register_weekly_cycle(athlete_id, scheduler, db)
