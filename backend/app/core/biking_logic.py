from __future__ import annotations

from datetime import date, timedelta

from ..schemas.athlete import AthleteProfile, Sport
from ..schemas.connector import StravaActivity
from ..schemas.fatigue import FatigueScore
from ..schemas.plan import WorkoutSlot

_COLD_START_FTP = 200  # watts


def estimate_ftp(athlete: AthleteProfile) -> int:
    """Return stored FTP or cold-start default."""
    return athlete.ftp_watts if athlete.ftp_watts else _COLD_START_FTP


def compute_biking_fatigue(rides: list[StravaActivity]) -> FatigueScore:
    """Compute FatigueScore from a pre-filtered list of Ride activities."""
    if not rides:
        return FatigueScore(
            local_muscular=0.0,
            cns_load=0.0,
            metabolic_cost=0.0,
            recovery_hours=0.0,
            affected_muscles=[],
        )

    total_duration_h = sum(r.duration_seconds for r in rides) / 3600
    total_distance_km = sum((r.distance_meters or 0) for r in rides) / 1000

    # Cycling: low CNS load, moderate local (quads/glutes), moderate metabolic
    local = min(100.0, total_duration_h * 8.0)
    cns = min(30.0, total_duration_h * 3.0)
    metabolic = min(100.0, total_distance_km * 0.8)
    recovery_h = 12.0 + total_duration_h * 2.0

    return FatigueScore(
        local_muscular=round(local, 1),
        cns_load=round(cns, 1),
        metabolic_cost=round(metabolic, 1),
        recovery_hours=round(recovery_h, 1),
        affected_muscles=["quads", "glutes", "calves"],
    )


# Phase → session type preference
_PHASE_SESSION_MAP: dict[str, list[str]] = {
    "general_prep": ["Z2_endurance_ride", "Z2_endurance_ride", "Z3_tempo_ride"],
    "specific_prep": ["Z2_endurance_ride", "Z3_tempo_ride", "Z4_threshold_intervals"],
    "pre_competition": ["Z3_tempo_ride", "Z4_threshold_intervals", "Z4_threshold_intervals"],
    "competition": ["Z2_endurance_ride", "Z3_tempo_ride"],
    "transition": ["Z2_endurance_ride"],
}

# Session type → (base_duration_min, min_hours_budget_to_add)
_SESSION_DURATIONS: dict[str, tuple[int, float]] = {
    "Z2_endurance_ride": (75, 1.0),
    "Z3_tempo_ride": (60, 0.8),
    "Z4_threshold_intervals": (50, 0.7),
}


def generate_biking_sessions(
    ftp: int,
    week_number: int,
    phase: str,
    available_days: list[int],
    hours_budget: float,
    volume_modifier: float,
    week_start: date,
) -> list[WorkoutSlot]:
    """Generate biking WorkoutSlots for the week."""
    if hours_budget <= 0 or not available_days:
        return []

    session_types = _PHASE_SESSION_MAP.get(phase, _PHASE_SESSION_MAP["general_prep"])
    effective_budget = hours_budget * volume_modifier

    sessions: list[WorkoutSlot] = []
    used_days: set[int] = set()
    budget_remaining = effective_budget

    fatigue_stub = FatigueScore(
        local_muscular=15.0,
        cns_load=5.0,
        metabolic_cost=20.0,
        recovery_hours=12.0,
        affected_muscles=["quads", "glutes"],
    )

    for session_type in session_types:
        base_min, min_budget = _SESSION_DURATIONS[session_type]
        if budget_remaining < min_budget:
            break

        # Find next available day not yet used
        day_offset = None
        for d in available_days:
            if d not in used_days:
                day_offset = d
                break
        if day_offset is None:
            break

        # Scale duration to budget (cap at base_duration)
        duration_min = min(base_min, int(budget_remaining * 60))
        duration_min = max(20, duration_min)  # floor 20min

        session_date = week_start + timedelta(days=day_offset)
        sessions.append(
            WorkoutSlot(
                date=session_date,
                sport=Sport.BIKING,
                workout_type=session_type,
                duration_min=int(duration_min * volume_modifier),
                fatigue_score=fatigue_stub,
                notes=f"FTP: {ftp}W | {session_type.replace('_', ' ')}",
            )
        )
        used_days.add(day_offset)
        budget_remaining -= duration_min / 60

    return sessions
