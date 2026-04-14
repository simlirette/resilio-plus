# LangGraph Runtime Validation — Design Spec

**Date:** 2026-04-14
**Status:** Approved
**Phase:** V3-S
**Scope:** Fix checkpoint persistence (SQLite + singleton), runtime tests, structured logging, debug endpoint, smoke script, LANGGRAPH-FLOW.md documentation.

---

## Context

The LangGraph coaching graph (11 nodes, HITL interrupt) works in E2E tests (V3-Q) where `CoachingService` is instantiated once per test module. In production, `workflow.py` creates a **new** `CoachingService()` per HTTP request — each with a fresh `MemorySaver` — so checkpoints are **lost** between `create_plan` and `approve/revise`. The graph literally cannot resume after interrupt via the API.

V3-S fixes this foundational issue and adds runtime validation infrastructure.

---

## Deliverables

| # | Deliverable | Location |
|---|---|---|
| 1 | SQLite checkpointer (replaces MemorySaver) | `coaching_graph.py`, `coaching_service.py` |
| 2 | CoachingService singleton (fixes workflow.py) | `coaching_service.py`, `workflow.py` |
| 3 | Structured node logging (JSON, decorator) | `graphs/logging.py`, `coaching_graph.py` |
| 4 | Runtime tests (mock agents, graph validation) | `tests/runtime/` |
| 5 | Debug endpoint (athlete-scoped) | `workflow.py` |
| 6 | Docs: LANGGRAPH-FLOW.md + smoke script | `docs/backend/`, `scripts/` |

---

## Architecture

### 1. Checkpointer Injection

**Current (broken):**
```
workflow.py → CoachingService() → build_coaching_graph() → MemorySaver()
                  ↑ new instance per request = checkpoint lost
```

**Proposed:**
```
coaching_graph.py:  build_coaching_graph(checkpointer) — required param, no default
coaching_service.py: CoachingService(checkpointer) — stores, passes to graph builder
                     coaching_service — module-level singleton instance
workflow.py:        imports coaching_service singleton (all endpoints share it)
```

`build_coaching_graph()` signature change:

```python
# BEFORE
def build_coaching_graph(interrupt: bool = True):
    ...
    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer, ...)

# AFTER
def build_coaching_graph(checkpointer, interrupt: bool = True):
    ...
    return builder.compile(checkpointer=checkpointer, ...)
```

### 2. SQLite Checkpointer

Package: `langgraph-checkpoint-sqlite` (official LangGraph package).

```python
from langgraph.checkpoint.sqlite import SqliteSaver

db_path = os.environ.get("LANGGRAPH_CHECKPOINT_DB", "data/checkpoints.sqlite")
checkpointer = SqliteSaver.from_conn_string(db_path)
```

- Path from `LANGGRAPH_CHECKPOINT_DB` env var
- Default: `data/checkpoints.sqlite` (relative to working dir)
- `data/` directory already in `.gitignore`
- Tests use `MemorySaver()` for speed (no file I/O)
- `test_checkpoint_persistence.py` uses `SqliteSaver` with temp file

### 3. CoachingService Singleton

```python
# coaching_service.py

_checkpointer = None

def _get_checkpointer():
    global _checkpointer
    if _checkpointer is None:
        db_path = os.environ.get("LANGGRAPH_CHECKPOINT_DB", "data/checkpoints.sqlite")
        _checkpointer = SqliteSaver.from_conn_string(db_path)
    return _checkpointer

class CoachingService:
    def __init__(self, checkpointer=None):
        self._checkpointer = checkpointer or _get_checkpointer()
        self._graph = build_coaching_graph(
            checkpointer=self._checkpointer,
            interrupt=True,
        )
        ...

# Module-level singleton
coaching_service = CoachingService()
```

```python
# workflow.py — BEFORE (broken, 3 places)
service = CoachingService()

# workflow.py — AFTER
from app.services.coaching_service import coaching_service
# All endpoints use same instance → same checkpointer → checkpoint persists
```

Consistent with existing `_review_service` singleton pattern in workflow.py.

### 4. Structured Node Logging

New file `backend/app/graphs/logging.py`:

```python
import logging
import time
import json
from functools import wraps

logger = logging.getLogger("resilio.graph")

def log_node(func):
    @wraps(func)
    def wrapper(state, config=None):
        node = func.__name__
        athlete = state.get("athlete_id", "?")
        logger.info(json.dumps({
            "event": "node_enter",
            "node": node,
            "athlete_id": athlete,
        }))
        t0 = time.perf_counter()
        result = func(state, config) if config else func(state)
        ms = round((time.perf_counter() - t0) * 1000)
        changed = list(result.keys()) if isinstance(result, dict) else []
        logger.info(json.dumps({
            "event": "node_exit",
            "node": node,
            "athlete_id": athlete,
            "duration_ms": ms,
            "keys_changed": changed,
        }))
        return result
    return wrapper
```

Applied in `coaching_graph.py`:
```python
builder.add_node("analyze_profile", log_node(analyze_profile))
builder.add_node("compute_acwr", log_node(compute_acwr))
# ... all 11 nodes
```

No new dependencies. JSON lines to stdout. Grep-friendly.

### 5. Runtime Tests

Directory: `tests/runtime/`

**Mock strategy:** Patch each agent's `.run()` at module level to return canned dicts matching real output shape. Agent prompt/reasoning logic does NOT run. Graph topology, state flow, and checkpointing are tested.

