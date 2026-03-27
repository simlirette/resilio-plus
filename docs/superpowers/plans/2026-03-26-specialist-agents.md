# Specialist Agents (RunningCoach + LiftingCoach) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `RunningCoach` and `LiftingCoach` specialist agents with full periodization-aware logic — VDOT zones, 80/20 TID, DUP rotation, SFR tiers, readiness modifiers — on top of stateless `core/` modules.

**Architecture:** Approach C — `core/` holds stateless business logic; `agents/` are thin wrappers. Shared readiness lives in `core/readiness.py`. `AgentContext` gains `week_number` + `weeks_remaining` fields (backwards-compatible defaults).

**Tech Stack:** Python 3.12, Pydantic v2, SQLAlchemy, pytest. No LLM calls — all logic is deterministic Python.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `backend/app/agents/base.py` | Modify | Add `week_number: int = 1`, `weeks_remaining: int = 0` to `AgentContext` |
| `backend/app/core/readiness.py` | Create | `compute_readiness()` — HRV + sleep → modifier in [0.5, 1.5] |
| `backend/app/core/running_logic.py` | Create | `estimate_vdot()`, `compute_running_fatigue()`, `generate_running_sessions()` |
| `backend/app/core/lifting_logic.py` | Create | `StrengthLevel`, `estimate_strength_level()`, `compute_lifting_fatigue()`, `generate_lifting_sessions()` |
| `backend/app/agents/running_coach.py` | Create | `RunningCoach` — thin wrapper around core modules |
| `backend/app/agents/lifting_coach.py` | Create | `LiftingCoach` — thin wrapper around core modules |
| `tests/backend/core/test_readiness.py` | Create | 6 tests for readiness logic |
| `tests/backend/core/test_running_logic.py` | Create | 12 tests for running logic |
| `tests/backend/core/test_lifting_logic.py` | Create | 12 tests for lifting logic |
| `tests/backend/agents/test_running_coach.py` | Create | 8 tests for RunningCoach |
| `tests/backend/agents/test_lifting_coach.py` | Create | 8 tests for LiftingCoach |

---

## Task 1: Enrich AgentContext

**Files:**
- Modify: `backend/app/agents/base.py`

- [ ] **Step 1: Write the failing test**

Create `tests/backend/agents/test_base_enrichment.py`:

```python
from datetime import date
from app.agents.base import AgentContext
from app.schemas.athlete import AthleteProfile, Sport


def _athlete():
    return AthleteProfile(
        name="A", age=30, sex="M", weight_kg=70, height_cm=175,
        sports=[Sport.RUNNING], primary_sport=Sport.RUNNING,
        goals=[], available_days=[0, 2, 4], hours_per_week=8.0,
    )


def test_agent_context_has_week_number_default():
    ctx = AgentContext(
        athlete=_athlete(),
        date_range=(date(2026, 4, 7), date(2026, 4, 13)),
        phase="general_prep",
    )
    assert ctx.week_number == 1


def test_agent_context_has_weeks_remaining_default():
    ctx = AgentContext(
        athlete=_athlete(),
        date_range=(date(2026, 4, 7), date(2026, 4, 13)),
        phase="general_prep",
    )
    assert ctx.weeks_remaining == 0


def test_agent_context_week_number_settable():
    ctx = AgentContext(
        athlete=_athlete(),
        date_range=(date(2026, 4, 7), date(2026, 4, 13)),
        phase="general_prep",
        week_number=5,
        weeks_remaining=12,
    )
    assert ctx.week_number == 5
    assert ctx.weeks_remaining == 12
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd backend && python -m pytest ../tests/backend/agents/test_base_enrichment.py -v
```
Expected: `AttributeError: AgentContext has no field week_number`

- [ ] **Step 3: Add fields to AgentContext**

In `backend/app/agents/base.py`, add two lines after `fatsecret_days`:

```python
@dataclass
class AgentContext:
    """All data available to specialist agents for a given planning week."""
    athlete: AthleteProfile
    date_range: tuple[date, date]
    phase: str                              # MacroPhase value (string)
    strava_activities: list[StravaActivity] = field(default_factory=list)
    hevy_workouts: list[HevyWorkout] = field(default_factory=list)
    terra_health: list[TerraHealthData] = field(default_factory=list)
    fatsecret_days: list[FatSecretDay] = field(default_factory=list)
    week_number: int = 1                    # 1-based week in multi-week plan
    weeks_remaining: int = 0               # weeks until target_race_date
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest ../tests/backend/agents/test_base_enrichment.py ../tests/backend/agents/ -v
```
Expected: all pass (new tests + existing agent tests unchanged)

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/base.py tests/backend/agents/test_base_enrichment.py
git commit -m "feat: add week_number and weeks_remaining to AgentContext"
```

---

## Task 2: core/readiness.py

**Files:**
- Create: `backend/app/core/readiness.py`
- Create: `tests/backend/core/test_readiness.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/backend/core/test_readiness.py`:

```python
from datetime import date, timedelta
from app.core.readiness import compute_readiness
from app.schemas.connector import TerraHealthData


def _terra(days_ago: int, hrv: float | None = None,
           sleep_h: float | None = None, sleep_s: float | None = None) -> TerraHealthData:
    return TerraHealthData(
        date=date(2026, 4, 7) - timedelta(days=days_ago),
        hrv_rmssd=hrv,
        sleep_duration_hours=sleep_h,
        sleep_score=sleep_s,
    )


def test_empty_data_returns_1_0():
    assert compute_readiness([]) == 1.0


def test_good_hrv_good_sleep_returns_bonus():
    # HRV ratio ≥ 1.0 → +0.10; sleep ≥ 7h and ≥ 70 → 0.0 → total 1.10
    data = [_terra(i, hrv=60.0, sleep_h=7.5, sleep_s=80.0) for i in range(7)]
    result = compute_readiness(data, hrv_baseline=55.0)
    assert abs(result - 1.1) < 0.01


def test_low_hrv_reduces_modifier():
    # HRV ratio < 0.60 → -0.30; sleep 7.5h/80 → 0.0 → total 0.70
    data = [_terra(i, hrv=25.0, sleep_h=7.5, sleep_s=80.0) for i in range(7)]
    result = compute_readiness(data, hrv_baseline=55.0)
    assert result <= 0.70


