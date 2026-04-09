# Session 10 — Weekly Review Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the H1-H4 weekly review loop — planned vs actual analysis, ACWR recalculation, adjustment recommendations, and a coaching report — exposed via `POST /api/v1/workflow/weekly-review`.

**Architecture:** Four-node LangGraph (`wr_collect → wr_analyze → wr_adjust → wr_report`) compiled without MemorySaver (stateless single-pass). Node functions live in `agents/head_coach/weekly_nodes.py`; the graph singleton and `build_weekly_review_graph()` are added to the existing `agents/head_coach/graph.py`. A new `WeeklyReviewState` model (composition with `AthleteState`) drives the graph; `WeeklyAnalyzer` and `WeeklyAdjuster` in `core/weekly_review.py` contain all the domain logic.

**Tech Stack:** Python 3.11, FastAPI, LangGraph 0.2.x, Pydantic v2, Anthropic SDK, pytest, ruff.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `models/weekly_review.py` | Create | `ActualWorkout` + `WeeklyReviewState` models |
| `core/weekly_review.py` | Create | `WeeklyAnalyzer` (TRIMP, completion) + `WeeklyAdjuster` (ACWR, rules) |
| `agents/head_coach/weekly_nodes.py` | Create | 4 LangGraph node functions + `_get_weekly_notes` LLM helper |
| `agents/head_coach/graph.py` | Modify | Replace `build_weekly_review_graph()` stub + add singleton |
| `api/v1/workflow.py` | Modify | Add `POST /workflow/weekly-review` route |
| `tests/test_weekly_review.py` | Create | 6 unit tests for Analyzer + Adjuster |
| `tests/test_weekly_review_route.py` | Create | 3 route tests |
| `CLAUDE.md` | Modify | Mark S10 ✅ FAIT, update file tree and test count |

---

## Task 1: Models — `ActualWorkout` + `WeeklyReviewState`

**Files:**
- Create: `models/weekly_review.py`

- [ ] **Step 1: Create `models/weekly_review.py`**

```python
# models/weekly_review.py
"""
WeeklyReviewState — état LangGraph pour le weekly review graph (H1-H4).
Distinct de AthleteState : composition, pas héritage.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from models.athlete_state import AthleteState


class ActualWorkout(BaseModel):
    """One completed (or missed) session from the past week."""

    sport: Literal["running", "lifting"]
    date: str  # "YYYY-MM-DD"
    completed: bool
    actual_data: dict = {}
    # Running actual_data keys: duration_min, avg_hr, type ("easy"|"tempo"|"interval")
    # Lifting actual_data keys: duration_min, session_type ("hypertrophy"|"strength"|"power")


class WeeklyReviewState(BaseModel):
    """LangGraph state for the weekly review graph."""

    model_config = ConfigDict(frozen=False)

    athlete_state: AthleteState
    actual_workouts: list[ActualWorkout] = Field(default_factory=list)

    # Written by graph nodes
    analysis: dict | None = None          # WeeklyAnalyzer output
    adjustments: list[dict] = Field(default_factory=list)  # WeeklyAdjuster output
    acwr_before: float | None = None      # ACWR captured before node_wr_adjust overwrites it
    acwr_after: float | None = None       # Recalculated ACWR
    report: dict | None = None            # Final report
```

- [ ] **Step 2: Verify import works**

```bash
cd C:/resilio-plus && poetry run python -c "from models.weekly_review import ActualWorkout, WeeklyReviewState; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add models/weekly_review.py
git commit -m "feat: add ActualWorkout and WeeklyReviewState models (S10)"
```

---

## Task 2: `WeeklyAnalyzer` — TRIMP + completion analysis

**Files:**
- Create: `core/weekly_review.py`
- Create: `tests/test_weekly_review.py` (first 3 tests)

- [ ] **Step 1: Write the 3 failing analyzer tests**

