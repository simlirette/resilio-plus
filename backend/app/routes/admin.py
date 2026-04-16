"""Admin endpoints — job monitoring."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..dependencies import get_current_athlete_id, get_db
from ..jobs.models import JobRunModel

router = APIRouter(prefix="/admin", tags=["admin"])

DB = Annotated[Session, Depends(get_db)]


def _require_admin(
    athlete_id: Annotated[str, Depends(get_current_athlete_id)],
) -> str:
    admin_id = os.getenv("ADMIN_ATHLETE_ID", "")
    if athlete_id != admin_id:
        raise HTTPException(status_code=403, detail="Admin access required")
    return athlete_id


@router.get("/jobs")
def list_jobs(
    _: Annotated[str, Depends(_require_admin)],
    db: DB,
) -> dict:
    """List all scheduled jobs with last run info and summary."""
    from ..jobs.scheduler import get_scheduler

    try:
        scheduler = get_scheduler()
        scheduled = scheduler.get_jobs()
    except RuntimeError:
        scheduled = []

    now = datetime.now(timezone.utc)
    cutoff_24h = now - timedelta(hours=24)

    jobs = []
    for job in scheduled:
        last_run_row = (
            db.query(JobRunModel)
            .filter(JobRunModel.job_id == job.id)
            .order_by(JobRunModel.started_at.desc())
            .first()
        )
        last_run = None
        if last_run_row:
            last_run = {
                "status": last_run_row.status,
                "started_at": last_run_row.started_at.isoformat(),
                "duration_ms": last_run_row.duration_ms,
            }

        parts = job.id.rsplit("_", 1)
        athlete_id = parts[-1] if len(parts) > 1 and "_sync_" in job.id else None
        job_type = job.id.rsplit("_" + parts[-1], 1)[0] if athlete_id else job.id

        jobs.append(
            {
                "job_id": job.id,
                "job_type": job_type,
                "athlete_id": athlete_id,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "last_run": last_run,
            }
        )

    errors_24h = (
        db.query(func.count(JobRunModel.id))
        .filter(JobRunModel.status != "ok", JobRunModel.created_at >= cutoff_24h)
        .scalar()
    )
    next_runs = [j.next_run_time for j in scheduled if j.next_run_time]
    earliest_next = min(next_runs).isoformat() if next_runs else None

    return {
        "jobs": jobs,
        "summary": {
            "total_jobs": len(scheduled),
            "errors_24h": errors_24h,
            "next_run": earliest_next,
        },
    }


from ..observability.metrics import metrics as _metrics_singleton


@router.get("/metrics")
def get_metrics(
    _: Annotated[str, Depends(_require_admin)],
) -> dict:
    """In-memory observability metrics snapshot (HTTP, agents, jobs)."""
    return _metrics_singleton.snapshot()
