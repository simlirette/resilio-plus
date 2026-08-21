"""The weekly coaching cycle — the thing that makes Resilio a coach, not an app.

Once a week, at the athlete's local time and without them asking: pull the last
seven days from every connected provider, recompute state, generate next week,
and text it over with approve / change / skip buttons. The job ends there —
approval is asynchronous and lands through :mod:`app.messaging.approval_service`.

Every step is individually failure-tolerant. A provider being down degrades the
week and is named in the message; it never cancels it.
"""
from __future__ import annotations

import logging
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from ..db.database import SessionLocal
from ..db.models import AthleteModel
from ..messaging.approval_service import ApprovalService
from ..messaging.calendar_hook import get_calendar_pusher
from ..messaging.notification_service import NotificationService
from ..messaging.outbound import configured_channels
from ..messaging.plan_renderer import render_session_line
from ..services.graph_invoker import DefaultGraphInvoker
from ..services.monitoring_service import MonitoringService
from .compute_jobs import snapshot_athlete
from .runner import run_job
from .sync_jobs import sync_hevy_for_athlete, sync_strava_for_athlete, sync_terra_for_athlete
from .weekly_review import write_statement

logger = logging.getLogger(__name__)

WEEKLY_CYCLE_TIMEOUT_S = 600
DAILY_REMINDER_TIMEOUT_S = 120

_PROVIDER_SYNCS: dict[str, Callable[[str], None]] = {
    "strava": sync_strava_for_athlete,
    "hevy": sync_hevy_for_athlete,
    "terra": sync_terra_for_athlete,
}


class WeeklyCycleError(RuntimeError):
    """Raised when the cycle cannot produce a week at all."""


@dataclass
class WeeklyCycleResult:
    athlete_id: str
    degraded_sources: list[str] = field(default_factory=list)
    plan_sent: bool = False
    approval_token: str | None = None
    thread_id: str | None = None
    reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "athlete_id": self.athlete_id,
            "degraded_sources": list(self.degraded_sources),
            "plan_sent": self.plan_sent,
            "approval_token": self.approval_token,
            "thread_id": self.thread_id,
            "reason": self.reason,
        }


def daily_reminder_enabled() -> bool:
    return os.getenv("DAILY_REMINDER_ENABLED", "false").lower() in ("1", "true", "yes")


# ─── The cycle ────────────────────────────────────────────────────────────────


def run_weekly_cycle_now(
    athlete_id: str,
    db: Session,
    *,
    invoker: DefaultGraphInvoker | None = None,
    approvals: ApprovalService | None = None,
) -> WeeklyCycleResult:
    """Run one full cycle synchronously on an existing session.

    Used by the scheduled job and by the athlete typing ``/plan``.
    """
    result = WeeklyCycleResult(athlete_id=athlete_id)

    athlete = db.get(AthleteModel, athlete_id)
    if athlete is None:
        raise WeeklyCycleError(f"Athlete {athlete_id!r} not found")
    _settle(db)

    result.degraded_sources = _sync_providers(athlete_id)
    _compute_state(athlete_id, db)

    # Look back before looking forward. Sending a fresh week without a word
    # about the one that just ended is a scheduler, not a coach -- and it is
    # what the athlete received every Sunday until now.
    statement = write_statement(athlete_id, db)
    _settle(db)

    output = _generate_week(athlete_id, db, invoker)
    plan = output.get("plan_proposal") if isinstance(output, Mapping) else None
    thread_id = output.get("plan_thread_id") if isinstance(output, Mapping) else None

    if plan is None or not isinstance(thread_id, str) or not thread_id:
        result.reason = "no_plan_generated"
        logger.warning("weekly_cycle_no_plan", extra={"athlete_id": athlete_id})
        return result

    _note_proactive_allowance(athlete_id, db)
    _settle(db)

    service = approvals or _build_approvals(db)
    token = service.send_plan_for_approval(
        athlete_id=athlete_id,
        thread_id=thread_id,
        plan=plan,
        degraded_sources=result.degraded_sources or None,
        payload={"trigger": "weekly_cycle"},
        preamble=statement,
    )

    result.plan_sent = True
    result.approval_token = token
    result.thread_id = thread_id
    return result


def run_weekly_coach_cycle(athlete_id: str) -> None:
    """APScheduler entry point — one athlete's weekly cycle, logged and bounded."""
    with SessionLocal() as db:
        run_job(
            job_id=f"weekly_cycle_{athlete_id}",
            job_type="weekly_cycle",
            athlete_id=athlete_id,
            fn=lambda: run_weekly_cycle_now(athlete_id, db),
            db=db,
            timeout_s=WEEKLY_CYCLE_TIMEOUT_S,
        )


