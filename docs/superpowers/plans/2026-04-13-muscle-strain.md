# Muscle Strain Index Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a per-muscle-group strain index (10 muscles, score 0–100) to `AthleteMetrics` in `AthleteState`, computed from Strava and Hevy data via a new `backend/app/core/strain.py` module.

**Architecture:** `MuscleStrainScore` Pydantic model added to `athlete_state.py`; `core/strain.py` computes EWMA 7d/28d per muscle group using TSS-equivalent load (cardio) and RPE-weighted volume (lifting); score = EWMA_7d / EWMA_28d × 100, capped at 100.

**Tech Stack:** Python 3.13, Pydantic v2, pytest — no new dependencies.

---

## File Map

| File | Action |
|---|---|
| `backend/app/models/athlete_state.py` | Modify — add `MuscleStrainScore`, add `muscle_strain` field to `AthleteMetrics` |
| `backend/app/core/strain.py` | Create — SPORT_MUSCLE_MAP, EXERCISE_MUSCLE_MAP, `compute_muscle_strain()` |
| `tests/test_models/test_muscle_strain.py` | Create — Pydantic validation tests |
| `tests/test_core/__init__.py` | Create — empty package marker |
| `tests/test_core/test_strain.py` | Create — compute_muscle_strain() with synthetic data |
| `tests/test_models/conftest.py` | Modify — add `muscle_strain` to `full_state` fixture |
| `docs/backend/STRAIN-DEFINITION.md` | Create — architectural decision document |

---

### Task 1: MuscleStrainScore model

**Files:**
- Modify: `backend/app/models/athlete_state.py:192–206`
- Create: `tests/test_models/test_muscle_strain.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_models/test_muscle_strain.py`:

```python
"""Tests for MuscleStrainScore Pydantic model."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError


def test_muscle_strain_score_import():
    from app.models.athlete_state import MuscleStrainScore  # noqa: F401


def test_muscle_strain_score_default_zeros():
    from app.models.athlete_state import MuscleStrainScore
    s = MuscleStrainScore(computed_at=datetime(2026, 4, 13, tzinfo=timezone.utc))
    assert s.quads == 0.0
    assert s.posterior_chain == 0.0
    assert s.glutes == 0.0
    assert s.calves == 0.0
    assert s.chest == 0.0
    assert s.upper_pull == 0.0
    assert s.shoulders == 0.0
    assert s.triceps == 0.0
    assert s.biceps == 0.0
    assert s.core == 0.0


def test_muscle_strain_score_valid_values():
    from app.models.athlete_state import MuscleStrainScore
    s = MuscleStrainScore(
        quads=75.0,
        posterior_chain=60.0,
        glutes=55.0,
        calves=30.0,
        chest=20.0,
        upper_pull=80.0,
        shoulders=45.0,
        triceps=40.0,
        biceps=35.0,
        core=50.0,
        computed_at=datetime(2026, 4, 13, tzinfo=timezone.utc),
    )
    assert s.quads == 75.0
    assert s.upper_pull == 80.0


def test_muscle_strain_score_above_100_raises():
    from app.models.athlete_state import MuscleStrainScore
    with pytest.raises(ValidationError):
        MuscleStrainScore(
            quads=101.0,
            computed_at=datetime(2026, 4, 13, tzinfo=timezone.utc),
        )


def test_muscle_strain_score_below_zero_raises():
    from app.models.athlete_state import MuscleStrainScore
    with pytest.raises(ValidationError):
        MuscleStrainScore(
            quads=-1.0,
            computed_at=datetime(2026, 4, 13, tzinfo=timezone.utc),
        )


def test_muscle_strain_score_computed_at_is_datetime():
    from app.models.athlete_state import MuscleStrainScore
    s = MuscleStrainScore(computed_at=datetime(2026, 4, 13, 8, 0, tzinfo=timezone.utc))
    assert isinstance(s.computed_at, datetime)


def test_athlete_metrics_muscle_strain_defaults_none():
    from datetime import date
    from app.models.athlete_state import AthleteMetrics
    m = AthleteMetrics(date=date(2026, 4, 13))
    assert m.muscle_strain is None


def test_athlete_metrics_accepts_muscle_strain():
    from datetime import date
    from app.models.athlete_state import AthleteMetrics, MuscleStrainScore
    strain = MuscleStrainScore(
        quads=50.0,
        computed_at=datetime(2026, 4, 13, tzinfo=timezone.utc),
    )
    m = AthleteMetrics(date=date(2026, 4, 13), muscle_strain=strain)
    assert m.muscle_strain is not None
    assert m.muscle_strain.quads == 50.0
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/test_models/test_muscle_strain.py -v 2>&1 | head -15
```