```python
# tests/test_weekly_review.py
"""Unit tests for WeeklyAnalyzer and WeeklyAdjuster."""
import pytest

from models.weekly_review import ActualWorkout


# ── helpers ──────────────────────────────────────────────────────────────────

def _run(date="2026-04-07", completed=True, duration_min=60, workout_type="easy", avg_hr=None):
    actual_data: dict = {"duration_min": duration_min, "type": workout_type}
    if avg_hr is not None:
        actual_data["avg_hr"] = avg_hr
    return ActualWorkout(sport="running", date=date, completed=completed, actual_data=actual_data)


def _lift(date="2026-04-08", completed=True, duration_min=60, session_type="hypertrophy"):
    return ActualWorkout(
        sport="lifting",
        date=date,
        completed=completed,
        actual_data={"duration_min": duration_min, "session_type": session_type},
    )


# ── WeeklyAnalyzer ────────────────────────────────────────────────────────────

def test_analyzer_all_completed():
    """All sessions completed → completion_rate=1.0."""
    from core.weekly_review import WeeklyAnalyzer

    workouts = [_run("2026-04-07"), _lift("2026-04-08")]
    planned = [{"id": 1}, {"id": 2}]
    result = WeeklyAnalyzer().analyze(planned, workouts)
    assert result["completion_rate"] == 1.0
    assert result["sessions_completed"] == 2
    assert result["sessions_planned"] == 2


def test_analyzer_partial_completion():
    """3 of 5 sessions completed → completion_rate=0.6."""
    from core.weekly_review import WeeklyAnalyzer

    workouts = [
        _run("2026-04-07", completed=True),
        _run("2026-04-08", completed=False),
        _lift("2026-04-09", completed=True),
        _lift("2026-04-10", completed=False),
        _run("2026-04-11", completed=True),
    ]
    planned = [{"id": i} for i in range(5)]
    result = WeeklyAnalyzer().analyze(planned, workouts)
    assert result["completion_rate"] == pytest.approx(0.6)
    assert result["sessions_completed"] == 3
    assert result["sessions_planned"] == 5


def test_analyzer_trimp_running_easy():
    """Easy run 60 min → TRIMP=60 (factor 1.0). 2026-04-07 is a Monday → week_loads[0]=60."""
    from core.weekly_review import WeeklyAnalyzer

    workout = _run("2026-04-07", duration_min=60, workout_type="easy")
    result = WeeklyAnalyzer().analyze([], [workout])
    assert result["trimp_total"] == pytest.approx(60.0)
    assert result["trimp_by_sport"]["running"] == pytest.approx(60.0)
    assert result["week_loads"][0] == pytest.approx(60.0)  # Monday = index 0
    assert len(result["week_loads"]) == 7
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd C:/resilio-plus && poetry run pytest tests/test_weekly_review.py::test_analyzer_all_completed tests/test_weekly_review.py::test_analyzer_partial_completion tests/test_weekly_review.py::test_analyzer_trimp_running_easy -v
```

Expected: 3 FAILED (ImportError — `core.weekly_review` does not exist yet)

- [ ] **Step 3: Create `core/weekly_review.py` with `WeeklyAnalyzer`**

