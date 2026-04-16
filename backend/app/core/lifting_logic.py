from __future__ import annotations
from typing import Any

import json
from datetime import date, timedelta
from enum import Enum
from pathlib import Path

from ..schemas.athlete import Sport
from ..schemas.connector import HevyWorkout
from ..schemas.fatigue import FatigueScore
from ..schemas.plan import WorkoutSlot

# Load data files at module import time
_REPO_ROOT = Path(__file__).resolve().parents[3]
_EXERCISE_DB: dict[str, Any] = json.loads(
    (_REPO_ROOT / ".bmad-core" / "data" / "exercise-database.json").read_text()
)
_VOLUME_LANDMARKS: dict[str, Any] = json.loads(
    (_REPO_ROOT / ".bmad-core" / "data" / "volume-landmarks.json").read_text()
)

_TIER3_EXERCISES: set[str] = {
    e.lower() for e in _EXERCISE_DB.get("tier_3_low_sfr_high_cns_use_sparingly", [])
}

# Keyword -> muscle group lookup (hand-authored)
_EXERCISE_MUSCLE_MAP: dict[str, list[str]] = {
    "squat": ["quads", "glutes"],
    "deadlift": ["hamstrings", "glutes", "back"],
    "bench": ["chest", "triceps"],
    "press": ["chest", "triceps", "shoulders"],
    "row": ["back", "biceps"],
    "pull": ["back", "biceps"],
    "curl": ["biceps"],
    "extension": ["triceps", "quads"],
    "lunge": ["quads", "glutes"],
    "calf": ["calves"],
    "lateral": ["shoulders"],
    "fly": ["chest"],
    "dip": ["triceps", "chest"],
}

# Lower body keywords for recovery classification
_LOWER_KEYWORDS = (
    "squat",
    "deadlift",
    "lunge",
    "leg press",
    "hack squat",
    "split squat",
    "romanian",
    "rdl",
)


class StrengthLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


def estimate_strength_level(workouts: list[HevyWorkout]) -> StrengthLevel:
    """Estimate strength level from Hevy workout history.

    sessions_per_week >= 3 AND mean_rpe > 8 -> ADVANCED
    sessions_per_week >= 2 AND mean_rpe in [6, 8] -> INTERMEDIATE
    else -> BEGINNER
    """
    if not workouts:
        return StrengthLevel.BEGINNER

    sessions_per_week = len(workouts) / 4.3

    all_rpes = [s.rpe for w in workouts for ex in w.exercises for s in ex.sets if s.rpe is not None]
    mean_rpe = sum(all_rpes) / len(all_rpes) if all_rpes else 0.0

    if sessions_per_week >= 3 and mean_rpe > 8:
        return StrengthLevel.ADVANCED
    if sessions_per_week >= 2 and 6 <= mean_rpe <= 8:
        return StrengthLevel.INTERMEDIATE
    return StrengthLevel.BEGINNER


def compute_lifting_fatigue(workouts: list[HevyWorkout]) -> FatigueScore:
    """Compute FatigueScore from a pre-filtered list of Hevy workouts.

    Caller must pre-filter to the relevant time window.
    """
    if not workouts:
        return FatigueScore(
            local_muscular=0.0,
            cns_load=0.0,
            metabolic_cost=0.0,
            recovery_hours=0.0,
            affected_muscles=[],
        )

    total_sets = sum(len(ex.sets) for w in workouts for ex in w.exercises)

    # Count workouts containing any Tier 3 exercise
    tier3_sessions = sum(
        1 for w in workouts if any(ex.name.lower() in _TIER3_EXERCISES for ex in w.exercises)
    )

    all_reps = [
        s.reps for w in workouts for ex in w.exercises for s in ex.sets if s.reps is not None
    ]
    total_reps_mean = sum(all_reps) / len(all_reps) if all_reps else 0.0

    # Recovery: lower body -> 48h; upper only -> 24h; light -> 12h
    all_names = [ex.name.lower() for w in workouts for ex in w.exercises]
    has_lower = any(kw in name for name in all_names for kw in _LOWER_KEYWORDS)
    if has_lower:
        recovery = 48.0
    elif all_names:
        recovery = 24.0
    else:
        recovery = 12.0

    # Affected muscles via keyword lookup
    muscles: list[str] = []
    seen: set[str] = set()
    for name in all_names:
        for kw, muscle_list in _EXERCISE_MUSCLE_MAP.items():
            if kw in name:
                for m in muscle_list:
                    if m not in seen:
                        seen.add(m)
                        muscles.append(m)

    return FatigueScore(
        local_muscular=min(100.0, float(total_sets) * 3.0),
        cns_load=min(100.0, float(tier3_sessions) * 25.0),
        metabolic_cost=min(100.0, float(total_sets) * total_reps_mean / 50.0),
        recovery_hours=recovery,
        affected_muscles=muscles,
    )


