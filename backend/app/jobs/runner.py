"""Job execution wrapper — logs every run to job_runs table + observability."""
from __future__ import annotations

import contextvars
import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy.orm import Session

from ..observability.correlation import correlation_id_ctx
from ..observability.metrics import metrics
from .models import JobRunModel

logger = logging.getLogger("resilio.jobs")

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
    """Execute fn() with timeout, log result to job_runs AND observability."""
    started_at = datetime.now(timezone.utc)
    cid = f"job-{uuid.uuid4()}"
    token = correlation_id_ctx.set(cid)

    try:
        logger.info(
            "job_start",
            extra={"job_id": job_id, "job_type": job_type, "athlete_id": athlete_id},
        )

        status = "ok"
        error_message: str | None = None
        exception_holder: list = []

        def _target():
            try:
                fn()
            except Exception as exc:
                exception_holder.append(exc)

        # Worker thread must inherit ContextVars (correlation_id) — use copy_context
        ctx = contextvars.copy_context()
        thread = threading.Thread(target=lambda: ctx.run(_target), daemon=True)
        thread.start()
        thread.join(timeout=timeout_s)

        if thread.is_alive():
            status = "timeout"
            error_message = f"Job timed out after {timeout_s}s"
            logger.warning(
                "job_timeout",
                extra={"job_id": job_id, "job_type": job_type, "timeout_s": timeout_s},
            )
        elif exception_holder:
            status = "error"
            error_message = str(exception_holder[0])[:_MAX_ERROR_LEN]
            logger.warning(
                "job_failed",
                extra={
                    "job_id": job_id,
                    "job_type": job_type,
                    "error_message": error_message,
                },
            )

        elapsed_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)

        metrics.inc_job(job_type, status)

        logger.info(
            "job_end",
            extra={
                "job_id": job_id,
                "job_type": job_type,
                "status": status,
                "duration_ms": elapsed_ms,
            },
        )

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
            logger.exception("persist_job_run_failed", extra={"job_id": job_id})
            try:
                db.rollback()
            except Exception:
                pass
    finally:
        correlation_id_ctx.reset(token)