```python
# core/weekly_review.py
"""
WeeklyAnalyzer  — planned vs actual session analysis + TRIMP calculation.
WeeklyAdjuster  — ACWR recalculation + adjustment rule engine.
"""
from __future__ import annotations

from datetime import datetime

from core.acwr import compute_ewma_acwr
from models.weekly_review import ActualWorkout

# ── TRIMP intensity factors ───────────────────────────────────────────────────
# Running: Z1=easy(1.0), Z2=tempo(1.5), Z3=interval(2.5), unknown(1.2)
# Lifting: hypertrophy(0.8), strength/power(1.2), default(1.0)

_RUN_TYPE_FACTOR: dict[str, float] = {
    "easy": 1.0,
    "tempo": 1.5,
    "interval": 2.5,
}
_LIFT_TYPE_FACTOR: dict[str, float] = {
    "hypertrophy": 0.8,
    "strength": 1.2,
    "power": 1.2,
}

# HRmax thresholds for avg_hr zone detection (assuming max_hr ≈ 185 bpm for V1)
_HR_Z1_MAX = 138   # < 75% of 185
_HR_Z2_MAX = 162   # < 88% of 185


def _running_factor(actual_data: dict) -> float:
    """Return TRIMP intensity factor for a running workout."""
    avg_hr = actual_data.get("avg_hr")
    if avg_hr is not None:
        if avg_hr < _HR_Z1_MAX:
            return 1.0
        if avg_hr <= _HR_Z2_MAX:
            return 1.5
        return 2.5
    workout_type = actual_data.get("type", "")
    return _RUN_TYPE_FACTOR.get(workout_type, 1.2)


def _lifting_factor(actual_data: dict) -> float:
    """Return TRIMP intensity factor for a lifting workout."""
    session_type = actual_data.get("session_type", "")
    return _LIFT_TYPE_FACTOR.get(session_type, 1.0)


def _trimp(workout: ActualWorkout) -> float:
    """Compute TRIMP for a single completed workout."""
    duration = workout.actual_data.get("duration_min", 60)
    if workout.sport == "running":
        return duration * _running_factor(workout.actual_data)
    return duration * _lifting_factor(workout.actual_data)


def _day_index(date_str: str) -> int:
    """Return 0-based weekday index (0=Monday) for a 'YYYY-MM-DD' string."""
    return datetime.strptime(date_str, "%Y-%m-%d").weekday()


class WeeklyAnalyzer:
    def analyze(
        self,
        planned_sessions: list[dict],
        actual_workouts: list[ActualWorkout],
    ) -> dict:
        """
        Compare planned sessions against actuals.

        Returns:
            {
              "completion_rate": float,
              "sessions_planned": int,
              "sessions_completed": int,
              "trimp_total": float,
              "trimp_by_sport": {"running": float, "lifting": float},
              "week_loads": list[float],   # 7 daily TRIMP values (Mon–Sun)
            }
        """
        sessions_planned = len(planned_sessions) if planned_sessions else len(actual_workouts)
        sessions_completed = sum(1 for w in actual_workouts if w.completed)
        completion_rate = (
            sessions_completed / sessions_planned if sessions_planned > 0 else 0.0
        )

        trimp_by_sport: dict[str, float] = {"running": 0.0, "lifting": 0.0}
        week_loads = [0.0] * 7

        for workout in actual_workouts:
            if not workout.completed:
                continue
            t = _trimp(workout)
            trimp_by_sport[workout.sport] = trimp_by_sport.get(workout.sport, 0.0) + t
            day_idx = _day_index(workout.date)
            week_loads[day_idx] += t

        trimp_total = sum(trimp_by_sport.values())

        return {
            "completion_rate": completion_rate,
            "sessions_planned": sessions_planned,
            "sessions_completed": sessions_completed,
            "trimp_total": trimp_total,
            "trimp_by_sport": trimp_by_sport,
            "week_loads": week_loads,
        }
```

- [ ] **Step 4: Run the 3 analyzer tests to verify they pass**

```bash
cd C:/resilio-plus && poetry run pytest tests/test_weekly_review.py::test_analyzer_all_completed tests/test_weekly_review.py::test_analyzer_partial_completion tests/test_weekly_review.py::test_analyzer_trimp_running_easy -v
```

Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add core/weekly_review.py tests/test_weekly_review.py
git commit -m "feat: add WeeklyAnalyzer with TRIMP calculation + 3 tests (S10)"
```

---

## Task 3: `WeeklyAdjuster` — ACWR recalculation + adjustment rules

**Files:**
- Modify: `core/weekly_review.py` (add `WeeklyAdjuster` class)
- Modify: `tests/test_weekly_review.py` (add 3 adjuster tests)

- [ ] **Step 1: Add the 3 failing adjuster tests to `tests/test_weekly_review.py`**

Append after the last analyzer test:

```python
# ── WeeklyAdjuster ────────────────────────────────────────────────────────────

def test_adjuster_low_completion_suggests_reduction():
    """completion_rate=0.5, no history → adjustments has volume_reduction."""
    from core.weekly_review import WeeklyAdjuster

    analysis = {"completion_rate": 0.5, "week_loads": [0.0] * 7}
    adjustments, acwr_new = WeeklyAdjuster().adjust(analysis, [], None)
    assert acwr_new is None  # no history → no ACWR
    types = [a["type"] for a in adjustments]
    assert "volume_reduction" in types
    vol = next(a for a in adjustments if a["type"] == "volume_reduction")
    assert vol["reason"] == "low_completion"
    assert vol["pct"] == 10


def test_adjuster_acwr_danger_suggests_rest():
    """21 days×10 + 7 days×40 → ACWR>1.5 → rest_week adjustment."""
    from core.weekly_review import WeeklyAdjuster

    daily_loads_28d = [10.0] * 21
    week_loads = [40.0] * 7
    analysis = {"completion_rate": 0.9, "week_loads": week_loads}
    adjustments, acwr_new = WeeklyAdjuster().adjust(analysis, daily_loads_28d, None)
    assert acwr_new is not None
    assert acwr_new > 1.5
    types = [a["type"] for a in adjustments]
    assert "rest_week" in types
    assert "intensity_reduction" not in types  # rule 2 fires, rule 3 skipped


