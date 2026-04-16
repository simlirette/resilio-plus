"""Cleanup job: delete old job_runs entries."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..db.database import SessionLocal
from .models import JobRunModel
from .runner import run_job

logger = logging.getLogger(__name__)

RETENTION_DAYS = 30


def _cleanup_old_runs(db: Session) -> int:
    """Delete job_runs older than RETENTION_DAYS. Returns count deleted."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    deleted = (
        db.query(JobRunModel)
        .filter(JobRunModel.created_at < cutoff)
        .delete(synchronize_session=False)
    )
    db.commit()
    logger.info("Cleaned up %d old job runs (older than %d days)", deleted, RETENTION_DAYS)
    return deleted


def run_cleanup_job_runs() -> None:
    """Weekly job: delete old job_runs entries."""
    with SessionLocal() as db:
        run_job(
            job_id="cleanup_job_runs",
            job_type="cleanup",
            athlete_id=None,
            fn=lambda: _cleanup_old_runs(db),
            db=db,
            timeout_s=60,
        )
