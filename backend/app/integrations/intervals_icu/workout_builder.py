"""Turn a planned slot into something a Garmin watch can run.

Step 4 of the goal document: the approved week goes to Google Calendar *and*
the workouts that can live on a watch go to intervals.icu, which syncs them to
Garmin. The calendar half was built; this half did not exist, so the athlete
could read the week on their phone and had nothing on their wrist.

Not every session is a workout. A hypertrophy block has no structure a watch
can execute, and pushing it produces an entry that means nothing mid-session.
Those are skipped, and the count of skipped ones is returned rather than
swallowed — an athlete who sees three of five sessions appear deserves to know
why.

`external_id` carries the slot id so a re-approval updates the existing entry
instead of adding a second one. Google Calendar learned that the expensive
way; the same rule applies here.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

#: Sports whose sessions a watch can meaningfully execute.
PUSHABLE_SPORTS = {"running", "biking", "swimming"}

#: How intervals.icu names the discipline.
_ICU_TYPE = {
    "running": "Run",
    "biking": "Ride",
    "swimming": "Swim",
}

_ID_PREFIX = "resilio-"


def is_pushable(slot: Any) -> bool:
    """Whether this session belongs on a watch at all."""
    if not isinstance(slot, dict):
        return False
    if str(slot.get("sport", "")) not in PUSHABLE_SPORTS:
        return False
    duration = slot.get("duration_min")
    if not isinstance(duration, (int, float)) or duration <= 0:
        return False
    return bool(slot.get("date"))


def build_workout(slot: Any) -> dict[str, Any] | None:
    """One intervals.icu event, or None when the session does not belong there."""
    if not is_pushable(slot):
        return None

    sport = str(slot["sport"])
    workout_type = str(slot.get("workout_type", "session"))
    minutes = int(slot["duration_min"])
    notes = str(slot.get("notes") or "").strip()

    description = f"{minutes} min"
    if notes:
        description = f"{description} — {notes}"

    event: dict[str, Any] = {
        "start_date_local": f"{str(slot['date'])[:10]}T00:00:00",
        "category": "WORKOUT",
        "type": _ICU_TYPE.get(sport, "Run"),
        "name": workout_type.replace("_", " "),
        "description": description,
        "moving_time": minutes * 60,
    }

    slot_id = slot.get("id")
    if slot_id:
        # Lets a re-approval update this entry rather than duplicate it.
        event["external_id"] = f"{_ID_PREFIX}{slot_id}"
    return event


def build_week(slots: Any) -> tuple[list[dict[str, Any]], int]:
    """Every pushable session in a week, and how many were left behind.

    A malformed slot is skipped rather than raised: one bad entry must not stop
    the rest of the week reaching the watch.
    """
    workouts: list[dict[str, Any]] = []
    skipped = 0

    for slot in slots or []:
        try:
            workout = build_workout(slot)
        except Exception:
            logger.warning("intervals_workout_unbuildable", exc_info=True)
            workout = None
        if workout is None:
            skipped += 1
            continue
        workouts.append(workout)

    return workouts, skipped
