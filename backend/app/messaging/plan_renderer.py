"""Render a generated week as chat text — the sessions *and* the reasoning.

The channel layer only knows a markdown subset (``**bold**``, ``*italic*``,
``- bullet``); :meth:`MessagingChannel.format` translates that to the provider
dialect. Nothing here emits provider markup directly.
"""
from __future__ import annotations

import re
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
    "caution": "prudence — la charge monte",
    "danger": "zone rouge — la charge doit baisser",
    "insufficient_data": "pas encore assez d'historique",
}

# strftime follows the process locale, which is C in every environment this
# runs in, so day and month names came out English inside French sentences.
# Explicit tables rather than locale.setlocale, which is process-global and
# would leak into every other thread.
_DAYS_FR: tuple[str, ...] = (
    "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche",
)
_MONTHS_FR: tuple[str, ...] = (
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
)

# Values that arrive as enum names from the planning engine and would otherwise
# be shown to the athlete raw.
_PHASE_FR: dict[str, str] = {
    "general_prep": "préparation générale",
    "specific_prep": "préparation spécifique",
    "pre_competition": "pré-compétition",
    "competition": "compétition",
    "transition": "transition",
    "recovery": "récupération",
}
_READINESS_FR: dict[str, str] = {
    "green": "verte",
    "yellow": "orange",
    "red": "rouge",
}
_SEVERITY_FR: dict[str, str] = {
    "critical": "critique",
    "warning": "attention",
    "info": "info",
}


def _fr_day(value: "date") -> str:
    return f"{_DAYS_FR[value.weekday()]} {value.day} {_MONTHS_FR[value.month - 1]}"


def _fr_short_day(value: "date") -> str:
    return f"{value.day} {_MONTHS_FR[value.month - 1]}"


def render_week(
    plan: Mapping[str, Any] | None,
    *,
    degraded_sources: Sequence[str] | None = None,
) -> str:
    """Return the athlete-facing text for a proposed or approved week."""
    if plan is None:
        return "Aucune semaine n'est disponible pour l'instant."

    sessions = [s for s in plan.get("sessions", []) or [] if isinstance(s, dict)]
    lines: list[str] = [_header(plan, sessions)]

    if not sessions:
        lines.append("")
        lines.append("Aucune séance cette semaine — repos complet, c'est la prescription.")
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
        lines.append("**Pourquoi cette semaine**")
        for entry in reasoning:
            lines.extend(_as_bullet(entry))

    if degraded_sources:
        lines.append("")
        joined = ", ".join(degraded_sources)
        lines.append(f"*Planifiée sans données fraîches de : {joined}.*")

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
    week_label = (
        f"Semaine du {_fr_short_day(start)}" if start is not None else "Semaine à venir"
    )
    total_minutes = sum(
        int(s.get("duration_min", 0) or 0)
        for s in sessions
        if isinstance(s.get("duration_min"), (int, float))
    )
    parts = [
        f"{len(sessions)} séance{'s' if len(sessions) != 1 else ''}",
        _format_duration(total_minutes),
    ]
    if phase:
        parts.append(f"phase {_PHASE_FR.get(phase, phase)}")
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


# A note written as `key=value key=value` is how an agent hands numbers to the
# Head Coach. It is not something a person reads on their phone. The first live
# plan ended with five lines of `carbs=3.5g/kg protein=1.8g/kg kcal≈2467`.
_KEY_VALUE = re.compile(r"[A-Za-z_]{2,}\s*[=≈]\s*[\d.]")

#: What each machine-readable note is replaced with. Dropping them silently
#: would lose a real coaching point; this keeps the point and loses the table.
_NOTE_SUMMARIES: tuple[tuple[str, str], ...] = (
    ("carb", "Nutrition : glucides indexés sur le type de séance, protéines constantes."),
    ("kcal", "Nutrition : glucides indexés sur le type de séance, protéines constantes."),
    ("acwr", "Charge suivie via l'ACWR."),
    ("vdot", "Allures calées sur ton VDOT actuel."),
    ("quads", "Fatigue musculaire suivie par groupe."),
)
_NOTE_FALLBACK = "Détail technique disponible sur demande."


def _is_machine_output(note: str) -> bool:
    """True when a note reads as data rather than as a sentence.

    A pace ("4:09/km") and a date carry digits and colons too, so the test is
    an ``=`` or ``≈`` binding a bare word to a number -- which prose does not do.
    """
    return bool(_KEY_VALUE.search(note))


def _readable_note(note: str) -> str:
    lowered = note.lower()
    for marker, summary in _NOTE_SUMMARIES:
        if marker in lowered:
            return summary
    return _NOTE_FALLBACK


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
        lines.append(f"Disponibilité {_READINESS_FR.get(readiness, readiness)}")

    fatigue = plan.get("global_fatigue")
    if isinstance(fatigue, Mapping):
        recovery = fatigue.get("recovery_hours")
        if isinstance(recovery, (int, float)):
            lines.append(f"Récupération estimée {int(recovery)} h sur la semaine")

    for conflict in plan.get("conflicts", []) or []:
        if isinstance(conflict, Mapping):
            message = str(conflict.get("message") or "").strip()
            if message:
                severity = str(conflict.get("severity") or "").strip()
                prefix = f"{_SEVERITY_FR.get(severity, severity)} : " if severity else ""
                lines.append(f"{prefix}{message}")

    raw_notes = plan.get("notes")
    if isinstance(raw_notes, str):
        candidates = [raw_notes]
    elif isinstance(raw_notes, Iterable) and not isinstance(raw_notes, bytes):
        candidates = [str(note) for note in raw_notes]
    else:
        candidates = []

    seen: set[str] = set()
    for note in (n.strip() for n in candidates):
        if not note:
            continue
        rendered = _readable_note(note) if _is_machine_output(note) else note
        if rendered not in seen:
            seen.add(rendered)
            lines.append(rendered)

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
    return _fr_day(parsed)


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