Expected: `ImportError` — `MuscleStrainScore` does not exist yet.

- [ ] **Step 3: Backup athlete_state.py**

```bash
cp backend/app/models/athlete_state.py backend/app/models/athlete_state.py.backup2
```

- [ ] **Step 4: Add MuscleStrainScore to athlete_state.py**

In `backend/app/models/athlete_state.py`, insert the new class **before** `class AthleteMetrics` (before line 187). Find the `# ---------------------------------------------------------------------------` comment that precedes `AthleteMetrics` and insert before it:

```python
# ---------------------------------------------------------------------------
# MuscleStrainScore  (index de fatigue musculaire par groupe)
# ---------------------------------------------------------------------------


class MuscleStrainScore(BaseModel):
    """Strain index 0–100 per muscle group.

    Computed as EWMA_7d / EWMA_28d × 100 (capped at 100).
    0 = no recent load or insufficient history.
    100 = acute load equals chronic baseline (fully loaded).
    """

    quads: float = Field(default=0.0, ge=0.0, le=100.0)
    posterior_chain: float = Field(default=0.0, ge=0.0, le=100.0)
    glutes: float = Field(default=0.0, ge=0.0, le=100.0)
    calves: float = Field(default=0.0, ge=0.0, le=100.0)
    chest: float = Field(default=0.0, ge=0.0, le=100.0)
    upper_pull: float = Field(default=0.0, ge=0.0, le=100.0)
    shoulders: float = Field(default=0.0, ge=0.0, le=100.0)
    triceps: float = Field(default=0.0, ge=0.0, le=100.0)
    biceps: float = Field(default=0.0, ge=0.0, le=100.0)
    core: float = Field(default=0.0, ge=0.0, le=100.0)
    computed_at: datetime

```

- [ ] **Step 5: Add muscle_strain field to AthleteMetrics**

In `AthleteMetrics`, add after the `fatigue_score` field (after line 206):

```python
    muscle_strain: Optional[MuscleStrainScore] = None
```

The full `AthleteMetrics` class should now end with:

```python
    fatigue_score: Optional[FatigueScore] = None
    muscle_strain: Optional[MuscleStrainScore] = None
```

- [ ] **Step 6: Run tests to confirm they pass**

```bash
/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/test_models/test_muscle_strain.py -v
```

Expected: 8 tests PASS.

- [ ] **Step 7: Run full suite for regressions**

```bash
/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/ -q 2>&1 | tail -5
```

