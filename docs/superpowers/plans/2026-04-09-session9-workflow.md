# S9 Workflow — Head Coach Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the Head Coach LangGraph workflow: constraint matrix builder, conflict resolver, plan merger, three stub node implementations, and a workflow REST API with interrupt/resume.

**Architecture:** `core/constraint_matrix.py` (pure function, greedy scheduler) + `agents/head_coach/resolver.py` (ACWR-based plan modifications) + `agents/head_coach/merger.py` (unified weekly plan) are three independent units consumed by `agents/head_coach/graph.py` (3 stub nodes replaced) and exposed through `api/v1/workflow.py` (3 routes, LangGraph interrupt/resume via `head_coach_graph.get_state()`).

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, LangGraph 0.2.x, pytest, ruff.

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `models/athlete_state.py` | Modify | Add `recovery_verdict`, `unified_plan`, `conflict_log` fields |
| `core/constraint_matrix.py` | Create | `build_constraint_matrix(state)` → weekly schedule dict |
| `agents/head_coach/resolver.py` | Create | `ConflictResolver.resolve()` — ACWR + overlap flags |
| `agents/head_coach/merger.py` | Create | `PlanMerger.merge()` — unified plan from partial plans |
| `agents/head_coach/graph.py` | Modify | Implement 3 stub nodes + fix `route_after_recovery_gate` None crash |
| `api/v1/workflow.py` | Create | `POST /plan`, `POST /plan/resume`, `POST /onboarding/init` |
| `api/main.py` | Modify | Mount workflow router |
| `tests/test_constraint_matrix.py` | Create | 5 tests |
| `tests/test_conflict_resolver.py` | Create | 4 tests |
| `tests/test_plan_merger.py` | Create | 3 tests |
| `tests/test_workflow_route.py` | Create | 4 tests |
| `CLAUDE.md` | Modify | S9 ✅ FAIT |

---

## Task 1: AthleteState new fields + build_constraint_matrix

**Files:**
- Modify: `models/athlete_state.py`
- Create: `core/constraint_matrix.py`
- Create: `tests/test_constraint_matrix.py`

### Background

`AthleteState` (models/athlete_state.py) extends `AthleteStateSchema` (models/schemas.py) and already has
`partial_plans`, `pending_conflicts`, `resolution_iterations`, `conflicts_resolved`, `constraint_matrix`.

We need three new optional fields (no breaking change):
- `recovery_verdict: dict | None = None` — stored by `node_recovery_gate`
- `unified_plan: dict | None = None` — stored by `node_merge_plans`
- `conflict_log: list[str]` — stored by `node_resolve_conflicts`

`AthleteProfile.available_days` is `dict[str, DayAvailability]` where `DayAvailability.available: bool`.
`AthleteState.lifting_profile.sessions_per_week: int` gives the desired number of lifting sessions.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_constraint_matrix.py
"""Tests for core/constraint_matrix.py — build_constraint_matrix()."""
import pytest


def _make_state(available_days: dict, lifting_sessions: int):
    """Helper: minimal AthleteState with custom availability."""
    from datetime import UTC, datetime
    from uuid import UUID
    from models.athlete_state import AthleteState

    return AthleteState(
        athlete_id=UUID("00000000-0000-0000-0000-000000000001"),
        updated_at=datetime.now(UTC),
        profile={
            "first_name": "Test",
            "age": 30,
            "sex": "M",
            "weight_kg": 75.0,
            "height_cm": 175,
            "active_sports": ["running", "lifting"],
            "available_days": available_days,
            "training_history": {
                "total_years_training": 3, "years_running": 1, "years_lifting": 2,
                "years_swimming": 0, "current_weekly_volume_hours": 5,
            },
            "lifestyle": {
                "work_type": "desk_sedentary", "work_hours_per_day": 8,
                "commute_active": False, "sleep_avg_hours": 7, "stress_level": "low",
            },
            "goals": {"primary": "get_fit", "timeline_weeks": 12},
            "equipment": {"gym_access": True, "pool_access": False, "outdoor_running": True},
        },
        current_phase={"macrocycle": "base_building", "mesocycle_week": 1, "mesocycle_length": 4},
        running_profile={
            "vdot": 38.2,
            "training_paces": {
                "easy_min_per_km": "6:24", "easy_max_per_km": "7:06",
                "threshold_pace_per_km": "5:18", "interval_pace_per_km": "4:48",
                "repetition_pace_per_km": "4:24", "long_run_pace_per_km": "6:36",
            },
            "weekly_km_current": 20, "weekly_km_target": 30, "max_long_run_km": 10,
        },
        lifting_profile={
            "training_split": "upper_lower",
            "sessions_per_week": lifting_sessions,
            "progression_model": "double_progression",
            "rir_target_range": [1, 3],
        },
        nutrition_profile={
            "tdee_estimated": 2600,
            "macros_target": {"protein_g": 150, "carbs_g": 280, "fat_g": 70},
        },
    )


_SIX_DAYS = {
    "monday":    {"available": True,  "max_hours": 1.5},
    "tuesday":   {"available": True,  "max_hours": 1.5},
    "wednesday": {"available": True,  "max_hours": 1.0},
    "thursday":  {"available": True,  "max_hours": 1.5},
    "friday":    {"available": False, "max_hours": 0},
    "saturday":  {"available": True,  "max_hours": 2.5},
    "sunday":    {"available": True,  "max_hours": 2.0},
}


def test_all_available_days_appear_in_result():
    """Every key in the result is a day name; all 7 days are present."""
    from core.constraint_matrix import build_constraint_matrix

    state = _make_state(_SIX_DAYS, lifting_sessions=2)
    result = build_constraint_matrix(state)

    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for day in days:
        assert day in result, f"Missing day: {day}"


