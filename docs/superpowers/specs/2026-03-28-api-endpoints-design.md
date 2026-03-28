# API Endpoints — Phase 1 Design

## Overview

Add a FastAPI layer exposing athlete CRUD and weekly training plan generation to a web frontend. No authentication in this phase. All business logic (agents, core modules) is already implemented and tested.

## Scope

**In scope:**
- Athlete CRUD: list, create, get, update, delete
- Plan generation: POST to generate, GET to retrieve latest
- Full-stack integration test calling real HeadCoach (no mocking)
- Add `created_at` timestamp to `TrainingPlanModel` for deterministic plan ordering

**Out of scope:**
- Authentication / authorization
- OAuth connector flows (Strava, Hevy)
- Nutrition plan endpoints
- Weekly review endpoints
- Async / background job processing

## Architecture

Router-per-resource pattern using FastAPI `APIRouter`. Two routers (`athletes`, `plans`) mounted in `main.py`. DB session injected via `Depends(get_db)` from `dependencies.py`.

```
backend/app/
├── main.py                  # FastAPI app, router mounts, CORS
├── dependencies.py          # get_db() session dependency
└── routes/
    ├── __init__.py
    ├── athletes.py          # CRUD /athletes
    └── plans.py             # POST/GET /athletes/{id}/plan
```

## Endpoints

### Athletes

| Method | Path | Status codes |
|--------|------|--------------|
| `GET` | `/athletes` | 200 |
| `POST` | `/athletes` | 201 |
| `GET` | `/athletes/{id}` | 200, 404 |
| `PUT` | `/athletes/{id}` | 200, 404 |
| `DELETE` | `/athletes/{id}` | 204, 404 |

**Schemas (already in `backend/app/schemas/athlete.py`):**
- Input: `AthleteCreate` — all `AthleteProfile` fields except `id` (auto-generated)
- Input: `AthleteUpdate` — all fields optional
- Output: `AthleteResponse` — all `AthleteProfile` fields

`AthleteProfile` includes fitness markers (`max_hr`, `resting_hr`, `ftp_watts`, `vdot`, `css_per_100m`) and lifestyle fields (`sleep_hours_typical`, `stress_level`, `job_physical`). These default to `None`/sensible defaults when not provided; agents handle missing values gracefully via cold-start logic.

**JSON field serialization:** `sports`, `goals`, `available_days`, `equipment` are stored as JSON strings in `AthleteModel`. Route handlers must:
- On write: `json.dumps([v.value for v in athlete.sports])` etc.
- On read: `json.loads(model.sports_json)` etc., then reconstruct `AthleteResponse`

FastAPI handles 422 validation automatically.

### Plans

| Method | Path | Status codes |
|--------|------|--------------|
| `POST` | `/athletes/{id}/plan` | 201, 404 |
| `GET` | `/athletes/{id}/plan` | 200, 404 |

**`POST /athletes/{id}/plan` request body:**
```json
{ "start_date": "2026-03-30", "end_date": "2026-04-05" }
```

**Generation flow (step by step):**

1. Load `AthleteModel` from DB by `id` → raise `HTTPException(404)` if not found
2. Deserialize into `AthleteProfile` (parse JSON fields, reconstruct `Sport` enums etc.)
3. Compute `phase` string (`PeriodizationPhase` is a dataclass, not an enum — access inner `MacroPhase` via `.phase.value`):
   ```python
   from app.core.periodization import get_current_phase
   phase_obj = get_current_phase(athlete_profile.target_race_date, start_date)
   phase = phase_obj.phase.value   # MacroPhase string e.g. "general_prep"
   ```
4. Compute `weeks_remaining`:
   ```python
   if athlete_profile.target_race_date:
       weeks_remaining = max(0, (athlete_profile.target_race_date - start_date).days // 7)
   else:
       weeks_remaining = 0
   ```
5. Build `AgentContext`:
   ```python
   context = AgentContext(
       athlete=athlete_profile,
       date_range=(start_date, end_date),
       phase=phase,
       strava_activities=[],
       hevy_workouts=[],
       terra_health=[],
       fatsecret_days=[],
       week_number=1,          # always 1 in Phase 1
       weeks_remaining=weeks_remaining,
   )
   ```
6. Call HeadCoach:
   ```python
   from app.agents.running_coach import RunningCoach
   from app.agents.lifting_coach import LiftingCoach
   from app.agents.head_coach import HeadCoach

   coach = HeadCoach(agents=[RunningCoach(), LiftingCoach()])
   weekly_plan = coach.build_week(context, load_history=[])
   # load_history=[] → no prior load data in Phase 1
   ```
