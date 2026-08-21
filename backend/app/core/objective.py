"""Where the athlete is in their objective cycle.

Step 6 of the goal document: "When the objective is reach, the athlete can set
up a new objective."

Nothing noticed a race going past. `weeks_to_race` clamps at zero, so every
week after the date read as race week — forever. The coach would have kept
periodising toward an event already run until the athlete thought to mention
it.

Detection is deterministic. What to do about it is the coach's judgement and
the athlete's decision, so this reports a state and nothing more: it never
proposes the next goal, because choosing it is the athlete's call.
"""
from __future__ import annotations

import enum
import json
from datetime import date
from typing import Any


class ObjectiveStatus(enum.Enum):
    ACTIVE = "active"
    #: The race date is behind us. The plan is aimed at something already run.
    PASSED = "passed"
    #: A real goal with no finish line — "get fitter", "run more".
    UNDATED = "undated"
    NONE = "none"


def _has_goal(athlete: Any) -> bool:
    raw = getattr(athlete, "goals_json", None)
    if not raw:
        return False
    try:
        goals = json.loads(raw)
    except (TypeError, ValueError):
        return False
    return bool(goals) if isinstance(goals, list) else False


def objective_status(athlete: Any, today: date | None = None) -> ObjectiveStatus:
    """Whether the athlete's objective is still ahead of them."""
    reference = today or date.today()
    race_date = getattr(athlete, "target_race_date", None)

    if isinstance(race_date, date):
        # The race day itself is still ahead at breakfast.
        return (
            ObjectiveStatus.ACTIVE
            if race_date >= reference
            else ObjectiveStatus.PASSED
        )

    return ObjectiveStatus.UNDATED if _has_goal(athlete) else ObjectiveStatus.NONE


def describe_objective(athlete: Any, today: date | None = None) -> str:
    """A line for the coach, or nothing when there is nothing to act on.

    An objective still ahead needs no comment — saying "your race is in 30
    days" every turn is the kind of noise that makes an athlete stop reading.
    """
    reference = today or date.today()
    status = objective_status(athlete, reference)

    if status is ObjectiveStatus.PASSED:
        race_date = getattr(athlete, "target_race_date", None)
        days = (reference - race_date).days if isinstance(race_date, date) else 0
        return (
            f"La course cible est passée depuis {days} jour"
            f"{'s' if days != 1 else ''}. Le plan vise encore un événement déjà "
            "couru. Demande-lui comment ça s'est passé et quel objectif vient "
            "ensuite — c'est lui qui le choisit."
        )

    if status is ObjectiveStatus.NONE:
        return "Aucun objectif n'est enregistré."

    return ""