def test_lifting_days_non_consecutive():
    """With 2 lifting sessions, no two lifted days are adjacent."""
    from core.constraint_matrix import build_constraint_matrix

    state = _make_state(_SIX_DAYS, lifting_sessions=2)
    result = build_constraint_matrix(state)

    day_order = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    lifting_days = [
        d for d in day_order
        if any(s["sport"] == "lifting" for s in result[d]["sessions"])
    ]
    assert len(lifting_days) == 2
    for i in range(len(lifting_days) - 1):
        idx_a = day_order.index(lifting_days[i])
        idx_b = day_order.index(lifting_days[i + 1])
        assert abs(idx_b - idx_a) > 1, f"Consecutive lifting days: {lifting_days[i]}, {lifting_days[i+1]}"


def test_running_fills_remaining_available_days():
    """Running sessions fill the available days not taken by lifting."""
    from core.constraint_matrix import build_constraint_matrix

    state = _make_state(_SIX_DAYS, lifting_sessions=2)
    result = build_constraint_matrix(state)

    running_days = [
        d for d in result
        if d not in ("total_sessions", "running_days", "lifting_days")
        and any(s["sport"] == "running" for s in result[d]["sessions"])
    ]
    assert result["running_days"] == len(running_days)
    assert result["lifting_days"] == 2
    assert result["total_sessions"] == result["running_days"] + result["lifting_days"]


def test_empty_available_days_no_crash():
    """No available days → empty schedule, no crash."""
    from core.constraint_matrix import build_constraint_matrix

    no_days = {d: {"available": False, "max_hours": 0} for d in
               ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]}
    state = _make_state(no_days, lifting_sessions=2)
    result = build_constraint_matrix(state)

    assert result["total_sessions"] == 0
    assert result["lifting_days"] == 0
    assert result["running_days"] == 0


