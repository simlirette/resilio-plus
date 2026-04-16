"""Job execution wrapper — logs every run to job_runs table."""
from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy.orm import Session

from .models import JobRunModel

logger = logging.getLogger(__name__)

_MAX_ERROR_LEN = 2000


def run_job(
    *,
    job_id: str,
    job_type: str,
    athlete_id: str | None,
    fn: Callable[[], Any],
    db: Session,
    timeout_s: int | float = 60,
) -> None:
    """Execute fn() with timeout, log result to job_runs."""
    started_at = datetime.now(timezone.utc)
    status = "ok"
    error_message = None
    exception_holder: list = []

    def _target():
        try:
            fn()
        except Exception as exc:
            exception_holder.append(exc)

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    thread.join(timeout=timeout_s)

    if thread.is_alive():
        status = "timeout"
        error_message = f"Job timed out after {timeout_s}s"
        logger.warning("Job %s timed out after %ss", job_id, timeout_s)
    elif exception_holder:
        status = "error"
        error_message = str(exception_holder[0])[:_MAX_ERROR_LEN]
        logger.warning("Job %s failed: %s", job_id, error_message)

    elapsed_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)

    run = JobRunModel(
        id=str(uuid.uuid4()),
        job_id=job_id,
        athlete_id=athlete_id,
        job_type=job_type,
        status=status,
        started_at=started_at,
        duration_ms=elapsed_ms,
        error_message=error_message,
    )
    try:
        db.add(run)
        db.commit()
    except Exception:
        logger.exception("Failed to persist job_run for %s", job_id)
        try:
            db.rollback()
        except Exception:
            pass