def generate_lifting_sessions(
    strength_level: StrengthLevel,
    phase: str,  # MacroPhase value string e.g. "general_prep"
    week_number: int,
    weeks_remaining: int,
    available_days: list[int],  # 0=Mon ... 6=Sun
    hours_budget: float,
    volume_modifier: float,
    running_load_ratio: float,
    week_start: date,  # Monday of the planning week
) -> list[WorkoutSlot]:
    """Generate weekly lifting sessions as WorkoutSlots.

    DUP rotation: week_number % 3 -> 0=hypertrophy, 1=strength, 2=endurance.
    Hybrid reduction: running_load_ratio > 0.5 -> lower body sessions shorter.
    Wave loading: week_number % 4 == 0 -> 60% duration (deload, checked first).
    Arms hypertrophy: included when dup==0 AND len(available_days) >= 4.
    """
    if not available_days:
        return []

    # Exercise tier note based on phase
    _TIER_NOTE: dict[str, str] = {
        "general_prep": "Tier 1",
        "specific_prep": "Tier 1-2",
        "pre_competition": "Tier 1-2",
        "competition": "Tier 1-2",
        "transition": "Tier 2-3",
    }
    tier_note = _TIER_NOTE.get(phase, "Tier 1")

    # Wave loading multiplier (deload check first), scaled by volume_modifier
    dur_mult = volume_modifier * (0.6 if week_number % 4 == 0 else 1.0)

    # Hybrid reduction for lower body (quads hybrid_reduction from volume-landmarks.json)
    lower_base = 60
    if running_load_ratio > 0.5:
        quads_reduction = _VOLUME_LANDMARKS.get("quads", {}).get("hybrid_reduction", 0.4)
        lower_base = int(60 * (1.0 - quads_reduction))

    lower_dur = max(20, int(lower_base * dur_mult))

    dup = week_number % 3
    # (workout_type, duration_min, notes)
    raw: list[tuple[str, int, str]] = []

    if dup == 0:  # Hypertrophy priority
        raw.append(("upper_hypertrophy", max(20, int(60 * dur_mult)), "chest, back, shoulders"))
        raw.append(("lower_strength", lower_dur, "quads, hamstrings, glutes"))
        if len(available_days) >= 4:
            raw.append(("arms_hypertrophy", max(20, int(60 * dur_mult)), "biceps, triceps"))
    elif dup == 1:  # Strength priority
        raw.append(
            (
                "upper_strength",
                max(20, int(75 * dur_mult)),
                f"{tier_note} | chest, back, shoulders, triceps, biceps",
            )
        )
        raw.append(("lower_strength", lower_dur, "quads, hamstrings"))
    else:  # Endurance priority (dup == 2)
        raw.append(("full_body_endurance", max(20, int(45 * dur_mult)), "core, quads, back"))

    # Cap to available days
    slots = raw[: len(available_days)]

    _Z = FatigueScore(
        local_muscular=0.0,
        cns_load=0.0,
        metabolic_cost=0.0,
        recovery_hours=0.0,
        affected_muscles=[],
    )

    return [
        WorkoutSlot(
            date=week_start + timedelta(days=available_days[i]),
            sport=Sport.LIFTING,
            workout_type=wtype,
            duration_min=dur,
            fatigue_score=_Z,
            notes=notes,
        )
        for i, (wtype, dur, notes) in enumerate(slots)
    ]
