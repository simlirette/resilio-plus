# E2E Coaching Scenarios — Design Spec

**Date:** 2026-04-14  
**Status:** Approved  
**Scope:** 8 scenario-based E2E tests covering the full CoachingService flow (create_plan → resume_plan). Service layer only — no HTTP, no mock on business logic.

---

## Context

`tests/e2e/` already has 6 files (33 tests) covering onboarding, plan, review, mode switch, and agent-level prescriptions. Gaps:

- `CoachingService.create_plan()` + `resume_plan()` tested with **real LangGraph graph** and real SQLite DB — currently only mocked at HTTP layer
- Reject/revise flow (`resume_plan(approved=False, feedback=...)`) — not tested
- RED-S energy veto through full graph — not tested end-to-end
- Missing sleep data graceful degradation — not tested at service layer
- Luteal phase adjustment through full plan — not tested at service layer

This spec defines 8 scenario files that close these gaps.

---

## Architecture

**Layer:** `CoachingService` directly — no TestClient, no HTTP routes.

**Graph mode:** `interrupt=True` (real interrupt behavior). Tests use `CoachingService._graph.update_state()` + `invoke(None)` pattern, identical to production `resume_plan()`.

**DB:** SQLite in-memory, module-scoped, created fresh per scenario file. AthleteModel seeded in `scenario_db` fixture before test execution.

**Mocking:** Strava/Hevy connectors patched to return `[]` (no real network). Terra data injected via `athlete_dict` (passed directly into `AgentContext` — no connector call).

**Determinism:** `random.seed(42)` at module top in each scenario file.

**Flow per scenario:**
```
scenario_db fixture → seed AthleteModel (+ optional EnergySnapshotModel)
→ CoachingService().create_plan(athlete_id, athlete_dict, load_history, db)
  → graph runs: analyze_profile → compute_acwr → delegate_specialists
               → merge_recommendations → detect_conflicts → resolve_conflicts
               → build_proposed_plan → apply_energy_snapshot → present_to_athlete [INTERRUPT]
  → returns (thread_id, proposed_plan_dict)
→ assert proposed_plan (step 1)
→ CoachingService().resume_plan(thread_id, approved, feedback, db)
  → graph resumes: check gate → revise_plan | finalize_plan
  → returns final_plan_dict | new proposed_plan_dict
→ assert final result (step 2)
```

---

## Files

### New files

| File | Purpose |
|---|---|
| `tests/fixtures/athlete_states.py` | Profile factories (dict, ready for coaching state) |
| `tests/e2e/test_scenario_01_fresh_athlete.py` | Happy path — confirm |
| `tests/e2e/test_scenario_02_recovery_veto.py` | Recovery Coach veto → reduced intensity |
| `tests/e2e/test_scenario_03_running_lifting_conflict.py` | HIIT + lower_strength same day → conflict resolution |
| `tests/e2e/test_scenario_04_user_rejects.py` | Reject → new proposed plan |
| `tests/e2e/test_scenario_05_user_modifies.py` | Reject with specific feedback → plan respects feedback |
| `tests/e2e/test_scenario_06_missing_sleep.py` | No Terra data → graceful degraded plan |
| `tests/e2e/test_scenario_07_reds_veto.py` | EA < 25 kcal/kg FFM → non-overridable veto |
| `tests/e2e/test_scenario_08_luteal_phase.py` | Luteal phase → adjusted prescription |
| `docs/backend/E2E-SCENARIOS.md` | Living spec table |

### Unmodified
- `tests/e2e/conftest.py` — `_make_e2e_engine()` reused (imported, not duplicated)
- `tests/fixtures/__init__.py` — already exists
- `backend/app/integrations/nutrition/` — **not touched**

---

## Fixtures — `tests/fixtures/athlete_states.py`

All factories return `dict` (JSON-serializable, ready for `athlete_dict` param). No Pydantic objects to avoid schema coupling in fixture layer.

### `simon_fresh()`
```
name: "Simon", sex: "M", age: 32, weight_kg: 78.5, height_cm: 178
sports: ["running", "lifting"], primary_sport: "running"
vdot: 45, resting_hr: 58, max_hr: 188
available_days: [0, 1, 3, 5, 6], hours_per_week: 8.0
terra_health: RMSSD=62ms, sleep=7.5h × 7 days  (list of TerraHealthData dicts)
goals: ["run sub-25min 5K", "maintain muscle mass"]
target_race_date: 27 weeks from WEEK_START
```

