"""Muscle Strain Index — per-muscle-group fatigue score (0–100).

Formula:
  - Cardio (Strava): base_au = (duration_h) × IF² × 100
    where IF = perceived_exertion / 10 (TSS-equivalent, matches methodology.md)
  - Lifting (Hevy): set_load = max(weight_kg, 1.0) × reps × (rpe / 10)
    (weight_kg is floored at 1.0 to handle bodyweight exercises)
  - Each session's load is distributed to muscle groups via recruitment maps.
  - Score per muscle = min(100, EWMA_7d / EWMA_28d × 100)
    When EWMA_28d == 0 (no history), score = 0.

Reference: Impellizzeri et al. (2004) sRPE; Coggan TSS model; ACWR methodology.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

from ..models.athlete_state import MuscleStrainScore
from ..schemas.connector import HevySet, HevyWorkout, StravaActivity

# ---------------------------------------------------------------------------
# Muscle groups
# ---------------------------------------------------------------------------

MUSCLES: list[str] = [
    "quads",
    "posterior_chain",
    "glutes",
    "calves",
    "chest",
    "upper_pull",
    "shoulders",
    "triceps",
    "biceps",
    "core",
]

# ---------------------------------------------------------------------------
# EWMA constants (matches acwr.py convention)
# ---------------------------------------------------------------------------

_LAMBDA_7D = 2 / (7 + 1)  # 0.25  — acute window
_LAMBDA_28D = 2 / (28 + 1)  # ≈ 0.069 — chronic window

# ---------------------------------------------------------------------------
# Cardio recruitment map — sport_type → muscle recruitment coefficient
# ---------------------------------------------------------------------------

SPORT_MUSCLE_MAP: dict[str, dict[str, float]] = {
    "Run": {
        "quads": 0.9,
        "posterior_chain": 0.7,
        "glutes": 0.6,
        "calves": 0.8,
        "chest": 0.0,
        "upper_pull": 0.0,
        "shoulders": 0.0,
        "triceps": 0.0,
        "biceps": 0.0,
        "core": 0.3,
    },
    "TrailRun": {
        "quads": 0.9,
        "posterior_chain": 0.8,
        "glutes": 0.7,
        "calves": 0.9,
        "chest": 0.0,
        "upper_pull": 0.0,
        "shoulders": 0.0,
        "triceps": 0.0,
        "biceps": 0.0,
        "core": 0.4,
    },
    "Ride": {
        "quads": 0.8,
        "posterior_chain": 0.4,
        "glutes": 0.5,
        "calves": 0.5,
        "chest": 0.0,
        "upper_pull": 0.1,
        "shoulders": 0.1,
        "triceps": 0.0,
        "biceps": 0.0,
        "core": 0.2,
    },
    "Swim": {
        "quads": 0.1,
        "posterior_chain": 0.2,
        "glutes": 0.1,
        "calves": 0.0,
        "chest": 0.6,
        "upper_pull": 0.9,
        "shoulders": 0.8,
        "triceps": 0.5,
        "biceps": 0.6,
        "core": 0.5,
    },
    # Fallback for unknown sport types
    "__unknown__": {
        "quads": 0.3,
        "posterior_chain": 0.2,
        "glutes": 0.2,
        "calves": 0.1,
        "chest": 0.1,
        "upper_pull": 0.1,
        "shoulders": 0.1,
        "triceps": 0.1,
        "biceps": 0.1,
        "core": 0.3,
    },
}

# ---------------------------------------------------------------------------
# Lifting recruitment map — exercise name → muscle recruitment coefficient
# ---------------------------------------------------------------------------

EXERCISE_MUSCLE_MAP: dict[str, dict[str, float]] = {
    "Squat": {
        "quads": 1.0,
        "glutes": 0.9,
        "posterior_chain": 0.5,
        "core": 0.3,
    },
    "Deadlift": {
        "posterior_chain": 1.0,
        "glutes": 0.9,
        "quads": 0.5,
        "core": 0.4,
    },
    "Romanian Deadlift": {
        "posterior_chain": 1.0,
        "glutes": 0.8,
        "core": 0.3,
    },
    "Bench Press": {
        "chest": 1.0,
        "triceps": 0.7,
        "shoulders": 0.5,
    },
    "Incline Bench Press": {
        "chest": 0.9,
        "shoulders": 0.6,
        "triceps": 0.5,
    },
    "Pull-up": {
        "upper_pull": 1.0,
        "biceps": 0.7,
        "shoulders": 0.4,
    },
    "Lat Pulldown": {
        "upper_pull": 1.0,
        "biceps": 0.7,
        "shoulders": 0.3,
    },
    "Barbell Row": {
        "upper_pull": 1.0,
        "biceps": 0.6,
        "posterior_chain": 0.4,
    },
    "Overhead Press": {
        "shoulders": 1.0,
        "triceps": 0.6,
        "upper_pull": 0.3,
    },
    "Leg Press": {
        "quads": 1.0,
        "glutes": 0.6,
        "calves": 0.3,
    },
    "Leg Curl": {
        "posterior_chain": 1.0,
        "glutes": 0.3,
    },
    "Leg Extension": {
        "quads": 1.0,
    },
    "Calf Raise": {
        "calves": 1.0,
    },
    "Dumbbell Curl": {
        "biceps": 1.0,
    },
    "Barbell Curl": {
        "biceps": 1.0,
        "shoulders": 0.2,
    },
    "Tricep Pushdown": {
        "triceps": 1.0,
    },
    "Skull Crusher": {
        "triceps": 1.0,
    },
    "Dips": {
        "chest": 0.7,
        "triceps": 0.8,
        "shoulders": 0.5,
    },
    "Face Pull": {
        "shoulders": 0.8,
        "upper_pull": 0.6,
        "biceps": 0.3,
    },
    "Lateral Raise": {
        "shoulders": 1.0,
    },
    "Hip Thrust": {
        "glutes": 1.0,
        "posterior_chain": 0.6,
        "quads": 0.3,
    },
    "Plank": {
        "core": 1.0,
        "shoulders": 0.2,
    },
    "Ab Rollout": {
        "core": 1.0,
        "shoulders": 0.3,
    },
    "Cable Crunch": {
        "core": 1.0,
    },
    "Lunge": {
        "quads": 0.9,
        "glutes": 0.8,
        "calves": 0.3,
        "core": 0.3,
    },
    "Step-up": {
        "quads": 0.8,
        "glutes": 0.8,
        "calves": 0.4,
    },
    "Good Morning": {
        "posterior_chain": 1.0,
        "glutes": 0.5,
        "core": 0.4,
    },
    "Push-up": {
        "chest": 0.9,
        "triceps": 0.7,
        "shoulders": 0.5,
        "core": 0.3,
    },
    "Seated Row": {
        "upper_pull": 1.0,
        "biceps": 0.5,
        "posterior_chain": 0.3,
    },
    # Fallback for unmapped exercises
    "__unknown__": {
        "core": 0.3,
    },
}


# ---------------------------------------------------------------------------
# Exercise name resolution
# ---------------------------------------------------------------------------
#
# EXERCISE_MUSCLE_MAP is keyed on clean canonical names. Hevy exports the
# equipment in the name itself -- "Incline Bench Press (Dumbbell)", "Pull Up
# (Weighted)" -- so an exact lookup misses almost everything a real account
# contains and silently charges `__unknown__` (core only). Resolution below is
# additive: exact keys keep resolving to themselves, byte for byte.

_EQUIPMENT_QUALIFIER = re.compile(r"\s*\([^)]*\)")
_SEPARATORS = re.compile(r"[\s\-_]+")


def _normalise(name: str) -> str:
    """Drop equipment qualifiers, unify separators and case."""
    return _SEPARATORS.sub(" ", _EQUIPMENT_QUALIFIER.sub(" ", name or "")).strip().lower()


_CANONICAL_BY_NORMAL: dict[str, str] = {
    _normalise(key): key for key in EXERCISE_MUSCLE_MAP if key != "__unknown__"
}

# Names Hevy uses that do not reduce to a canonical key. Mapped to the closest
# canonical movement by recruitment pattern, not by name.
_ALIASES: dict[str, str] = {
    "shoulder press": "Overhead Press",
    "military press": "Overhead Press",
    "arnold press": "Overhead Press",
    "upright row": "Lateral Raise",
    "rear delt reverse fly": "Face Pull",
    "reverse fly": "Face Pull",
    "shrug": "Face Pull",
    "triceps extension": "Skull Crusher",
    "tricep extension": "Skull Crusher",
    "overhead press extension": "Skull Crusher",
    "triceps pushdown": "Tricep Pushdown",
    "triceps dip": "Dips",
    "dip": "Dips",
    "preacher curl": "Barbell Curl",
    "hammer curl": "Dumbbell Curl",
    "bicep curl": "Dumbbell Curl",
    "biceps curl": "Dumbbell Curl",
    "concentration curl": "Dumbbell Curl",
    "chest press": "Bench Press",
    "chest fly": "Bench Press",
    "cable fly": "Bench Press",
    "pec deck": "Bench Press",
    "t bar row": "Barbell Row",
    "bent over row": "Barbell Row",
    "chin up": "Pull-up",
    "front squat": "Squat",
    "goblet squat": "Squat",
    "hack squat": "Squat",
    "bulgarian split squat": "Lunge",
    "split squat": "Lunge",
    "calf press": "Calf Raise",
    "crunch": "Cable Crunch",
    "sit up": "Cable Crunch",
    "leg raise": "Cable Crunch",
    "russian twist": "Cable Crunch",
    "hyperextension": "Good Morning",
    "back extension": "Good Morning",
}


def _longest_containing(normal: str, candidates: dict[str, str]) -> str | None:
    """Return the canonical name whose key appears in `normal`, longest first.

    "Seated Lateral Raise" contains "lateral raise"; "Overhead Tricep
    Extension" contains "tricep extension". Longest wins so "incline bench
    press" is not stolen by "bench press".
    """
    best: str | None = None
    best_len = 0
    for key, canonical in candidates.items():
        if len(key) > best_len and re.search(rf"(?:^|\s){re.escape(key)}(?:\s|$)", normal):
            best, best_len = canonical, len(key)
    return best


def resolve_exercise(name: str) -> dict[str, float]:
    """Return the muscle recruitment map for an exercise name.

    Falls back to ``EXERCISE_MUSCLE_MAP["__unknown__"]`` rather than raising --
    an unrecognised movement should cost precision, not a planning run.
    """
    exact = EXERCISE_MUSCLE_MAP.get(name)
    if exact is not None:
        return exact

    normal = _normalise(name)
    if not normal:
        return EXERCISE_MUSCLE_MAP["__unknown__"]

    canonical = _CANONICAL_BY_NORMAL.get(normal) or _ALIASES.get(normal)
    if canonical is None:
        canonical = _longest_containing(normal, _CANONICAL_BY_NORMAL) or _longest_containing(
            normal, _ALIASES
        )
    if canonical is None:
        return EXERCISE_MUSCLE_MAP["__unknown__"]
    return EXERCISE_MUSCLE_MAP[canonical]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _ewma(loads: list[float], lam: float) -> float:
    """EWMA over loads (oldest-first). Seed = first element."""
    if not loads:
        return 0.0
    result = loads[0]
    for v in loads[1:]:
        result = v * lam + result * (1 - lam)
    return result


def _rpe_fallback(sets: list["HevySet"], exercise_default: float = 7.0) -> list[float]:
    """Return RPE for each set using cascade: set RPE → exercise avg → 7.0."""
    available = [s.rpe for s in sets if s.rpe is not None]
    exercise_avg = sum(available) / len(available) if available else exercise_default
    return [s.rpe if s.rpe is not None else exercise_avg for s in sets]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_muscle_strain(
    strava_activities: list[StravaActivity],
    hevy_workouts: list[HevyWorkout],
    reference_date: date | None = None,
) -> MuscleStrainScore:
    """Compute per-muscle strain score (0–100) from 28-day activity history.

    Args:
        strava_activities: All available Strava activities (filtered to 28d window).
        hevy_workouts: All available Hevy workouts (filtered to 28d window).
        reference_date: Date to treat as "today". Defaults to date.today().

    Returns:
        MuscleStrainScore with scores 0–100 per muscle group.
        All zeros if no data or insufficient history (EWMA_28d == 0).
    """
    if reference_date is None:
        reference_date = date.today()

    start_date = reference_date - timedelta(days=27)

    # Build 28-day daily muscle load buckets (index 0 = oldest day)
    daily: dict[str, list[float]] = {m: [0.0] * 28 for m in MUSCLES}

    # --- Strava activities ---
    for activity in strava_activities:
        delta = (activity.date - start_date).days
        if not (0 <= delta < 28):
            continue
        rpe: float = float(activity.perceived_exertion or 7)
        duration_h = activity.duration_seconds / 3600.0
        intensity_factor = rpe / 10.0
        base_au = duration_h * intensity_factor**2 * 100.0
        sport_map = SPORT_MUSCLE_MAP.get(activity.sport_type, SPORT_MUSCLE_MAP["__unknown__"])
        for m in MUSCLES:
            daily[m][delta] += base_au * sport_map.get(m, 0.0)

    # --- Hevy workouts ---
    for workout in hevy_workouts:
        delta = (workout.date - start_date).days
        if not (0 <= delta < 28):
            continue
        for exercise in workout.exercises:
            ex_map = resolve_exercise(exercise.name)
            rpes = _rpe_fallback(exercise.sets)
            for s, rpe in zip(exercise.sets, rpes):
                if s.reps is None:
                    continue
                rpe_coeff = rpe / 10.0
                # Floor weight_kg at 1.0 to handle bodyweight exercises (weight_kg == 0)
                effective_weight = max(s.weight_kg if s.weight_kg is not None else 1.0, 1.0)
                set_load = effective_weight * s.reps * rpe_coeff
                for m in MUSCLES:
                    daily[m][delta] += set_load * ex_map.get(m, 0.0)

    # --- Normalise to 0–100 ---
    scores: dict[str, float] = {}
    for m in MUSCLES:
        # Both EWMAs run over the full 28-day series; λ controls the effective window.
        acute = _ewma(daily[m], _LAMBDA_7D)  # λ=0.25 weights recent days heavily
        chronic = _ewma(daily[m], _LAMBDA_28D)  # λ≈0.069 weights load over ~28 days
        if chronic <= 0.0:
            scores[m] = 0.0
        else:
            scores[m] = min(100.0, round((acute / chronic) * 100.0, 1))

    return MuscleStrainScore(
        quads=scores["quads"],
        posterior_chain=scores["posterior_chain"],
        glutes=scores["glutes"],
        calves=scores["calves"],
        chest=scores["chest"],
        upper_pull=scores["upper_pull"],
        shoulders=scores["shoulders"],
        triceps=scores["triceps"],
        biceps=scores["biceps"],
        core=scores["core"],
        computed_at=datetime.now(tz=timezone.utc),
    )