def test_adjuster_healthy_load_no_adjustments():
    """completion_rate=0.9, ACWR≈1.02 → adjustments=[]."""
    from core.weekly_review import WeeklyAdjuster

    daily_loads_28d = [50.0] * 21
    week_loads = [52.0] * 7
    analysis = {"completion_rate": 0.9, "week_loads": week_loads}
    adjustments, acwr_new = WeeklyAdjuster().adjust(analysis, daily_loads_28d, None)
    assert acwr_new is not None
    assert 0.8 <= acwr_new <= 1.3
    assert adjustments == []
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd C:/resilio-plus && poetry run pytest tests/test_weekly_review.py::test_adjuster_low_completion_suggests_reduction tests/test_weekly_review.py::test_adjuster_acwr_danger_suggests_rest tests/test_weekly_review.py::test_adjuster_healthy_load_no_adjustments -v
```

Expected: 3 FAILED (ImportError — `WeeklyAdjuster` not defined yet)

- [ ] **Step 3: Add `WeeklyAdjuster` to `core/weekly_review.py`**

Append after the `WeeklyAnalyzer` class:

```python

class WeeklyAdjuster:
    def adjust(
        self,
        analysis: dict,
        daily_loads_28d: list[float],
        fatigue_state,  # FatigueState | None — reserved for future use
    ) -> tuple[list[dict], float | None]:
        """
        Recalculate ACWR and generate adjustment recommendations.

        Args:
            analysis: output of WeeklyAnalyzer.analyze()
            daily_loads_28d: existing 28-day load history from constraint_matrix
            fatigue_state: state.fatigue (reserved, not used in V1 calculation)

        Returns:
            (adjustments, acwr_new)
            - adjustments: list of {type, reason, pct?}
            - acwr_new: recalculated float, or None if no history
        """
        week_loads: list[float] = analysis["week_loads"]

        # ── ACWR recalculation ────────────────────────────────────────────────
        if not daily_loads_28d:
            acwr_new = None
        else:
            updated = (daily_loads_28d + week_loads)[-28:]
            _, _, acwr_new = compute_ewma_acwr(updated)

        # ── Adjustment rules (evaluated in order, all that apply) ─────────────
        adjustments: list[dict] = []
        completion_rate: float = analysis["completion_rate"]

        # Rule 1: low completion
        if completion_rate < 0.70:
            adjustments.append({"type": "volume_reduction", "reason": "low_completion", "pct": 10})

        # Rules 2-4: ACWR-based (skip if no history)
        if acwr_new is not None:
            if acwr_new > 1.5:
                adjustments.append({"type": "rest_week", "reason": "acwr_danger"})
            elif acwr_new > 1.3:
                adjustments.append({"type": "intensity_reduction", "reason": "acwr_caution", "pct": 15})
            elif acwr_new < 0.8:
                adjustments.append({"type": "volume_increase", "reason": "acwr_low", "pct": 10})

        return adjustments, acwr_new
```

- [ ] **Step 4: Run all 6 weekly_review tests to verify they pass**

```bash
cd C:/resilio-plus && poetry run pytest tests/test_weekly_review.py -v
```

Expected: 6 PASSED

- [ ] **Step 5: Run full suite to verify no regressions**

```bash
cd C:/resilio-plus && poetry run pytest --tb=short -q
```

Expected: all existing tests still passing

- [ ] **Step 6: Commit**

```bash
git add core/weekly_review.py tests/test_weekly_review.py
git commit -m "feat: add WeeklyAdjuster with ACWR recalculation + 3 tests (S10)"
```

---

## Task 4: `weekly_nodes.py` — 4 LangGraph nodes + LLM helper

**Files:**
- Create: `agents/head_coach/weekly_nodes.py`

- [ ] **Step 1: Create `agents/head_coach/weekly_nodes.py`**

```python
# agents/head_coach/weekly_nodes.py
"""
Weekly review graph nodes (H1-H4) for Resilio+ Head Coach.

node_wr_collect  — H1: normalize actual_workouts (V1: data already in state)
node_wr_analyze  — H2: planned vs actual + TRIMP via WeeklyAnalyzer
node_wr_adjust   — H3: ACWR recalculation + adjustment rules via WeeklyAdjuster
node_wr_report   — H4: assemble final report + LLM coaching note
"""
import anthropic