7. Persist as `TrainingPlanModel`:
   ```python
   import json, uuid
   from datetime import datetime, timezone

   plan_id = str(uuid.uuid4())
   model = TrainingPlanModel(
       id=plan_id,
       athlete_id=str(athlete_profile.id),
       start_date=start_date,
       end_date=end_date,
       phase=weekly_plan.phase.phase.value,   # PeriodizationPhase → MacroPhase → str
       total_weekly_hours=sum(s.duration_min for s in weekly_plan.sessions) / 60,
       acwr=weekly_plan.acwr.ratio,
       weekly_slots_json=json.dumps(
           [s.model_dump(mode="json") for s in weekly_plan.sessions]
       ),
       created_at=datetime.now(timezone.utc),
   )
   db.add(model)
   db.commit()
   ```
8. Return `TrainingPlanResponse` (see Response schema below)

**`GET /athletes/{id}/plan`** — retrieve most recently generated plan:
```python
from sqlalchemy import desc
plan = (
    db.query(TrainingPlanModel)
    .filter(TrainingPlanModel.athlete_id == id)
    .order_by(desc(TrainingPlanModel.created_at))
    .first()
)
if plan is None:
    raise HTTPException(404)
```

**Response schema (`TrainingPlanResponse`):**

Define a new Pydantic response model in `backend/app/schemas/plan.py`. Note: `id` and `athlete_id` are `str` (not `UUID`) because `TrainingPlanModel` stores them as strings — this is intentional and differs from the existing `TrainingPlan` schema.
```python
class TrainingPlanResponse(BaseModel):
    id: str
    athlete_id: str
    start_date: date
    end_date: date
    phase: str
    total_weekly_hours: float
    acwr: float
    sessions: list[WorkoutSlot]    # parsed from weekly_slots_json

    @classmethod
    def from_model(cls, m: TrainingPlanModel) -> "TrainingPlanResponse":
        import json
        sessions = [WorkoutSlot.model_validate(s) for s in json.loads(m.weekly_slots_json)]
        return cls(
            id=m.id,
            athlete_id=m.athlete_id,
            start_date=m.start_date,
            end_date=m.end_date,
            phase=m.phase,
            total_weekly_hours=m.total_weekly_hours,
            acwr=m.acwr,
            sessions=sessions,
        )
```

## DB Model Change

Add `created_at` column to `TrainingPlanModel` in `backend/app/db/models.py`:
```python
from sqlalchemy import DateTime
from datetime import datetime, timezone

class TrainingPlanModel(Base):
    ...
    created_at = Column(DateTime, nullable=True,
                        default=lambda: datetime.now(timezone.utc))
```

`nullable=True` keeps SQLite compatible (no SQL-level DEFAULT clause; the Python-side `default` fires on ORM inserts). All new rows created via SQLAlchemy ORM will always have a non-null value. Order by `created_at DESC` (NULLs last) to get the most recently generated plan.

## Dependencies

`backend/app/dependencies.py`:
```python
from collections.abc import Generator
from sqlalchemy.orm import Session
from app.db.database import SessionLocal

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

## Error Handling

- **404**: `HTTPException(status_code=404)` for missing athlete or plan
- **422**: Handled automatically by FastAPI/Pydantic
- No custom error middleware in this phase

## Testing

**Setup pattern** (same as `tests/backend/db/test_models.py`):
```python
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_db

def override_get_db():
    # fresh in-memory SQLite per test
    ...
    yield session

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)
```

**Test files:**
- `tests/backend/api/test_athletes.py` (~8 tests):
  - `test_create_athlete_returns_201`
  - `test_get_athlete_returns_200`
  - `test_get_athlete_not_found_returns_404`
  - `test_list_athletes_empty`
  - `test_list_athletes_after_create`
  - `test_update_athlete_returns_200`
  - `test_delete_athlete_returns_204`
  - `test_create_athlete_missing_required_field_returns_422`

- `tests/backend/api/test_plans.py` (~8 tests):
  - `test_generate_plan_returns_201_with_sessions` — assert `weekly_plan.sessions` is non-empty and `acwr >= 0`
  - `test_generate_plan_unknown_athlete_returns_404`
  - `test_get_plan_returns_latest` — generate two plans with `time.sleep(0.001)` between them to ensure distinct `created_at` values, assert GET returns the second one
  - `test_get_plan_no_plan_returns_404`
  - `test_plan_phase_matches_periodization` — assert returned `phase` matches `get_current_phase(target_race_date, start_date).value`
  - `test_plan_total_weekly_hours_positive`
  - `test_plan_sessions_have_valid_dates` — all `WorkoutSlot.date` values fall within `[start_date, end_date]`
  - `test_plan_persisted_in_db` — after POST, query DB directly and assert row exists

## File Summary

| File | Action |
|------|--------|
| `backend/app/main.py` | Create |
| `backend/app/dependencies.py` | Create |
| `backend/app/routes/__init__.py` | Create |
| `backend/app/routes/athletes.py` | Create |
| `backend/app/routes/plans.py` | Create |
| `backend/app/schemas/plan.py` | Modify — add `TrainingPlanResponse` |
| `backend/app/db/models.py` | Modify — add `created_at` to `TrainingPlanModel` |
| `tests/backend/api/__init__.py` | Create |
| `tests/backend/api/test_athletes.py` | Create |
| `tests/backend/api/test_plans.py` | Create |
