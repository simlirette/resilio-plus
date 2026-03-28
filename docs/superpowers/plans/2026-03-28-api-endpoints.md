# API Endpoints Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a FastAPI layer with athlete CRUD and weekly training plan generation/retrieval backed by the existing HeadCoach + SQLite stack.

**Architecture:** Router-per-resource pattern (`routes/athletes.py`, `routes/plans.py`) mounted in `main.py`. DB session injected via `Depends(get_db)`. Plan generation calls `HeadCoach.build_week` synchronously. Tests use FastAPI `TestClient` with `dependency_overrides` for DB isolation.

**Tech Stack:** FastAPI 0.115+, SQLAlchemy 2.0, Pydantic v2, pytest + `httpx` (via TestClient)

**Spec:** `docs/superpowers/specs/2026-03-28-api-endpoints-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/app/db/models.py` | Modify | Add `created_at` to `TrainingPlanModel` |
| `backend/app/schemas/athlete.py` | Modify | Add `AthleteCreate`, `AthleteUpdate`, `AthleteResponse` |
| `backend/app/schemas/plan.py` | Modify | Add `TrainingPlanResponse` |
| `backend/app/dependencies.py` | Create | `get_db()` session dependency |
| `backend/app/main.py` | Create | FastAPI app factory, router mounts, CORS |
| `backend/app/routes/__init__.py` | Create | Empty package marker |
| `backend/app/routes/athletes.py` | Create | CRUD endpoints for `/athletes` |
| `backend/app/routes/plans.py` | Create | Plan generation/retrieval for `/athletes/{id}/plan` |
| `tests/backend/api/__init__.py` | Create | Empty package marker |
| `tests/backend/api/conftest.py` | Create | Shared `client` fixture + `_athlete_payload` helper |
| `tests/backend/api/test_athletes.py` | Create | 8 athlete endpoint tests |
| `tests/backend/api/test_plans.py` | Create | 8 plan endpoint tests |

---

### Task 1: Add `created_at` to `TrainingPlanModel`

**Files:**
- Modify: `backend/app/db/models.py`
- Modify: `tests/backend/db/test_models.py`