from core.config import settings
from core.weekly_review import WeeklyAdjuster, WeeklyAnalyzer
from models.weekly_review import WeeklyReviewState


def node_wr_collect(state: WeeklyReviewState) -> WeeklyReviewState:
    """H1: Normalize actual_workouts — V1: data is already provided in state by the API caller."""
    # Future: pull from Strava/Hevy APIs here
    return state


def node_wr_analyze(state: WeeklyReviewState) -> WeeklyReviewState:
    """H2: Planned vs actual analysis + TRIMP calculation."""
    planned = (
        state.athlete_state.partial_plans.get("running", {}).get("sessions", [])
        + state.athlete_state.partial_plans.get("lifting", {}).get("sessions", [])
    )
    state.analysis = WeeklyAnalyzer().analyze(planned, state.actual_workouts)
    return state


def node_wr_adjust(state: WeeklyReviewState) -> WeeklyReviewState:
    """H3: ACWR recalculation + adjustment recommendations."""
    daily_loads: list[float] = state.athlete_state.constraint_matrix.schedule.get(
        "_daily_loads_28d", []
    )
    # Capture ACWR before overwriting it
    state.acwr_before = state.athlete_state.fatigue.acwr

    adjustments, acwr_new = WeeklyAdjuster().adjust(
        state.analysis,
        daily_loads,
        state.athlete_state.fatigue,
    )
    state.adjustments = adjustments
    state.acwr_after = acwr_new

    # Update the living constraint matrix with this week's loads
    if state.analysis:
        updated_loads = (daily_loads + state.analysis["week_loads"])[-28:]
        state.athlete_state.constraint_matrix.schedule["_daily_loads_28d"] = updated_loads

    # Sync fatigue.acwr forward
    if acwr_new is not None:
        state.athlete_state.fatigue.acwr = acwr_new

    return state


def node_wr_report(state: WeeklyReviewState) -> WeeklyReviewState:
    """H4: Assemble final report + LLM coaching note."""
    analysis = state.analysis or {}
    state.report = {
        "agent": "head_coach",
        "week_reviewed": state.athlete_state.current_phase.mesocycle_week,
        "completion_rate": analysis.get("completion_rate", 0.0),
        "sessions_completed": analysis.get("sessions_completed", 0),
        "sessions_planned": analysis.get("sessions_planned", 0),
        "trimp_total": analysis.get("trimp_total", 0.0),
        "acwr_before": state.acwr_before,
        "acwr_after": state.acwr_after,
        "adjustments": state.adjustments,
        "next_week_notes": _get_weekly_notes(state),
    }
    return state


def _get_weekly_notes(state: WeeklyReviewState) -> str:
    """
    Generate a 1-sentence coaching note via LLM.

    Returns "" on any exception (LLM unavailable, API key missing, etc.).
    """
    try:
        analysis = state.analysis or {}
        content = (
            f"Weekly review — completion: {analysis.get('completion_rate', 0):.0%}, "
            f"TRIMP total: {analysis.get('trimp_total', 0):.1f}, "
            f"ACWR before: {state.acwr_before}, after: {state.acwr_after}, "
            f"adjustments: {[a['type'] for a in state.adjustments]}. "
            "Write exactly 1 coaching sentence (max 300 chars, direct, no fluff)."
        )
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=100,
            messages=[{"role": "user", "content": content}],
        )
        return response.content[0].text.strip()[:300]
    except Exception:
        return ""
