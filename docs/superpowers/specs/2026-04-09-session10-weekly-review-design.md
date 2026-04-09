# Session 10 — Weekly Review Loop Design Spec

## Goal

Implement the H1-H4 weekly review loop: planned vs actual analysis, ACWR recalculation, adjustment recommendations, and a brief feedback report. Expose via `POST /api/v1/workflow/weekly-review` and implement the `build_weekly_review_graph()` stub from `agents/head_coach/graph.py`.

---

## Architecture

```
POST /api/v1/workflow/weekly-review
        ↓
weekly_review_graph.invoke(WeeklyReviewState)
        ↓
node_collect          ← normalizes actual_workouts (V1: already in state)
        ↓
node_analyze          ← WeeklyAnalyzer.analyze()
        ↓
node_adjust           ← WeeklyAdjuster.adjust() + updates AthleteState ACWR
        ↓
node_report           ← assembles report dict + LLM next_week_notes
        ↓
200 {report dict}
```

No interrupt needed — weekly review is a report, not a decision gate. No MemorySaver for the weekly review graph (stateless single-pass).

---

## New Model: `models/weekly_review.py`

```python
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from models.athlete_state import AthleteState


class ActualWorkout(BaseModel):
    """One completed (or missed) session from the past week."""
    sport: Literal["running", "lifting"]
    date: str                   # "YYYY-MM-DD"
    completed: bool
    actual_data: dict = {}      # {distance_km, duration_min, avg_hr} for running
                                # {exercises: [...], session_type: str} for lifting


class WeeklyReviewState(BaseModel):
    """LangGraph state for the weekly review graph."""
    model_config = ConfigDict(frozen=False)

    athlete_state: AthleteState
    actual_workouts: list[ActualWorkout] = Field(default_factory=list)

    # Written by graph nodes
    analysis: dict | None = None         # WeeklyAnalyzer output
    adjustments: list[dict] = Field(default_factory=list)  # WeeklyAdjuster output
    acwr_after: float | None = None      # Recalculated ACWR
    report: dict | None = None           # Final report
```

---

## `core/weekly_review.py`

### `WeeklyAnalyzer`

```python
class WeeklyAnalyzer:
    def analyze(self, planned_sessions: list[dict], actual_workouts: list[ActualWorkout]) -> dict:
        """
        Compare planned sessions against actuals.

        Returns:
            {
              "completion_rate": float,         # 0.0–1.0
              "sessions_planned": int,
              "sessions_completed": int,
              "trimp_total": float,             # total Training Impulse this week
              "trimp_by_sport": {"running": float, "lifting": float},
              "week_loads": list[float],        # 7 daily TRIMP values (Mon–Sun)
            }
        """
```

**TRIMP calculation:**

For running (based on `actual_data`):
- Infer intensity from `avg_hr` if available, else from session `type` in `actual_data`
  - type `"easy"` or avg_hr < 75% HRmax → Z1, factor = 1.0
  - type `"tempo"` or 75–88% HRmax → Z2, factor = 1.5
  - type `"interval"` or > 88% HRmax → Z3, factor = 2.5
  - Default (no data): factor = 1.2 (neutral)
- TRIMP = `duration_min × factor`

For lifting:
- Infer from `session_type` in `actual_data`:
  - `"hypertrophy"`: factor = 0.8
  - `"strength"` or `"power"`: factor = 1.2
  - Default: factor = 1.0
- TRIMP = `duration_min × factor` (if duration_min absent, default = 60)

`week_loads`: 7-element list indexed by day-of-week (0=Monday). Days with no session get 0.0.

If `planned_sessions` is empty (no unified plan available), use `len(actual_workouts)` as denominator for completion_rate with `sessions_planned = len(actual_workouts)`.

### `WeeklyAdjuster`

