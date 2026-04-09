# Session 9 — Workflow Design Spec

## Goal

Implement the Head Coach orchestration workflow: constraint matrix builder, conflict resolver, plan merger, LangGraph stub nodes (recovery gate, resolve conflicts, merge plans), and workflow REST API with interrupt/resume pattern.

---

## Architecture

```
POST /api/v1/workflow/plan
        ↓
LangGraph StateGraph (graph.py)
        ↓
node_recovery_gate           ← calls RecoveryCoachAgent.run()
        ↓ (route: red → interrupt, else continue)
node_delegate_to_agents      ← already implemented
        ↓
node_resolve_conflicts       ← ConflictResolver.resolve()
        ↓
node_merge_plans             ← PlanMerger.merge()
        ↓
node_present_plan            ← already implemented
        ↓
200 {status:"complete", unified_plan}
OR 202 {status:"awaiting_decision", thread_id, pending_decision}
```

Interrupt/resume uses LangGraph `MemorySaver` (in-memory) keyed by `thread_id` (UUID). The client stores `thread_id` and calls `POST /workflow/plan/resume` with the user's decision.

---

## Component Design

### `core/constraint_matrix.py` — `build_constraint_matrix`

Single public function. No class needed (stateless transformation).

```python
def build_constraint_matrix(state: AthleteState) -> dict:
    """
    Build a weekly session schedule from the athlete's availability and goals.

    Returns:
        {
          "week_days": {
            "monday": {"available": bool, "sessions": []},
            ...
            "sunday": {"available": bool, "sessions": []},
          },
          "total_sessions": int,
          "running_days": int,
          "lifting_days": int,
        }
    """
```

**Algorithm** (greedy):
1. Extract `available_days` from `state.profile.available_days` (list of lowercase day names).
2. Assign lifting sessions first (2–3 days, non-consecutive preferred, spaced ≥48h apart).
3. Assign running sessions on remaining available days (up to `state.profile.sessions_per_week - lifting_count`).
4. Sessions list per day: `[{"sport": "lifting"|"running", "type": "primary"}]`.
5. If `available_days` is empty or `sessions_per_week` is 0, return empty matrix (no crash).

Sources from `AthleteState`:
- `state.profile.available_days: list[str]` — days available (e.g., `["monday","tuesday","thursday","friday","saturday"]`)
- `state.profile.sessions_per_week: int` — total desired sessions
- `state.profile.lifting_days_per_week: int` — desired lifting sessions (default 2)

---

### `agents/head_coach/resolver.py` — `ConflictResolver`

```python
class ConflictResolver:
    MAX_ITERATIONS = 2

    def resolve(self, state: AthleteState, partial_plans: dict) -> tuple[dict, list[str]]:
        """
        Detect and resolve scheduling/load conflicts between partial plans.

        Args:
            state: current AthleteState
            partial_plans: {"running": <running plan dict>, "lifting": <lifting plan dict>}

        Returns:
            (resolved_partial_plans, conflict_log)
            - resolved_partial_plans: modified copies of partial_plans
            - conflict_log: list of strings describing each resolution applied
        """
```

**Conflict types detected:**
1. **Muscle overlap** — lifting day + running day on same calendar day when lifting targets legs. Resolution: swap the lifting session to the nearest available adjacent day.
2. **ACWR overload** — `state.fatigue.acwr > 1.3`. Resolution: reduce volume of all sessions by 20% (volume_reduction_pct field in plan).
3. **ACWR danger** — `state.fatigue.acwr > 1.5`. Resolution: reduce intensity (intensity_reduction_pct = 30%), tier_max = 1.

**Circuit breaker**: if iteration count exceeds `MAX_ITERATIONS`, stop resolving and log `"circuit_breaker_triggered"`. Return plans as-is.

**Muscle overlap detection**: a day has overlap if `partial_plans["lifting"]` has a session on that day with `muscle_groups` containing any of `["quadriceps","hamstrings","glutes","calves"]` AND `partial_plans["running"]` also has a session on that day.

---

### `agents/head_coach/merger.py` — `PlanMerger`

```python
class PlanMerger:
    def merge(self, state: AthleteState, partial_plans: dict, conflict_log: list[str]) -> dict:
        """
        Merge partial agent plans into a unified weekly plan.

        Args:
            state: current AthleteState
            partial_plans: {"running": dict, "lifting": dict} — already conflict-resolved
            conflict_log: list of resolution strings

        Returns unified plan:
        {
          "agent": "head_coach",
          "week": int,
          "phase": str,
          "sessions": [
            {
              "day": "monday"|...|"sunday",
              "sport": "running"|"lifting",
              "workout": <session dict from partial plan>
            },
            ...
          ],
          "acwr": float | None,
          "conflicts_resolved": list[str],
          "coaching_summary": str,   # "" — filled by LLM in future session
        }
        """
```

**Merge logic**:
1. Collect sessions from `partial_plans["running"]["sessions"]` and `partial_plans["lifting"]["sessions"]`.
2. Assign each session a day from the constraint matrix (first-fit: running sessions get non-lifting days, lifting sessions get their designated days).
3. Sort sessions by day-of-week order (monday first).
4. `week` and `phase` come from `state.current_phase` (week_number, phase_name).
5. `acwr` from `state.fatigue.acwr`.
6. `conflicts_resolved` = `conflict_log`.

---

### `agents/head_coach/graph.py` — Node Implementations

#### `node_recovery_gate` (replace stub)

```python
def node_recovery_gate(state: AthleteState) -> AthleteState:
    agent = RecoveryCoachAgent()
    verdict = agent.run(state)
    state.recovery_verdict = verdict   # store for downstream nodes
    return state
```

