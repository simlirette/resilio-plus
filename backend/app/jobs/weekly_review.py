"""The look back that happens before the look forward.

Step 5 of the goal document: "Once a week, coach AI is doing a follow up,
taking the data from the last completed week and making a short statement for
the athlete."

The weekly cycle synced providers, computed a snapshot and generated a new
week. It never compared the week that had just ended to what was planned, so
the athlete received a fresh plan with no acknowledgement that they had missed
two sessions. That is a scheduler.

The statement is written by the coach from adherence facts, not assembled from
a template. A real coach says something different to an athlete who did every
session than to one who did none, and neither sentence can be written in
advance.

A week that went to plan produces no statement at all. A weekly "well done"
that arrives whatever happened is noise, and noise is what makes an athlete
stop reading.
"""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from typing import Any

from ..core.adherence import WeekComparison, compare_week, describe_week
from ..services.coach_loop import run_coach_turn

logger = logging.getLogger(__name__)

REVIEW_DAYS = 7

_ASK = (
    "Bilan hebdomadaire. Voici ce qui était prévu la semaine dernière et ce que "
    "l'athlète a réellement fait :\n\n{facts}\n\n"
    "Écris-lui un constat court — trois phrases au maximum. Dis ce qui s'est "
    "passé et ce que ça implique pour la suite. N'invente aucun chiffre au-delà "
    "de ceux ci-dessus, ne prescris pas de séance ici, ne félicite pas pour "
    "féliciter."
)


def _completed(athlete_id: str, db: Any, since: date) -> list[dict[str, Any]]:
    """What the athlete actually did, from the connectors."""
    from ..db.models import StravaActivityModel

    rows = (
        db.query(StravaActivityModel)
        .filter(StravaActivityModel.athlete_id == athlete_id)
        .all()
    )
    done: list[dict[str, Any]] = []
    for row in rows:
        day = row.started_at.date() if row.started_at else None
        if day is None or day < since:
            continue
        done.append(
            {
                "date": day,
                "sport": row.sport_type or "",
                "duration_min": int((row.duration_s or 0) / 60),
            }
        )
    return done


def gather_week(athlete_id: str, db: Any) -> WeekComparison | None:
    """Compare the week that just ended against the plan that covered it."""
    from ..db.models import TrainingPlanModel

    plan = (
        db.query(TrainingPlanModel)
        .filter(TrainingPlanModel.athlete_id == athlete_id)
        .order_by(TrainingPlanModel.created_at.desc())
        .first()
    )
    if plan is None:
        return None

    try:
        slots = json.loads(plan.weekly_slots_json or "[]")
    except (TypeError, ValueError):
        logger.warning("weekly_review_plan_unreadable", extra={"athlete_id": athlete_id})
        return None

    today = date.today()
    since = today - timedelta(days=REVIEW_DAYS)
    planned = [
        slot
        for slot in slots
        if isinstance(slot, dict)
        and since.isoformat() <= str(slot.get("date", ""))[:10] < today.isoformat()
    ]
    if not planned:
        return None

    return compare_week(planned, _completed(athlete_id, db, since))


def write_statement(athlete_id: str, db: Any) -> str | None:
    """The coach's short read on the week that ended, or nothing.

    Best-effort on purpose: the new week still has to reach the athlete even if
    the look back cannot be written.
    """
    comparison = gather_week(athlete_id, db)
    if comparison is None or not comparison.worth_raising:
        return None

    try:
        outcome = run_coach_turn(
            athlete_id=athlete_id,
            user_message=_ASK.format(facts=describe_week(comparison)),
            db=db,
        )
    except Exception:
        logger.warning(
            "weekly_review_statement_failed", extra={"athlete_id": athlete_id},
            exc_info=True,
        )
        return None

    reply = (outcome.reply or "").strip()
    return reply or None
