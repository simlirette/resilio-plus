"""What was planned against what was actually done.

Nothing compared the two. There was no `skipped`, no compliance, no adherence
logic anywhere in the codebase, and the daily reminder only recited today's
slots. So "faire le suivi" — one of the four things the athlete asked the coach
to do — had no factual basis at all.

This module reports; it does not advise. The coach forms the judgement from
these facts, the way it forms every other one.

Matching is loose on numbers and strict on the day. Forty minutes instead of
forty-five is the session. Nothing at all is not. A run done a day late was
*moved*, which is a different fact from skipped, and a coach that cannot tell
them apart will say the wrong thing to an athlete who simply shifted a day.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import date
from typing import Any

#: Within this ratio of the planned duration the session counts as done.
_CLOSE_ENOUGH = 0.30
#: Beyond this, the athlete did materially more than was asked.
_OVERSHOOT = 1.5
#: A session done within this many days of its slot was moved, not missed.
_MOVE_WINDOW_DAYS = 2


class Status(enum.Enum):
    DONE = "done"
    MOVED = "moved"
    CUT_SHORT = "cut_short"
    OVERSHOT = "overshot"
    MISSED = "missed"


STATUS_LABELS: dict[Status, str] = {
    Status.DONE: "faite",
    Status.MOVED: "déplacée",
    Status.CUT_SHORT: "écourtée",
    Status.OVERSHOT: "dépassée",
    Status.MISSED: "non faite",
}


@dataclass(frozen=True)
class SessionOutcome:
    date: date
    status: Status
    planned: dict[str, Any]
    actual: dict[str, Any] | None = None


@dataclass
class WeekComparison:
    outcomes: list[SessionOutcome] = field(default_factory=list)
    #: Training the athlete did that no slot asked for.
    unplanned: list[dict[str, Any]] = field(default_factory=list)

    @property
    def done(self) -> int:
        return sum(1 for o in self.outcomes if o.status is Status.DONE)

    @property
    def missed(self) -> int:
        return sum(1 for o in self.outcomes if o.status is Status.MISSED)

    @property
    def worth_raising(self) -> bool:
        """Whether anything happened that a coach would mention unprompted.

        A week that went to plan is not worth a message. Neither is a week that
        does not exist -- messaging an athlete about an empty plan is noise.
        """
        if not self.outcomes and not self.unplanned:
            return False
        return bool(self.unplanned) or any(
            o.status is not Status.DONE for o in self.outcomes
        )


def _as_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _classify(planned_min: float, actual_min: float, day_gap: int) -> Status:
    if day_gap != 0:
        return Status.MOVED
    if planned_min <= 0:
        return Status.DONE
    ratio = actual_min / planned_min
    if ratio >= _OVERSHOOT:
        return Status.OVERSHOT
    if ratio < 1 - _CLOSE_ENOUGH:
        return Status.CUT_SHORT
    return Status.DONE


def compare_week(
    planned: list[dict[str, Any]],
    completed: list[dict[str, Any]],
) -> WeekComparison:
    """Match each planned slot to a completed session, or mark it missed."""
    comparison = WeekComparison()
    unclaimed = list(completed)

    for slot in planned:
        slot_day = _as_date(slot.get("date"))
        if slot_day is None:
            continue
        sport = str(slot.get("sport", ""))
        planned_min = float(slot.get("duration_min") or 0)

        match: dict[str, Any] | None = None
        best_gap = _MOVE_WINDOW_DAYS + 1
        for candidate in unclaimed:
            if str(candidate.get("sport", "")) != sport:
                continue
            candidate_day = _as_date(candidate.get("date"))
            if candidate_day is None:
                continue
            gap = abs((candidate_day - slot_day).days)
            if gap <= _MOVE_WINDOW_DAYS and gap < best_gap:
                match, best_gap = candidate, gap

        if match is None:
            comparison.outcomes.append(
                SessionOutcome(date=slot_day, status=Status.MISSED, planned=slot)
            )
            continue

        unclaimed.remove(match)
        matched_day = _as_date(match.get("date")) or slot_day
        comparison.outcomes.append(
            SessionOutcome(
                date=slot_day,
                status=_classify(
                    planned_min,
                    float(match.get("duration_min") or 0),
                    (matched_day - slot_day).days,
                ),
                planned=slot,
                actual=match,
            )
        )

    comparison.unplanned = unclaimed
    return comparison


def describe_week(comparison: WeekComparison) -> str:
    """The facts, for the coach to reason from. No advice, no instruction."""
    if not comparison.outcomes and not comparison.unplanned:
        return "Aucune séance planifiée sur la période."

    lines: list[str] = []
    for outcome in comparison.outcomes:
        slot = outcome.planned
        label = STATUS_LABELS[outcome.status]
        detail = f"{slot.get('sport', '?')} {slot.get('workout_type', '')}".strip()
        planned_min = slot.get("duration_min")
        piece = f"{outcome.date.isoformat()} — {detail} ({planned_min} min) : {label}"
        if outcome.actual is not None:
            actual_min = outcome.actual.get("duration_min")
            if actual_min is not None and outcome.status is not Status.DONE:
                piece += f", {actual_min} min réalisées"
        lines.append(piece)

    for extra in comparison.unplanned:
        day = _as_date(extra.get("date"))
        when = day.isoformat() if day else "date inconnue"
        lines.append(
            f"{when} — {extra.get('sport', '?')} "
            f"({extra.get('duration_min', '?')} min) : hors plan"
        )

    return "\n".join(lines)