```python
class WeeklyAdjuster:
    def adjust(
        self,
        analysis: dict,
        daily_loads_28d: list[float],
        fatigue_state,          # FatigueState
    ) -> tuple[list[dict], float]:
        """
        Recalculate ACWR and generate adjustment recommendations.

        Args:
            analysis: output of WeeklyAnalyzer.analyze()
            daily_loads_28d: existing 28-day load history from constraint_matrix
            fatigue_state: state.fatigue (reads acwr as baseline)

        Returns:
            (adjustments, acwr_new)
            - adjustments: list of {type, reason, pct?}
            - acwr_new: recalculated ACWR
        """
```

**ACWR recalculation:**
- Extend `daily_loads_28d` with `analysis["week_loads"]` (7 values)
- Keep the last 28 days: `updated = (daily_loads_28d + week_loads)[-28:]`
- Call `compute_ewma_acwr(updated)` → `(ctl, atl, acwr_new)`
- If `daily_loads_28d` is empty: `acwr_new = None` (no history yet)

**Adjustment rules** (evaluated in order, all that apply are returned):
1. `completion_rate < 0.70` → `{type:"volume_reduction", reason:"low_completion", pct:10}`
2. `acwr_new > 1.5` → `{type:"rest_week", reason:"acwr_danger"}`
3. `acwr_new > 1.3` (and rule 2 not triggered) → `{type:"intensity_reduction", reason:"acwr_caution", pct:15}`
4. `acwr_new < 0.8` → `{type:"volume_increase", reason:"acwr_low", pct:10}`
5. No conditions → `[]` (empty, maintain load)

If `acwr_new` is None: skip ACWR-based rules.

---

## `build_weekly_review_graph()` — 4 Nodes

Add a `weekly_review_graph` singleton (compiled, no MemorySaver) alongside `head_coach_graph` at the bottom of `agents/head_coach/graph.py`.

```python
def node_wr_collect(state: WeeklyReviewState) -> WeeklyReviewState:
    """H1: Normalize actual_workouts (already in state for V1)."""
    # V1: data is provided by the API caller, not pulled from connectors
    # Future: pull from Strava/Hevy APIs here
    return state

def node_wr_analyze(state: WeeklyReviewState) -> WeeklyReviewState:
    """H2: Planned vs actual analysis."""
    planned = state.athlete_state.partial_plans.get("running", {}).get("sessions", []) + \
              state.athlete_state.partial_plans.get("lifting", {}).get("sessions", [])
    analyzer = WeeklyAnalyzer()
    state.analysis = analyzer.analyze(planned, state.actual_workouts)
    return state

def node_wr_adjust(state: WeeklyReviewState) -> WeeklyReviewState:
    """H3: ACWR recalculation + adjustment recommendations."""
    daily_loads = state.athlete_state.constraint_matrix.schedule.get("_daily_loads_28d", [])
    adjuster = WeeklyAdjuster()
    adjustments, acwr_new = adjuster.adjust(
        state.analysis,
        daily_loads,
        state.athlete_state.fatigue,
    )
    state.adjustments = adjustments
    state.acwr_after = acwr_new
    # Update the living matrix with this week's loads
    if state.analysis:
        updated_loads = (daily_loads + state.analysis["week_loads"])[-28:]
        state.athlete_state.constraint_matrix.schedule["_daily_loads_28d"] = updated_loads
    if acwr_new is not None:
        state.athlete_state.fatigue.acwr = acwr_new
    return state

def node_wr_report(state: WeeklyReviewState) -> WeeklyReviewState:
    """H4: Assemble final report + LLM coaching note."""
    report = {
        "agent": "head_coach",
        "week_reviewed": state.athlete_state.current_phase.mesocycle_week,
        "completion_rate": state.analysis.get("completion_rate", 0.0) if state.analysis else 0.0,
        "sessions_completed": state.analysis.get("sessions_completed", 0) if state.analysis else 0,
        "sessions_planned": state.analysis.get("sessions_planned", 0) if state.analysis else 0,
        "trimp_total": state.analysis.get("trimp_total", 0.0) if state.analysis else 0.0,
        "acwr_before": state.athlete_state.fatigue.acwr,
        "acwr_after": state.acwr_after,
        "adjustments": state.adjustments,
        "next_week_notes": _get_weekly_notes(state),  # LLM, "" on failure
    }
    state.report = report
    return state
```

