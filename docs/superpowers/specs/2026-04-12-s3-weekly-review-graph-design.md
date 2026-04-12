# S-3 Weekly Review Graph — Design Spec

**Date:** 2026-04-12
**Branch:** session/s3-weekly-review
**Source:** SESSION_REPORT.md § S-3

---

## Scope

Add a human-in-the-loop weekly review graph that compares actual training vs planned, recomputes ACWR, and asks the athlete to confirm adjustments before persisting.

---

## Architecture

### Graph: `backend/app/graphs/weekly_review_graph.py`

5-node `StateGraph[WeeklyReviewState]` with `MemorySaver`, `interrupt_before=["present_review"]`.

**State fields (all JSON-serializable):**

| Field | Type | Set by |
|---|---|---|
| `athlete_id` | `str` | input |
| `plan_id` | `str \| None` | input |
| `week_start` | `str` (ISO date) | input |
| `week_number` | `int` | input |
| `sessions_planned` | `int` | node 1 |
| `sessions_completed` | `int` | node 1 |
| `completion_rate` | `float` | node 1 |
| `actual_hours` | `float` | node 1 |
| `load_history` | `list[float]` | input |
| `acwr_dict` | `dict \| None` | node 2 |
| `review_summary_dict` | `dict \| None` | node 3 |
| `human_approved` | `bool` | resume_review() |
| `db_review_id` | `str \| None` | node 5 |
| `messages` | `list[BaseMessage]` | add_messages |

**Node pipeline:**

```
analyze_actual_vs_planned
  → compute_new_acwr
  → update_athlete_state
  → [INTERRUPT] present_review
  → apply_adjustments → END
```

No conditional edges — linear pipeline with single interrupt gate.

### CoachingService additions

`weekly_review(athlete_id, db) -> tuple[str, dict | None]`
- Queries the latest TrainingPlan for the athlete
- Builds initial WeeklyReviewState from DB data
- Runs graph until interrupt at `present_review`
- Returns `(thread_id, review_summary_dict)`

`resume_review(thread_id, approved, db) -> None`
- Updates state with `human_approved=approved`
- Invokes `None` to resume from checkpoint
- No return value (side effect: WeeklyReviewModel written to DB)

### New endpoints in `workflow.py`

```
POST /athletes/{id}/plan/review/start   → ReviewStartResponse(thread_id, review_summary)
POST /athletes/{id}/plan/review/confirm → ReviewConfirmResponse(success, review_id)
```

Both protected by `_require_own`. No `require_full_mode` guard — reviews apply to both modes.

---

## Node Descriptions

### 1. `analyze_actual_vs_planned`
- Loads `TrainingPlanModel.weekly_slots_json` from DB via `config["configurable"]["db"]`
- Counts sessions planned for `week_start`
- Counts completed `SessionLogModel` rows (non-skipped, has `actual_duration_min`)
- Computes `completion_rate`, `actual_hours`

### 2. `compute_new_acwr`
- Uses `load_history` from state
- Calls `core.acwr.compute_acwr(load_history)` — returns None if history empty
- Serializes to `acwr_dict`

### 3. `update_athlete_state`
- Assembles `review_summary_dict`: completion stats + ACWR + readiness + recommendations list
- Appends an `AIMessage` summarizing the week

### 4. `present_review` (INTERRUPT node)
- No-op node — presence in graph triggers `interrupt_before`
- Returns state unchanged; human review happens externally via `resume_review()`

### 5. `apply_adjustments`
- Creates `WeeklyReviewModel` in DB with full stats
- Sets `db_review_id` in state
- Appends confirmation `AIMessage`

---

## Testing Strategy

### Unit tests — `tests/backend/graphs/test_weekly_review_graph.py`
- `test_build_weekly_review_graph_returns_compiled`
- `test_graph_no_interrupt_runs_to_completion` (with pre-set `human_approved=True`)
- `test_graph_creates_weekly_review_in_db`
- Node-level tests for each of the 5 nodes
- Interrupt + resume tests

### API tests — `tests/backend/api/test_weekly_review_endpoints.py`
- `test_review_start_returns_thread_id`
- `test_review_confirm_returns_success`
- `test_review_start_404_no_plan`
- Authorization tests

---

## Invariants

- No existing code deleted or modified
- All additions appended to end of `coaching_service.py` and `workflow.py`
- `pytest tests/` ≥ 1243 passing after implementation
