"""APScheduler setup with global/dynamic jobs."""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from ..db.database import SessionLocal
from .cleanup_jobs import run_cleanup_job_runs
from .compute_jobs import run_daily_snapshot, run_energy_patterns
from .registry import restore_all_jobs, restore_weekly_cycles

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None

#: Postgres coming up a few seconds after the API is ordinary. Losing every
#: per-athlete job because of it is not.
_RETRY_JOB_ID = "restore_athlete_jobs_retry"
_RETRY_INTERVAL_S = 30


def get_scheduler() -> BackgroundScheduler:
    """Return the running scheduler. Raises RuntimeError if not started."""
    if _scheduler is None:
        raise RuntimeError("Scheduler not started")
    return _scheduler


def restore_athlete_jobs(scheduler: BackgroundScheduler) -> bool:
    """Re-register every athlete's sync and weekly-cycle jobs. Retries if the DB is down.

    Returns whether the restore succeeded.

    This used to be a `try/except: logger.warning` and nothing else. On a live
    restart on 2026-08-21 the database was a moment behind the API, the warning
    scrolled past, the process reported healthy — and every per-athlete job was
    gone until the next manual restart. The weekly cycle is *the* unprompted
    half of the coach: it failing behind a healthy process is the worst shape a
    failure can take here.
    """
    try:
        with SessionLocal() as db:
            restore_all_jobs(scheduler, db)
            restore_weekly_cycles(scheduler, db)
    except Exception as exc:
        logger.warning(
            "athlete_jobs_restore_failed_retrying",
            extra={"error": str(exc), "retry_in_s": _RETRY_INTERVAL_S},
        )
        scheduler.add_job(
            restore_athlete_jobs,
            trigger="interval",
            seconds=_RETRY_INTERVAL_S,
            args=[scheduler],
            id=_RETRY_JOB_ID,
            replace_existing=True,
            max_instances=1,
        )
        return False

    # Reached on the first successful startup too, where there is no retry job.
    try:
        scheduler.remove_job(_RETRY_JOB_ID)
        logger.info("athlete_jobs_restored_after_retry")
    except Exception:
        pass
    return True


def setup_scheduler() -> BackgroundScheduler:
    """Create, configure, and start the BackgroundScheduler."""
    global _scheduler

    scheduler = BackgroundScheduler()

    scheduler.add_job(
        run_daily_snapshot,
        trigger="cron",
        hour=4,
        id="daily_snapshot",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        run_energy_patterns,
        trigger="cron",
        day_of_week="mon",
        hour=6,
        minute=0,
        id="energy_patterns",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        run_cleanup_job_runs,
        trigger="cron",
        day_of_week="sun",
        hour=3,
        minute=0,
        id="cleanup_job_runs",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    scheduler.start()
    restore_athlete_jobs(scheduler)

    _scheduler = scheduler
    logger.info("Background scheduler started with %d jobs", len(scheduler.get_jobs()))
    return scheduler