`_get_weekly_notes(state)` — LLM call (same pattern as RecoveryCoachAgent): 1 sentence, max 300 chars, `""` on any exception.

```python
def build_weekly_review_graph() -> StateGraph:
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

weekly_review_graph = build_weekly_review_graph()
```

Imports to add to `graph.py`:
```python
from agents.head_coach.weekly_nodes import (
    WeeklyAnalyzer, WeeklyAdjuster, _get_weekly_notes
)
from models.weekly_review import WeeklyReviewState, ActualWorkout
```

Wait — to keep `graph.py` from growing too large, the H1-H4 node functions and helpers go in a new file `agents/head_coach/weekly_nodes.py` (imported by graph.py). `graph.py` only gets `build_weekly_review_graph()` and the singleton.

---

## `agents/head_coach/weekly_nodes.py`

New file containing:
- `node_wr_collect`, `node_wr_analyze`, `node_wr_adjust`, `node_wr_report`
- `_get_weekly_notes(state) -> str` (LLM helper, silent fail)
- Imports: `WeeklyAnalyzer`, `WeeklyAdjuster` from `core/weekly_review`

---

## `api/v1/workflow.py` — New Route

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
    workouts = [ActualWorkout.model_validate(w) for w in body.actual_workouts]
    review_state = WeeklyReviewState(athlete_state=state, actual_workouts=workouts)

    from agents.head_coach.graph import weekly_review_graph
    result = weekly_review_graph.invoke(review_state)
    return result["report"] if isinstance(result, dict) else result.report
```

---

## Tests

### `tests/test_weekly_review.py` — 6 tests

```python
def test_analyzer_all_completed():
    """All sessions completed → completion_rate=1.0."""

def test_analyzer_partial_completion():
    """3 of 5 sessions completed → completion_rate=0.6."""

def test_analyzer_trimp_running_easy():
    """Easy run 60min → TRIMP = 60 × 1.0 = 60."""

def test_adjuster_low_completion_suggests_reduction():
    """completion_rate=0.5 → adjustments has volume_reduction."""

def test_adjuster_acwr_danger_suggests_rest():
    """Updated ACWR > 1.5 → adjustments has rest_week."""

def test_adjuster_healthy_load_no_adjustments():
    """completion_rate=0.9, ACWR stays 1.1 → adjustments=[]."""
```

### `tests/test_weekly_review_route.py` — 3 tests

```python
def test_post_weekly_review_returns_200(simon_pydantic_state): ...
def test_post_weekly_review_invalid_body(): ...
def test_post_weekly_review_report_structure(simon_pydantic_state): ...
```

---

## Files — Summary

| Fichier | Action |
|---------|--------|
| `models/weekly_review.py` | Créer — `ActualWorkout` + `WeeklyReviewState` |
| `core/weekly_review.py` | Créer — `WeeklyAnalyzer` + `WeeklyAdjuster` |
| `agents/head_coach/weekly_nodes.py` | Créer — 4 nœuds LangGraph H1-H4 + `_get_weekly_notes` |
| `agents/head_coach/graph.py` | Modifier — impl `build_weekly_review_graph()` + singleton |
| `api/v1/workflow.py` | Modifier — `POST /workflow/weekly-review` |
| `tests/test_weekly_review.py` | Créer — 6 tests |
| `tests/test_weekly_review_route.py` | Créer — 3 tests |
| `CLAUDE.md` | Modifier — S10 ✅ FAIT en fin de session |

---

## Invariants post-S10

- Tous les tests existants continuent de passer (138 → ~147 tests)
- `ruff check` propre
- `WeeklyReviewState` est indépendante de `AthleteState` (composition, pas héritage)
- `weekly_review_graph` est sans MemorySaver — stateless single-pass
- `node_wr_adjust` met à jour `_daily_loads_28d` et `fatigue.acwr` dans l'AthleteState imbriqué
- H5 (planification semaine suivante) est hors scope — le rapport inclut des recommandations, l'utilisateur déclenche le workflow S9 manuellement
