"""
Constraint Matrix Builder — core/constraint_matrix.py
Builds a weekly session schedule from the athlete's availability and training goals.
"""
from __future__ import annotations

from models.athlete_state import AthleteState

_DAY_ORDER = [
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
]


def build_constraint_matrix(state: AthleteState) -> dict:
    """
    Build a weekly session schedule from the athlete's availability and goals.

    Returns a dict with one key per day (schedule info) plus summary keys:
        {
          "monday":   {"available": bool, "sessions": [{"sport": str, "type": str}]},
          ...
          "sunday":   {"available": bool, "sessions": [...]},
          "total_sessions": int,
          "running_days":   int,
          "lifting_days":   int,
        }
    """
    available_days: list[str] = [
        day for day in _DAY_ORDER
        if _is_available(state, day)
    ]

    lifting_count = min(
        state.lifting_profile.sessions_per_week,
        len(available_days),
    )

    lifting_days = _pick_non_consecutive(available_days, lifting_count)
    running_days = [d for d in available_days if d not in lifting_days]

    schedule: dict[str, dict] = {}
    for day in _DAY_ORDER:
        sessions = []
        if day in lifting_days:
            sessions.append({"sport": "lifting", "type": "primary"})
        elif day in running_days:
            sessions.append({"sport": "running", "type": "primary"})
        schedule[day] = {
            "available": day in available_days,
            "sessions": sessions,
        }

    return {
        **schedule,
        "total_sessions": len(lifting_days) + len(running_days),
        "running_days": len(running_days),
        "lifting_days": len(lifting_days),
    }


def _is_available(state: AthleteState, day: str) -> bool:
    """Return True if the athlete is available on this day."""
    day_info = state.profile.available_days.get(day)
    if day_info is None:
        return False
    # DayAvailability instance (after Pydantic coercion) or plain dict
    if hasattr(day_info, "available"):
        return bool(day_info.available)
    return bool(day_info.get("available", False))


def _pick_non_consecutive(days: list[str], count: int) -> list[str]:
    """
    Greedily pick `count` days, preferring non-consecutive spacing.
    Falls back to consecutive days if not enough non-consecutive options exist.
    """
    if count <= 0 or not days:
        return []

    indices = [_DAY_ORDER.index(d) for d in days if d in _DAY_ORDER]
    chosen: list[int] = []

    for idx in indices:
        if len(chosen) >= count:
            break
        if not chosen or abs(idx - chosen[-1]) > 1:
            chosen.append(idx)

    # Fill remaining slots allowing consecutive days
    for idx in indices:
        if len(chosen) >= count:
            break
        if idx not in chosen:
            chosen.append(idx)

    return [_DAY_ORDER[i] for i in sorted(chosen[:count])]
