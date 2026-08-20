"""Render a generated week as chat text — the sessions *and* the reasoning.

The channel layer only knows a markdown subset (``**bold**``, ``*italic*``,
``- bullet``); :meth:`MessagingChannel.format` translates that to the provider
dialect. Nothing here emits provider markup directly.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from typing import Any

SPORT_EMOJI: dict[str, str] = {
    "running": "🏃",
    "lifting": "🏋️",
    "swimming": "🏊",
    "biking": "🚴",
}

_FALLBACK_EMOJI = "•"

_ACWR_COMMENT: dict[str, str] = {
    "safe": "safe zone",
    "caution": "caution — load is climbing",
    "danger": "danger zone — load must come down",
    "insufficient_data": "not enough history yet",
}


def render_week(
    plan: Mapping[str, Any] | None,
    *,
    degraded_sources: Sequence[str] | None = None,
) -> str:
    """Return the athlete-facing text for a proposed or approved week."""
    if plan is None:
        return "No plan is available for this week yet."

    sessions = [s for s in plan.get("sessions", []) or [] if isinstance(s, dict)]
    lines: list[str] = [_header(plan, sessions)]

    if not sessions:
        lines.append("")
        lines.append("No sessions this week — full rest is the prescription.")
    else:
        for day, day_sessions in _group_by_day(sessions):
            lines.append("")
            lines.append(f"**{day}**")
            for session in day_sessions:
                lines.append(f"- {render_session_line(session)}")
                note = str(session.get("notes") or "").strip()
                if note:
                    lines.append(f"  {note}")

    reasoning = _reasoning_lines(plan)
    if reasoning:
        lines.append("")
        lines.append("**Why this week**")
        for entry in reasoning:
            lines.extend(_as_bullet(entry))

    if degraded_sources:
        lines.append("")
        joined = ", ".join(degraded_sources)
        lines.append(f"*Planned without fresh data from: {joined}.*")

    return "\n".join(lines)


def render_session_line(session: Mapping[str, Any]) -> str:
    """Return the one-line summary of a single workout slot."""
    sport = str(session.get("sport", ""))
    emoji = SPORT_EMOJI.get(sport, _FALLBACK_EMOJI)
    workout_type = str(session.get("workout_type", "session"))
    duration = session.get("duration_min")
    duration_text = f" — {int(duration)} min" if isinstance(duration, (int, float)) else ""
    return f"{emoji} {workout_type}{duration_text}"


def _header(plan: Mapping[str, Any], sessions: Sequence[Mapping[str, Any]]) -> str:
    phase = str(plan.get("phase") or "").strip()
    start = _first_date(sessions)
    week_label = f"Week of {start:%d %B}" if start is not None else "Next week"
    total_minutes = sum(
        int(s.get("duration_min", 0) or 0)
        for s in sessions
        if isinstance(s.get("duration_min"), (int, float))
    )
    parts = [
        f"{len(sessions)} session{'s' if len(sessions) != 1 else ''}",
        _format_duration(total_minutes),
    ]
    if phase:
        parts.append(f"phase {phase}")
    return f"**{week_label}** — {' · '.join(parts)}"


def _as_bullet(entry: str) -> list[str]:
    """Render one reasoning entry as a bullet, indenting any extra lines.

    Agent notes are sometimes several lines — nutrition targets per day type,
    for instance. Emitting them raw leaves orphan lines that do not read as
    part of the bullet above them.
    """
    parts = [part.rstrip() for part in entry.splitlines() if part.strip()]
    if not parts:
        return []
    return [f"- {parts[0]}"] + [f"  {part.lstrip()}" for part in parts[1:]]


def _reasoning_lines(plan: Mapping[str, Any]) -> list[str]:
    lines: list[str] = []

    acwr = plan.get("acwr")
    if isinstance(acwr, Mapping):
        ratio = acwr.get("ratio")
        status = str(acwr.get("status", ""))
        if isinstance(ratio, (int, float)):
            comment = _ACWR_COMMENT.get(status, status.replace("_", " "))
            suffix = f" ({comment})" if comment else ""
            lines.append(f"ACWR {ratio:.2f}{suffix}")

    readiness = plan.get("readiness_level")
    if isinstance(readiness, str) and readiness:
        lines.append(f"Readiness {readiness}")

    fatigue = plan.get("global_fatigue")
    if isinstance(fatigue, Mapping):
        recovery = fatigue.get("recovery_hours")
        if isinstance(recovery, (int, float)):
            lines.append(f"Estimated recovery {int(recovery)} h across the week")

    for conflict in plan.get("conflicts", []) or []:
        if isinstance(conflict, Mapping):
            message = str(conflict.get("message") or "").strip()
            if message:
                severity = str(conflict.get("severity") or "").strip()
                prefix = f"{severity}: " if severity else ""
                lines.append(f"{prefix}{message}")

    notes = plan.get("notes")
    if isinstance(notes, str) and notes.strip():
        lines.append(notes.strip())
    elif isinstance(notes, Iterable) and not isinstance(notes, (str, bytes)):
        lines.extend(str(n).strip() for n in notes if str(n).strip())

    return lines


def _group_by_day(
    sessions: Sequence[Mapping[str, Any]],
) -> list[tuple[str, list[Mapping[str, Any]]]]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    order: list[str] = []
    for session in sorted(sessions, key=_sort_key):
        label = _day_label(session)
        if label not in grouped:
            grouped[label] = []
            order.append(label)
        grouped[label].append(session)
    return [(label, grouped[label]) for label in order]


def _sort_key(session: Mapping[str, Any]) -> tuple[int, str]:
    parsed = _parse_date(session.get("date"))
    if parsed is None:
        return (1, str(session.get("date") or ""))
    return (0, parsed.isoformat())


def _day_label(session: Mapping[str, Any]) -> str:
    parsed = _parse_date(session.get("date"))
    if parsed is None:
        return "Unscheduled"
    return f"{parsed:%A %d %B}"


def _first_date(sessions: Sequence[Mapping[str, Any]]) -> date | None:
    parsed = [d for d in (_parse_date(s.get("date")) for s in sessions) if d is not None]
    return min(parsed) if parsed else None


def _parse_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _format_duration(total_minutes: int) -> str:
    if total_minutes <= 0:
        return "0 min"
    hours, minutes = divmod(total_minutes, 60)
    if hours and minutes:
        return f"{hours}h{minutes:02d}"
    if hours:
        return f"{hours}h00"
    return f"{minutes} min"
