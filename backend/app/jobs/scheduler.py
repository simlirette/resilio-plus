"""APScheduler setup with global/dynamic jobs."""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from ..db.database import SessionLocal
from .cleanup_jobs import run_cleanup_job_runs
from .compute_jobs import run_daily_snapshot, run_energy_patterns
from .registry import restore_all_jobs

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def get_scheduler() -> BackgroundScheduler:
    """Return the running scheduler. Raises RuntimeError if not started."""
    if _scheduler is None:
        raise RuntimeError("Scheduler not started")
    return _scheduler


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

    with SessionLocal() as db:
        restore_all_jobs(scheduler, db)

    _scheduler = scheduler
    logger.info("Background scheduler started with %d jobs", len(scheduler.get_jobs()))
    return scheduler