**Context:** `TrainingPlanModel` (line ~39 of `models.py`) needs a `created_at` column so the GET latest plan endpoint can order deterministically. Use `nullable=True` with a Python-side `default` (SQLite doesn't get a SQL-level DEFAULT clause this way, but the ORM fires the default on every insert). The existing tests in `test_models.py` use helper functions `make_test_engine()`, `setup_db(engine)`, `teardown_db(engine)`, `make_athlete_row()` — reuse them.

- [ ] **Step 1: Write the failing test**

Add to `tests/backend/db/test_models.py`:

```python
def test_training_plan_created_at_auto_populated():
    from app.db.models import AthleteModel, TrainingPlanModel
    from datetime import datetime
    import uuid
    engine = make_test_engine()
    Session = setup_db(engine)
    athlete_id = str(uuid.uuid4())
    plan_id = str(uuid.uuid4())
    with Session() as session:
        session.add(AthleteModel(**{**make_athlete_row(), "id": athlete_id}))
        session.add(TrainingPlanModel(
            id=plan_id,
            athlete_id=athlete_id,
            start_date=date(2026, 4, 7),
            end_date=date(2026, 4, 13),
            phase="general_prep",
            total_weekly_hours=8.0,
            acwr=1.0,
            weekly_slots_json="[]",
            # created_at intentionally omitted — must auto-populate
        ))
        session.commit()
        fetched = session.get(TrainingPlanModel, plan_id)
        assert fetched.created_at is not None
        assert isinstance(fetched.created_at, datetime)
    teardown_db(engine)
```

- [ ] **Step 2: Run test to verify it fails**

```
cd backend && python -m pytest ../tests/backend/db/test_models.py::test_training_plan_created_at_auto_populated -v
```

Expected: FAIL — `TrainingPlanModel has no attribute 'created_at'`

- [ ] **Step 3: Add `created_at` column to `TrainingPlanModel`**

In `backend/app/db/models.py`, add these imports at the top (after existing imports):

```python
from datetime import datetime, timezone
```

And add to the `TrainingPlanModel` class (after `weekly_slots_json`):

```python
    created_at = Column(DateTime, nullable=True,
                        default=lambda: datetime.now(timezone.utc))
```

Also add `DateTime` to the existing sqlalchemy import line:

```python
from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
```

- [ ] **Step 4: Run tests to verify they pass**

```
cd backend && python -m pytest ../tests/backend/db/test_models.py -v
```

Expected: All tests PASS including the new one.

- [ ] **Step 5: Commit**

```bash
git add backend/app/db/models.py tests/backend/db/test_models.py
git commit -m "feat: add created_at column to TrainingPlanModel"
```

---

### Task 2: Add athlete request/response schemas

**Files:**
- Modify: `backend/app/schemas/athlete.py`

**Context:** `AthleteProfile` already exists in this file. We need three additions:
- `AthleteCreate`: same fields as `AthleteProfile` but without `id` (caller doesn't supply it)
- `AthleteUpdate`: all fields optional (for partial PATCH-style updates via PUT)
- `AthleteResponse`: identical to `AthleteProfile` — a type alias is sufficient

There are no existing schema tests. We'll verify via the route tests in Task 5. For now, a quick smoke test ensures the models are importable and validate correctly.

- [ ] **Step 1: Write the failing import test**

Create `tests/backend/schemas/__init__.py` (empty) and `tests/backend/schemas/test_athlete_schemas.py`:

```python
from datetime import date


def test_athlete_create_requires_name():
    from pydantic import ValidationError
    from app.schemas.athlete import AthleteCreate
    import pytest
    with pytest.raises(ValidationError):
        AthleteCreate(
            age=30, sex="F", weight_kg=60.0, height_cm=168.0,
            sports=["running"], primary_sport="running",
            goals=[], available_days=[0, 2, 4], hours_per_week=10.0,
        )


def test_athlete_update_all_optional():
    from app.schemas.athlete import AthleteUpdate
    update = AthleteUpdate()  # no fields — must not raise
    assert update.name is None


def test_athlete_response_is_athlete_profile():
    from app.schemas.athlete import AthleteResponse, AthleteProfile
    assert AthleteResponse is AthleteProfile
```

- [ ] **Step 2: Run test to verify it fails**

```
cd backend && python -m pytest ../tests/backend/schemas/test_athlete_schemas.py -v
```

Expected: FAIL — `cannot import name 'AthleteCreate' from 'app.schemas.athlete'`

- [ ] **Step 3: Add schemas to `backend/app/schemas/athlete.py`**

Append after the existing `AthleteProfile` class:

```python
class AthleteCreate(BaseModel):
    name: str
    age: int = Field(..., ge=14, le=100)
    sex: Literal["M", "F", "other"]
    weight_kg: float = Field(..., gt=0)
    height_cm: float = Field(..., gt=0)
    sports: list[Sport]
    primary_sport: Sport
    goals: list[str]
    target_race_date: date | None = None
    available_days: list[int] = Field(..., description="0=Mon … 6=Sun")
    hours_per_week: float = Field(..., gt=0)
    equipment: list[str] = Field(default_factory=list)
    max_hr: int | None = None
    resting_hr: int | None = None
    ftp_watts: int | None = None
    vdot: float | None = None
    css_per_100m: float | None = None
    sleep_hours_typical: float = 7.0
    stress_level: int = Field(default=5, ge=1, le=10)
    job_physical: bool = False


class AthleteUpdate(BaseModel):
    name: str | None = None
    age: int | None = None
    sex: Literal["M", "F", "other"] | None = None
    weight_kg: float | None = None
    height_cm: float | None = None
    sports: list[Sport] | None = None
    primary_sport: Sport | None = None
    goals: list[str] | None = None
    target_race_date: date | None = None
    available_days: list[int] | None = None
    hours_per_week: float | None = None
    equipment: list[str] | None = None
    max_hr: int | None = None
    resting_hr: int | None = None
    ftp_watts: int | None = None
    vdot: float | None = None
    css_per_100m: float | None = None
    sleep_hours_typical: float | None = None
    stress_level: int | None = None
    job_physical: bool | None = None


AthleteResponse = AthleteProfile
```

- [ ] **Step 4: Run tests to verify they pass**

```
cd backend && python -m pytest ../tests/backend/schemas/test_athlete_schemas.py -v
```

Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/athlete.py tests/backend/schemas/__init__.py tests/backend/schemas/test_athlete_schemas.py
git commit -m "feat: add AthleteCreate, AthleteUpdate, AthleteResponse schemas"
```

---

### Task 3: Add `TrainingPlanResponse` schema

**Files:**
- Modify: `backend/app/schemas/plan.py`

**Context:** `plan.py` currently has `WorkoutSlot` and `TrainingPlan`. We add `TrainingPlanResponse` — a response model that deserializes from `TrainingPlanModel` ORM rows. Note: `id` and `athlete_id` are `str` (not `UUID`) intentionally — they're stored as strings in the DB. Add `import json` at the top of the file. The `from_model` classmethod uses `WorkoutSlot.model_validate(s)` (Pydantic v2) to handle nested objects (`Sport` enum, `FatigueScore` model).

- [ ] **Step 1: Write the failing test**

Create `tests/backend/schemas/test_plan_schemas.py`:

```python
import json
from datetime import date


def test_training_plan_response_from_model():
    from app.schemas.plan import TrainingPlanResponse, WorkoutSlot
    from app.schemas.athlete import Sport
    from app.schemas.fatigue import FatigueScore

    slot = WorkoutSlot(
        date=date(2026, 4, 7),
        sport=Sport.RUNNING,
        workout_type="easy_z2",
        duration_min=45,
        fatigue_score=FatigueScore(
            local_muscular=0, cns_load=0, metabolic_cost=0,
            recovery_hours=0, affected_muscles=[],
        ),
    )

    class FakeModel:
        id = "plan-1"
        athlete_id = "ath-1"
        start_date = date(2026, 4, 7)
        end_date = date(2026, 4, 13)
        phase = "general_prep"
        total_weekly_hours = 5.0
        acwr = 1.05
        weekly_slots_json = json.dumps([slot.model_dump(mode="json")])

    resp = TrainingPlanResponse.from_model(FakeModel())
    assert resp.id == "plan-1"
    assert resp.athlete_id == "ath-1"
    assert resp.phase == "general_prep"
    assert resp.acwr == 1.05
    assert len(resp.sessions) == 1
    assert resp.sessions[0].sport == Sport.RUNNING
    assert resp.sessions[0].workout_type == "easy_z2"


def test_training_plan_response_id_is_str():
    from app.schemas.plan import TrainingPlanResponse
    import inspect
    hints = TrainingPlanResponse.model_fields
    assert hints["id"].annotation is str
    assert hints["athlete_id"].annotation is str
```

- [ ] **Step 2: Run test to verify it fails**

```
cd backend && python -m pytest ../tests/backend/schemas/test_plan_schemas.py -v
```

Expected: FAIL — `cannot import name 'TrainingPlanResponse' from 'app.schemas.plan'`

- [ ] **Step 3: Add `TrainingPlanResponse` to `backend/app/schemas/plan.py`**

Add `import json` at the top (after existing imports), then append after `TrainingPlan`:

```python
import json
```

And at the bottom of the file:

```python
class TrainingPlanResponse(BaseModel):
    id: str
    athlete_id: str
    start_date: date
    end_date: date
    phase: str
    total_weekly_hours: float
    acwr: float
    sessions: list[WorkoutSlot]

    @classmethod
    def from_model(cls, m: object) -> "TrainingPlanResponse":
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

- [ ] **Step 4: Run tests to verify they pass**

```
cd backend && python -m pytest ../tests/backend/schemas/test_plan_schemas.py -v
```

Expected: Both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/plan.py tests/backend/schemas/test_plan_schemas.py
git commit -m "feat: add TrainingPlanResponse schema with from_model factory"
```

---

### Task 4: Bootstrap FastAPI app

**Files:**
- Create: `backend/app/dependencies.py`
- Create: `backend/app/main.py`
- Create: `backend/app/routes/__init__.py`

**Context:** `SessionLocal` is in `backend/app/db/database.py`. `main.py` creates the `FastAPI()` instance, adds CORS middleware (`allow_origins=["*"]` — no auth in Phase 1), and includes the two routers (created in Tasks 5 and 6). The routes aren't implemented yet, so we write a minimal smoke test just for the app startup.

- [ ] **Step 1: Write the failing smoke test**

Create `tests/backend/api/__init__.py` (empty) and `tests/backend/api/test_app_smoke.py`:

```python
def test_app_is_importable():
    from app.main import app
    assert app is not None


def test_get_db_yields_session():
    from app.dependencies import get_db
    from sqlalchemy.orm import Session
    gen = get_db()
    # Can't call next() without a real DB; just verify it's a generator
    import inspect
    assert inspect.isgeneratorfunction(get_db)
```

- [ ] **Step 2: Run test to verify it fails**

```
cd backend && python -m pytest ../tests/backend/api/test_app_smoke.py -v
```

Expected: FAIL — `No module named 'app.main'`

- [ ] **Step 3: Create `backend/app/dependencies.py`**

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

- [ ] **Step 4: Create `backend/app/routes/__init__.py`**

Empty file:

```python
```

- [ ] **Step 5: Create `backend/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.athletes import router as athletes_router
from app.routes.plans import router as plans_router

app = FastAPI(title="Resilio Plus API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(athletes_router)
app.include_router(plans_router)
```

Note: `main.py` imports from `routes/athletes.py` and `routes/plans.py` which don't exist yet. To make the smoke test pass, create stub files first:

`backend/app/routes/athletes.py` (stub — will be replaced in Task 5):

```python
from fastapi import APIRouter
router = APIRouter()
```

`backend/app/routes/plans.py` (stub — will be replaced in Task 6):

```python
from fastapi import APIRouter
router = APIRouter()
```

- [ ] **Step 6: Run smoke tests to verify they pass**

```
cd backend && python -m pytest ../tests/backend/api/test_app_smoke.py -v
```

Expected: Both tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/dependencies.py backend/app/main.py backend/app/routes/__init__.py backend/app/routes/athletes.py backend/app/routes/plans.py tests/backend/api/__init__.py tests/backend/api/test_app_smoke.py
git commit -m "feat: bootstrap FastAPI app with dependencies and stub routes"
```

---

### Task 5: Athletes CRUD routes + tests

**Files:**
- Replace: `backend/app/routes/athletes.py`
- Create: `tests/backend/api/conftest.py`
- Create: `tests/backend/api/test_athletes.py`

**Context:** Replace the stub `athletes.py` with the full implementation. The `_model_to_response` helper converts `AthleteModel` → `AthleteResponse` (which is `AthleteProfile`). The `PUT` handler uses `model_dump(exclude_unset=True)` to apply only provided fields. JSON fields are stored in `_json` columns; `primary_sport` is stored as `.value` string. All 404s raise `HTTPException(status_code=404)`.

The `conftest.py` provides a `client` fixture that creates a fresh in-memory SQLite DB per test and overrides the `get_db` dependency. The `_athlete_payload()` helper returns a minimal valid athlete dict for POST bodies.

- [ ] **Step 1: Create `tests/backend/api/conftest.py`**

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db import models  # noqa: F401 — registers ORM models with Base
from app.dependencies import get_db
from app.main import app


def _make_test_engine():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def set_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


@pytest.fixture()
def client():
    engine = _make_test_engine()
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(engine)

    def override_get_db():
        with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def athlete_payload(**overrides):
    base = {
        "name": "Alice",
        "age": 30,
        "sex": "F",
        "weight_kg": 60.0,
        "height_cm": 168.0,
        "sports": ["running", "lifting"],
        "primary_sport": "running",
        "goals": ["run sub-4h marathon"],
        "available_days": [0, 2, 4, 6],
        "hours_per_week": 10.0,
    }
    return {**base, **overrides}
```

- [ ] **Step 2: Write the failing athletes tests**

Create `tests/backend/api/test_athletes.py`:

```python
from tests.backend.api.conftest import athlete_payload


def test_list_athletes_empty(client):
    resp = client.get("/athletes/")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_athlete_returns_201(client):
    resp = client.post("/athletes/", json=athlete_payload())
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Alice"
    assert body["primary_sport"] == "running"
    assert "id" in body


def test_list_athletes_after_create(client):
    client.post("/athletes/", json=athlete_payload())
    resp = client.get("/athletes/")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_get_athlete_returns_200(client):
    create_resp = client.post("/athletes/", json=athlete_payload())
    athlete_id = create_resp.json()["id"]
    resp = client.get(f"/athletes/{athlete_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == athlete_id


def test_get_athlete_not_found_returns_404(client):
    resp = client.get("/athletes/does-not-exist")
    assert resp.status_code == 404


def test_update_athlete_returns_200(client):
    create_resp = client.post("/athletes/", json=athlete_payload())
    athlete_id = create_resp.json()["id"]
    resp = client.put(f"/athletes/{athlete_id}", json={"name": "Bob", "age": 25})
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Bob"
    assert body["age"] == 25
    assert body["sex"] == "F"  # unchanged


def test_delete_athlete_returns_204(client):
    create_resp = client.post("/athletes/", json=athlete_payload())
    athlete_id = create_resp.json()["id"]
    resp = client.delete(f"/athletes/{athlete_id}")
    assert resp.status_code == 204
    assert client.get(f"/athletes/{athlete_id}").status_code == 404


def test_create_athlete_missing_required_field_returns_422(client):
    payload = athlete_payload()
    del payload["name"]
    resp = client.post("/athletes/", json=payload)
    assert resp.status_code == 422
```

- [ ] **Step 3: Run tests to verify they fail**

```
cd backend && python -m pytest ../tests/backend/api/test_athletes.py -v
```

Expected: FAIL — routes return 404 (stub router has no routes)

- [ ] **Step 4: Implement `backend/app/routes/athletes.py`**

Replace the stub with:

```python
import json
import uuid
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import AthleteModel
from app.dependencies import get_db
from app.schemas.athlete import AthleteCreate, AthleteResponse, AthleteUpdate, Sport

router = APIRouter(prefix="/athletes", tags=["athletes"])

DB = Annotated[Session, Depends(get_db)]


def _model_to_response(m: AthleteModel) -> AthleteResponse:
    return AthleteResponse(
        id=UUID(m.id),
        name=m.name,
        age=m.age,
        sex=m.sex,
        weight_kg=m.weight_kg,
        height_cm=m.height_cm,
        sports=[Sport(v) for v in json.loads(m.sports_json)],
        primary_sport=Sport(m.primary_sport),
        goals=json.loads(m.goals_json),
        target_race_date=m.target_race_date,
        available_days=json.loads(m.available_days_json),
        hours_per_week=m.hours_per_week,
        equipment=json.loads(m.equipment_json),
        max_hr=m.max_hr,
        resting_hr=m.resting_hr,
        ftp_watts=m.ftp_watts,
        vdot=m.vdot,
        css_per_100m=m.css_per_100m,
        sleep_hours_typical=m.sleep_hours_typical,
        stress_level=m.stress_level,
        job_physical=m.job_physical,
    )


@router.get("/", response_model=list[AthleteResponse])
def list_athletes(db: DB) -> list[AthleteResponse]:
    return [_model_to_response(m) for m in db.query(AthleteModel).all()]


@router.post("/", response_model=AthleteResponse, status_code=201)
def create_athlete(data: AthleteCreate, db: DB) -> AthleteResponse:
    model = AthleteModel(
        id=str(uuid.uuid4()),
        name=data.name,
        age=data.age,
        sex=data.sex,
        weight_kg=data.weight_kg,
        height_cm=data.height_cm,
        primary_sport=data.primary_sport.value,
        target_race_date=data.target_race_date,
        hours_per_week=data.hours_per_week,
        sleep_hours_typical=data.sleep_hours_typical,
        stress_level=data.stress_level,
        job_physical=data.job_physical,
        max_hr=data.max_hr,
        resting_hr=data.resting_hr,
        ftp_watts=data.ftp_watts,
        vdot=data.vdot,
        css_per_100m=data.css_per_100m,
        sports_json=json.dumps([v.value for v in data.sports]),
        goals_json=json.dumps(data.goals),
        available_days_json=json.dumps(data.available_days),
        equipment_json=json.dumps(data.equipment),
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return _model_to_response(model)


@router.get("/{athlete_id}", response_model=AthleteResponse)
def get_athlete(athlete_id: str, db: DB) -> AthleteResponse:
    model = db.get(AthleteModel, athlete_id)
    if model is None:
        raise HTTPException(status_code=404)
    return _model_to_response(model)


@router.put("/{athlete_id}", response_model=AthleteResponse)
def update_athlete(athlete_id: str, data: AthleteUpdate, db: DB) -> AthleteResponse:
    model = db.get(AthleteModel, athlete_id)
    if model is None:
        raise HTTPException(status_code=404)
    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        if key == "sports":
            model.sports_json = json.dumps([v.value for v in value])
        elif key == "goals":
            model.goals_json = json.dumps(value)
        elif key == "available_days":
            model.available_days_json = json.dumps(value)
        elif key == "equipment":
            model.equipment_json = json.dumps(value)
        elif key == "primary_sport":
            model.primary_sport = value.value
        else:
            setattr(model, key, value)
    db.commit()
    db.refresh(model)
    return _model_to_response(model)


@router.delete("/{athlete_id}", status_code=204)
def delete_athlete(athlete_id: str, db: DB) -> None:
    model = db.get(AthleteModel, athlete_id)
    if model is None:
        raise HTTPException(status_code=404)
    db.delete(model)
    db.commit()
```

- [ ] **Step 5: Run tests to verify they pass**

```
cd backend && python -m pytest ../tests/backend/api/test_athletes.py -v
```

Expected: All 8 tests PASS.

- [ ] **Step 6: Run full test suite to check for regressions**

```
cd backend && python -m pytest ../tests/ -v --tb=short 2>&1 | tail -20
```

Expected: All previously passing tests still pass.

- [ ] **Step 7: Commit**

```bash
git add backend/app/routes/athletes.py tests/backend/api/conftest.py tests/backend/api/test_athletes.py
git commit -m "feat: add athletes CRUD routes with tests"
```

---

### Task 6: Plans routes + tests

**Files:**
- Replace: `backend/app/routes/plans.py`
- Create: `tests/backend/api/test_plans.py`

**Context:** Replace the stub with full implementation. The generation flow is:
1. Load `AthleteModel` → 404 if missing
2. Convert to `AthleteProfile` using the same logic as `routes/athletes.py` (copy `_athlete_model_to_profile` — it's identical to `_model_to_response` but returns `AthleteProfile` not `AthleteResponse`, which are the same type)
3. Compute `phase` via `get_current_phase(...).phase.value` (`PeriodizationPhase` is a dataclass; `.phase` is the inner `MacroPhase` enum)
4. Build `AgentContext` with empty connector lists, `week_number=1`
5. Call `HeadCoach(agents=[RunningCoach(), LiftingCoach()]).build_week(context, load_history=[])`
6. Persist `TrainingPlanModel` with `created_at=datetime.now(timezone.utc)`
7. Return `TrainingPlanResponse.from_model(plan_model)`

The GET endpoint checks athlete existence first (404 if missing), then queries for the latest plan ordered by `created_at DESC`.

- [ ] **Step 1: Write the failing plan tests**

Create `tests/backend/api/test_plans.py`:

```python
import time
from datetime import date, timedelta

from tests.backend.api.conftest import athlete_payload

START = "2026-03-30"
END = "2026-04-05"
PLAN_BODY = {"start_date": START, "end_date": END}


def _create_athlete(client, **overrides):
    resp = client.post("/athletes/", json=athlete_payload(**overrides))
    assert resp.status_code == 201
    return resp.json()["id"]


def test_generate_plan_returns_201_with_sessions(client):
    athlete_id = _create_athlete(client)
    resp = client.post(f"/athletes/{athlete_id}/plan", json=PLAN_BODY)
    assert resp.status_code == 201
    body = resp.json()
    assert len(body["sessions"]) > 0
    assert body["acwr"] >= 0


def test_generate_plan_unknown_athlete_returns_404(client):
    resp = client.post("/athletes/does-not-exist/plan", json=PLAN_BODY)
    assert resp.status_code == 404


def test_get_plan_no_plan_returns_404(client):
    athlete_id = _create_athlete(client)
    resp = client.get(f"/athletes/{athlete_id}/plan")
    assert resp.status_code == 404


def test_get_plan_returns_latest(client):
    athlete_id = _create_athlete(client)
    resp1 = client.post(f"/athletes/{athlete_id}/plan", json=PLAN_BODY)
    assert resp1.status_code == 201
    first_id = resp1.json()["id"]

    time.sleep(0.01)  # ensure distinct created_at values

    resp2 = client.post(
        f"/athletes/{athlete_id}/plan",
        json={"start_date": "2026-04-07", "end_date": "2026-04-13"},
    )
    assert resp2.status_code == 201
    second_id = resp2.json()["id"]

    assert first_id != second_id

    get_resp = client.get(f"/athletes/{athlete_id}/plan")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == second_id


def test_plan_phase_matches_periodization(client):
    from app.core.periodization import get_current_phase

    target_race = (date(2026, 3, 30) + timedelta(weeks=30)).isoformat()
    athlete_id = _create_athlete(client, target_race_date=target_race)
    resp = client.post(f"/athletes/{athlete_id}/plan", json=PLAN_BODY)
    assert resp.status_code == 201

    start_date = date.fromisoformat(START)
    expected_phase = get_current_phase(
        date.fromisoformat(target_race), start_date
    ).phase.value  # PeriodizationPhase.phase.value → MacroPhase string
    assert resp.json()["phase"] == expected_phase


def test_plan_total_weekly_hours_positive(client):
    athlete_id = _create_athlete(client)
    resp = client.post(f"/athletes/{athlete_id}/plan", json=PLAN_BODY)
    assert resp.status_code == 201
    assert resp.json()["total_weekly_hours"] > 0


def test_plan_sessions_have_valid_dates(client):
    athlete_id = _create_athlete(client)
    resp = client.post(f"/athletes/{athlete_id}/plan", json=PLAN_BODY)
    assert resp.status_code == 201
    start = date.fromisoformat(START)
    end = date.fromisoformat(END)
    for session in resp.json()["sessions"]:
        session_date = date.fromisoformat(session["date"])
        assert start <= session_date <= end


def test_plan_persisted_in_db(client):
    # Verify persistence by generating a plan then retrieving it via GET.
    # Using the client (not raw DB) avoids timing issues with fixture teardown.
    athlete_id = _create_athlete(client)
    post_resp = client.post(f"/athletes/{athlete_id}/plan", json=PLAN_BODY)
    assert post_resp.status_code == 201
    plan_id = post_resp.json()["id"]

    get_resp = client.get(f"/athletes/{athlete_id}/plan")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == plan_id
```

- [ ] **Step 2: Run tests to verify they fail**

```
cd backend && python -m pytest ../tests/backend/api/test_plans.py -v
```

Expected: FAIL — stub plans router returns 404/405

- [ ] **Step 3: Implement `backend/app/routes/plans.py`**

Replace the stub with:

```python
import json
import uuid
from datetime import date, datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.agents.base import AgentContext
from app.agents.head_coach import HeadCoach
from app.agents.lifting_coach import LiftingCoach
from app.agents.running_coach import RunningCoach
from app.core.periodization import get_current_phase
from app.db.models import AthleteModel, TrainingPlanModel
from app.dependencies import get_db
from app.schemas.athlete import AthleteProfile, Sport
from app.schemas.plan import TrainingPlanResponse

router = APIRouter(prefix="/athletes", tags=["plans"])

DB = Annotated[Session, Depends(get_db)]


class PlanRequest(BaseModel):
    start_date: date
    end_date: date


def _athlete_model_to_profile(m: AthleteModel) -> AthleteProfile:
    return AthleteProfile(
        id=UUID(m.id),
        name=m.name,
        age=m.age,
        sex=m.sex,
        weight_kg=m.weight_kg,
        height_cm=m.height_cm,
        sports=[Sport(v) for v in json.loads(m.sports_json)],
        primary_sport=Sport(m.primary_sport),
        goals=json.loads(m.goals_json),
        target_race_date=m.target_race_date,
        available_days=json.loads(m.available_days_json),
        hours_per_week=m.hours_per_week,
        equipment=json.loads(m.equipment_json),
        max_hr=m.max_hr,
        resting_hr=m.resting_hr,
        ftp_watts=m.ftp_watts,
        vdot=m.vdot,
        css_per_100m=m.css_per_100m,
        sleep_hours_typical=m.sleep_hours_typical,
        stress_level=m.stress_level,
        job_physical=m.job_physical,
    )


@router.post("/{athlete_id}/plan", response_model=TrainingPlanResponse, status_code=201)
def generate_plan(athlete_id: str, req: PlanRequest, db: DB) -> TrainingPlanResponse:
    athlete_model = db.get(AthleteModel, athlete_id)
    if athlete_model is None:
        raise HTTPException(status_code=404)

    athlete = _athlete_model_to_profile(athlete_model)

    phase_obj = get_current_phase(athlete.target_race_date, req.start_date)
    phase = phase_obj.phase.value  # PeriodizationPhase → MacroPhase → str

    if athlete.target_race_date:
        weeks_remaining = max(0, (athlete.target_race_date - req.start_date).days // 7)
    else:
        weeks_remaining = 0

    context = AgentContext(
        athlete=athlete,
        date_range=(req.start_date, req.end_date),
        phase=phase,
        strava_activities=[],
        hevy_workouts=[],
        terra_health=[],
        fatsecret_days=[],
        week_number=1,
        weeks_remaining=weeks_remaining,
    )

    coach = HeadCoach(agents=[RunningCoach(), LiftingCoach()])
    weekly_plan = coach.build_week(context, load_history=[])

    plan_model = TrainingPlanModel(
        id=str(uuid.uuid4()),
        athlete_id=athlete_id,
        start_date=req.start_date,
        end_date=req.end_date,
        phase=weekly_plan.phase.phase.value,  # PeriodizationPhase → MacroPhase → str
        total_weekly_hours=sum(s.duration_min for s in weekly_plan.sessions) / 60,
        acwr=weekly_plan.acwr.ratio,
        weekly_slots_json=json.dumps(
            [s.model_dump(mode="json") for s in weekly_plan.sessions]
        ),
        created_at=datetime.now(timezone.utc),
    )
    db.add(plan_model)
    db.commit()
    db.refresh(plan_model)
    return TrainingPlanResponse.from_model(plan_model)


@router.get("/{athlete_id}/plan", response_model=TrainingPlanResponse)
def get_latest_plan(athlete_id: str, db: DB) -> TrainingPlanResponse:
    athlete = db.get(AthleteModel, athlete_id)
    if athlete is None:
        raise HTTPException(status_code=404, detail="Athlete not found")

    plan = (
        db.query(TrainingPlanModel)
        .filter(TrainingPlanModel.athlete_id == athlete_id)
        .order_by(desc(TrainingPlanModel.created_at))
        .first()
    )
    if plan is None:
        raise HTTPException(status_code=404, detail="No plan found for this athlete")
    return TrainingPlanResponse.from_model(plan)
```

- [ ] **Step 4: Run plan tests to verify they pass**

```
cd backend && python -m pytest ../tests/backend/api/test_plans.py -v
```

Expected: All 8 tests PASS.

- [ ] **Step 5: Run full test suite**

```
cd backend && python -m pytest ../tests/ -v --tb=short 2>&1 | tail -30
```

Expected: All previously passing tests still pass + new tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routes/plans.py tests/backend/api/test_plans.py
git commit -m "feat: add plan generation and retrieval routes with tests"
```

---

## Final Verification

After all tasks complete, run the full suite one last time:

```
cd backend && python -m pytest ../tests/ --tb=short -q
```

Then delete the temporary smoke test (it's superseded by the full suite):

```bash
git rm tests/backend/api/test_app_smoke.py
git commit -m "chore: remove app smoke test (superseded by api tests)"
```