### `simon_fatigued()`
Simon base + terra overridden:
```
terra_health: RMSSD=9ms (< 10ms veto threshold), sleep=4.5h × 7 days
sleep_score: 30.0
```

### `simon_no_sleep()`
Simon base + terra overridden:
```
terra_health: []  (no data at all)
```

### `simon_reds()`
Simon base. EnergySnapshotModel pre-seeded in DB (not in dict):
```
EnergySnapshotModel:
  athlete_id: simon_id
  allostatic_score: 85.0
  energy_availability: 18.0  (< 25 kcal/kg FFM — critical male threshold)
  recommended_intensity_cap: 0.0
  veto_triggered: True
  veto_reason: "EA critique (18.0 < 25 kcal/kg FFM)"
  sleep_quality: 3.5
  cognitive_load: 7.0
  timestamp: now(UTC)
```

### `layla_luteal()`
```
name: "Layla", sex: "F", age: 28, weight_kg: 62.0, height_cm: 168
sports: ["running", "lifting"], primary_sport: "running"
vdot: 40, resting_hr: 62, max_hr: 192
available_days: [0, 2, 4, 6], hours_per_week: 7.0
terra_health: RMSSD=38ms, sleep=6.5h × 7 days
hormonal_profile: { current_phase: "luteal", current_cycle_day: 20,
                    cycle_length_days: 28, enabled: True }
goals: ["sub-30min 5K", "stay healthy"]
```

### Load history constants
```python
STABLE_LOAD = [400.0] * 28      # ACWR safe
ELEVATED_LOAD = [600.0] * 28    # ACWR caution
FRESH_LOAD = [50.0] * 28        # new athlete
```

---

## Scenario Specifications

### S1 — Fresh athlete → confirm → execute
**File:** `test_scenario_01_fresh_athlete.py`  
**Profile:** `simon_fresh()`, `STABLE_LOAD`

**Step 1 — create_plan:**
- `proposed` is not None
- `proposed["sessions"]` non-empty
- `proposed["readiness_level"] == "green"`
- `proposed["acwr"]["status"] in ("safe",)` (STABLE_LOAD keeps ACWR ~1.0)
- No session has `duration_min <= 0`

**Step 2 — resume_plan(approved=True):**
- Returns `final` dict (not None)
- `final.get("db_plan_id")` is not None
- DB: `TrainingPlanModel` row exists for `athlete_id`
- `final["sessions"]` matches `proposed["sessions"]` (no modification on approve)

---

### S2 — Fatigued → Recovery veto → confirm alternative
**File:** `test_scenario_02_recovery_veto.py`  
**Profile:** `simon_fatigued()`, `STABLE_LOAD`

**Step 1 — create_plan:**
- `proposed` is not None
- `proposed["readiness_level"] == "red"`
- Total session duration sum < total from `simon_fresh()` equivalent plan (intensity reduced)
- At least one note in `proposed["notes"]` references HRV or readiness

**Step 2 — resume_plan(approved=True):**
- `final` is not None, `final["db_plan_id"]` is not None
- Plan persists despite red readiness (no exception, not blocked)

---

### S3 — Running vs Lifting conflict → Head Coach resolution
**File:** `test_scenario_03_running_lifting_conflict.py`  
**Profile:** `simon_fresh()` with available_days=[0] only (forces both sports onto Monday)  
**Load:** `STABLE_LOAD`

**Step 1 — create_plan:**
- `proposed["conflicts"]` is not empty
- No two high-intensity sessions on the same date
- The shorter conflicting session is absent from `proposed["sessions"]`

**Step 2 — resume_plan(approved=True):**
- `final` not None, persisted

---

### S4 — User rejects → Head Coach proposes alternative
**File:** `test_scenario_04_user_rejects.py`  
**Profile:** `simon_fresh()`, `STABLE_LOAD`

**Step 1 — create_plan:**
- `proposed_v1` not None
- Record `proposed_v1["sessions"]` count + total duration

**Step 2 — resume_plan(approved=False, feedback="Too much volume this week"):**
- Returns `proposed_v2` (not None, not a final plan)
- `proposed_v2` is structurally valid (has `sessions`, `readiness_level`)
- Re-plan occurred: assert `proposed_v2.get("sessions") is not None` (graph did not crash on revise loop)
- Note: content equality not asserted — LangGraph re-plan is deterministic given same state but feedback may or may not change output; what matters is the graph completed the revise cycle without error

---

### S5 — User modifies → validates against vetos
**File:** `test_scenario_05_user_modifies.py`  
**Profile:** `simon_fresh()`, `STABLE_LOAD`

