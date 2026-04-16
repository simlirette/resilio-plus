from __future__ import annotations

from datetime import date, timedelta

from ..schemas.athlete import AthleteProfile, Sport
from ..schemas.connector import StravaActivity
from ..schemas.fatigue import FatigueScore
from ..schemas.plan import WorkoutSlot

_COLD_START_CSS = 105.0  # seconds per 100m = 1:45/100m


def estimate_css(athlete: AthleteProfile) -> float:
    """Return stored CSS (s/100m) or cold-start default."""
    return athlete.css_per_100m if athlete.css_per_100m else _COLD_START_CSS


def compute_swimming_fatigue(swims: list[StravaActivity]) -> FatigueScore:
    """Compute FatigueScore from a pre-filtered list of Swim activities."""
    if not swims:
        return FatigueScore(
            local_muscular=0.0,
            cns_load=0.0,
            metabolic_cost=0.0,
            recovery_hours=0.0,
            affected_muscles=[],
        )

    total_duration_h = sum(s.duration_seconds for s in swims) / 3600
    total_distance_m = sum((s.distance_meters or 0) for s in swims)

    # Swimming: moderate local (shoulders/lats), low CNS, moderate metabolic
    local = min(100.0, total_distance_m / 100 * 1.5)
    cns = min(20.0, total_duration_h * 2.0)
    metabolic = min(100.0, total_duration_h * 12.0)
    recovery_h = 10.0 + total_duration_h * 1.5

    return FatigueScore(
        local_muscular=round(local, 1),
        cns_load=round(cns, 1),
        metabolic_cost=round(metabolic, 1),
        recovery_hours=round(recovery_h, 1),
        affected_muscles=["shoulders", "lats", "triceps"],
    )


_PHASE_SESSION_MAP: dict[str, list[str]] = {
    "general_prep": ["Z1_technique", "Z2_endurance_swim"],
    "specific_prep": ["Z2_endurance_swim", "Z3_threshold_set"],
    "pre_competition": ["Z3_threshold_set", "Z2_endurance_swim"],
    "competition": ["Z2_endurance_swim"],
    "transition": ["Z1_technique"],
}

_SESSION_DURATIONS: dict[str, tuple[int, float]] = {
    "Z1_technique": (45, 0.6),
    "Z2_endurance_swim": (60, 0.8),
    "Z3_threshold_set": (50, 0.7),
}

_INTENSITY: dict[str, float] = {
    "Z1_technique": 0.8,
    "Z2_endurance_swim": 1.0,
    "Z3_threshold_set": 1.5,
}


def generate_swimming_sessions(
    css_per_100m: float,
    week_number: int,
    phase: str,
    available_days: list[int],
    hours_budget: float,
    volume_modifier: float,
    week_start: date,
) -> list[WorkoutSlot]:
    """Generate swimming WorkoutSlots for the week."""
    if hours_budget <= 0 or not available_days:
        return []

    session_types = _PHASE_SESSION_MAP.get(phase, _PHASE_SESSION_MAP["general_prep"])
    effective_budget = hours_budget * volume_modifier

    sessions: list[WorkoutSlot] = []
    used_days: set[int] = set()
    budget_remaining = effective_budget

    fatigue_stub = FatigueScore(
        local_muscular=12.0,
        cns_load=4.0,
        metabolic_cost=18.0,
        recovery_hours=10.0,
        affected_muscles=["shoulders", "lats"],
    )

    css_pace_str = f"{int(css_per_100m // 60)}:{int(css_per_100m % 60):02d}/100m"

    for session_type in session_types:
        base_min, min_budget = _SESSION_DURATIONS[session_type]
        if budget_remaining < min_budget:
            break

        day_offset = None
        for d in available_days:
            if d not in used_days:
                day_offset = d
                break
        if day_offset is None:
            break

        duration_min = min(base_min, int(budget_remaining * 60))
        duration_min = max(20, duration_min)

        sessions.append(
            WorkoutSlot(
                date=week_start + timedelta(days=day_offset),
                sport=Sport.SWIMMING,
                workout_type=session_type,
                duration_min=int(duration_min * volume_modifier),
                fatigue_score=fatigue_stub,
                notes=f"CSS: {css_pace_str} | {session_type.replace('_', ' ')}",
            )
        )
        used_days.add(day_offset)
        budget_remaining -= duration_min / 60

    return sessions
