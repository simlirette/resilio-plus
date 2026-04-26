"""CrossDisciplineInterferenceService — Phase D (D5), DEP-C4-004.

Deterministic computation of CrossDisciplineLoadV1 from an active plan dict.
Used by chat_turn to inject cross-discipline context into specialist views.
"""
from __future__ import annotations

from typing import Any

from ..schemas.cross_discipline import CrossDisciplineLoadV1

# Sport name normalisation: map plan sport values → discipline buckets
_RUNNING_SPORTS = {"running"}
_BIKING_SPORTS = {"cycling", "biking", "bike", "velo", "vélo"}
_SWIMMING_SPORTS = {"swimming", "swim", "natation"}


def compute_cross_discipline_load_v1(
    active_plan: dict[str, Any] | None,
) -> CrossDisciplineLoadV1:
    """Compute weekly session counts per endurance discipline from active_plan.

    Args:
        active_plan: Plan dict with a 'sessions' list (each item has a 'sport' key),
                     or None if no active plan exists.

    Returns:
        CrossDisciplineLoadV1 with per-discipline session counts (zeroes if no plan).
    """
    if not active_plan:
        return CrossDisciplineLoadV1()

    sessions: list[dict[str, Any]] = active_plan.get("sessions", [])

    running = 0
    biking = 0
    swimming = 0

    for session in sessions:
        sport = str(session.get("sport", "")).lower().strip()
        if sport in _RUNNING_SPORTS:
            running += 1
        elif sport in _BIKING_SPORTS:
            biking += 1
        elif sport in _SWIMMING_SPORTS:
            swimming += 1

    return CrossDisciplineLoadV1(
        weekly_running_sessions=running,
        weekly_biking_sessions=biking,
        weekly_swimming_sessions=swimming,
    )