def test_poor_sleep_reduces_modifier():
    # Sleep < 6h → -0.20; HRV ratio 1.0 → +0.10 → total 0.90
    data = [_terra(i, hrv=55.0, sleep_h=5.5, sleep_s=45.0) for i in range(7)]
    result = compute_readiness(data, hrv_baseline=55.0)
    assert abs(result - 0.90) < 0.01


def test_combined_low_hrv_and_poor_sleep_clamped():
    # HRV delta = -0.30, sleep delta = -0.20 → 1.0 - 0.50 = 0.50 → clamped 0.5
    data = [_terra(i, hrv=20.0, sleep_h=5.0, sleep_s=40.0) for i in range(7)]
    result = compute_readiness(data, hrv_baseline=55.0)
    assert result == 0.5


def test_no_hrv_baseline_cold_start_returns_neutral():
    # < 4 valid HRV entries → cold start → hrv_delta = 0
    # good sleep → sleep_delta = 0 → modifier = 1.0
    data = [
        _terra(0, hrv=60.0, sleep_h=7.5, sleep_s=80.0),
        _terra(1, hrv=None, sleep_h=7.5, sleep_s=80.0),
        _terra(2, hrv=None, sleep_h=7.5, sleep_s=80.0),
    ]
    result = compute_readiness(data)
    assert result == 1.0
```

- [ ] **Step 2: Run to verify fails**

```bash
cd backend && python -m pytest ../tests/backend/core/test_readiness.py -v
```
Expected: `ModuleNotFoundError: No module named 'app.core.readiness'`

- [ ] **Step 3: Implement compute_readiness**

Create `backend/app/core/readiness.py`:

```python
from __future__ import annotations

from app.schemas.connector import TerraHealthData


def compute_readiness(
    terra_data: list[TerraHealthData],
    hrv_baseline: float | None = None,
) -> float:
    """Compute readiness modifier in [0.5, 1.5] from HRV and sleep data.

    Returns 1.0 for empty input (cold start with no data).
    hrv_baseline: externally provided long-term HRV mean (ms). If None, computed
    from available data or cold-start (delta = 0) if fewer than 4 valid entries.
    """
    if not terra_data:
        return 1.0

    # Sort newest-first, take last 7 entries
    sorted_data = sorted(terra_data, key=lambda e: e.date, reverse=True)
    last_7 = sorted_data[:7]

    # ── Step 1: HRV delta ──────────────────────────────────────────────────────
    all_hrv = [e.hrv_rmssd for e in sorted_data if e.hrv_rmssd is not None]
    hrv_7d = [e.hrv_rmssd for e in last_7 if e.hrv_rmssd is not None]

    if hrv_7d:
        hrv_7d_mean = sum(hrv_7d) / len(hrv_7d)
        if hrv_baseline is None:
            if len(all_hrv) < 4:
                hrv_delta = 0.0  # cold start — not enough data for meaningful comparison
            else:
                computed_baseline = sum(all_hrv) / len(all_hrv)
                hrv_delta = _hrv_ratio_to_delta(hrv_7d_mean / computed_baseline)
        else:
            hrv_delta = _hrv_ratio_to_delta(hrv_7d_mean / hrv_baseline if hrv_baseline > 0 else 1.0)
    else:
        hrv_delta = 0.0

    # ── Step 2: Sleep delta ────────────────────────────────────────────────────
    sleep_hours = [e.sleep_duration_hours for e in last_7 if e.sleep_duration_hours is not None]
    sleep_scores = [e.sleep_score for e in last_7 if e.sleep_score is not None]

    if sleep_hours or sleep_scores:
        h_mean = sum(sleep_hours) / len(sleep_hours) if sleep_hours else None
        s_mean = sum(sleep_scores) / len(sleep_scores) if sleep_scores else None
        if (h_mean is not None and h_mean < 6.0) or (s_mean is not None and s_mean < 50):
            sleep_delta = -0.20
        elif h_mean is not None and h_mean >= 7.0 and s_mean is not None and s_mean >= 70:
            sleep_delta = 0.0
        else:
            sleep_delta = -0.10
    else:
        sleep_delta = 0.0

    modifier = 1.0 + hrv_delta + sleep_delta
    return max(0.5, min(1.5, modifier))


def _hrv_ratio_to_delta(ratio: float) -> float:
    if ratio >= 1.0:
        return 0.10
    if ratio >= 0.80:
        return 0.0
    if ratio >= 0.60:
        return -0.15
    return -0.30
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest ../tests/backend/core/test_readiness.py -v
```
Expected: 6/6 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/readiness.py tests/backend/core/test_readiness.py
git commit -m "feat: add core/readiness.py with HRV+sleep modifier computation"
```

---

## Task 3: core/running_logic.py

**Files:**
- Create: `backend/app/core/running_logic.py`
- Create: `tests/backend/core/test_running_logic.py`