Expected: ≥2001 passed, 0 failed.

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/athlete_state.py tests/test_models/test_muscle_strain.py
git commit -m "feat(models): add MuscleStrainScore and muscle_strain field to AthleteMetrics"
```

---

### Task 2: Core strain module

**Files:**
- Create: `tests/test_core/__init__.py`
- Create: `tests/test_core/test_strain.py`
- Create: `backend/app/core/strain.py`

- [ ] **Step 1: Create test package**

```bash
touch tests/test_core/__init__.py
```

- [ ] **Step 2: Write failing tests**

Create `tests/test_core/test_strain.py`:

```python
"""Tests for compute_muscle_strain() — synthetic data, no network.

Each test verifies a specific aspect of the formula using minimal data:
  - One workout/activity in the last 7 days (acute window)
  - No chronic history → EWMA_28d converges to a small value
    so normalized score > 0 for the tested muscles.

The EWMA formula: if all 28 days have load=0 except the last day,
EWMA_7d > EWMA_28d, so score = min(100, EWMA_7d/EWMA_28d * 100) == 100.0.
When EWMA_28d == 0 (no history at all), score == 0.0.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest


def _make_hevy_workout(
    exercise_name: str,
    weight_kg: float,
    reps: int,
    rpe: float | None,
    workout_date: date,
) -> object:
    from app.schemas.connector import HevyExercise, HevySet, HevyWorkout
    s = HevySet(reps=reps, weight_kg=weight_kg, rpe=rpe, set_type="normal")
    ex = HevyExercise(name=exercise_name, sets=[s])
    return HevyWorkout(
        id="test-1",
        title="Test Workout",
        date=workout_date,
        duration_seconds=3600,
        exercises=[ex],
    )


def _make_strava_run(duration_seconds: int, rpe: int, run_date: date) -> object:
    from app.schemas.connector import StravaActivity
    return StravaActivity(
        id="strava-1",
        name="Morning Run",
        sport_type="Run",
        date=run_date,
        duration_seconds=duration_seconds,
        perceived_exertion=rpe,
    )


TODAY = date(2026, 4, 13)


def test_import():
    from app.core.strain import compute_muscle_strain  # noqa: F401


def test_squat_targets_quads_glutes_posterior():
    from app.core.strain import compute_muscle_strain
    workout = _make_hevy_workout("Squat", weight_kg=100.0, reps=5, rpe=8.0, workout_date=TODAY)
    result = compute_muscle_strain([], [workout], reference_date=TODAY)
    assert result.quads > 0.0
    assert result.glutes > 0.0
    assert result.posterior_chain > 0.0
    assert result.chest == 0.0
    assert result.upper_pull == 0.0


def test_pullup_targets_upper_pull_biceps_not_quads():
    from app.core.strain import compute_muscle_strain
    workout = _make_hevy_workout("Pull-up", weight_kg=0.0, reps=8, rpe=7.0, workout_date=TODAY)
    result = compute_muscle_strain([], [workout], reference_date=TODAY)
    assert result.upper_pull > 0.0
    assert result.biceps > 0.0
    assert result.quads == 0.0
    assert result.calves == 0.0


def test_run_targets_quads_calves_not_chest():
    from app.core.strain import compute_muscle_strain
    activity = _make_strava_run(duration_seconds=3600, rpe=6, run_date=TODAY)
    result = compute_muscle_strain([activity], [], reference_date=TODAY)
    assert result.quads > 0.0
    assert result.calves > 0.0
    assert result.chest == 0.0
    assert result.biceps == 0.0


def test_hevy_set_without_rpe_uses_fallback():
    """Set with rpe=None falls back to RPE 7 → result non-zero."""
    from app.core.strain import compute_muscle_strain
    workout = _make_hevy_workout("Squat", weight_kg=80.0, reps=5, rpe=None, workout_date=TODAY)
    result = compute_muscle_strain([], [workout], reference_date=TODAY)
    assert result.quads > 0.0


def test_unknown_exercise_hits_core_fallback():
    from app.core.strain import compute_muscle_strain
    workout = _make_hevy_workout(
        "Some Weird Machine Exercise XYZ",
        weight_kg=50.0, reps=10, rpe=7.0,
        workout_date=TODAY,
    )
    result = compute_muscle_strain([], [workout], reference_date=TODAY)
    assert result.core > 0.0


def test_no_history_returns_all_zeros():
    """No activities → EWMA_28d == 0 → all scores == 0.0."""
    from app.core.strain import compute_muscle_strain
    result = compute_muscle_strain([], [], reference_date=TODAY)
    assert result.quads == 0.0
    assert result.posterior_chain == 0.0
    assert result.core == 0.0


def test_score_is_bounded_0_to_100():
    from app.core.strain import compute_muscle_strain
    # Many heavy squats today — score must not exceed 100
    workouts = [
        _make_hevy_workout("Squat", weight_kg=200.0, reps=10, rpe=10.0, workout_date=TODAY)
        for _ in range(10)
    ]
    result = compute_muscle_strain([], workouts, reference_date=TODAY)
    for field in ["quads", "posterior_chain", "glutes", "calves",
                  "chest", "upper_pull", "shoulders", "triceps", "biceps", "core"]:
        assert 0.0 <= getattr(result, field) <= 100.0, f"{field} out of bounds"


def test_activity_outside_28d_window_ignored():
    from app.core.strain import compute_muscle_strain
    old_date = date(2026, 3, 1)  # > 28 days before TODAY (2026-04-13)
    activity = _make_strava_run(duration_seconds=3600, rpe=8, run_date=old_date)
    result = compute_muscle_strain([activity], [], reference_date=TODAY)
    assert result.quads == 0.0


def test_result_has_computed_at():
    from app.core.strain import compute_muscle_strain
    result = compute_muscle_strain([], [], reference_date=TODAY)
    assert isinstance(result.computed_at, datetime)


def test_repeated_sessions_accumulate():
    """Two squat sessions score higher on quads than one."""
    from app.core.strain import compute_muscle_strain
    w1 = _make_hevy_workout("Squat", weight_kg=100.0, reps=5, rpe=8.0, workout_date=TODAY)
    result_one = compute_muscle_strain([], [w1], reference_date=TODAY)
    w2 = _make_hevy_workout("Squat", weight_kg=100.0, reps=5, rpe=8.0,
                             workout_date=date(2026, 4, 12))
    result_two = compute_muscle_strain([], [w1, w2], reference_date=TODAY)
    assert result_two.quads > result_one.quads
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/test_core/test_strain.py -v 2>&1 | head -15
```

Expected: `ModuleNotFoundError` — `app.core.strain` does not exist yet.

- [ ] **Step 4: Create backend/app/core/strain.py**

```python
"""Muscle Strain Index — per-muscle-group fatigue score (0–100).