```

- [ ] **Step 2: Verify import works**

```bash
cd C:/resilio-plus && poetry run python -c "from agents.head_coach.weekly_nodes import node_wr_collect, node_wr_analyze, node_wr_adjust, node_wr_report, _get_weekly_notes; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add agents/head_coach/weekly_nodes.py
git commit -m "feat: add weekly review graph nodes H1-H4 (S10)"
```

---

## Task 5: `build_weekly_review_graph()` + singleton in `graph.py`

**Files:**
- Modify: `agents/head_coach/graph.py`

The file currently has a stub `build_weekly_review_graph()` that returns `None` (just a `pass`). Replace it with the real implementation and add the singleton.

- [ ] **Step 1: Add imports at the top of `agents/head_coach/graph.py`**

After the existing import block (after `from models.athlete_state import AthleteState`), add:

```python
from agents.head_coach.weekly_nodes import (
    node_wr_adjust,
    node_wr_analyze,
    node_wr_collect,
    node_wr_report,
)
from models.weekly_review import WeeklyReviewState
```

- [ ] **Step 2: Replace the stub `build_weekly_review_graph()` function**

Find and replace the entire stub (lines ~490-501):

```python
def build_weekly_review_graph() -> StateGraph:
    """
    Graph simplifié pour le suivi hebdomadaire.
    Différent du graph de création de plan initial.
    TODO Session 10 : implémenter complètement.
    """
    # H1: Collecte (pull Strava, Hevy, Apple Health)
    # H2: Analyse prévu vs réalisé
    # H3: ACWR update + matrice vivante + ajustements
    # H4: Rapport + feedback utilisateur
    # H5: Planification semaine suivante
    pass
```

Replace with:

```python
def build_weekly_review_graph() -> StateGraph:
    """
    Graph H1-H4 du weekly review.
    Stateless single-pass — pas de MemorySaver, pas d'interrupt.
    """
    builder = StateGraph(WeeklyReviewState)
    builder.add_node("wr_collect", node_wr_collect)
    builder.add_node("wr_analyze", node_wr_analyze)
    builder.add_node("wr_adjust",  node_wr_adjust)
    builder.add_node("wr_report",  node_wr_report)
    builder.add_edge(START, "wr_collect")
    builder.add_edge("wr_collect", "wr_analyze")
    builder.add_edge("wr_analyze", "wr_adjust")
    builder.add_edge("wr_adjust",  "wr_report")
    builder.add_edge("wr_report",  END)
    return builder.compile()  # No checkpointer — stateless single-pass
```

- [ ] **Step 3: Add the `weekly_review_graph` singleton**

After the existing line `head_coach_graph = build_head_coach_graph()` at the bottom of the file, add:

```python
weekly_review_graph = build_weekly_review_graph()
```

- [ ] **Step 4: Verify graph builds**

```bash
cd C:/resilio-plus && poetry run python -c "from agents.head_coach.graph import weekly_review_graph; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Run full suite to verify no regressions**

```bash
cd C:/resilio-plus && poetry run pytest --tb=short -q
```

Expected: all existing tests still passing

- [ ] **Step 6: Commit**

```bash
git add agents/head_coach/graph.py
git commit -m "feat: implement build_weekly_review_graph() + singleton (S10)"
```

---

## Task 6: `POST /workflow/weekly-review` route + 3 route tests

**Files:**
- Modify: `api/v1/workflow.py`
- Create: `tests/test_weekly_review_route.py`

- [ ] **Step 1: Write the 3 failing route tests**

```python
# tests/test_weekly_review_route.py
"""Tests for POST /api/v1/workflow/weekly-review. Graph always mocked — no real LangGraph run."""
from unittest.mock import patch


_MOCK_REPORT = {
    "agent": "head_coach",
    "week_reviewed": 3,
    "completion_rate": 0.8,
    "sessions_completed": 4,
    "sessions_planned": 5,
    "trimp_total": 280.0,
    "acwr_before": 1.05,
    "acwr_after": 1.1,
    "adjustments": [],
    "next_week_notes": "",
}


def test_post_weekly_review_returns_200(simon_pydantic_state):
    """POST /api/v1/workflow/weekly-review with valid state → 200 + report."""
    from api.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)

    with patch("api.v1.workflow.weekly_review_graph") as mock_graph:
        mock_graph.invoke.return_value = {"report": _MOCK_REPORT}

        response = client.post(
            "/api/v1/workflow/weekly-review",
            json={
                "athlete_state": simon_pydantic_state.model_dump(mode="json"),
                "actual_workouts": [],
            },
        )

    assert response.status_code == 200


def test_post_weekly_review_invalid_body():
    """POST /api/v1/workflow/weekly-review with bad athlete_state → 422."""
    from api.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)

    response = client.post(
        "/api/v1/workflow/weekly-review",
        json={"athlete_state": {"not_a_valid": "state"}, "actual_workouts": []},
    )

    assert response.status_code == 422


def test_post_weekly_review_report_structure(simon_pydantic_state):
    """POST /api/v1/workflow/weekly-review → report contains all required keys."""
    from api.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)

    with patch("api.v1.workflow.weekly_review_graph") as mock_graph:
        mock_graph.invoke.return_value = {"report": _MOCK_REPORT}

        response = client.post(
            "/api/v1/workflow/weekly-review",
            json={
                "athlete_state": simon_pydantic_state.model_dump(mode="json"),
                "actual_workouts": [
                    {
                        "sport": "running",
                        "date": "2026-04-07",
                        "completed": True,
                        "actual_data": {"duration_min": 45, "type": "easy"},
                    }
                ],
            },
        )

    assert response.status_code == 200
    data = response.json()
    required_keys = {
        "agent", "week_reviewed", "completion_rate", "sessions_completed",
        "sessions_planned", "trimp_total", "acwr_before", "acwr_after",
        "adjustments", "next_week_notes",
    }
    assert required_keys.issubset(data.keys())
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd C:/resilio-plus && poetry run pytest tests/test_weekly_review_route.py -v
```

