"""Send an approved week to the athlete's watch, alongside the calendar.

Step 4 of the goal document asks for both: the plan on Google Calendar for the
overview, and the runnable workouts on intervals.icu so Garmin picks them up.
The calendar half shipped in V4-T5; this is the other half.

Off unless configured, and never fatal. The week is approved and saved before
either push happens — a watch that did not receive it is a smaller problem than
an athlete told their plan was lost.
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def watch_enabled() -> bool:
    """True when a key and an intervals.icu athlete id are both configured."""
    return bool(
        os.getenv("INTERVALS_ICU_API_KEY", "").strip()
        and os.getenv("INTERVALS_ICU_ATHLETE_ID", "").strip()
    )


def push_to_watch(plan: Any) -> dict[str, int] | None:
    """Push the runnable sessions of a week. None when the watch is not set up.

    Returns counts rather than raising: a rejected workout must not turn an
    approved week into an error message.
    """
    if not watch_enabled():
        return None

    from ..integrations.intervals_icu.client import push_workouts
    from ..integrations.intervals_icu.workout_builder import build_week

    sessions = plan.get("sessions") if isinstance(plan, dict) else None
    workouts, skipped = build_week(sessions or [])
    if not workouts:
        return {"created": 0, "updated": 0, "skipped": skipped, "failed": 0}

    try:
        report = push_workouts(
            os.environ["INTERVALS_ICU_ATHLETE_ID"].strip(),
            workouts,
            already_skipped=skipped,
        )
    except Exception:
        logger.warning("watch_push_failed", exc_info=True)
        return None

    return report.as_dict()


def describe_push(report: dict[str, int] | None) -> str:
    """One clause for the approval message, or nothing.

    Silence when the watch is not configured: an athlete without a Garmin does
    not need a line about it every week.
    """
    if report is None:
        return ""
    pushed = report.get("created", 0) + report.get("updated", 0)
    if not pushed and not report.get("failed"):
        return ""

    parts = [f"{pushed} séance{'s' if pushed != 1 else ''} envoyée"]
    if pushed != 1:
        parts[0] += "s"
    parts[0] += " sur ta montre"
    if report.get("skipped"):
        parts.append(f"{report['skipped']} non transposable")
    if report.get("failed"):
        parts.append(f"{report['failed']} en échec")
    return " — " + ", ".join(parts) + "."