Formula:
  - Cardio (Strava): base_au = (duration_h) × IF² × 100
    where IF = perceived_exertion / 10 (TSS-equivalent, matches methodology.md)
  - Lifting (Hevy): set_load = weight_kg × reps × (rpe / 10)
  - Each session's load is distributed to muscle groups via recruitment maps.
  - Score per muscle = EWMA_7d / EWMA_28d × 100, capped at 100.
    When EWMA_28d == 0 (no history), score = 0.

Reference: Impellizzeri et al. (2004) sRPE; Coggan TSS model.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from ..models.athlete_state import MuscleStrainScore
from ..schemas.connector import HevyWorkout, StravaActivity

# ---------------------------------------------------------------------------
# Muscle groups
# ---------------------------------------------------------------------------

MUSCLES: list[str] = [
    "quads", "posterior_chain", "glutes", "calves", "chest",
    "upper_pull", "shoulders", "triceps", "biceps", "core",
]

# ---------------------------------------------------------------------------
# EWMA constants (matches acwr.py convention)
# ---------------------------------------------------------------------------

_LAMBDA_7D = 2 / (7 + 1)    # 0.25  — acute window
_LAMBDA_28D = 2 / (28 + 1)  # ≈ 0.069 — chronic window

# ---------------------------------------------------------------------------
# Cardio recruitment map — sport_type → muscle recruitment coefficient
# ---------------------------------------------------------------------------

SPORT_MUSCLE_MAP: dict[str, dict[str, float]] = {
    "Run": {
        "quads": 0.9, "posterior_chain": 0.7, "glutes": 0.6, "calves": 0.8,
        "chest": 0.0, "upper_pull": 0.0, "shoulders": 0.0,
        "triceps": 0.0, "biceps": 0.0, "core": 0.3,
    },
    "TrailRun": {
        "quads": 0.9, "posterior_chain": 0.8, "glutes": 0.7, "calves": 0.9,
        "chest": 0.0, "upper_pull": 0.0, "shoulders": 0.0,
        "triceps": 0.0, "biceps": 0.0, "core": 0.4,
    },
    "Ride": {
        "quads": 0.8, "posterior_chain": 0.4, "glutes": 0.5, "calves": 0.5,
        "chest": 0.0, "upper_pull": 0.1, "shoulders": 0.1,
        "triceps": 0.0, "biceps": 0.0, "core": 0.2,
    },
    "Swim": {
        "quads": 0.1, "posterior_chain": 0.2, "glutes": 0.1, "calves": 0.0,
        "chest": 0.6, "upper_pull": 0.9, "shoulders": 0.8,
        "triceps": 0.5, "biceps": 0.6, "core": 0.5,
    },
    # Fallback for unknown sport types
    "__unknown__": {
        "quads": 0.3, "posterior_chain": 0.2, "glutes": 0.2, "calves": 0.1,
        "chest": 0.1, "upper_pull": 0.1, "shoulders": 0.1,
        "triceps": 0.1, "biceps": 0.1, "core": 0.3,
    },
}

