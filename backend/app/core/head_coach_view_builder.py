"""HeadCoachView builder — Phase D (D4).

Constructs the HeadCoachView snapshot from an AthleteModel instance.
Expanded in D6 with Recovery and Energy context.
"""
from __future__ import annotations

import json

from ..db.models import AthleteModel
from ..schemas.head_coach_view import HeadCoachView


def build_head_coach_view(athlete: AthleteModel) -> HeadCoachView:
    """Build a HeadCoachView from the athlete DB record.

    Args:
        athlete: ORM model with current journey state.

    Returns:
        HeadCoachView with all available context for Head Coach chat responses.
    """
    sports: list[str] = json.loads(athlete.sports_json or "[]")
    clinical_flag = getattr(athlete, "clinical_context_flag", None)

    return HeadCoachView(
        athlete_id=athlete.id,
        journey_phase=athlete.journey_phase,
        sports=sports,
        primary_sport=athlete.primary_sport,
        hours_per_week=athlete.hours_per_week,
        coaching_mode=getattr(athlete, "coaching_mode", "full"),
        active_plan_summary=None,  # D6: populated from active plan
        clinical_context_flag=clinical_flag,
    )