**Note:** `generate_running_sessions` requires a `week_start: date` parameter (not in spec's function signature, but required by `WorkoutSlot.date`). The calling agents pass `context.date_range[0]`.

- [ ] **Step 1: Write the failing tests**

Create `tests/backend/core/test_running_logic.py`:

```python
from datetime import date, timedelta
from app.core.running_logic import (
    estimate_vdot, compute_running_fatigue, generate_running_sessions,
)
from app.core.periodization import TIDStrategy
from app.schemas.connector import StravaActivity


def _run(distance_m: float, duration_s: int, rpe: int | None = None,
         avg_hr: float | None = None, days_ago: int = 1) -> StravaActivity:
    return StravaActivity(
        id="s1", name="Run", sport_type="Run",
        date=date(2026, 4, 7) - timedelta(days=days_ago),
        duration_seconds=duration_s,
        distance_meters=distance_m,
        perceived_exertion=rpe,
        average_hr=avg_hr,
    )


# ── estimate_vdot ──────────────────────────────────────────────────────────────

def test_estimate_vdot_no_activities_returns_default():
    assert estimate_vdot([]) == 35.0


def test_estimate_vdot_from_recent_activity():
    # 10km in 3000s → pace = 300 s/km → VDOT table row (53, easy=300) → VDOT 53
    activity = _run(distance_m=10000, duration_s=3000, days_ago=5)
    assert estimate_vdot([activity]) == 53


def test_estimate_vdot_ignores_non_run():
    activity = StravaActivity(
        id="s2", name="Ride", sport_type="Ride",
        date=date(2026, 4, 6), duration_seconds=3000, distance_meters=10000,
    )
    assert estimate_vdot([activity]) == 35.0


# ── compute_running_fatigue ────────────────────────────────────────────────────

def test_fatigue_empty_activities_returns_zeros():
    f = compute_running_fatigue([])
    assert f.local_muscular == 0
    assert f.cns_load == 0
    assert f.metabolic_cost == 0
    assert f.recovery_hours == 0
    assert f.affected_muscles == []


def test_fatigue_hiit_increases_cns_load():
    # RPE ≥ 8 → HIIT → cns_load = 20
    f = compute_running_fatigue([_run(5000, 1200, rpe=9)])
    assert f.cns_load == 20.0


def test_fatigue_long_distance_increases_local_muscular():
    # 30km → local_muscular = min(100, 90) = 90
    f = compute_running_fatigue([_run(30000, 7200)])
    assert f.local_muscular == 90.0


def test_fatigue_affected_muscles_are_running_muscles():
    f = compute_running_fatigue([_run(5000, 1500)])
    assert set(f.affected_muscles) == {"quads", "calves", "hamstrings"}


def test_fatigue_hiit_sets_recovery_24h():
    f = compute_running_fatigue([_run(3000, 900, rpe=9)])
    assert f.recovery_hours == 24.0


# ── generate_running_sessions ──────────────────────────────────────────────────

_WEEK_START = date(2026, 4, 7)  # Monday


def _gen(week_number=1, weeks_remaining=10, hours=8.0,
         available_days=None, tid=TIDStrategy.PYRAMIDAL, volume_mod=1.0):
    return generate_running_sessions(
        vdot=50.0,
        week_number=week_number,
        weeks_remaining=weeks_remaining,
        available_days=available_days or [0, 2, 4, 5, 6],
        hours_budget=hours,
        volume_modifier=volume_mod,
        tid_strategy=tid,
        week_start=_WEEK_START,
    )


def test_generate_sessions_respects_80_20_ratio():
    sessions = _gen()
    z1_types = ("easy_z1", "long_run_z1")
    z1_total = sum(s.duration_min for s in sessions if s.workout_type in z1_types)
    total = sum(s.duration_min for s in sessions)
    assert total > 0
    assert z1_total / total >= 0.80


def test_generate_sessions_deload_week_reduces_volume():
    # week 4 (deload) should be less total volume than week 3
    regular = _gen(week_number=3)
    deload = _gen(week_number=4)
    total_regular = sum(s.duration_min for s in regular)
    total_deload = sum(s.duration_min for s in deload)
    assert total_deload < total_regular


def test_generate_sessions_tapering_near_race():
    sessions = _gen(weeks_remaining=1)
    types = {s.workout_type for s in sessions}
    assert "tempo_z2" not in types
    assert "vo2max_z3" not in types or "activation_z3" in types


def test_generate_sessions_pyramidal_includes_tempo():
    sessions = _gen(tid=TIDStrategy.PYRAMIDAL)
    types = {s.workout_type for s in sessions}
    assert "tempo_z2" in types


def test_generate_sessions_polarized_avoids_z2():
    sessions = _gen(tid=TIDStrategy.POLARIZED)
    types = {s.workout_type for s in sessions}
    assert "tempo_z2" not in types


def test_generate_sessions_no_long_run_below_6h_budget():
    sessions = _gen(hours=4.0)
    types = {s.workout_type for s in sessions}
    assert "long_run_z1" not in types


def test_generate_sessions_long_run_included_at_6h():
    sessions = _gen(hours=6.0)
    types = {s.workout_type for s in sessions}
    assert "long_run_z1" in types


def test_generate_sessions_workout_slots_have_valid_dates():
    sessions = _gen()
    for s in sessions:
        assert s.date >= _WEEK_START
        assert s.date <= _WEEK_START + timedelta(days=6)
```

- [ ] **Step 2: Run to verify fails**

```bash
cd backend && python -m pytest ../tests/backend/core/test_running_logic.py -v
```
Expected: `ModuleNotFoundError: No module named 'app.core.running_logic'`

- [ ] **Step 3: Implement running_logic.py**

Create `backend/app/core/running_logic.py`:

```python
from __future__ import annotations

from datetime import date, timedelta

from app.core.periodization import TIDStrategy
from app.schemas.athlete import Sport
from app.schemas.connector import StravaActivity
from app.schemas.fatigue import FatigueScore
from app.schemas.plan import WorkoutSlot

# ── VDOT lookup table (Jack Daniels, simplified) ──────────────────────────────
# (vdot, easy_pace_s_per_km, threshold_pace_s_per_km)
_VDOT_TABLE: list[tuple[int, int, int]] = [
    (30, 450, 390), (33, 425, 368), (35, 405, 350), (38, 383, 332),
    (40, 370, 315), (43, 350, 300), (45, 340, 290), (48, 322, 275),
    (50, 315, 270), (53, 300, 258), (55, 295, 250), (58, 280, 238),
    (60, 275, 235), (65, 258, 220), (70, 242, 207),
]

_ZEROED_FATIGUE = FatigueScore(
    local_muscular=0.0, cns_load=0.0, metabolic_cost=0.0,
    recovery_hours=0.0, affected_muscles=[],
)


def estimate_vdot(activities: list[StravaActivity]) -> float:
    """Estimate VDOT from recent run activities. Returns 35.0 (beginner) if no data.

    Filters to last 30 days, sport_type == "Run", distance ≥ 1000m.
    Computes pace per km and finds the nearest VDOT row by easy_pace.
    Returns the maximum VDOT found across all valid activities.
    """
    from datetime import date as _date
    cutoff = _date.today() - timedelta(days=30)
    runs = [
        a for a in activities
        if a.sport_type == "Run"
        and a.date >= cutoff
        and a.distance_meters is not None
        and a.distance_meters >= 1000
    ]
    if not runs:
        return 35.0

    best = 0
    for a in runs:
        pace = a.duration_seconds / (a.distance_meters / 1000)  # s/km
        row = min(_VDOT_TABLE, key=lambda r: abs(r[1] - pace))
        if row[0] > best:
            best = row[0]

    return float(best) if best > 0 else 35.0


def compute_running_fatigue(activities: list[StravaActivity]) -> FatigueScore:
    """Compute FatigueScore from a pre-filtered list of running activities.

    Caller must pre-filter to the relevant time window (e.g., last 7 days).
    This function does NOT filter by date.
    """
    if not activities:
        return FatigueScore(
            local_muscular=0.0, cns_load=0.0, metabolic_cost=0.0,
            recovery_hours=0.0, affected_muscles=[],
        )

    total_km = sum((a.distance_meters or 0.0) / 1000.0 for a in activities)

    hiit_count = sum(1 for a in activities if _is_hiit(a))

    metabolic = sum(
        (a.duration_seconds / 60.0) * ((a.perceived_exertion or 5) / 10.0)
        for a in activities
    ) / 10.0

    if any(_is_hiit(a) for a in activities):
        recovery = 24.0
    elif any(
        a.perceived_exertion is not None and 6 <= a.perceived_exertion <= 7
        for a in activities
    ):
        recovery = 12.0
    else:
        recovery = 6.0

    return FatigueScore(
        local_muscular=min(100.0, total_km * 3.0),
        cns_load=min(100.0, float(hiit_count) * 20.0),
        metabolic_cost=min(100.0, metabolic),
        recovery_hours=recovery,
        affected_muscles=["quads", "calves", "hamstrings"],
    )


def _is_hiit(a: StravaActivity) -> bool:
    """HIIT = RPE ≥ 8, OR short effort with high average HR (> 160 bpm)."""
    if a.perceived_exertion is not None and a.perceived_exertion >= 8:
        return True
    if a.duration_seconds < 1800 and a.average_hr is not None and a.average_hr > 160:
        return True
    return False


def generate_running_sessions(
    vdot: float,
    week_number: int,
    weeks_remaining: int,
    available_days: list[int],   # 0=Mon … 6=Sun
    hours_budget: float,
    volume_modifier: float,
    tid_strategy: TIDStrategy,
    week_start: date,            # Monday of the planning week (WorkoutSlot.date base)
) -> list[WorkoutSlot]:
    """Generate weekly running sessions as WorkoutSlots.

    Wave loading: week_number % 4 == 0 → deload (60%). Otherwise 5% progressive
    overload per week in block. Taper (weeks_remaining ≤ 2) overrides to 50%.
    80/20 TID: 80% Z1, 20% quality. Quality selection by tid_strategy.
    """
    if not available_days:
        return []

    # 1. Wave loading (deload check MUST come first)
    base_minutes = hours_budget * 60.0 * volume_modifier
    if week_number % 4 == 0:
        weekly_minutes = base_minutes * 0.6
    else:
        weekly_minutes = base_minutes * (1.0 + 0.05 * ((week_number % 4) - 1))

    # 2. Tapering override
    if weeks_remaining <= 2:
        weekly_minutes = base_minutes * 0.5

    # 3. Build (workout_type, duration_min) list
    raw: list[tuple[str, int]] = []

    if weeks_remaining <= 2:
        z1_dur = max(30, int(weekly_minutes * 0.9))
        raw.append(("easy_z1", min(90, z1_dur)))
        raw.append(("activation_z3", 20))
    else:
        quality_min = int(weekly_minutes * 0.2)
        z1_min = int(weekly_minutes * 0.8)

        # Quality sessions by TID strategy
        if tid_strategy == TIDStrategy.PYRAMIDAL:
            raw.append(("tempo_z2", min(60, max(20, quality_min))))
        elif tid_strategy == TIDStrategy.MIXED:
            tempo_dur = min(40, quality_min)
            raw.append(("tempo_z2", tempo_dur))
            vo2_budget = quality_min - tempo_dur
            if vo2_budget >= 20:
                raw.append(("vo2max_z3", min(45, vo2_budget)))
        elif tid_strategy == TIDStrategy.POLARIZED:
            raw.append(("vo2max_z3", min(45, quality_min)))

        # Z1 sessions
        remaining_z1 = z1_min
        if hours_budget >= 6.0 and remaining_z1 >= 60:
            long_dur = min(120, remaining_z1)
            raw.append(("long_run_z1", long_dur))
            remaining_z1 -= long_dur

        while remaining_z1 >= 30:
            dur = min(90, remaining_z1)
            raw.append(("easy_z1", max(30, dur)))
            remaining_z1 -= dur

    # 4. Assign days: longest sessions → weekend (5–6) first
    raw_sorted = sorted(raw, key=lambda t: t[1], reverse=True)

    weekend = sorted(d for d in available_days if d >= 5)
    weekday = sorted(d for d in available_days if d < 5)
    if not weekend:
        # No weekend: longest session to last available day
        last = max(available_days)
        day_pool = [last] + sorted(d for d in available_days if d != last)
    else:
        day_pool = weekend + weekday

    sessions_to_place = raw_sorted[:len(day_pool)]

    return [
        WorkoutSlot(
            date=week_start + timedelta(days=day_pool[i]),
            sport=Sport.RUNNING,
            workout_type=wtype,
            duration_min=dur,
            fatigue_score=FatigueScore(
                local_muscular=0.0, cns_load=0.0, metabolic_cost=0.0,
                recovery_hours=0.0, affected_muscles=[],
            ),
        )
        for i, (wtype, dur) in enumerate(sessions_to_place)
    ]
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest ../tests/backend/core/test_running_logic.py -v
```
Expected: 13/13 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/running_logic.py tests/backend/core/test_running_logic.py
git commit -m "feat: add core/running_logic.py (VDOT estimation, fatigue, session generation)"
```

---

## Task 4: core/lifting_logic.py

**Files:**
- Create: `backend/app/core/lifting_logic.py`
- Create: `tests/backend/core/test_lifting_logic.py`

**Important data files used at runtime:**
- `.bmad-core/data/exercise-database.json` — keys: `tier_1_high_sfr_low_cns`, `tier_2_moderate_sfr_moderate_cns`, `tier_3_low_sfr_high_cns_use_sparingly`
- `.bmad-core/data/volume-landmarks.json` — per-muscle `MEV`, `MRV`, `hybrid_reduction` values

**Note:** `generate_lifting_sessions` requires `week_start: date` (same reason as running).

- [ ] **Step 1: Write the failing tests**

Create `tests/backend/core/test_lifting_logic.py`:

```python
from datetime import date, timedelta
from app.core.lifting_logic import (
    StrengthLevel, estimate_strength_level,
    compute_lifting_fatigue, generate_lifting_sessions,
)
from app.schemas.connector import HevyWorkout, HevyExercise, HevySet


def _set(reps=8, kg=60.0, rpe=7.0) -> HevySet:
    return HevySet(reps=reps, weight_kg=kg, rpe=rpe, set_type="normal")


def _exercise(name: str, sets=3) -> HevyExercise:
    return HevyExercise(name=name, sets=[_set() for _ in range(sets)])


def _workout(exercises: list[HevyExercise], days_ago=1) -> HevyWorkout:
    return HevyWorkout(
        id="h1", title="Workout",
        date=date(2026, 4, 7) - timedelta(days=days_ago),
        duration_seconds=3600,
        exercises=exercises,
    )


# ── estimate_strength_level ───────────────────────────────────────────────────

def test_estimate_strength_level_no_data_returns_beginner():
    assert estimate_strength_level([]) == StrengthLevel.BEGINNER


def test_estimate_strength_level_advanced():
    # 4 workouts in "30 days" → sessions_per_week = 4/4.3 ≈ 0.93... need more
    # 14 workouts → sessions_per_week ≈ 3.26 and high RPE → ADVANCED
    workouts = [_workout([_exercise("Bench Press", 4)], days_ago=i*2) for i in range(14)]
    # Override rpe to be > 8 for all sets
    for w in workouts:
        for ex in w.exercises:
            ex.sets = [HevySet(reps=5, weight_kg=100, rpe=9.0, set_type="normal")]
    assert estimate_strength_level(workouts) == StrengthLevel.ADVANCED


# ── compute_lifting_fatigue ───────────────────────────────────────────────────

def test_fatigue_empty_workouts_returns_zeros():
    f = compute_lifting_fatigue([])
    assert f.local_muscular == 0
    assert f.cns_load == 0
    assert f.recovery_hours == 0
    assert f.affected_muscles == []


def test_fatigue_tier3_increases_cns_load():
    # "Barbell Back Squat" is Tier 3 → cns_load = 25
    workout = _workout([_exercise("Barbell Back Squat", 4)])
    f = compute_lifting_fatigue([workout])
    assert f.cns_load == 25.0


def test_fatigue_squat_sets_recovery_48h():
    workout = _workout([_exercise("Barbell Back Squat", 3)])
    f = compute_lifting_fatigue([workout])
    assert f.recovery_hours == 48.0


def test_fatigue_upper_body_only_sets_recovery_24h():
    workout = _workout([_exercise("Lat Pulldown", 3), _exercise("Dumbbell Bench Press", 3)])
    f = compute_lifting_fatigue([workout])
    assert f.recovery_hours == 24.0


# ── generate_lifting_sessions ─────────────────────────────────────────────────

_WEEK_START = date(2026, 4, 7)


def _gen(week_number=1, available_days=None, phase="general_prep",
         running_ratio=0.4, weeks_remaining=10):
    return generate_lifting_sessions(
        strength_level=StrengthLevel.INTERMEDIATE,
        phase=phase,
        week_number=week_number,
        weeks_remaining=weeks_remaining,
        available_days=available_days or [1, 3, 5, 6],
        hours_budget=4.0,
        volume_modifier=1.0,
        running_load_ratio=running_ratio,
        week_start=_WEEK_START,
    )


def test_generate_sessions_dup_rotation_week_0_hypertrophy():
    # week 3 → 3 % 3 == 0 → hypertrophy priority
    sessions = _gen(week_number=3)
    types = {s.workout_type for s in sessions}
    assert "upper_hypertrophy" in types


def test_generate_sessions_dup_rotation_week_1_strength():
    # week 1 → 1 % 3 == 1 → strength priority
    sessions = _gen(week_number=1)
    types = {s.workout_type for s in sessions}
    assert "upper_strength" in types


def test_generate_sessions_dup_rotation_week_2_endurance():
    # week 2 → 2 % 3 == 2 → endurance priority
    sessions = _gen(week_number=2)
    types = {s.workout_type for s in sessions}
    assert "full_body_endurance" in types


def test_generate_sessions_hybrid_reduction_applied_when_running_high():
    # running_ratio > 0.5 → lower_strength shorter than default 60 min
    normal = _gen(running_ratio=0.3)
    hybrid = _gen(running_ratio=0.7)
    normal_lower = [s for s in normal if s.workout_type == "lower_strength"]
    hybrid_lower = [s for s in hybrid if s.workout_type == "lower_strength"]
    if normal_lower and hybrid_lower:
        assert hybrid_lower[0].duration_min < normal_lower[0].duration_min


def test_generate_sessions_deload_week_reduces_duration():
    normal = _gen(week_number=1)
    deload = _gen(week_number=4)  # 4 % 4 == 0 → deload
    total_normal = sum(s.duration_min for s in normal)
    total_deload = sum(s.duration_min for s in deload)
    assert total_deload < total_normal


def test_generate_sessions_arms_hypertrophy_included():
    # week 3 (dup=0) + 4 available days → arms_hypertrophy included
    sessions = _gen(week_number=3, available_days=[0, 2, 4, 6])
    types = {s.workout_type for s in sessions}
    assert "arms_hypertrophy" in types


def test_generate_sessions_tier1_only_in_general_prep():
    # general_prep → upper_strength notes should mention "Tier 1"
    sessions = _gen(week_number=1, phase="general_prep")
    upper = [s for s in sessions if s.workout_type == "upper_strength"]
    if upper:
        assert "Tier 1" in upper[0].notes


def test_generate_sessions_workout_slots_have_positive_duration():
    sessions = _gen()
    assert all(s.duration_min > 0 for s in sessions)
```

- [ ] **Step 2: Run to verify fails**

```bash
cd backend && python -m pytest ../tests/backend/core/test_lifting_logic.py -v
```
Expected: `ModuleNotFoundError: No module named 'app.core.lifting_logic'`

- [ ] **Step 3: Implement lifting_logic.py**

Create `backend/app/core/lifting_logic.py`:

```python
from __future__ import annotations

import json
from datetime import date, timedelta
from enum import Enum
from pathlib import Path

from app.schemas.athlete import Sport
from app.schemas.connector import HevyWorkout
from app.schemas.fatigue import FatigueScore
from app.schemas.plan import WorkoutSlot

# ── Load data files ────────────────────────────────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parents[3]
_EXERCISE_DB: dict = json.loads(
    (_REPO_ROOT / ".bmad-core" / "data" / "exercise-database.json").read_text()
)
_VOLUME_LANDMARKS: dict = json.loads(
    (_REPO_ROOT / ".bmad-core" / "data" / "volume-landmarks.json").read_text()
)

_TIER3_EXERCISES: set[str] = {
    e.lower() for e in _EXERCISE_DB.get("tier_3_low_sfr_high_cns_use_sparingly", [])
}

# ── Keyword → muscle group lookup (hand-authored) ─────────────────────────────
_EXERCISE_MUSCLE_MAP: dict[str, list[str]] = {
    "squat":    ["quads", "glutes"],
    "deadlift": ["hamstrings", "glutes", "back"],
    "bench":    ["chest", "triceps"],
    "press":    ["chest", "triceps", "shoulders"],
    "row":      ["back", "biceps"],
    "pull":     ["back", "biceps"],
    "curl":     ["biceps"],
    "extension": ["triceps", "quads"],
    "lunge":    ["quads", "glutes"],
    "calf":     ["calves"],
    "lateral":  ["shoulders"],
    "fly":      ["chest"],
    "dip":      ["triceps", "chest"],
}

# lower-body keywords for recovery logic
_LOWER_KEYWORDS = ("squat", "deadlift", "lunge", "leg press", "hack squat",
                   "split squat", "romanian", "rdl")


class StrengthLevel(str, Enum):
    BEGINNER     = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED     = "advanced"


def estimate_strength_level(workouts: list[HevyWorkout]) -> StrengthLevel:
    """Estimate strength level from recent Hevy workouts (last 30 days)."""
    if not workouts:
        return StrengthLevel.BEGINNER

    sessions_per_week = len(workouts) / 4.3

    all_rpes = [
        s.rpe
        for w in workouts
        for ex in w.exercises
        for s in ex.sets
        if s.rpe is not None
    ]
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
            local_muscular=0.0, cns_load=0.0, metabolic_cost=0.0,
            recovery_hours=0.0, affected_muscles=[],
        )

    total_sets = sum(
        len(ex.sets) for w in workouts for ex in w.exercises
    )

    # Tier 3 detection: workout contains any exercise from Tier 3 list
    tier3_sessions = sum(
        1 for w in workouts
        if any(ex.name.lower() in _TIER3_EXERCISES for ex in w.exercises)
    )

    all_reps = [
        s.reps for w in workouts for ex in w.exercises
        for s in ex.sets if s.reps is not None
    ]
    total_reps_mean = sum(all_reps) / len(all_reps) if all_reps else 0.0

    # Recovery: lower body (squat/deadlift) → 48h; upper only → 24h; light → 12h
    all_exercise_names = [ex.name.lower() for w in workouts for ex in w.exercises]
    has_lower = any(kw in name for name in all_exercise_names for kw in _LOWER_KEYWORDS)
    if has_lower:
        recovery = 48.0
    elif all_exercise_names:
        recovery = 24.0
    else:
        recovery = 12.0

    # Affected muscles via keyword lookup
    muscles: list[str] = []
    seen: set[str] = set()
    for name in all_exercise_names:
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
    phase: str,                    # MacroPhase value string
    week_number: int,
    weeks_remaining: int,
    available_days: list[int],     # 0=Mon … 6=Sun
    hours_budget: float,
    volume_modifier: float,
    running_load_ratio: float,
    week_start: date,              # Monday of the planning week
) -> list[WorkoutSlot]:
    """Generate weekly lifting sessions as WorkoutSlots.

    DUP rotation: week_number % 3 → 0=hypertrophy, 1=strength, 2=endurance.
    Hybrid reduction: running_load_ratio > 0.5 → lower body sessions shorter.
    Wave loading: week_number % 4 == 0 → 60% duration (deload).
    """
    if not available_days:
        return []

    # Exercise tier note based on phase
    _TIER_NOTE: dict[str, str] = {
        "general_prep":    "Tier 1",
        "specific_prep":   "Tier 1-2",
        "pre_competition": "Tier 1-2",
        "competition":     "Tier 1-2",
        "transition":      "Tier 2-3",
    }
    tier_note = _TIER_NOTE.get(phase, "Tier 1")

    # Wave loading multiplier (deload check first)
    dur_mult = 0.6 if week_number % 4 == 0 else 1.0

    # Hybrid reduction for lower body (quads hybrid_reduction = 0.4)
    lower_base = 60
    if running_load_ratio > 0.5:
        quads_reduction = _VOLUME_LANDMARKS.get("quads", {}).get("hybrid_reduction", 0.4)
        lower_base = int(60 * (1.0 - quads_reduction))  # 36 min default

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
        raw.append((
            "upper_strength",
            max(20, int(75 * dur_mult)),
            f"{tier_note} | chest, back, shoulders, triceps, biceps",
        ))
        raw.append(("lower_strength", lower_dur, "quads, hamstrings"))
    else:  # Endurance priority
        raw.append(("full_body_endurance", max(20, int(45 * dur_mult)), "core, quads, back"))

    # Cap to available days
    slots = raw[:len(available_days)]

    _Z = FatigueScore(
        local_muscular=0.0, cns_load=0.0, metabolic_cost=0.0,
        recovery_hours=0.0, affected_muscles=[],
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
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest ../tests/backend/core/test_lifting_logic.py -v
```
Expected: 13/13 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/lifting_logic.py tests/backend/core/test_lifting_logic.py
git commit -m "feat: add core/lifting_logic.py (strength level, fatigue, DUP session generation)"
```

---

## Task 5: agents/running_coach.py

**Files:**
- Create: `backend/app/agents/running_coach.py`
- Create: `tests/backend/agents/test_running_coach.py`

**Note:** The agent passes `context.date_range[0]` as `week_start` to `generate_running_sessions` (practical addition not in spec signature).

- [ ] **Step 1: Write the failing tests**

Create `tests/backend/agents/test_running_coach.py`:

```python
from datetime import date, timedelta
import pytest
from app.agents.base import AgentContext, AgentRecommendation
from app.agents.running_coach import RunningCoach
from app.schemas.athlete import AthleteProfile, Sport
from app.schemas.connector import StravaActivity, TerraHealthData
from app.schemas.plan import WorkoutSlot


def _athlete(primary=Sport.RUNNING, hours=8.0, days=None):
    return AthleteProfile(
        name="Alice", age=28, sex="F", weight_kg=58, height_cm=165,
        sports=[Sport.RUNNING, Sport.LIFTING], primary_sport=primary,
        goals=["sub-4h marathon"], target_race_date=date(2026, 10, 15),
        available_days=days or [0, 2, 4, 5, 6],
        hours_per_week=hours,
    )


def _context(athlete=None, week_number=1, weeks_remaining=28,
             strava=None, terra=None):
    a = athlete or _athlete()
    return AgentContext(
        athlete=a,
        date_range=(date(2026, 4, 7), date(2026, 4, 13)),
        phase="general_prep",
        strava_activities=strava or [],
        terra_health=terra or [],
        week_number=week_number,
        weeks_remaining=weeks_remaining,
    )


def test_analyze_returns_agent_recommendation():
    coach = RunningCoach()
    result = coach.analyze(_context())
    assert isinstance(result, AgentRecommendation)


def test_analyze_name_is_running():
    assert RunningCoach().name == "running"


def test_analyze_readiness_modifier_propagated_from_terra():
    # Good HRV + good sleep → modifier = 1.1
    terra = [
        TerraHealthData(date=date(2026, 4, 7) - timedelta(days=i),
                        hrv_rmssd=60.0, sleep_duration_hours=7.5, sleep_score=80.0)
        for i in range(7)
    ]
    result = RunningCoach().analyze(_context(terra=terra))
    assert result.readiness_modifier > 1.0


def test_analyze_sessions_are_workout_slots():
    result = RunningCoach().analyze(_context())
    assert all(isinstance(s, WorkoutSlot) for s in result.suggested_sessions)


def test_analyze_weekly_load_positive():
    result = RunningCoach().analyze(_context())
    assert result.weekly_load > 0


def test_analyze_cold_start_no_strava_data():
    # No data → VDOT defaults to 35.0, still returns valid recommendation
    result = RunningCoach().analyze(_context(strava=[]))
    assert result.agent_name == "running"
    assert result.weekly_load >= 0


def test_analyze_week_number_deload_less_load():
    # Week 4 (deload) should produce less weekly_load than week 3
    regular = RunningCoach().analyze(_context(week_number=3, weeks_remaining=28))
    deload = RunningCoach().analyze(_context(week_number=4, weeks_remaining=28))
    assert deload.weekly_load < regular.weekly_load


def test_analyze_near_race_only_z1_sessions():
    result = RunningCoach().analyze(_context(weeks_remaining=1))
    types = {s.workout_type for s in result.suggested_sessions}
    assert "tempo_z2" not in types
```

- [ ] **Step 2: Run to verify fails**

```bash
cd backend && python -m pytest ../tests/backend/agents/test_running_coach.py -v
```
Expected: `ModuleNotFoundError: No module named 'app.agents.running_coach'`

- [ ] **Step 3: Implement running_coach.py**

Create `backend/app/agents/running_coach.py`:

```python
from __future__ import annotations

from datetime import timedelta

from app.agents.base import AgentContext, AgentRecommendation, BaseAgent
from app.core.periodization import get_current_phase
from app.core.readiness import compute_readiness
from app.core.running_logic import (
    compute_running_fatigue, estimate_vdot, generate_running_sessions,
)
from app.schemas.athlete import Sport


class RunningCoach(BaseAgent):
    """Specialist agent for running: VDOT-aware, 80/20 TID, wave loading."""

    @property
    def name(self) -> str:
        return "running"

    def analyze(self, context: AgentContext) -> AgentRecommendation:
        # 1. Filter Strava activities to the 7 days before this week
        prior_activities = [
            a for a in context.strava_activities
            if context.date_range[0] - timedelta(days=7) <= a.date < context.date_range[0]
        ]

        # 2. VDOT: use athlete's stored value, else estimate from full history
        vdot = context.athlete.vdot or estimate_vdot(context.strava_activities)

        # 3. Readiness modifier from Terra health data
        readiness_modifier = compute_readiness(context.terra_health)

        # 4. Fatigue from last week's runs
        fatigue_score = compute_running_fatigue(prior_activities)

        # 5. Periodization phase
        phase = get_current_phase(context.athlete.target_race_date, context.date_range[0])

        # 6. Budget split: 60% running / 40% lifting; reversed if primary is LIFTING
        run_ratio = 0.4 if context.athlete.primary_sport == Sport.LIFTING else 0.6
        hours_budget = context.athlete.hours_per_week * run_ratio

        # 7. Generate sessions
        sessions = generate_running_sessions(
            vdot=vdot,
            week_number=context.week_number,
            weeks_remaining=context.weeks_remaining,
            available_days=context.athlete.available_days,
            hours_budget=hours_budget,
            volume_modifier=phase.volume_modifier,
            tid_strategy=phase.tid_recommendation,
            week_start=context.date_range[0],
        )

        # 8. Weekly load: sum(duration_min × intensity_weight)
        _INTENSITY = {
            "easy_z1": 1.0, "long_run_z1": 1.0,
            "tempo_z2": 1.5, "vo2max_z3": 2.0, "activation_z3": 2.0,
        }
        weekly_load = sum(
            s.duration_min * _INTENSITY.get(s.workout_type, 1.0)
            for s in sessions
        )

        return AgentRecommendation(
            agent_name=self.name,
            fatigue_score=fatigue_score,
            weekly_load=weekly_load,
            suggested_sessions=sessions,
            readiness_modifier=readiness_modifier,
            notes=(
                f"VDOT {vdot:.0f} | Phase: {phase.phase.value} | "
                f"Week: {context.week_number} | Weeks remaining: {context.weeks_remaining}"
            ),
        )
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest ../tests/backend/agents/test_running_coach.py -v
```
Expected: 8/8 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/running_coach.py tests/backend/agents/test_running_coach.py
git commit -m "feat: add RunningCoach agent"
```

---

## Task 6: agents/lifting_coach.py

**Files:**
- Create: `backend/app/agents/lifting_coach.py`
- Create: `tests/backend/agents/test_lifting_coach.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/backend/agents/test_lifting_coach.py`:

```python
from datetime import date, timedelta
import pytest
from app.agents.base import AgentContext, AgentRecommendation
from app.agents.lifting_coach import LiftingCoach
from app.schemas.athlete import AthleteProfile, Sport
from app.schemas.connector import HevyWorkout, HevyExercise, HevySet, TerraHealthData
from app.schemas.plan import WorkoutSlot


def _athlete(primary=Sport.RUNNING, hours=8.0, days=None):
    return AthleteProfile(
        name="Bob", age=32, sex="M", weight_kg=80, height_cm=180,
        sports=[Sport.RUNNING, Sport.LIFTING], primary_sport=primary,
        goals=["strength + run hybrid"], target_race_date=None,
        available_days=days or [1, 3, 5, 6],
        hours_per_week=hours,
    )


def _context(athlete=None, week_number=1, weeks_remaining=20,
             hevy=None, terra=None):
    a = athlete or _athlete()
    return AgentContext(
        athlete=a,
        date_range=(date(2026, 4, 7), date(2026, 4, 13)),
        phase="general_prep",
        hevy_workouts=hevy or [],
        terra_health=terra or [],
        week_number=week_number,
        weeks_remaining=weeks_remaining,
    )


def test_analyze_returns_agent_recommendation():
    result = LiftingCoach().analyze(_context())
    assert isinstance(result, AgentRecommendation)


def test_analyze_name_is_lifting():
    assert LiftingCoach().name == "lifting"


def test_analyze_readiness_modifier_propagated_from_terra():
    terra = [
        TerraHealthData(date=date(2026, 4, 7) - timedelta(days=i),
                        hrv_rmssd=60.0, sleep_duration_hours=7.5, sleep_score=80.0)
        for i in range(7)
    ]
    result = LiftingCoach().analyze(_context(terra=terra))
    assert result.readiness_modifier > 1.0


def test_analyze_sessions_are_workout_slots():
    result = LiftingCoach().analyze(_context())
    assert all(isinstance(s, WorkoutSlot) for s in result.suggested_sessions)


def test_analyze_weekly_load_positive():
    result = LiftingCoach().analyze(_context())
    assert result.weekly_load > 0


def test_analyze_cold_start_no_hevy_data():
    result = LiftingCoach().analyze(_context(hevy=[]))
    assert result.agent_name == "lifting"
    assert result.weekly_load >= 0


def test_analyze_week_number_affects_dup_rotation():
    # week_number=3 → dup=0 → hypertrophy; week_number=1 → dup=1 → strength
    hypertrophy_week = LiftingCoach().analyze(_context(week_number=3))
    strength_week = LiftingCoach().analyze(_context(week_number=1))
    hyper_types = {s.workout_type for s in hypertrophy_week.suggested_sessions}
    strength_types = {s.workout_type for s in strength_week.suggested_sessions}
    assert "upper_hypertrophy" in hyper_types
    assert "upper_strength" in strength_types


def test_analyze_deload_week_reduces_load():
    normal = LiftingCoach().analyze(_context(week_number=1))
    deload = LiftingCoach().analyze(_context(week_number=4))
    assert deload.weekly_load < normal.weekly_load
```

- [ ] **Step 2: Run to verify fails**

```bash
cd backend && python -m pytest ../tests/backend/agents/test_lifting_coach.py -v
```
Expected: `ModuleNotFoundError: No module named 'app.agents.lifting_coach'`

- [ ] **Step 3: Implement lifting_coach.py**

Create `backend/app/agents/lifting_coach.py`:

```python
from __future__ import annotations

from datetime import timedelta

from app.agents.base import AgentContext, AgentRecommendation, BaseAgent
from app.core.lifting_logic import (
    compute_lifting_fatigue, estimate_strength_level, generate_lifting_sessions,
)
from app.core.periodization import get_current_phase
from app.core.readiness import compute_readiness
from app.schemas.athlete import Sport


class LiftingCoach(BaseAgent):
    """Specialist agent for lifting: DUP rotation, SFR tiers, hybrid reduction."""

    @property
    def name(self) -> str:
        return "lifting"

    def analyze(self, context: AgentContext) -> AgentRecommendation:
        # 1. Filter Hevy workouts to 7 days before this week
        prior_workouts = [
            w for w in context.hevy_workouts
            if context.date_range[0] - timedelta(days=7) <= w.date < context.date_range[0]
        ]

        # 2. Strength level from full history
        strength_level = estimate_strength_level(context.hevy_workouts)

        # 3. Readiness modifier from Terra data
        readiness_modifier = compute_readiness(context.terra_health)

        # 4. Fatigue from last week
        fatigue_score = compute_lifting_fatigue(prior_workouts)

        # 5. Periodization phase
        phase = get_current_phase(context.athlete.target_race_date, context.date_range[0])

        # 6. Budget split: 40% lifting / 60% running; reversed if primary is LIFTING
        lift_ratio = 0.6 if context.athlete.primary_sport == Sport.LIFTING else 0.4
        hours_budget = context.athlete.hours_per_week * lift_ratio

        # 7. Running load ratio (default 0.6 — refined when HeadCoach passes data)
        running_load_ratio = 0.6

        # 8. Generate sessions
        sessions = generate_lifting_sessions(
            strength_level=strength_level,
            phase=phase.phase.value,
            week_number=context.week_number,
            weeks_remaining=context.weeks_remaining,
            available_days=context.athlete.available_days,
            hours_budget=hours_budget,
            volume_modifier=phase.volume_modifier,
            running_load_ratio=running_load_ratio,
            week_start=context.date_range[0],
        )

        # 9. Weekly load: sum(duration_min × intensity_weight)
        _LIFT_INTENSITY = {
            "upper_strength": 2.0, "lower_strength": 2.0,
            "upper_hypertrophy": 1.5, "arms_hypertrophy": 1.0,
            "full_body_endurance": 1.0,
        }
        weekly_load = sum(
            s.duration_min * _LIFT_INTENSITY.get(s.workout_type, 1.0)
            for s in sessions
        )

        return AgentRecommendation(
            agent_name=self.name,
            fatigue_score=fatigue_score,
            weekly_load=weekly_load,
            suggested_sessions=sessions,
            readiness_modifier=readiness_modifier,
            notes=(
                f"Level: {strength_level.value} | Phase: {phase.phase.value} | "
                f"DUP block: {context.week_number % 3}"
            ),
        )
```

- [ ] **Step 4: Run all tests**

```bash
cd backend && python -m pytest ../tests/backend/agents/test_lifting_coach.py -v
```
Expected: 8/8 PASS

- [ ] **Step 5: Run full test suite**

```bash
cd backend && python -m pytest ../tests/ -v
```
Expected: all previously passing tests still pass + 46 new tests pass

- [ ] **Step 6: Commit**

```bash
git add backend/app/agents/lifting_coach.py tests/backend/agents/test_lifting_coach.py
git commit -m "feat: add LiftingCoach agent (DUP rotation, SFR tiers, hybrid volume reduction)"
```