**`route_after_recovery_gate`** — fix None crash:
```python
def route_after_recovery_gate(state: AthleteState) -> str:
    verdict = getattr(state, "recovery_verdict", None)
    if verdict and verdict.get("color") == "red":
        return "interrupt_recovery"
    return "delegate_to_agents"
```

The `recovery_verdict` field must be added to `AthleteState` as `recovery_verdict: dict | None = None`.

#### `node_resolve_conflicts` (replace stub)

```python
def node_resolve_conflicts(state: AthleteState) -> AthleteState:
    resolver = ConflictResolver()
    resolved, conflict_log = resolver.resolve(state, state.partial_plans or {})
    state.partial_plans = resolved
    state.conflict_log = conflict_log
    return state
```

#### `node_merge_plans` (replace stub)

```python
def node_merge_plans(state: AthleteState) -> AthleteState:
    merger = PlanMerger()
    state.unified_plan = merger.merge(state, state.partial_plans or {}, state.conflict_log or [])
    return state
```

New `AthleteState` fields needed:
- `recovery_verdict: dict | None = None`
- `partial_plans: dict | None = None`
- `conflict_log: list[str] = []`
- `unified_plan: dict | None = None`

---

### `api/v1/workflow.py` — Routes

```python
class PlanRequest(BaseModel):
    athlete_state: dict
    thread_id: str | None = None   # provided for resume

class ResumeRequest(BaseModel):
    thread_id: str
    user_decision: str   # "proceed"|"rest"|"modify"

@router.post("/plan")
def generate_plan(body: PlanRequest) -> dict:
    """
    Run the LangGraph workflow.
    Returns 200 {status:"complete", unified_plan} OR 202 {status:"awaiting_decision", thread_id, pending_decision}.
    """

@router.post("/plan/resume")
def resume_plan(body: ResumeRequest) -> dict:
    """Resume a workflow interrupted for human-in-the-loop decision."""

@router.post("/onboarding/init")
def init_onboarding(body: dict) -> dict:
    """
    Accept a complete athlete profile dict, validate as AthleteState,
    return initialized state with constraint_matrix attached.
    """
```

**LangGraph interrupt pattern**:
- `thread_id = str(uuid4())` on new requests (or use provided thread_id for resume)
- `config = {"configurable": {"thread_id": thread_id}}`
- Invoke graph: `result = graph.invoke(state, config=config)`
- If `result` is `GraphInterrupted` or contains `__interrupt__` key → return 202

---

### `api/main.py` — Mount Workflow Router

```python
from api.v1.workflow import router as workflow_router
app.include_router(workflow_router, prefix="/api/v1/workflow", tags=["workflow"])
```

---

## `models/athlete_state.py` — New Fields

```python
class AthleteState(TypedDict, total=False):
    # ... existing fields ...
    recovery_verdict: dict | None
    partial_plans: dict | None
    conflict_log: list[str]
    unified_plan: dict | None
```

(These use `total=False` so they're optional — no breaking change to existing tests.)

---

## Tests

### `tests/test_constraint_matrix.py` — 5 tests

```python
def test_all_available_days_assigned(): ...
def test_lifting_days_non_consecutive(): ...
def test_running_fills_remaining_days(): ...
def test_empty_available_days_no_crash(): ...
def test_sessions_per_week_respected(): ...
```

### `tests/test_conflict_resolver.py` — 4 tests

```python
def test_no_conflicts_returns_unchanged_plans(): ...
def test_acwr_overload_reduces_volume(): ...
def test_acwr_danger_reduces_intensity(): ...
def test_circuit_breaker_stops_after_max_iterations(): ...
```

### `tests/test_plan_merger.py` — 3 tests

```python
def test_merge_returns_unified_structure(): ...
def test_sessions_sorted_by_day(): ...
def test_conflict_log_included(): ...
```

### `tests/test_workflow_route.py` — 4 tests

```python
def test_post_plan_returns_200_complete(simon_pydantic_state): ...
def test_post_plan_returns_202_on_interrupt(simon_pydantic_state): ...
def test_post_plan_invalid_body(): ...
def test_post_resume_plan(simon_pydantic_state): ...
```

---

## Files — Summary

| Fichier | Action |
|---------|--------|
| `models/athlete_state.py` | Modifier — ajouter 4 champs optionnels |
| `core/constraint_matrix.py` | Créer — `build_constraint_matrix` |
| `agents/head_coach/resolver.py` | Créer — `ConflictResolver` |
| `agents/head_coach/merger.py` | Créer — `PlanMerger` |
| `agents/head_coach/graph.py` | Modifier — impl. 3 stub nodes + fix route_after_recovery_gate |
| `api/v1/workflow.py` | Créer — 3 routes workflow |
| `api/main.py` | Modifier — monter le workflow router |
| `tests/test_constraint_matrix.py` | Créer — 5 tests |
| `tests/test_conflict_resolver.py` | Créer — 4 tests |
| `tests/test_plan_merger.py` | Créer — 3 tests |
| `tests/test_workflow_route.py` | Créer — 4 tests |
| `CLAUDE.md` | Modifier — S9 ✅ FAIT en fin de session |

---

## Invariants post-S9

- Tous les tests existants continuent de passer (122 → ~138 tests)
- `ruff check` propre
- `AthleteState` reste rétrocompatible (tous nouveaux champs optionnels)
- `route_after_recovery_gate` ne crash plus si `recovery_verdict` est None
- Le workflow supporte à la fois le cas "complete" (200) et le cas "interrupt" (202)