# ---------------------------------------------------------------------------
# Lifting recruitment map — exercise name → muscle recruitment coefficient
# ---------------------------------------------------------------------------

EXERCISE_MUSCLE_MAP: dict[str, dict[str, float]] = {
    "Squat": {
        "quads": 1.0, "glutes": 0.9, "posterior_chain": 0.5, "core": 0.3,
    },
    "Deadlift": {
        "posterior_chain": 1.0, "glutes": 0.9, "quads": 0.5, "core": 0.4,
    },
    "Romanian Deadlift": {
        "posterior_chain": 1.0, "glutes": 0.8, "core": 0.3,
    },
    "Bench Press": {
        "chest": 1.0, "triceps": 0.7, "shoulders": 0.5,
    },
    "Incline Bench Press": {
        "chest": 0.9, "shoulders": 0.6, "triceps": 0.5,
    },
    "Pull-up": {
        "upper_pull": 1.0, "biceps": 0.7, "shoulders": 0.4,
    },
    "Lat Pulldown": {
        "upper_pull": 1.0, "biceps": 0.7, "shoulders": 0.3,
    },
    "Barbell Row": {
        "upper_pull": 1.0, "biceps": 0.6, "posterior_chain": 0.4,
    },
    "Overhead Press": {
        "shoulders": 1.0, "triceps": 0.6, "upper_pull": 0.3,
    },
    "Leg Press": {
        "quads": 1.0, "glutes": 0.6, "calves": 0.3,
    },
    "Leg Curl": {
        "posterior_chain": 1.0, "glutes": 0.3,
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
        "biceps": 1.0, "shoulders": 0.2,
    },
    "Tricep Pushdown": {
        "triceps": 1.0,
    },
    "Skull Crusher": {
        "triceps": 1.0,
    },
    "Dips": {
        "chest": 0.7, "triceps": 0.8, "shoulders": 0.5,
    },
    "Face Pull": {
        "shoulders": 0.8, "upper_pull": 0.6, "biceps": 0.3,
    },
    "Lateral Raise": {
        "shoulders": 1.0,
    },
    "Hip Thrust": {
        "glutes": 1.0, "posterior_chain": 0.6, "quads": 0.3,
    },
    "Plank": {
        "core": 1.0, "shoulders": 0.2,
    },
    "Ab Rollout": {
        "core": 1.0, "shoulders": 0.3,
    },
    "Cable Crunch": {
        "core": 1.0,
    },
    "Lunge": {
        "quads": 0.9, "glutes": 0.8, "calves": 0.3, "core": 0.3,
    },
    "Step-up": {
        "quads": 0.8, "glutes": 0.8, "calves": 0.4,
    },
    "Good Morning": {
        "posterior_chain": 1.0, "glutes": 0.5, "core": 0.4,
    },
    "Push-up": {
        "chest": 0.9, "triceps": 0.7, "shoulders": 0.5, "core": 0.3,
    },
    "Seated Row": {
        "upper_pull": 1.0, "biceps": 0.5, "posterior_chain": 0.3,
    },
    # Fallback for unmapped exercises
    "__unknown__": {
        "core": 0.3,
    },
}

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


