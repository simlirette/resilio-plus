"""Build the plain-dict athlete profile the coaching graph expects.

``AthleteModel`` stores list fields as JSON text; the graph wants a validated
:class:`~app.schemas.athlete.AthleteProfile` dumped to JSON-safe primitives.
Shared by the HTTP workflow surface and the text-native coach so both feed the
graph the same shape.
"""
from __future__ import annotations

import json
from typing import Any, Literal, cast
from uuid import UUID

from ..db.models import AthleteModel
from ..schemas.athlete import AthleteProfile
from ..schemas.athlete import Sport as _Sport


def _json_list(raw: str | None) -> list[Any]:
    try:
        value = json.loads(raw or "[]")
    except (TypeError, ValueError):
        return []
    return value if isinstance(value, list) else []


def athlete_profile(athlete: AthleteModel) -> AthleteProfile:
    """Return the validated profile for an athlete row."""
    return AthleteProfile(
        id=UUID(athlete.id),
        name=athlete.name,
        age=athlete.age,
        sex=cast(Literal["M", "F", "other"], athlete.sex),
        weight_kg=athlete.weight_kg,
        height_cm=athlete.height_cm,
        sports=_json_list(athlete.sports_json),
        primary_sport=_Sport(athlete.primary_sport),
        goals=_json_list(athlete.goals_json),
        available_days=_json_list(athlete.available_days_json),
        hours_per_week=athlete.hours_per_week,
        target_race_date=athlete.target_race_date,
        sleep_hours_typical=athlete.sleep_hours_typical,
        stress_level=athlete.stress_level,
        job_physical=athlete.job_physical,
        max_hr=athlete.max_hr,
        resting_hr=athlete.resting_hr,
        ftp_watts=athlete.ftp_watts,
        vdot=athlete.vdot,
        css_per_100m=athlete.css_per_100m,
        equipment=_json_list(athlete.equipment_json),
        coaching_mode=cast(Literal["full", "tracking_only"], athlete.coaching_mode),
    )


def athlete_profile_dict(athlete: AthleteModel) -> dict[str, Any]:
    """Return the JSON-safe profile dict passed into the coaching graph."""
    return athlete_profile(athlete).model_dump(mode="json")