# ─── Daily reminder ───────────────────────────────────────────────────────────


def send_daily_reminder(athlete_id: str, db: Session) -> bool:
    """Text today's sessions. Returns whether anything was sent."""
    from datetime import date

    from ..db.models import TrainingPlanModel

    plan = (
        db.query(TrainingPlanModel)
        .filter(TrainingPlanModel.athlete_id == athlete_id)
        .order_by(TrainingPlanModel.created_at.desc())
        .first()
    )
    if plan is None:
        return False

    import json

    try:
        slots = json.loads(plan.weekly_slots_json or "[]")
    except (TypeError, ValueError):
        return False

    today = date.today().isoformat()
    todays = [
        s
        for s in slots
        if isinstance(s, dict) and str(s.get("date", ""))[:10] == today
    ]
    if not todays:
        return False

    lines = ["**Today**", ""]
    lines.extend(f"- {render_session_line(slot)}" for slot in todays)
    for slot in todays:
        note = str(slot.get("notes") or "").strip()
        if note:
            lines.append(f"  {note}")

    channels = configured_channels()
    if not channels:
        return False
    NotificationService(db, channels).send(
        athlete_id, "\n".join(lines), kind="daily_reminder"
    )
    return True


def run_daily_reminder(athlete_id: str) -> None:
    """APScheduler entry point for the opt-in daily session reminder."""
    if not daily_reminder_enabled():
        return
    with SessionLocal() as db:
        run_job(
            job_id=f"daily_reminder_{athlete_id}",
            job_type="daily_reminder",
            athlete_id=athlete_id,
            fn=lambda: send_daily_reminder(athlete_id, db),
            db=db,
            timeout_s=DAILY_REMINDER_TIMEOUT_S,
        )


# ─── Steps ────────────────────────────────────────────────────────────────────


def _sync_providers(athlete_id: str) -> list[str]:
    """Force a pull from every provider; return the ones that failed."""
    degraded: list[str] = []
    for provider, sync in _PROVIDER_SYNCS.items():
        try:
            sync(athlete_id)
        except Exception:
            logger.warning(
                "weekly_cycle_sync_failed",
                extra={"athlete_id": athlete_id, "provider": provider},
                exc_info=True,
            )
            degraded.append(provider)
    return degraded


def _settle(db: Session) -> None:
    """Close a transaction a read autobegan.

    Messaging and approval writes each own their own unit of work and refuse a
    session that is already mid-transaction, so every read step here has to hand
    the session back clean.
    """
    if db.in_transaction():
        db.commit()


def _compute_state(athlete_id: str, db: Session) -> None:
    try:
        snapshot_athlete(athlete_id, db)
        db.commit()
    except Exception:
        db.rollback()
        logger.warning(
            "weekly_cycle_snapshot_failed",
            extra={"athlete_id": athlete_id},
            exc_info=True,
        )


def _generate_week(
    athlete_id: str,
    db: Session,
    invoker: DefaultGraphInvoker | None,
) -> Mapping[str, Any]:
    """Ask for a week outright.

    The coordinator routes *inbound* events by journey phase — in steady_state a
    proactive event would land on chat_turn, which has nothing to say without a
    message. The weekly cycle is plan generation by definition, so it names the
    graph instead of asking the router to infer it.
    """
    runner = invoker or DefaultGraphInvoker()
    output = runner.invoke(
        "plan_generation",
        athlete_id,
        f"{athlete_id}:weekly_cycle",
        {"trigger": "weekly_cycle"},
        db,
    )
    _settle(db)
    return output if isinstance(output, Mapping) else {}


def _note_proactive_allowance(athlete_id: str, db: Session) -> None:
    """The weekly plan deliberately bypasses the soft pro-activity cap.

    The cap exists to stop the coach nagging; the one message the athlete
    signed up for is not nagging. Logged so the bypass is visible, never silent.
    """
    try:
        allowed = MonitoringService(db).check_proactive_message_allowed(athlete_id)
    except Exception:
        return
    if not allowed.get("allowed", True):
        logger.info(
            "weekly_cycle_bypasses_proactive_cap",
            extra={"athlete_id": athlete_id},
        )


def _build_approvals(db: Session) -> ApprovalService:
    channels = configured_channels()
    if not channels:
        raise WeeklyCycleError("No messaging channel is configured")
    return ApprovalService(
        db,
        notifier=NotificationService(db, channels),
        calendar_pusher=get_calendar_pusher(),
    )