**Step 1 — create_plan:**
- `proposed_v1` not None

**Step 2 — resume_plan(approved=False, feedback="Replace long run with 45min easy run"):**
- Returns `proposed_v2` not None
- `proposed_v2["readiness_level"]` in ("green", "yellow", "red") — valid, no crash
- No session in `proposed_v2` has `duration_min > 120` for running (long run replaced)
  — OR notes contain "easy" / "z1" reference

---

### S6 — Missing sleep data → graceful degradation
**File:** `test_scenario_06_missing_sleep.py`  
**Profile:** `simon_no_sleep()` (terra_health=[]), `STABLE_LOAD`

**Step 1 — create_plan:**
- Does NOT raise an exception
- `proposed` is not None
- `proposed["sessions"]` non-empty (plan still produced)
- `proposed["readiness_level"]` in ("yellow", "red") — degraded, not "green"
- No field in proposed is `None` that should be set

**Step 2 — resume_plan(approved=True):**
- `final` not None, persisted normally

---

### S7 — RED-S threshold → non-overridable veto
**File:** `test_scenario_07_reds_veto.py`  
**Profile:** `simon_reds()` — `EnergySnapshotModel` pre-seeded with `veto_triggered=True, intensity_cap=0.0`  
**Load:** `STABLE_LOAD`

**Step 1 — create_plan:**
- `proposed` not None (no crash, no raise)
- `proposed["energy_snapshot"]["veto_triggered"] == True`
- All sessions: `duration_min == 1` (cap=0.0 → `max(1, int(d * 0.0)) = 1`)
- `proposed["energy_snapshot"]["intensity_cap"] == pytest.approx(0.0)`

**Step 2 — resume_plan(approved=True):**
- `final` not None (plan persists — decision to continue is athlete's)
- DB: `TrainingPlanModel` created with sessions all at `duration_min == 1`

---

### S8 — Luteal phase → adjusted prescription
**File:** `test_scenario_08_luteal_phase.py`  
**Profile:** `layla_luteal()`, `STABLE_LOAD`

**Step 1 — create_plan:**
- `proposed` not None
- `proposed["readiness_level"]` in ("yellow", "red") — luteal phase triggers conservative readiness
- At least one session note contains "luteal" OR "cycle" OR intensity reduced vs `simon_fresh()` equivalent
- Nutrition notes (if present): `protein_g_per_kg` ≥ 1.8 (luteal protein bonus)

**Step 2 — resume_plan(approved=True):**
- `final` not None, persisted

---

## Infrastructure Details

### `scenario_db` fixture pattern (per file)
```python
import random
random.seed(42)

@pytest.fixture(scope="module")
def scenario_db():
    engine = _make_e2e_engine()
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)
    with Session() as db:
        athlete = AthleteModel(id="simon-e2e-001", name="Simon", ...)
        db.add(athlete)
        db.commit()
        yield db
    Base.metadata.drop_all(engine)
```

### Connector mocking
Each file patches at module level:
```python
@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr("app.connectors.strava.StravaConnector.fetch_activities",
                        lambda *a, **kw: [])
    monkeypatch.setattr("app.connectors.hevy.HevyConnector.fetch_workouts",
                        lambda *a, **kw: [])
```

### Cross-test state
`_state: dict = {}` module-level dict carries `thread_id` from step 1 to step 2 within each scenario file (same pattern as `test_full_workflow.py`).

---

## `docs/backend/E2E-SCENARIOS.md` — structure

Living spec table — updated after each scenario added:

```markdown
# E2E Coaching Scenarios — Living Spec

| # | Scenario | File | Key coverage | Status |
|---|---|---|---|---|
| 1 | Fresh athlete → confirm | test_scenario_01_fresh_athlete.py | create+resume approved, DB persist | ✅ |
...

## Common Pattern
## Fixture Reference (athlete_states.py)
## How to Add a Scenario
```

---

## Execution Rules

1. `git pull --rebase origin main` before first commit
2. 1 commit per scenario file + fixtures: `test(e2e): add scenario N — <description>`
3. After each commit: `pytest tests/e2e/test_scenario_0N_*.py -v` — all tests green before next scenario
4. Final commit: `docs(e2e): add E2E-SCENARIOS.md living spec`
5. `/revise-claude-md` after all scenarios green

---

## Out of Scope

- HTTP route tests — already covered by `test_full_mode_workflow.py`
- Weekly review graph (`WeeklyReviewGraph`) — separate concern
- Nutrition Lookup Service — V3-P, different domain
- `backend/app/integrations/nutrition/` — not touched
