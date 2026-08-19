"""Turn a planned workout slot into a Google Calendar event body.

Times are always athlete-local: the wall time comes from the athlete's
preferred hour for that sport and the zone is sent explicitly, so a 07:00
session stays 07:00 across a DST boundary instead of drifting an hour.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

CALENDAR_NAME = "Resilio Training"

DEFAULT_TIMEZONE = "America/Montreal"
DEFAULT_HOUR = 7
REMINDER_MINUTES = 120

SLOT_ID_PROPERTY = "resilio_slot_id"

SPORT_EMOJI: dict[str, str] = {
    "running": "🏃",
    "lifting": "🏋️",
    "swimming": "🏊",
    "biking": "🚴",
}

# Google's fixed event colour ids — kept stable per sport across weeks.
SPORT_COLOR_ID: dict[str, str] = {
    "running": "11",  # tomato
    "lifting": "9",  # blueberry
    "swimming": "7",  # peacock
    "biking": "10",  # basil
}

_DEFAULT_COLOR_ID = "8"  # graphite


class InvalidSlotError(ValueError):
    """Raised when a slot cannot be placed on a calendar at all."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"Cannot build a calendar event: {reason}")


def resolve_zone(timezone_name: str | None) -> ZoneInfo:
    """Return the athlete's zone, falling back to the default when unknown."""
    try:
        return ZoneInfo(timezone_name or DEFAULT_TIMEZONE)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo(DEFAULT_TIMEZONE)


def preferred_hour(sport: str, preferences: Mapping[str, Any] | None) -> int:
    """Return the athlete's preferred local start hour for a sport."""
    if isinstance(preferences, Mapping):
        raw = preferences.get(sport, preferences.get("default"))
        if isinstance(raw, bool):
            return DEFAULT_HOUR
        if isinstance(raw, (int, float)) and 0 <= int(raw) <= 23:
            return int(raw)
    return DEFAULT_HOUR


def slot_date(slot: Mapping[str, Any]) -> date:
    """Parse the slot's date, raising when it is unusable."""
    raw = slot.get("date")
    if isinstance(raw, date) and not isinstance(raw, datetime):
        return raw
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, str):
        try:
            return date.fromisoformat(raw[:10])
        except ValueError as exc:
            raise InvalidSlotError(f"unparseable date {raw!r}") from exc
    raise InvalidSlotError("slot has no date")


def build_event(
    slot: Mapping[str, Any],
    *,
    timezone_name: str,
    preferences: Mapping[str, Any] | None = None,
    rationale: str = "",
) -> dict[str, Any]:
    """Return the Google event body for one workout slot."""
    day = slot_date(slot)
    sport = str(slot.get("sport", ""))
    zone = resolve_zone(timezone_name)
    hour = preferred_hour(sport, preferences)

    start = datetime.combine(day, time(hour=hour), tzinfo=zone)
    duration = slot.get("duration_min")
    minutes = int(duration) if isinstance(duration, (int, float)) and duration else 60
    end = start + timedelta(minutes=minutes)

    return {
        "summary": _summary(slot),
        "description": _description(slot, rationale),
        "start": {"dateTime": start.isoformat(), "timeZone": timezone_name},
        "end": {"dateTime": end.isoformat(), "timeZone": timezone_name},
        "colorId": SPORT_COLOR_ID.get(sport, _DEFAULT_COLOR_ID),
        "reminders": {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": REMINDER_MINUTES}],
        },
        "extendedProperties": {
            "private": {SLOT_ID_PROPERTY: str(slot.get("id", ""))},
        },
    }


def content_hash(event: Mapping[str, Any]) -> str:
    """Stable fingerprint of an event body, used to skip no-op patches."""
    payload = json.dumps(event, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _summary(slot: Mapping[str, Any]) -> str:
    sport = str(slot.get("sport", ""))
    emoji = SPORT_EMOJI.get(sport, "•")
    workout_type = str(slot.get("workout_type") or "session")
    metric = _key_metric(slot)
    return f"{emoji} {workout_type} — {metric}" if metric else f"{emoji} {workout_type}"


def _key_metric(slot: Mapping[str, Any]) -> str:
    notes = str(slot.get("notes") or "").strip()
    if notes:
        return notes.splitlines()[0].strip()
    duration = slot.get("duration_min")
    if isinstance(duration, (int, float)) and duration:
        return f"{int(duration)} min"
    return ""


def _description(slot: Mapping[str, Any], rationale: str) -> str:
    lines: list[str] = []
    notes = str(slot.get("notes") or "").strip()
    if notes:
        lines.append(notes)

    fatigue = slot.get("fatigue_score")
    if isinstance(fatigue, Mapping):
        parts = []
        for label, key in (
            ("local", "local_muscular"),
            ("CNS", "cns_load"),
            ("metabolic", "metabolic_cost"),
        ):
            value = fatigue.get(key)
            if isinstance(value, (int, float)):
                parts.append(f"{label} {int(value)}")
        recovery = fatigue.get("recovery_hours")
        if isinstance(recovery, (int, float)):
            parts.append(f"recovery {int(recovery)}h")
        if parts:
            lines.append("Fatigue — " + ", ".join(parts))

    if rationale.strip():
        lines.append(rationale.strip())

    lines.append("Planned by Resilio.")
    return "\n\n".join(lines)