```python
# tests/runtime/conftest.py
@pytest.fixture(autouse=True)
def mock_agents(monkeypatch):
    monkeypatch.setattr("app.agents.running_coach.RunningCoach.run",
                        lambda *a, **kw: CANNED_RUNNING_RESPONSE)
    monkeypatch.setattr("app.agents.lifting_coach.LiftingCoach.run",
                        lambda *a, **kw: CANNED_LIFTING_RESPONSE)
    # ... all active agents
```

**Test files:**

| File | Tests | Coverage |
|---|---|---|
| `test_graph_topology.py` | ~5 | All 11 nodes reachable; conditional edges route correctly for each branch |
| `test_checkpoint_persistence.py` | ~4 | Create → kill service → new service with same SQLite file → resume succeeds |
| `test_interrupt_resume.py` | ~5 | Interrupt at `present_to_athlete`; approve, reject, and revise all resume correctly |
| `test_state_transitions.py` | ~6 | Each node produces expected state keys; no None in required fields |
| `test_revision_loop.py` | ~3 | Max 1 revision enforced; second reject routes to `present_to_athlete` not `delegate_specialists` |

**DB:** SQLite in-memory for `AthleteModel` etc. (same pattern as E2E scenarios).
**Checkpointer:** `MemorySaver()` for all tests except `test_checkpoint_persistence.py` which uses `SqliteSaver` with `tempfile.NamedTemporaryFile`.

### 6. Debug Endpoint

```
GET /coach/session/{thread_id}/state
```

- Located in `workflow.py` alongside existing coaching endpoints
- Auth: JWT required, reuses `_validate_thread_ownership(thread_id, athlete_id)`
- Returns graph state snapshot:

```python
{
    "thread_id": str,
    "current_node": str | None,
    "state": {
        "athlete_id": str,
        "human_approved": bool | None,
        "proposed_plan_dict": dict | None,
        "final_plan_dict": dict | None,
        # ... all AthleteCoachingState fields except config/db
    },
    "checkpoint_ts": str  # ISO 8601
}
```

- Reads from checkpointer via `coaching_service._graph.get_state(config)`
- 404 if thread_id not found in checkpointer
- 403 if thread ownership validation fails

### 7. Smoke Script

`scripts/smoke_test_runtime.py` — manual, not CI.

- Real LLM calls (requires `OPENAI_API_KEY`)
- Real SQLite checkpointer (temp file)
- In-memory SQLite for DB models
- Full flow: seed athlete → `create_plan()` → print proposed → `resume_plan(approved=True)` → print final
- CLI: `python scripts/smoke_test_runtime.py --athlete-id test-smoke`
- Exit 0 = pass, exit 1 = fail with diagnostics printed to stderr
- Prints structured log output (demonstrates logging decorator)

### 8. LANGGRAPH-FLOW.md

`docs/backend/LANGGRAPH-FLOW.md`:

- Mermaid diagram of full 11-node graph
- Node descriptions table: name, purpose, input keys read, output keys written
- 3 conditional edges documented: `_has_critical_conflicts`, `_after_present`, `_after_revise`
- Interrupt behavior: where it pauses, how to resume (update_state + invoke pattern)
- Checkpoint lifecycle: creation, persistence, retrieval, cleanup
- Thread ID format and ownership model

---

## Dependencies

New package: `langgraph-checkpoint-sqlite` — added to `pyproject.toml`.

No other new dependencies.

---

## Files Modified

| File | Change |
|---|---|
| `backend/app/graphs/coaching_graph.py` | `build_coaching_graph(checkpointer, ...)`, `log_node` wrapping |
| `backend/app/graphs/logging.py` | **New** — `log_node` decorator |
| `backend/app/services/coaching_service.py` | `CoachingService(checkpointer)`, `_get_checkpointer()`, module singleton |
| `backend/app/routes/workflow.py` | Import singleton, debug endpoint, remove per-request instantiation |
| `pyproject.toml` | Add `langgraph-checkpoint-sqlite` |
| `tests/runtime/conftest.py` | **New** — mock agents fixture, canned responses |
| `tests/runtime/test_graph_topology.py` | **New** |
| `tests/runtime/test_checkpoint_persistence.py` | **New** |
| `tests/runtime/test_interrupt_resume.py` | **New** |
| `tests/runtime/test_state_transitions.py` | **New** |
| `tests/runtime/test_revision_loop.py` | **New** |
| `scripts/smoke_test_runtime.py` | **New** |
| `docs/backend/LANGGRAPH-FLOW.md` | **New** |

---

## Files NOT Touched

- `backend/app/integrations/strava/` — explicitly excluded per user rules
- `backend/app/graphs/nodes.py` — node functions unchanged (decorator applied externally)
- `backend/app/graphs/state.py` — `AthleteCoachingState` unchanged
- `tests/e2e/` — existing E2E tests unaffected (they construct `CoachingService()` directly with default checkpointer)

---

## Migration Notes

- Existing E2E tests (`tests/e2e/test_scenario_*.py`) create `CoachingService()` without args. After this change, the constructor defaults to `_get_checkpointer()` → `SqliteSaver`. To keep E2E tests fast and isolated, update `tests/fixtures/athlete_states.py` to provide a `MemorySaver()` helper that E2E tests pass explicitly: `CoachingService(checkpointer=MemorySaver())`.
- No Alembic migration needed — SQLite checkpoint DB is a separate file from the app DB.
- `data/` directory must exist at runtime. `_get_checkpointer()` creates it via `os.makedirs(exist_ok=True)`.

---

## Out of Scope

- Weekly review graph (`_review_service`) — separate concern, already works as singleton
- Role-based auth / admin system — debug endpoint uses athlete-scoped ownership
- Checkpoint cleanup / TTL — future optimization
- Production deployment changes — checkpointer works with any WSGI/ASGI server