def _rpe_fallback(sets: list, exercise_default: float = 7.0) -> list[float]:
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
        rpe = activity.perceived_exertion or 7
        duration_h = activity.duration_seconds / 3600.0
        intensity_factor = rpe / 10.0
        base_au = duration_h * intensity_factor ** 2 * 100.0
        sport_map = SPORT_MUSCLE_MAP.get(
            activity.sport_type, SPORT_MUSCLE_MAP["__unknown__"]
        )
        for m in MUSCLES:
            daily[m][delta] += base_au * sport_map.get(m, 0.0)

    # --- Hevy workouts ---
    for workout in hevy_workouts:
        delta = (workout.date - start_date).days
        if not (0 <= delta < 28):
            continue
        for exercise in workout.exercises:
            ex_map = EXERCISE_MUSCLE_MAP.get(
                exercise.name, EXERCISE_MUSCLE_MAP["__unknown__"]
            )
            rpes = _rpe_fallback(exercise.sets)
            for s, rpe in zip(exercise.sets, rpes):
                if s.weight_kg is None or s.reps is None:
                    continue
                rpe_coeff = rpe / 10.0
                set_load = s.weight_kg * s.reps * rpe_coeff
                for m in MUSCLES:
                    daily[m][delta] += set_load * ex_map.get(m, 0.0)

    # --- Normalise to 0–100 ---
    scores: dict[str, float] = {}
    for m in MUSCLES:
        acute = _ewma(daily[m], _LAMBDA_7D)
        chronic = _ewma(daily[m], _LAMBDA_28D)
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
```

- [ ] **Step 5: Run strain tests**

```bash
/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/test_core/test_strain.py -v
```

Expected: All tests PASS.

- [ ] **Step 6: Run full suite for regressions**

```bash
/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/ -q 2>&1 | tail -5
```

Expected: ≥2001 passed + new tests, 0 failed.

- [ ] **Step 7: Commit**

```bash
git add tests/test_core/__init__.py tests/test_core/test_strain.py backend/app/core/strain.py
git commit -m "feat(core): add compute_muscle_strain() with TSS-equivalent per-muscle load"
```

---

### Task 3: Update conftest fixture

**Files:**
- Modify: `tests/test_models/conftest.py`

- [ ] **Step 1: Add MuscleStrainScore import to conftest.py**

In `tests/test_models/conftest.py`, add `MuscleStrainScore` to the existing import from `app.models.athlete_state`:

```python
from app.models.athlete_state import (
    AllostaticComponents,
    AllostaticEntry,
    AllostaticSummary,
    AthleteMetrics,
    AthleteState,
    ConnectorSnapshot,
    DailyJournal,
    EnergyCheckIn,
    EnergySnapshot,
    HormonalProfile,
    MuscleStrainScore,
    PlanSnapshot,
    RecoveryVetoV3,
    SyncSource,
)
```

- [ ] **Step 2: Add muscle_strain to the metrics fixture**

In the `full_state()` fixture, find the `metrics = AthleteMetrics(...)` block and add `muscle_strain`:

```python
    metrics = AthleteMetrics(
        date=date(2026, 4, 13),
        hrv_rmssd=65.0,
        hrv_history_7d=[60.0, 62.0, 65.0, 58.0, 70.0, 64.0, 65.0],
        sleep_hours=7.5,
        terra_sleep_score=82.0,
        resting_hr=48.0,
        acwr=1.1,
        acwr_status="safe",
        readiness_score=87.0,
        muscle_strain=MuscleStrainScore(
            quads=72.0,
            posterior_chain=55.0,
            glutes=60.0,
            calves=45.0,
            chest=30.0,
            upper_pull=80.0,
            shoulders=40.0,
            triceps=35.0,
            biceps=50.0,
            core=65.0,
            computed_at=datetime(2026, 4, 13, 8, 0, tzinfo=timezone.utc),
        ),
    )
```

- [ ] **Step 3: Run full suite**

```bash
/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/ -q 2>&1 | tail -5
```

Expected: all passing, 0 failed.

- [ ] **Step 4: Commit**

```bash
git add tests/test_models/conftest.py
git commit -m "test(models): add MuscleStrainScore to full_state fixture"
```

---

### Task 4: Architectural decision document

**Files:**
- Create: `docs/backend/STRAIN-DEFINITION.md`

- [ ] **Step 1: Check docs/backend/ exists**

```bash
ls docs/backend/ 2>/dev/null || mkdir -p docs/backend
```

- [ ] **Step 2: Create STRAIN-DEFINITION.md**

```bash
cat > docs/backend/STRAIN-DEFINITION.md << 'EOF'
# Strain Index — Architectural Decision Record