Expected: 3 FAILED (route `/workflow/weekly-review` does not exist yet)

- [ ] **Step 3: Add the route to `api/v1/workflow.py`**

Add after the existing imports at the top (no new imports needed — `AthleteState` already imported):

After the `init_onboarding` function, append:

```python

class WeeklyReviewRequest(BaseModel):
    athlete_state: dict
    actual_workouts: list[dict] = []


@router.post("/weekly-review")
def weekly_review(body: WeeklyReviewRequest) -> dict:
    """
    Run the weekly review loop (H1-H4).

    Body: {"athlete_state": <AthleteState as dict>, "actual_workouts": [<ActualWorkout as dict>]}
    Returns: report dict with completion_rate, ACWR update, adjustments, next_week_notes.
    """
    try:
        state = AthleteState.model_validate(body.athlete_state)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    from models.weekly_review import ActualWorkout, WeeklyReviewState
    from agents.head_coach.graph import weekly_review_graph

    workouts = [ActualWorkout.model_validate(w) for w in body.actual_workouts]
    review_state = WeeklyReviewState(athlete_state=state, actual_workouts=workouts)

    result = weekly_review_graph.invoke(review_state)
    return result["report"] if isinstance(result, dict) else result.report
```

- [ ] **Step 4: Run the 3 route tests to verify they pass**

```bash
cd C:/resilio-plus && poetry run pytest tests/test_weekly_review_route.py -v
```

Expected: 3 PASSED

- [ ] **Step 5: Run full test suite**

```bash
cd C:/resilio-plus && poetry run pytest --tb=short -q
```

Expected: all tests passing (~147 total, up from ~138)

- [ ] **Step 6: ruff check**

```bash
cd C:/resilio-plus && poetry run ruff check .
```

Expected: no errors

- [ ] **Step 7: Commit**

```bash
git add api/v1/workflow.py tests/test_weekly_review_route.py
git commit -m "feat: add POST /workflow/weekly-review route + 3 route tests (S10)"
```

---

## Task 7: Update `CLAUDE.md` for S10

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Mark S10 as done and update file tree + test count in `CLAUDE.md`**

In `CLAUDE.md`, find the session log section and add S10. Also add the 3 new files to the repository map and update the test count from ~138 to ~147.

Add to the Repository Map table:

| `models/weekly_review.py` | `ActualWorkout` + `WeeklyReviewState` | Phase 3 (S10) |
| `core/weekly_review.py` | `WeeklyAnalyzer` + `WeeklyAdjuster` | Phase 3 (S10) |
| `agents/head_coach/weekly_nodes.py` | H1-H4 LangGraph nodes + `_get_weekly_notes` | Phase 3 (S10) |

- [ ] **Step 2: Run final full test suite**

```bash
cd C:/resilio-plus && poetry run pytest -v --tb=short 2>&1 | tail -20
```

Expected: all ~147 tests passing

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: mark S10 weekly review loop ✅ FAIT in CLAUDE.md"
```

---

## Invariants to verify after all tasks

- `poetry run pytest` → all ~147 tests pass
- `poetry run ruff check .` → clean
- `WeeklyReviewState` is independent of `AthleteState` (composition, not inheritance)
- `weekly_review_graph` has no MemorySaver — stateless single-pass
- `node_wr_adjust` updates `_daily_loads_28d` and `fatigue.acwr` in the nested `AthleteState`
- `acwr_before` is captured *before* `fatigue.acwr` is overwritten
- `_get_weekly_notes` returns `""` on any exception (never raises)