def test_unavailable_day_has_no_sessions():
    """Friday (available=False in _SIX_DAYS) must have sessions=[]."""
    from core.constraint_matrix import build_constraint_matrix

    state = _make_state(_SIX_DAYS, lifting_sessions=2)
    result = build_constraint_matrix(state)

    assert result["friday"]["sessions"] == []
    assert result["friday"]["available"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

```
poetry run pytest tests/test_constraint_matrix.py -v
```

Expected: `ImportError: cannot import name 'build_constraint_matrix'`

- [ ] **Step 3: Add 3 fields to AthleteState**

In `models/athlete_state.py`, after `conflicts_resolved: bool = True`, add:

```python
    # ── S9 — Résultats des nœuds orchestration ───────────────────────────────
    recovery_verdict: dict | None = None
    unified_plan: dict | None = None
    conflict_log: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Create core/constraint_matrix.py**

```python
"""
Constraint Matrix Builder — core/constraint_matrix.py
Builds a weekly session schedule from the athlete's availability and training goals.
"""
from __future__ import annotations

from models.athlete_state import AthleteState

_DAY_ORDER = [
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
]


def build_constraint_matrix(state: AthleteState) -> dict:
    """
    Build a weekly session schedule from the athlete's availability and goals.

    Returns a dict with one key per day (schedule info) plus summary keys:
        {
          "monday":   {"available": bool, "sessions": [{"sport": str, "type": str}]},
          ...
          "sunday":   {"available": bool, "sessions": [...]},
          "total_sessions": int,
          "running_days":   int,
          "lifting_days":   int,
        }
    """
    available_days: list[str] = [
        day for day in _DAY_ORDER
        if _is_available(state, day)
    ]

    lifting_count = min(
        state.lifting_profile.sessions_per_week,
        len(available_days),
    )

    lifting_days = _pick_non_consecutive(available_days, lifting_count)
    running_days = [d for d in available_days if d not in lifting_days]

    schedule: dict[str, dict] = {}
    for day in _DAY_ORDER:
        sessions = []
        if day in lifting_days:
            sessions.append({"sport": "lifting", "type": "primary"})
        elif day in running_days:
            sessions.append({"sport": "running", "type": "primary"})
        schedule[day] = {
            "available": day in available_days,
            "sessions": sessions,
        }

    return {
        **schedule,
        "total_sessions": len(lifting_days) + len(running_days),
        "running_days": len(running_days),
        "lifting_days": len(lifting_days),
    }


def _is_available(state: AthleteState, day: str) -> bool:
    """Return True if the athlete is available on this day."""
    day_info = state.profile.available_days.get(day)
    if day_info is None:
        return False
    # DayAvailability instance (after Pydantic coercion) or plain dict
    if hasattr(day_info, "available"):
        return bool(day_info.available)
    return bool(day_info.get("available", False))


def _pick_non_consecutive(days: list[str], count: int) -> list[str]:
    """
    Greedily pick `count` days, preferring non-consecutive spacing.
    Falls back to consecutive days if not enough non-consecutive options exist.
    """
    if count <= 0 or not days:
        return []

    indices = [_DAY_ORDER.index(d) for d in days if d in _DAY_ORDER]
    chosen: list[int] = []

    for idx in indices:
        if len(chosen) >= count:
            break
        if not chosen or abs(idx - chosen[-1]) > 1:
            chosen.append(idx)

    # Fill remaining slots allowing consecutive days
    for idx in indices:
        if len(chosen) >= count:
            break
        if idx not in chosen:
            chosen.append(idx)

    return [_DAY_ORDER[i] for i in sorted(chosen[:count])]
```

- [ ] **Step 5: Run tests to verify they pass**

```
poetry run pytest tests/test_constraint_matrix.py -v
```

Expected: 5 passed.

- [ ] **Step 6: Check ruff**

```
poetry run ruff check core/constraint_matrix.py models/athlete_state.py
```

Expected: no issues.

- [ ] **Step 7: Commit**

```bash
git add models/athlete_state.py core/constraint_matrix.py tests/test_constraint_matrix.py
git commit -m "feat: add AthleteState fields + build_constraint_matrix (S9 Task 1)"
```

---

## Task 2: ConflictResolver

**Files:**
- Create: `agents/head_coach/resolver.py`
- Create: `tests/test_conflict_resolver.py`

### Background

The `ConflictResolver` reads `state.acwr_computed` (or `state.fatigue.acwr`) and `state.constraint_matrix.schedule` to determine what modifications to apply to `partial_plans`. It does NOT modify sessions — it adds top-level modification keys (`intensity_reduction_pct`, `volume_reduction_pct`, `tier_max`) to each sport's plan dict. These keys are read downstream by `PlanMerger`.

`state.pending_conflicts` (list of conflict dicts) is populated by `node_detect_conflicts()` in graph.py. The resolver can re-use this data or detect independently from ACWR.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_conflict_resolver.py
"""Tests for agents/head_coach/resolver.py — ConflictResolver."""
import pytest


def _make_minimal_state(acwr: float):
    """Create a minimal AthleteState with given ACWR."""
    from datetime import UTC, datetime
    from uuid import UUID
    from models.athlete_state import AthleteState

    state = AthleteState(
        athlete_id=UUID("00000000-0000-0000-0000-000000000001"),
        updated_at=datetime.now(UTC),
        profile={
            "first_name": "Test", "age": 30, "sex": "M",
            "weight_kg": 75.0, "height_cm": 175,
            "active_sports": ["running", "lifting"],
            "available_days": {},
            "training_history": {
                "total_years_training": 3, "years_running": 1, "years_lifting": 2,
                "years_swimming": 0, "current_weekly_volume_hours": 5,
            },
            "lifestyle": {
                "work_type": "desk_sedentary", "work_hours_per_day": 8,
                "commute_active": False, "sleep_avg_hours": 7, "stress_level": "low",
            },
            "goals": {"primary": "get_fit", "timeline_weeks": 12},
            "equipment": {"gym_access": True, "pool_access": False, "outdoor_running": True},
        },
        current_phase={"macrocycle": "base_building", "mesocycle_week": 1, "mesocycle_length": 4},
        running_profile={
            "vdot": 38.2,
            "training_paces": {
                "easy_min_per_km": "6:24", "easy_max_per_km": "7:06",
                "threshold_pace_per_km": "5:18", "interval_pace_per_km": "4:48",
                "repetition_pace_per_km": "4:24", "long_run_pace_per_km": "6:36",
            },
            "weekly_km_current": 20, "weekly_km_target": 30, "max_long_run_km": 10,
        },
        lifting_profile={
            "training_split": "upper_lower", "sessions_per_week": 3,
            "progression_model": "double_progression", "rir_target_range": [1, 3],
        },
        nutrition_profile={
            "tdee_estimated": 2600,
            "macros_target": {"protein_g": 150, "carbs_g": 280, "fat_g": 70},
        },
    )
    state.acwr_computed = acwr
    state.fatigue.acwr = acwr
    return state


_MOCK_PLANS = {
    "running": {"agent": "running_coach", "sessions": [], "coaching_notes": []},
    "lifting": {"agent": "lifting_coach", "sessions": [], "coaching_notes": []},
}


def test_no_conflicts_returns_unchanged_plans():
    """ACWR = 1.0 (safe zone) → plans unchanged, log is empty."""
    from agents.head_coach.resolver import ConflictResolver

    state = _make_minimal_state(acwr=1.0)
    resolver = ConflictResolver()
    resolved, log = resolver.resolve(state, _MOCK_PLANS)

    assert "intensity_reduction_pct" not in resolved.get("running", {})
    assert "volume_reduction_pct" not in resolved.get("running", {})
    assert log == []


def test_acwr_overload_adds_volume_reduction():
    """ACWR = 1.4 (1.3–1.5 caution zone) → volume_reduction_pct=20 in both plans."""
    from agents.head_coach.resolver import ConflictResolver

    state = _make_minimal_state(acwr=1.4)
    resolver = ConflictResolver()
    resolved, log = resolver.resolve(state, _MOCK_PLANS)

    assert resolved["running"]["volume_reduction_pct"] == 20
    assert resolved["lifting"]["volume_reduction_pct"] == 20
    assert len(log) == 1
    assert "acwr_overload" in log[0]


def test_acwr_danger_adds_intensity_reduction():
    """ACWR = 1.6 (>1.5 danger zone) → intensity_reduction_pct=30, tier_max=1 in both plans."""
    from agents.head_coach.resolver import ConflictResolver

    state = _make_minimal_state(acwr=1.6)
    resolver = ConflictResolver()
    resolved, log = resolver.resolve(state, _MOCK_PLANS)

    assert resolved["running"]["intensity_reduction_pct"] == 30
    assert resolved["running"]["tier_max"] == 1
    assert resolved["lifting"]["intensity_reduction_pct"] == 30
    assert resolved["lifting"]["tier_max"] == 1
    assert len(log) == 1
    assert "acwr_danger" in log[0]


def test_resolve_returns_tuple_of_dict_and_list():
    """resolve() always returns (dict, list[str]) even with no conflicts."""
    from agents.head_coach.resolver import ConflictResolver

    state = _make_minimal_state(acwr=0.9)
    resolver = ConflictResolver()
    result = resolver.resolve(state, {})

    assert isinstance(result, tuple)
    assert len(result) == 2
    resolved, log = result
    assert isinstance(resolved, dict)
    assert isinstance(log, list)
```

- [ ] **Step 2: Run tests to verify they fail**

```
poetry run pytest tests/test_conflict_resolver.py -v
```

Expected: `ImportError: cannot import name 'ConflictResolver'`

- [ ] **Step 3: Create agents/head_coach/resolver.py**

```python
"""
Conflict Resolver — agents/head_coach/resolver.py
Resolves scheduling and load conflicts between partial agent plans.
"""
from __future__ import annotations

from models.athlete_state import AthleteState

_DAY_ORDER = [
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
]


class ConflictResolver:
    """Applies ACWR-based and overlap-based modifications to partial plans."""

    MAX_ITERATIONS = 2

    def resolve(
        self, state: AthleteState, partial_plans: dict
    ) -> tuple[dict, list[str]]:
        """
        Detect and resolve conflicts between partial plans.

        Reads state.acwr_computed (or state.fatigue.acwr) and
        state.constraint_matrix.schedule for muscle overlap detection.

        Returns:
            (resolved_plans, conflict_log)
            - resolved_plans: shallow copies of partial_plans with modification keys added
            - conflict_log: list of strings describing each resolution
        """
        resolved = {sport: dict(plan) for sport, plan in partial_plans.items()}
        log: list[str] = []

        acwr = state.acwr_computed or state.fatigue.acwr or 0.0

        if acwr > 1.5:
            for sport in resolved:
                resolved[sport]["intensity_reduction_pct"] = 30
                resolved[sport]["tier_max"] = 1
            log.append(f"acwr_danger:{acwr:.2f} → intensity_reduction_pct=30, tier_max=1")

        elif acwr > 1.3:
            for sport in resolved:
                resolved[sport]["volume_reduction_pct"] = 20
            log.append(f"acwr_overload:{acwr:.2f} → volume_reduction_pct=20")

        overlap_log = self._detect_muscle_overlap(state)
        log.extend(overlap_log)

        return resolved, log

    def _detect_muscle_overlap(self, state: AthleteState) -> list[str]:
        """
        Detect days where running and leg-heavy lifting overlap in the
        constraint matrix schedule. Flags only (no structural plan change).
        """
        log: list[str] = []
        schedule = state.constraint_matrix.schedule

        for day in _DAY_ORDER:
            day_info = schedule.get(day, {})
            if not isinstance(day_info, dict):
                continue
            sessions = day_info.get("sessions", [])
            sports = {s.get("sport") for s in sessions if isinstance(s, dict)}
            if "running" in sports and "lifting" in sports:
                log.append(f"muscle_overlap:{day} → running+lifting same day flagged")

        return log
```

- [ ] **Step 4: Run tests to verify they pass**

```
poetry run pytest tests/test_conflict_resolver.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Check ruff**

```
poetry run ruff check agents/head_coach/resolver.py
```

Expected: no issues.

- [ ] **Step 6: Commit**

```bash
git add agents/head_coach/resolver.py tests/test_conflict_resolver.py
git commit -m "feat: implement ConflictResolver (S9 Task 2)"
```

---

## Task 3: PlanMerger

**Files:**
- Create: `agents/head_coach/merger.py`
- Create: `tests/test_plan_merger.py`

### Background

`PlanMerger.merge()` combines `partial_plans["running"]` and `partial_plans["lifting"]` into one unified weekly plan. Sessions are assigned to days from `state.constraint_matrix.schedule`. If the schedule is empty (e.g., in tests without matrix init), sessions get sequential fallback day labels.

The unified plan format:
```json
{
  "agent": "head_coach",
  "week": 3,
  "phase": "base_building",
  "sessions": [
    {"day": "monday", "sport": "lifting", "workout": {...}},
    {"day": "tuesday", "sport": "running", "workout": {...}}
  ],
  "acwr": 1.05,
  "conflicts_resolved": ["acwr_overload:1.35 → volume_reduction_pct=20"],
  "coaching_summary": ""
}
```

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_plan_merger.py
"""Tests for agents/head_coach/merger.py — PlanMerger."""


def _make_state_with_schedule():
    """Simon-like state with a pre-built constraint matrix schedule."""
    from datetime import UTC, datetime
    from uuid import UUID
    from models.athlete_state import AthleteState

    state = AthleteState(
        athlete_id=UUID("00000000-0000-0000-0000-000000000001"),
        updated_at=datetime.now(UTC),
        profile={
            "first_name": "Test", "age": 30, "sex": "M",
            "weight_kg": 75.0, "height_cm": 175,
            "active_sports": ["running", "lifting"],
            "available_days": {},
            "training_history": {
                "total_years_training": 3, "years_running": 1, "years_lifting": 2,
                "years_swimming": 0, "current_weekly_volume_hours": 5,
            },
            "lifestyle": {
                "work_type": "desk_sedentary", "work_hours_per_day": 8,
                "commute_active": False, "sleep_avg_hours": 7, "stress_level": "low",
            },
            "goals": {"primary": "get_fit", "timeline_weeks": 12},
            "equipment": {"gym_access": True, "pool_access": False, "outdoor_running": True},
        },
        current_phase={"macrocycle": "base_building", "mesocycle_week": 3, "mesocycle_length": 4},
        running_profile={
            "vdot": 38.2,
            "training_paces": {
                "easy_min_per_km": "6:24", "easy_max_per_km": "7:06",
                "threshold_pace_per_km": "5:18", "interval_pace_per_km": "4:48",
                "repetition_pace_per_km": "4:24", "long_run_pace_per_km": "6:36",
            },
            "weekly_km_current": 20, "weekly_km_target": 30, "max_long_run_km": 10,
        },
        lifting_profile={
            "training_split": "upper_lower", "sessions_per_week": 2,
            "progression_model": "double_progression", "rir_target_range": [1, 3],
        },
        nutrition_profile={
            "tdee_estimated": 2600,
            "macros_target": {"protein_g": 150, "carbs_g": 280, "fat_g": 70},
        },
    )
    # Pre-built schedule: monday=lifting, tuesday=running, thursday=lifting, saturday=running
    state.constraint_matrix.schedule = {
        "monday":    {"available": True,  "sessions": [{"sport": "lifting", "type": "primary"}]},
        "tuesday":   {"available": True,  "sessions": [{"sport": "running", "type": "primary"}]},
        "wednesday": {"available": False, "sessions": []},
        "thursday":  {"available": True,  "sessions": [{"sport": "lifting", "type": "primary"}]},
        "friday":    {"available": False, "sessions": []},
        "saturday":  {"available": True,  "sessions": [{"sport": "running", "type": "primary"}]},
        "sunday":    {"available": False, "sessions": []},
    }
    state.fatigue.acwr = 1.05
    return state


_MOCK_RUNNING_PLAN = {
    "agent": "running_coach",
    "sessions": [
        {"type": "easy", "distance_km": 6.0, "notes": "Easy Z1 run"},
        {"type": "long_run", "distance_km": 12.0, "notes": "Long run Z1"},
    ],
    "coaching_notes": [],
}

_MOCK_LIFTING_PLAN = {
    "agent": "lifting_coach",
    "sessions": [
        {"type": "upper_hypertrophy", "exercises": []},
        {"type": "lower_strength", "exercises": []},
    ],
    "coaching_notes": [],
}


def test_merge_returns_unified_structure():
    """merge() returns dict with all required keys."""
    from agents.head_coach.merger import PlanMerger

    state = _make_state_with_schedule()
    partial = {"running": _MOCK_RUNNING_PLAN, "lifting": _MOCK_LIFTING_PLAN}
    result = PlanMerger().merge(state, partial, conflict_log=[])

    assert result["agent"] == "head_coach"
    assert "week" in result
    assert "phase" in result
    assert "sessions" in result
    assert isinstance(result["sessions"], list)
    assert "acwr" in result
    assert "conflicts_resolved" in result
    assert "coaching_summary" in result


def test_sessions_sorted_by_day():
    """Sessions in the unified plan appear in Monday→Sunday order."""
    from agents.head_coach.merger import PlanMerger

    _DAY_ORDER = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    state = _make_state_with_schedule()
    partial = {"running": _MOCK_RUNNING_PLAN, "lifting": _MOCK_LIFTING_PLAN}
    result = PlanMerger().merge(state, partial, conflict_log=[])

    session_days = [s["day"] for s in result["sessions"] if s["day"] in _DAY_ORDER]
    assert session_days == sorted(session_days, key=lambda d: _DAY_ORDER.index(d))


def test_conflict_log_included():
    """conflict_log passed to merge() appears as conflicts_resolved in the plan."""
    from agents.head_coach.merger import PlanMerger

    state = _make_state_with_schedule()
    log = ["acwr_overload:1.40 → volume_reduction_pct=20"]
    result = PlanMerger().merge(state, {}, conflict_log=log)

    assert result["conflicts_resolved"] == log
```

- [ ] **Step 2: Run tests to verify they fail**

```
poetry run pytest tests/test_plan_merger.py -v
```

Expected: `ImportError: cannot import name 'PlanMerger'`

- [ ] **Step 3: Create agents/head_coach/merger.py**

```python
"""
Plan Merger — agents/head_coach/merger.py
Combines partial agent plans into a unified weekly plan.
"""
from __future__ import annotations

from models.athlete_state import AthleteState

_DAY_ORDER = [
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
]


class PlanMerger:
    """Merges running and lifting partial plans into a single unified weekly plan."""

    def merge(
        self,
        state: AthleteState,
        partial_plans: dict,
        conflict_log: list[str],
    ) -> dict:
        """
        Combine partial agent plans into a unified weekly plan.

        Args:
            state: current AthleteState (reads current_phase, fatigue, constraint_matrix)
            partial_plans: {"running": dict, "lifting": dict} from agent runs
            conflict_log: resolution strings from ConflictResolver

        Returns unified plan dict.
        """
        schedule = state.constraint_matrix.schedule

        running_days = self._days_for_sport(schedule, "running")
        lifting_days = self._days_for_sport(schedule, "lifting")

        sessions: list[dict] = []

        running_sessions = partial_plans.get("running", {}).get("sessions", [])
        for i, session in enumerate(running_sessions):
            day = running_days[i] if i < len(running_days) else f"day_r{i + 1}"
            sessions.append({"day": day, "sport": "running", "workout": session})

        lifting_sessions = partial_plans.get("lifting", {}).get("sessions", [])
        for i, session in enumerate(lifting_sessions):
            day = lifting_days[i] if i < len(lifting_days) else f"day_l{i + 1}"
            sessions.append({"day": day, "sport": "lifting", "workout": session})

        # Sort by day-of-week order (unknown/fallback days go last)
        day_idx = {day: i for i, day in enumerate(_DAY_ORDER)}
        sessions.sort(key=lambda s: day_idx.get(s["day"], 99))

        return {
            "agent": "head_coach",
            "week": state.current_phase.mesocycle_week,
            "phase": state.current_phase.macrocycle,
            "sessions": sessions,
            "acwr": state.fatigue.acwr,
            "conflicts_resolved": conflict_log,
            "coaching_summary": "",
        }

    def _days_for_sport(self, schedule: dict, sport: str) -> list[str]:
        """Return days assigned to a given sport, in day-of-week order."""
        return [
            day for day in _DAY_ORDER
            if isinstance(schedule.get(day), dict)
            and any(
                s.get("sport") == sport
                for s in schedule[day].get("sessions", [])
            )
        ]
```

- [ ] **Step 4: Run tests to verify they pass**

```
poetry run pytest tests/test_plan_merger.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Check ruff**

```
poetry run ruff check agents/head_coach/merger.py
```

Expected: no issues.

- [ ] **Step 6: Commit**

```bash
git add agents/head_coach/merger.py tests/test_plan_merger.py
git commit -m "feat: implement PlanMerger (S9 Task 3)"
```

---

## Task 4: Update graph.py — 3 stub nodes + route fix

**Files:**
- Modify: `agents/head_coach/graph.py`

### Background

Three stub nodes need implementations. The `route_after_recovery_gate` crashes on `None` because
`state.fatigue.recovery_score_today` defaults to `None`.

Imports to add at the top of graph.py:
```python
from agents.recovery_coach.agent import RecoveryCoachAgent
from agents.head_coach.resolver import ConflictResolver
from agents.head_coach.merger import PlanMerger
```

The existing test `test_graph_compiles` in `tests/test_head_coach_graph.py` must keep passing.

- [ ] **Step 1: Add imports to graph.py**

In `agents/head_coach/graph.py`, find this block:
```python
from agents.lifting_coach.agent import LiftingCoachAgent
from agents.running_coach.agent import RunningCoachAgent
```

Replace it with (keeping alphabetical order for ruff):
```python
from agents.head_coach.merger import PlanMerger
from agents.head_coach.resolver import ConflictResolver
from agents.lifting_coach.agent import LiftingCoachAgent
from agents.recovery_coach.agent import RecoveryCoachAgent
from agents.running_coach.agent import RunningCoachAgent
```

- [ ] **Step 2: Replace node_recovery_gate stub**

Find the existing `node_recovery_gate` function body (it currently ends with `return state` after a TODO comment). Replace the entire function with:

```python
def node_recovery_gate(state: AthleteState) -> AthleteState:
    """
    Nœud 2 : Recovery Coach évalue le readiness du jour.
    Calcule le Readiness Score et détermine vert/jaune/rouge.
    Stocke le verdict dans state.recovery_verdict.
    Met à jour state.fatigue.recovery_score_today pour la compatibilité aval.
    """
    agent = RecoveryCoachAgent()
    verdict = agent.run(state)
    state.recovery_verdict = verdict
    # Keep recovery_score_today in sync for node_recovery_blocked display
    score = verdict.get("readiness_score")
    if score is not None:
        state.fatigue.recovery_score_today = float(score)
    return state
```

- [ ] **Step 3: Fix route_after_recovery_gate**

Find the existing `route_after_recovery_gate` function. It currently contains:
```python
    if state.fatigue.recovery_score_today < 30:
        # Score < 30 = veto absolu, même le Head Coach ne peut pas override
        return "recovery_blocked"
    return "check_edge_cases"
```

Replace the entire function with:
```python
def route_after_recovery_gate(
    state: AthleteState,
) -> Literal["check_edge_cases", "recovery_blocked"]:
    """
    Après le Recovery Gate : si veto ROUGE absolu → fin (repos forcé).
    Sinon : continuer vers la vérification des edge cases.
    Uses recovery_verdict.color to avoid None crash on recovery_score_today.
    """
    verdict = state.recovery_verdict
    if verdict and verdict.get("color") == "red":
        return "recovery_blocked"
    return "check_edge_cases"
```

- [ ] **Step 4: Replace node_resolve_conflicts stub**

Find the existing `node_resolve_conflicts` function body (it ends with `# TODO Session 9` and `return state`). Replace the entire function with:

```python
def node_resolve_conflicts(state: AthleteState) -> AthleteState:
    """
    Nœud 7 : Résoudre les conflits inter-agents.
    Appelle ConflictResolver sur les plans partiels issus de node_delegate_to_agents.
    Incrémente resolution_iterations pour le circuit breaker.
    """
    resolver = ConflictResolver()
    resolved, log = resolver.resolve(state, state.partial_plans)
    state.partial_plans = resolved
    state.conflict_log = log
    state.resolution_iterations += 1
    # Resolver has applied all available modifications — proceed to merge
    state.conflicts_resolved = True
    return state
```

- [ ] **Step 5: Replace node_merge_plans stub**

Find the existing `node_merge_plans` function body (it ends with `# TODO Session 9` and `return state`). Replace the entire function with:

```python
def node_merge_plans(state: AthleteState) -> AthleteState:
    """
    Nœud 8 : Fusionner les plans partiels en un plan unifié.
    Stocke le résultat dans state.unified_plan.
    """
    merger = PlanMerger()
    state.unified_plan = merger.merge(state, state.partial_plans, state.conflict_log)
    return state
```

- [ ] **Step 6: Run existing graph tests**

```
poetry run pytest tests/test_head_coach_graph.py -v
```

Expected: 4 passed (test_graph_compiles, test_node_load_computes_acwr, test_node_detect_no_conflicts, test_node_detect_acwr_danger).

- [ ] **Step 7: Run full test suite to check no regressions**

```
poetry run pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: all existing tests pass (122+).

- [ ] **Step 8: Check ruff**

```
poetry run ruff check agents/head_coach/graph.py
```

Expected: no issues.

- [ ] **Step 9: Commit**

```bash
git add agents/head_coach/graph.py
git commit -m "feat: implement graph.py stub nodes + fix route_after_recovery_gate (S9 Task 4)"
```

---

## Task 5: Workflow API routes + mount

**Files:**
- Create: `api/v1/workflow.py`
- Modify: `api/main.py`
- Create: `tests/test_workflow_route.py`

### Background

The workflow routes expose the LangGraph `head_coach_graph` via REST. LangGraph 0.2.x pattern:
1. `graph.invoke(state, config=config)` runs the graph until END or an interrupt
2. After invoke, `graph.get_state(config).next` is non-empty if the graph is paused
3. To resume: `graph.invoke({"user_decision_input": decision}, config=config)` with the same thread_id

`head_coach_graph` is the singleton compiled graph imported from `agents.head_coach.graph`.

The existing `api/main.py` mounts routers like:
```python
app.include_router(plan_router, prefix="/api/v1/plan", tags=["plan"])
```

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_workflow_route.py
"""Tests for POST /api/v1/workflow routes. Graph always mocked — no real LangGraph run."""
from unittest.mock import MagicMock, patch


_MOCK_UNIFIED_PLAN = {
    "agent": "head_coach",
    "week": 3,
    "phase": "base_building",
    "sessions": [],
    "acwr": 1.05,
    "conflicts_resolved": [],
    "coaching_summary": "",
}


def test_post_plan_returns_200_complete(simon_pydantic_state):
    """POST /api/v1/workflow/plan with healthy state → 200 + unified_plan."""
    from api.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)

    mock_invoke_result = {**simon_pydantic_state.model_dump(mode="json"), "unified_plan": _MOCK_UNIFIED_PLAN}
    mock_graph_state = MagicMock()
    mock_graph_state.next = []  # No pending nodes → complete

    with patch("api.v1.workflow.head_coach_graph") as mock_graph:
        mock_graph.invoke.return_value = mock_invoke_result
        mock_graph.get_state.return_value = mock_graph_state

        response = client.post(
            "/api/v1/workflow/plan",
            json={"athlete_state": simon_pydantic_state.model_dump(mode="json")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "complete"
    assert "unified_plan" in data


def test_post_plan_returns_202_on_interrupt(simon_pydantic_state):
    """POST /api/v1/workflow/plan when graph is interrupted → 202 + thread_id."""
    from api.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)

    mock_invoke_result = {
        **simon_pydantic_state.model_dump(mode="json"),
        "pending_decision": {"conflict_id": "PLAN_CONFIRMATION", "status": "awaiting_user_input"},
    }
    mock_graph_state = MagicMock()
    mock_graph_state.next = ["present_plan"]  # Graph still has pending nodes → interrupted

    with patch("api.v1.workflow.head_coach_graph") as mock_graph:
        mock_graph.invoke.return_value = mock_invoke_result
        mock_graph.get_state.return_value = mock_graph_state

        response = client.post(
            "/api/v1/workflow/plan",
            json={"athlete_state": simon_pydantic_state.model_dump(mode="json")},
        )

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "awaiting_decision"
    assert "thread_id" in data


def test_post_plan_invalid_body():
    """POST /api/v1/workflow/plan with invalid athlete_state → 422."""
    from api.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)

    response = client.post(
        "/api/v1/workflow/plan",
        json={"athlete_state": {"invalid_field": "bad"}},
    )

    assert response.status_code == 422


def test_post_resume_plan_complete(simon_pydantic_state):
    """POST /api/v1/workflow/plan/resume with valid thread_id → 200 complete."""
    from api.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)

    # First call: graph is interrupted
    mock_state_interrupted = MagicMock()
    mock_state_interrupted.next = ["present_plan"]

    # Second call: graph is complete
    mock_state_complete = MagicMock()
    mock_state_complete.next = []

    mock_invoke_result = {**simon_pydantic_state.model_dump(mode="json"), "unified_plan": _MOCK_UNIFIED_PLAN}

    with patch("api.v1.workflow.head_coach_graph") as mock_graph:
        mock_graph.get_state.side_effect = [mock_state_interrupted, mock_state_complete]
        mock_graph.invoke.return_value = mock_invoke_result

        response = client.post(
            "/api/v1/workflow/plan/resume",
            json={"thread_id": "test-thread-123", "user_decision": "CONFIRM"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "complete"
```

- [ ] **Step 2: Run tests to verify they fail**

```
poetry run pytest tests/test_workflow_route.py -v
```

Expected: 4 failures (ImportError or 404 for routes not yet mounted).

- [ ] **Step 3: Create api/v1/workflow.py**

```python
"""
Workflow routes — api/v1/workflow.py
POST /workflow/plan         : run the full Head Coach LangGraph workflow
POST /workflow/plan/resume  : resume an interrupted workflow
POST /workflow/onboarding/init : initialize AthleteState with constraint matrix
"""
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from agents.head_coach.graph import head_coach_graph
from core.constraint_matrix import build_constraint_matrix
from models.athlete_state import AthleteState

router = APIRouter()


class PlanRequest(BaseModel):
    athlete_state: dict
    thread_id: str | None = None


class ResumeRequest(BaseModel):
    thread_id: str
    user_decision: str


@router.post("/plan")
def generate_plan(body: PlanRequest):
    """
    Run the Head Coach LangGraph workflow.

    Returns 200 {status:"complete", unified_plan} if graph reaches END,
    or 202 {status:"awaiting_decision", thread_id, pending_decision} if interrupted.
    """
    try:
        state = AthleteState.model_validate(body.athlete_state)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    thread_id = body.thread_id or str(uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    result = head_coach_graph.invoke(state, config=config)

    graph_state = head_coach_graph.get_state(config)
    if graph_state.next:
        pending = result.get("pending_decision") if isinstance(result, dict) else None
        return JSONResponse(
            status_code=202,
            content={
                "status": "awaiting_decision",
                "thread_id": thread_id,
                "pending_decision": pending,
            },
        )

    unified_plan = result.get("unified_plan") if isinstance(result, dict) else None
    return {"status": "complete", "unified_plan": unified_plan}


@router.post("/plan/resume")
def resume_plan(body: ResumeRequest):
    """
    Resume a workflow interrupted for human-in-the-loop decision.

    Returns same format as /plan (200 complete or 202 awaiting).
    """
    config = {"configurable": {"thread_id": body.thread_id}}

    graph_state = head_coach_graph.get_state(config)
    if not graph_state.next:
        raise HTTPException(status_code=404, detail="Thread not found or already complete.")

    result = head_coach_graph.invoke(
        {"user_decision_input": body.user_decision},
        config=config,
    )

    graph_state = head_coach_graph.get_state(config)
    if graph_state.next:
        pending = result.get("pending_decision") if isinstance(result, dict) else None
        return JSONResponse(
            status_code=202,
            content={
                "status": "awaiting_decision",
                "thread_id": body.thread_id,
                "pending_decision": pending,
            },
        )

    unified_plan = result.get("unified_plan") if isinstance(result, dict) else None
    return {"status": "complete", "unified_plan": unified_plan}


@router.post("/onboarding/init")
def init_onboarding(body: dict):
    """
    Accept a complete athlete profile dict, validate as AthleteState,
    build the constraint matrix, and return the initialized state.
    """
    try:
        state = AthleteState.model_validate(body)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    matrix = build_constraint_matrix(state)
    # Store in constraint_matrix.schedule (preserving existing _daily_loads_28d if any)
    for day, info in matrix.items():
        if day not in ("total_sessions", "running_days", "lifting_days"):
            state.constraint_matrix.schedule[day] = info

    result = state.model_dump(mode="json")
    result["constraint_matrix_summary"] = {
        "total_sessions": matrix["total_sessions"],
        "running_days": matrix["running_days"],
        "lifting_days": matrix["lifting_days"],
    }
    return result
```

- [ ] **Step 4: Mount workflow router in api/main.py**

Add import and `include_router` to `api/main.py`. The full updated file:

```python
"""
FastAPI application stub — Resilio+
S11 complétera : auth JWT, middleware CORS, autres routers.
"""

from fastapi import FastAPI

from api.v1.apple_health import router as apple_health_router
from api.v1.connectors import router as connectors_router
from api.v1.files import router as files_router
from api.v1.food import router as food_router
from api.v1.plan import router as plan_router
from api.v1.workflow import router as workflow_router

app = FastAPI(title="Resilio+", version="0.1.0")

app.include_router(
    connectors_router,
    prefix="/api/v1/connectors",
    tags=["connectors"],
)
app.include_router(
    apple_health_router,
    prefix="/api/v1/connectors",
    tags=["apple-health"],
)
app.include_router(
    files_router,
    prefix="/api/v1/connectors",
    tags=["files"],
)
app.include_router(
    food_router,
    prefix="/api/v1/connectors",
    tags=["food"],
)
app.include_router(
    plan_router,
    prefix="/api/v1/plan",
    tags=["plan"],
)
app.include_router(
    workflow_router,
    prefix="/api/v1/workflow",
    tags=["workflow"],
)
```

- [ ] **Step 5: Run workflow tests**

```
poetry run pytest tests/test_workflow_route.py -v
```

Expected: 4 passed.

- [ ] **Step 6: Run full test suite**

```
poetry run pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: all tests pass (~138 total).

- [ ] **Step 7: Check ruff**

```
poetry run ruff check api/v1/workflow.py api/main.py
```

Expected: no issues.

- [ ] **Step 8: Commit**

```bash
git add api/v1/workflow.py api/main.py tests/test_workflow_route.py
git commit -m "feat: add workflow API routes + mount router (S9 Task 5)"
```

---

## Task 6: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update CLAUDE.md**

In the session table, change S9 from `⬜ À FAIRE` to `✅ FAIT`.

Find:
```
| **S9** | Workflow | Onboarding 7 blocs + création de plan + audit conflits | ⬜ À FAIRE |
```

Replace with:
```
| **S9** | Workflow | Constraint matrix + ConflictResolver + PlanMerger + graph stub nodes + workflow API | ✅ FAIT |
```

In the repo structure tree, update `plan.py` line:
```
│       └── plan.py                   ← ✅ S6 — POST /plan/running
```
→
```
│       ├── plan.py                   ← ✅ S6–S8 — POST /plan/running, /lifting, /recovery
│       └── workflow.py               ← ✅ S9 — POST /workflow/plan, /plan/resume, /onboarding/init
```

Add new files to the agents section:
```
│   ├── head_coach/
│   │   ├── ...
│   │   ├── resolver.py               ← ✅ S9 — ConflictResolver (ACWR + overlap flags)
│   │   └── merger.py                 ← ✅ S9 — PlanMerger (unified weekly plan)
```

Add to tests section:
```
│   ├── test_constraint_matrix.py     ← ✅ S9 — 5 tests build_constraint_matrix
│   ├── test_conflict_resolver.py     ← ✅ S9 — 4 tests ConflictResolver
│   ├── test_plan_merger.py           ← ✅ S9 — 3 tests PlanMerger
│   └── test_workflow_route.py        ← ✅ S9 — 4 tests workflow API (~138 tests total)
```

Add to core section:
```
├── core/
│   ├── ...
│   └── constraint_matrix.py          ← ✅ S9 — build_constraint_matrix()
```

Update total test count: `122 → ~138 tests`.

- [ ] **Step 2: Verify all tests still pass**

```
poetry run pytest tests/ --tb=short -q
```

Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md — S9 ✅ FAIT (138 tests)"
```