**Date:** 2026-04-13
**Status:** Implemented
**Module:** `backend/app/core/strain.py`
**Model:** `MuscleStrainScore` in `backend/app/models/athlete_state.py`

---

## Definition

Strain is a per-muscle-group fatigue index (0–100) representing how hard a muscle
group has been worked in the past 7 days relative to its chronic baseline (28 days).

**Score interpretation:**
- 0–69%: Green — normal or underloaded
- 70–84%: Orange — elevated load, monitor
- 85–100%: Red — near peak load, recovery recommended

---

## Formula

### Score

```
score[m] = min(100, EWMA_7d[m] / EWMA_28d[m] × 100)
```

When `EWMA_28d[m] == 0` (no history): `score[m] = 0.0`

EWMA constants:
- λ_7d = 2 / (7 + 1) = 0.25
- λ_28d = 2 / (28 + 1) ≈ 0.069

### Cardio load (Strava)

```
IF = perceived_exertion / 10
base_au = (duration_seconds / 3600) × IF² × 100
muscle_au[m] = base_au × SPORT_MUSCLE_MAP[sport_type][m]
```

Consistent with TSS-equivalent formula in `methodology.md`
(Coggan/TrainingPeaks, normalized so 1h at threshold = 100 AU).

### Lifting load (Hevy)

```
set_load = weight_kg × reps × (rpe / 10)
muscle_au[m] += set_load × EXERCISE_MUSCLE_MAP[exercise][m]
```

RPE fallback cascade (when `set.rpe` is None):
1. Mean RPE of other sets in same exercise
2. RPE 7 (default for a logged session)

### Muscle groups (10 axes)

`quads`, `posterior_chain`, `glutes`, `calves`, `chest`,
`upper_pull`, `shoulders`, `triceps`, `biceps`, `core`

---

## Scientific basis

**Cardio formula:** TSS-equivalent (Coggan, 1997) extended to muscle group
recruitment via sport-specific coefficients. Normalized intensity factor (IF)
derived from RPE (session-RPE method, Impellizzeri et al. 2004).

**Lifting formula:** Volume load (weight × reps) weighted by relative intensity
(RPE/10). Aligns with Zourdos et al. (2016) modified RPE scale for strength
training and the Gillingham total tonnage model.

**EWMA windows:** Matches existing ACWR implementation (`core/acwr.py`).
Acute 7d / Chronic 28d is the Gabbett (2016) recommendation for load spike
detection, applied per muscle group.

---

## Alternatives considered

**A — sRPE × duration (global):** Simpler but ignores mechanical load
specificity. A 1h deadlift session and a 1h easy run would have the same
posterior_chain score. Rejected.

**C — Banister Impulse-Response:** Scientifically superior for calibrated
athletes with dense data. Requires individual fitting (τ₁, τ₂, k₁, k₂).
Deferred to V2 when longitudinal data is available.

---

## Known limitations

1. `EXERCISE_MUSCLE_MAP` covers ~30 exercises. Unmapped exercises default to
   `core: 0.3`. Extend the map as new exercises appear in athlete data.
2. Normalization uses EWMA_28d as baseline. True individual max requires
   storing historical EWMA peaks. Deferred to V2.
3. Swim coefficients are estimates — electromyography data for swimming is
   limited in the literature.
4. Perceived exertion (RPE) is subjective. Connector data quality affects
   score accuracy.
EOF
```

- [ ] **Step 3: Commit**

```bash
git add docs/backend/STRAIN-DEFINITION.md
git commit -m "docs(backend): add STRAIN-DEFINITION.md architectural decision record"
```

---

### Task 5: Final verification

- [ ] **Step 1: Run full test suite**

```bash
/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/ -v 2>&1 | tail -20
```

Expected: ≥2001 tests + new model + core tests, 0 failed.

- [ ] **Step 2: Verify new test files**

```bash
/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/test_models/test_muscle_strain.py tests/test_core/test_strain.py -v
```

Expected: all passing.

- [ ] **Step 3: Verify backup exists**

```bash
ls backend/app/models/athlete_state.py.backup2
```

Expected: file present.

- [ ] **Step 4: Verify docs**

```bash
ls docs/backend/STRAIN-DEFINITION.md
```

Expected: file present.
