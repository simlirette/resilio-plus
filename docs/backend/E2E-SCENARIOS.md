# E2E Coaching Scenarios — Living Spec

Tests in `tests/e2e/test_scenario_*.py`. Each file is an independent scenario with its own SQLite in-memory DB and module-scoped fixture.

**Layer:** CoachingService (S1–S7) or HeadCoach.build_week() (S8).
**Fixtures:** `tests/fixtures/athlete_states.py` — `simon_fresh_profile()`, `layla_luteal_context()`, `seed_athlete()`, `seed_energy_snapshot()`.
**Pytest:** `C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/e2e/test_scenario_*.py -v`

---

## Scenario Table

| # | Name | File | Layer | Key assertion |
|---|---|---|---|---|
| 1 | Fresh athlete → confirm | `test_scenario_01_fresh_athlete.py` | CoachingService | `db_plan_id` not None after approve |
| 2 | Energy cap 60% → sessions scaled | `test_scenario_02_energy_cap.py` | CoachingService | `energy_snapshot_dict.intensity_cap == 0.6`, final sessions scaled |
| 3 | Running/Lifting conflict → resolved | `test_scenario_03_conflict_resolution.py` | CoachingService | conflicts key present, all sessions same date |
| 4 | User rejects → revise cycle | `test_scenario_04_user_rejects.py` | CoachingService | `proposed_v2` returned, `db_plan_id=None` |
| 5 | User modifies with feedback | `test_scenario_05_user_modifies.py` | CoachingService | revise cycle completes without error |
| 6 | No energy snapshot → graceful | `test_scenario_06_no_energy_snapshot.py` | CoachingService | `energy_snapshot_dict=None`, sessions unscaled |
| 7 | RED-S veto cap=0.0 | `test_scenario_07_reds_veto.py` | CoachingService | all final sessions `duration_min=1` |
| 8 | Luteal phase → adjusted plan | `test_scenario_08_luteal_phase.py` | HeadCoach.build_week() | notes reference "luteal", readiness valid |

---

## Common Pattern (S1–S7)

```python
# 1. Module-level state dict
_state: dict = {}

# 2. Module-scoped DB fixture
@pytest.fixture(scope="module")
def scenario_db():
    engine = make_scenario_engine()
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)
    with Session() as db:
        seed_athlete(db, ATHLETE_ID)
        # optional: seed_energy_snapshot(...)
        yield db
    Base.metadata.drop_all(engine)

# 3. Step 1 — create plan, store svc instance
def test_01_create_plan(scenario_db):
    svc = CoachingService()
    _state["svc"] = svc  # MUST reuse same instance for resume_plan
    thread_id, proposed = svc.create_plan(ATHLETE_ID, profile_dict, STABLE_LOAD, scenario_db)
    _state["thread_id"] = thread_id

# 4. Step 2 — resume
def test_02_approve(scenario_db):
    final = _state["svc"].resume_plan(_state["thread_id"], approved=True, feedback=None, db=scenario_db)
```

> **Critical:** `CoachingService` instance must be shared across steps. The MemorySaver
> (LangGraph checkpointer) is attached to `svc._graph`. A new `CoachingService()` would
> have a fresh MemorySaver with no checkpoint — `resume_plan` would fail.

---

## Graph Flow (important for S2, S6, S7)

```
build_proposed_plan → present_to_athlete [INTERRUPT]
resume(approved=True) → apply_energy_snapshot → finalize_plan → END
resume(approved=False) → revise_plan → delegate_specialists → ... → present_to_athlete [INTERRUPT again]
```

`apply_energy_snapshot` runs AFTER approval. Check energy scaling on `final` dict (from `resume_plan`), not on `proposed` (from `create_plan`). Use `svc._graph.get_state(config)` to inspect `energy_snapshot_dict` in graph state.

---

## Why S8 uses HeadCoach.build_week() instead of CoachingService

`CoachingService.create_plan()` → `delegate_specialists` node builds `AgentContext` with:
```python
context = AgentContext(athlete=athlete, date_range=..., phase=..., sport_budgets=...)
# No terra_health, no strava_activities, no hevy_workouts, no hormonal_profile
```

Terra health and HormonalProfile don't flow through the graph. HRV-based Recovery Coach
veto and hormonal adjustments require `AgentContext` built with explicit data — only
possible via `HeadCoach.build_week()` directly (as in `test_agents_integration.py`).

---

## Adding a New Scenario

1. Create `tests/e2e/test_scenario_NN_<name>.py`
2. Use `seed_athlete()` + optional `seed_energy_snapshot()` from `athlete_states.py`
3. Follow the Common Pattern above — store `svc` in `_state` and reuse it
4. Run: `pytest tests/e2e/test_scenario_NN_*.py -v`
5. Add row to Scenario Table above
6. Commit: `test(e2e): add scenario NN — <description>`
