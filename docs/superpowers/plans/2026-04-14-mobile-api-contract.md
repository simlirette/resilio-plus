# Mobile API Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement 5 new business endpoints that freeze the mobile home screen API contract, plus 5 contract test files and an OpenAPI export.

**Architecture:** Each endpoint is added to its natural route file (or a new `strain.py`). New Pydantic schemas go into the existing `schemas/` files they logically belong to. Contract tests use SQLite in-memory + TestClient via a shared `tests/backend/conftest.py`, mirroring the e2e test pattern.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic v2, pytest, SQLite (tests), Python 3.13.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `backend/app/routes/strain.py` | **Create** | `GET /athletes/{id}/strain` + `MuscleStrainResponse` |
| `backend/app/routes/sessions.py` | **Modify** | Add `GET /athletes/{id}/today` + `POST /athletes/{id}/workouts` |
| `backend/app/routes/nutrition.py` | **Modify** | Add `GET /athletes/{id}/nutrition-today` + `_resolve_day_type()` |
| `backend/app/routes/connectors.py` | **Modify** | Add `POST /athletes/{id}/connectors/sync` + `SyncAllResponse` |
| `backend/app/schemas/session_log.py` | **Modify** | Add `TodayResponse`, `ManualWorkoutRequest`, `ManualWorkoutResponse` |
| `backend/app/schemas/nutrition.py` | **Modify** | Add `NutritionTodayResponse` |
| `backend/app/main.py` | **Modify** | Include `strain_router` |
| `tests/backend/conftest.py` | **Create** | Shared `api_client` + `auth_state` fixtures |
| `tests/backend/test_contract_strain.py` | **Create** | Contract tests for `/strain` |
| `tests/backend/test_contract_today.py` | **Create** | Contract tests for `/today` |
| `tests/backend/test_contract_nutrition_today.py` | **Create** | Contract tests for `/nutrition-today` |
| `tests/backend/test_contract_workouts.py` | **Create** | Contract tests for `POST /workouts` |
| `tests/backend/test_contract_sync.py` | **Create** | Contract tests for `/connectors/sync` |
| `docs/backend/openapi.json` | **Create** | Exported OpenAPI spec |

---

## Task 1: Shared contract test infrastructure

**Files:**
- Create: `tests/backend/conftest.py`

- [ ] **Step 1: Create `tests/backend/conftest.py`**

```python
# tests/backend/conftest.py
"""Shared fixtures for contract tests — SQLite in-memory + TestClient."""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db import models  # noqa: F401 — registers ORM models with Base
from app.dependencies import get_db
from app.main import app


def _make_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_pragma(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def _next_monday() -> str:
    d = date.today()
    days_ahead = (7 - d.weekday()) % 7 or 7
    return str(d + timedelta(days=days_ahead))


def _onboarding_payload() -> dict:
    return {
        "email": "contract@resilio.test",
        "password": "testpass123",
        "plan_start_date": _next_monday(),
        "name": "Contract Tester",
        "age": 30,
        "sex": "M",
        "weight_kg": 75.0,
        "height_cm": 180.0,
        "primary_sport": "running",
        "sports": ["running", "lifting"],
        "goals": ["test"],
        "available_days": [0, 2, 4, 6],
        "hours_per_week": 8.0,
    }


@pytest.fixture(scope="module")
def api_client():
    engine = _make_engine()
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(engine)

    def override_get_db():
        with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="module")
def auth_state(api_client):
    """Create athlete via onboarding, return token + athlete_id."""
    resp = api_client.post("/athletes/onboarding", json=_onboarding_payload())
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return {
        "token": body["access_token"],
        "athlete_id": body["athlete"]["id"],
        "headers": {"Authorization": f"Bearer {body['access_token']}"},
        "plan": body["plan"],
    }
```

- [ ] **Step 2: Verify conftest loads without error**

Run:
```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/ --collect-only
```
Expected: `no tests ran` (no test files yet), no import errors.

- [ ] **Step 3: Commit**

```bash
git add tests/backend/conftest.py
git commit -m "test(contract): add shared api_client + auth_state fixtures"
```

---

## Task 2: Strain endpoint

**Files:**
- Create: `backend/app/routes/strain.py`
- Modify: `backend/app/main.py`
- Create: `tests/backend/test_contract_strain.py`

- [ ] **Step 1: Write failing contract tests**

```python
# tests/backend/test_contract_strain.py
"""Contract tests — GET /athletes/{id}/strain."""


def test_strain_requires_auth(api_client, auth_state):
    resp = api_client.get(f"/athletes/{auth_state['athlete_id']}/strain")
    assert resp.status_code == 401


def test_strain_returns_200_with_schema(api_client, auth_state):
    resp = api_client.get(
        f"/athletes/{auth_state['athlete_id']}/strain",
        headers=auth_state["headers"],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "computed_at" in body
    assert "scores" in body
    assert "peak_group" in body
    assert "peak_score" in body


def test_strain_scores_all_ten_muscle_groups(api_client, auth_state):
    resp = api_client.get(
        f"/athletes/{auth_state['athlete_id']}/strain",
        headers=auth_state["headers"],
    )
    body = resp.json()
    expected = {
        "quads", "posterior_chain", "glutes", "calves", "chest",
        "upper_pull", "shoulders", "triceps", "biceps", "core",
    }
    assert set(body["scores"].keys()) == expected
    for score in body["scores"].values():
        assert 0.0 <= score <= 100.0


def test_strain_peak_matches_max_score(api_client, auth_state):
    resp = api_client.get(
        f"/athletes/{auth_state['athlete_id']}/strain",
        headers=auth_state["headers"],
    )
    body = resp.json()
    assert body["scores"][body["peak_group"]] == body["peak_score"]


def test_strain_403_for_other_athlete(api_client, auth_state):
    resp = api_client.get(
        "/athletes/00000000-0000-0000-0000-000000000000/strain",
        headers=auth_state["headers"],
    )
    assert resp.status_code == 403
```

- [ ] **Step 2: Run to verify all 5 tests fail**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/test_contract_strain.py -v
```
Expected: 5 FAILED (404 Not Found — route doesn't exist yet).

- [ ] **Step 3: Create `backend/app/routes/strain.py`**

```python
# backend/app/routes/strain.py
from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.strain import compute_muscle_strain
from ..db.models import AthleteModel
from ..dependencies import get_db, get_current_athlete_id
from ..services.connector_service import fetch_connector_data

router = APIRouter(prefix="/athletes", tags=["strain"])

DB = Annotated[Session, Depends(get_db)]


class MuscleStrainResponse(BaseModel):
    computed_at: date
    scores: dict[str, float]
    peak_group: str
    peak_score: float


def _require_own(
    athlete_id: str,
    current_id: Annotated[str, Depends(get_current_athlete_id)],
) -> str:
    if current_id != athlete_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return athlete_id


@router.get("/{athlete_id}/strain", response_model=MuscleStrainResponse)
def get_strain(
    athlete_id: str,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> MuscleStrainResponse:
    if db.get(AthleteModel, athlete_id) is None:
        raise HTTPException(status_code=404, detail="Athlete not found")

    connector_data = fetch_connector_data(athlete_id, db)
    strain = compute_muscle_strain(
        strava_activities=connector_data["strava_activities"],
        hevy_workouts=connector_data["hevy_workouts"],
        reference_date=date.today(),
    )

    scores = strain.model_dump()
    peak_group = max(scores, key=lambda k: scores[k])

    return MuscleStrainResponse(
        computed_at=date.today(),
        scores=scores,
        peak_group=peak_group,
        peak_score=scores[peak_group],
    )
```

- [ ] **Step 4: Register strain router in `backend/app/main.py`**

Add after the last import line (around line 22) and after `app.include_router(external_plan_router)`:

```python
# Add to imports:
from .routes.strain import router as strain_router

# Add to router registrations (after external_plan_router):
app.include_router(strain_router)
```

- [ ] **Step 5: Run strain tests — all should pass**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/test_contract_strain.py -v
```
Expected: 5 PASSED.

- [ ] **Step 6: Run full test suite — no regressions**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -x -q
```
Expected: all existing tests still pass.

- [ ] **Step 7: Commit**

```bash
git add backend/app/routes/strain.py backend/app/main.py tests/backend/test_contract_strain.py
git commit -m "feat(api): add GET /athletes/{id}/strain — muscle strain radar endpoint"
```

---

## Task 3: Today's sessions endpoint

**Files:**
- Modify: `backend/app/schemas/session_log.py` (add `TodayResponse`)
- Modify: `backend/app/routes/sessions.py` (add `GET /today`)
- Create: `tests/backend/test_contract_today.py`

- [ ] **Step 1: Write failing contract tests**

```python
# tests/backend/test_contract_today.py
"""Contract tests — GET /athletes/{id}/today."""
from datetime import date, timedelta


def test_today_requires_auth(api_client, auth_state):
    resp = api_client.get(f"/athletes/{auth_state['athlete_id']}/today")
    assert resp.status_code == 401


def test_today_returns_200(api_client, auth_state):
    resp = api_client.get(
        f"/athletes/{auth_state['athlete_id']}/today",
        headers=auth_state["headers"],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "date" in body
    assert "is_rest_day" in body
    assert "sessions" in body
    assert isinstance(body["sessions"], list)


def test_today_past_date_is_rest_day(api_client, auth_state):
    """A date with no plan sessions → is_rest_day=True, empty list."""
    resp = api_client.get(
        f"/athletes/{auth_state['athlete_id']}/today",
        headers=auth_state["headers"],
        params={"target_date": "2020-01-01"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_rest_day"] is True
    assert body["sessions"] == []
    assert body["date"] == "2020-01-01"


def test_today_session_fields(api_client, auth_state):
    """Sessions in response have all required schema fields."""
    # Use plan start date — guaranteed to have sessions
    plan = auth_state["plan"]
    start_date = plan["start_date"]
    resp = api_client.get(
        f"/athletes/{auth_state['athlete_id']}/today",
        headers=auth_state["headers"],
        params={"target_date": start_date},
    )
    body = resp.json()
    for session in body["sessions"]:
        assert "session_id" in session
        assert "plan_id" in session
        assert "sport" in session
        assert "workout_type" in session
        assert "duration_min" in session
        assert "fatigue_score" in session
        assert "log" in session  # None when not logged


def test_today_403_for_other_athlete(api_client, auth_state):
    resp = api_client.get(
        "/athletes/00000000-0000-0000-0000-000000000000/today",
        headers=auth_state["headers"],
    )
    assert resp.status_code == 403
```

- [ ] **Step 2: Run to verify all 5 tests fail**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/test_contract_today.py -v
```
Expected: 5 FAILED (404 — route doesn't exist yet).

- [ ] **Step 3: Add `TodayResponse` to `backend/app/schemas/session_log.py`**

Append at the end of the file:

```python
class TodayResponse(BaseModel):
    date: date
    is_rest_day: bool
    plan_id: str | None
    sessions: list[SessionDetailResponse]
```

- [ ] **Step 4: Add `GET /today` route to `backend/app/routes/sessions.py`**

Add the following imports at the top of `sessions.py` (merge with existing imports):
```python
from datetime import date as date_type   # alias to avoid shadowing Query param name
from fastapi import Query
from ..db.models import AthleteModel
```

Then add this route after the existing `get_history` function:

```python
@router.get("/{athlete_id}/today", response_model=TodayResponse)
def get_today(
    athlete_id: str,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
    target_date: date_type | None = Query(default=None),
) -> TodayResponse:
    if db.get(AthleteModel, athlete_id) is None:
        raise HTTPException(status_code=404, detail="Athlete not found")

    today = target_date or date_type.today()

    plan = (
        db.query(TrainingPlanModel)
        .filter(TrainingPlanModel.athlete_id == athlete_id)
        .order_by(desc(TrainingPlanModel.created_at))
        .first()
    )

    if plan is None:
        return TodayResponse(date=today, is_rest_day=True, plan_id=None, sessions=[])

    slots = [WorkoutSlot.model_validate(s) for s in json.loads(plan.weekly_slots_json)]
    today_slots = [s for s in slots if s.date == today]

    sessions = []
    for slot in today_slots:
        log_model = (
            db.query(SessionLogModel)
            .filter(
                SessionLogModel.athlete_id == athlete_id,
                SessionLogModel.session_id == slot.id,
            )
            .first()
        )
        sessions.append(
            SessionDetailResponse(
                session_id=slot.id,
                plan_id=plan.id,
                date=slot.date,
                sport=slot.sport,
                workout_type=slot.workout_type,
                duration_min=slot.duration_min,
                fatigue_score=slot.fatigue_score,
                notes=slot.notes,
                log=_log_to_response(log_model) if log_model else None,
            )
        )

    return TodayResponse(
        date=today,
        is_rest_day=len(sessions) == 0,
        plan_id=plan.id,
        sessions=sessions,
    )
```

Also update the import of `TodayResponse` in `sessions.py`:
```python
from ..schemas.session_log import (
    SessionDetailResponse,
    SessionLogRequest,
    SessionLogResponse,
    TodayResponse,
    WeekSummary,
)
```

- [ ] **Step 5: Run today tests — all pass**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/test_contract_today.py -v
```
Expected: 5 PASSED.

- [ ] **Step 6: Full suite — no regressions**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -x -q
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/session_log.py backend/app/routes/sessions.py tests/backend/test_contract_today.py
git commit -m "feat(api): add GET /athletes/{id}/today — date-filtered session list"
```

---

## Task 4: Nutrition today endpoint

**Files:**
- Modify: `backend/app/schemas/nutrition.py` (add `NutritionTodayResponse`)
- Modify: `backend/app/routes/nutrition.py` (add `GET /nutrition-today`, `_resolve_day_type()`)
- Create: `tests/backend/test_contract_nutrition_today.py`

- [ ] **Step 1: Write failing contract tests**

```python
# tests/backend/test_contract_nutrition_today.py
"""Contract tests — GET /athletes/{id}/nutrition-today."""


def test_nutrition_today_requires_auth(api_client, auth_state):
    resp = api_client.get(f"/athletes/{auth_state['athlete_id']}/nutrition-today")
    assert resp.status_code == 401


def test_nutrition_today_returns_200(api_client, auth_state):
    resp = api_client.get(
        f"/athletes/{auth_state['athlete_id']}/nutrition-today",
        headers=auth_state["headers"],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "date" in body
    assert "day_type" in body
    assert "macro_target" in body


def test_nutrition_today_macro_target_fields(api_client, auth_state):
    resp = api_client.get(
        f"/athletes/{auth_state['athlete_id']}/nutrition-today",
        headers=auth_state["headers"],
    )
    mt = resp.json()["macro_target"]
    assert "carbs_g_per_kg" in mt
    assert "protein_g_per_kg" in mt
    assert "fat_g_per_kg" in mt
    assert "calories_total" in mt
    assert mt["calories_total"] > 0


def test_nutrition_today_valid_day_type(api_client, auth_state):
    resp = api_client.get(
        f"/athletes/{auth_state['athlete_id']}/nutrition-today",
        headers=auth_state["headers"],
    )
    valid = {"rest", "strength", "endurance_short", "endurance_long", "race"}
    assert resp.json()["day_type"] in valid


def test_nutrition_today_rest_fallback_for_past_date(api_client, auth_state):
    """Date with no planned sessions → day_type=rest."""
    resp = api_client.get(
        f"/athletes/{auth_state['athlete_id']}/nutrition-today",
        headers=auth_state["headers"],
        params={"target_date": "2020-01-01"},
    )
    assert resp.status_code == 200
    assert resp.json()["day_type"] == "rest"


def test_nutrition_today_403_for_other_athlete(api_client, auth_state):
    resp = api_client.get(
        "/athletes/00000000-0000-0000-0000-000000000000/nutrition-today",
        headers=auth_state["headers"],
    )
    assert resp.status_code == 403
```

- [ ] **Step 2: Run to verify 6 tests fail**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/test_contract_nutrition_today.py -v
```
Expected: 6 FAILED.

- [ ] **Step 3: Add `NutritionTodayResponse` to `backend/app/schemas/nutrition.py`**

Append at the end:

```python
from datetime import date as _date
from .athlete import DayType as _DayType  # already imported above, alias for clarity


class NutritionTodayResponse(BaseModel):
    date: _date
    day_type: DayType
    macro_target: MacroTarget
    intra_effort_carbs_g_per_h: float | None
    sodium_mg_per_h: float | None
```

Actually, `DayType` is imported from `.athlete` — add a clean import at the top of `nutrition.py` schema file. The existing `nutrition.py` already has `from .athlete import DayType`. So just append:

```python
from datetime import date


class NutritionTodayResponse(BaseModel):
    date: date
    day_type: DayType
    macro_target: MacroTarget
    intra_effort_carbs_g_per_h: float | None
    sodium_mg_per_h: float | None
```

- [ ] **Step 4: Add helpers and route to `backend/app/routes/nutrition.py`**

Add these imports at the top (merge with existing):
```python
import json
from datetime import date as date_type
from sqlalchemy import desc
from fastapi import Query
from ..db.models import TrainingPlanModel
from ..schemas.athlete import DayType, Sport
from ..schemas.nutrition import NutritionTodayResponse
from ..schemas.plan import WorkoutSlot
```

Add the helper functions and route before or after `get_nutrition_directives`:

```python
_DAY_TYPE_PRIORITY: dict[DayType, int] = {
    DayType.RACE: 5,
    DayType.ENDURANCE_LONG: 4,
    DayType.ENDURANCE_SHORT: 3,
    DayType.STRENGTH: 2,
    DayType.REST: 1,
}


def _slot_to_day_type(slot: WorkoutSlot) -> DayType:
    if "race" in slot.workout_type.lower():
        return DayType.RACE
    if slot.sport == Sport.LIFTING:
        return DayType.STRENGTH
    if slot.duration_min > 60:
        return DayType.ENDURANCE_LONG
    return DayType.ENDURANCE_SHORT


def _resolve_day_type(plan: TrainingPlanModel | None, target: date_type) -> DayType:
    if plan is None:
        return DayType.REST
    slots = [WorkoutSlot.model_validate(s) for s in json.loads(plan.weekly_slots_json)]
    today_slots = [s for s in slots if s.date == target]
    if not today_slots:
        return DayType.REST
    best = DayType.REST
    for slot in today_slots:
        candidate = _slot_to_day_type(slot)
        if _DAY_TYPE_PRIORITY[candidate] > _DAY_TYPE_PRIORITY[best]:
            best = candidate
    return best


@router.get("/{athlete_id}/nutrition-today", response_model=NutritionTodayResponse)
def get_nutrition_today(
    athlete_id: str,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
    target_date: date_type | None = Query(default=None),
) -> NutritionTodayResponse:
    athlete_model = db.get(AthleteModel, athlete_id)
    if athlete_model is None:
        raise HTTPException(status_code=404, detail="Athlete not found")
    athlete = athlete_model_to_response(athlete_model)

    today = target_date or date_type.today()

    plan = (
        db.query(TrainingPlanModel)
        .filter(TrainingPlanModel.athlete_id == athlete_id)
        .order_by(desc(TrainingPlanModel.created_at))
        .first()
    )

    day_type = _resolve_day_type(plan, today)
    nutrition_plan = compute_nutrition_directives(athlete)
    day_nutrition = nutrition_plan.targets_by_day_type.get(day_type)
    if day_nutrition is None:
        day_nutrition = nutrition_plan.targets_by_day_type[DayType.REST]

    return NutritionTodayResponse(
        date=today,
        day_type=day_type,
        macro_target=day_nutrition.macro_target,
        intra_effort_carbs_g_per_h=day_nutrition.intra_effort_carbs_g_per_h,
        sodium_mg_per_h=day_nutrition.sodium_mg_per_h,
    )
```

- [ ] **Step 5: Run nutrition-today tests — all pass**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/test_contract_nutrition_today.py -v
```
Expected: 6 PASSED.

- [ ] **Step 6: Full suite — no regressions**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -x -q
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/nutrition.py backend/app/routes/nutrition.py tests/backend/test_contract_nutrition_today.py
git commit -m "feat(api): add GET /athletes/{id}/nutrition-today — day-type resolved macros"
```

---

## Task 5: Manual workout endpoint

**Files:**
- Modify: `backend/app/schemas/session_log.py` (add `ManualWorkoutRequest`, `ManualWorkoutResponse`)
- Modify: `backend/app/routes/sessions.py` (add `POST /workouts`)
- Create: `tests/backend/test_contract_workouts.py`

- [ ] **Step 1: Write failing contract tests**

```python
# tests/backend/test_contract_workouts.py
"""Contract tests — POST /athletes/{id}/workouts (off-plan manual log)."""
from datetime import date


def test_post_workout_requires_auth(api_client, auth_state):
    resp = api_client.post(
        f"/athletes/{auth_state['athlete_id']}/workouts",
        json={
            "sport": "running",
            "workout_type": "Easy run",
            "date": str(date.today()),
            "actual_duration_min": 45,
        },
    )
    assert resp.status_code == 401


def test_post_workout_creates_201(api_client, auth_state):
    resp = api_client.post(
        f"/athletes/{auth_state['athlete_id']}/workouts",
        headers=auth_state["headers"],
        json={
            "sport": "running",
            "workout_type": "Easy run",
            "date": str(date.today()),
            "actual_duration_min": 45,
            "rpe": 6,
            "notes": "Bonus jog",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["session_id"].startswith("manual-")
    assert body["sport"] == "running"
    assert body["actual_duration_min"] == 45
    assert body["rpe"] == 6
    assert "logged_at" in body


def test_post_workout_session_id_is_unique(api_client, auth_state):
    """Two separate manual workouts get distinct session_ids."""
    payload = {
        "sport": "lifting",
        "workout_type": "Upper body",
        "date": str(date.today()),
        "actual_duration_min": 60,
    }
    r1 = api_client.post(
        f"/athletes/{auth_state['athlete_id']}/workouts",
        headers=auth_state["headers"],
        json=payload,
    )
    r2 = api_client.post(
        f"/athletes/{auth_state['athlete_id']}/workouts",
        headers=auth_state["headers"],
        json=payload,
    )
    assert r1.json()["session_id"] != r2.json()["session_id"]


def test_post_workout_invalid_duration_zero(api_client, auth_state):
    resp = api_client.post(
        f"/athletes/{auth_state['athlete_id']}/workouts",
        headers=auth_state["headers"],
        json={
            "sport": "running",
            "workout_type": "Easy",
            "date": str(date.today()),
            "actual_duration_min": 0,
        },
    )
    assert resp.status_code == 422


def test_post_workout_invalid_sport(api_client, auth_state):
    resp = api_client.post(
        f"/athletes/{auth_state['athlete_id']}/workouts",
        headers=auth_state["headers"],
        json={
            "sport": "hockey",
            "workout_type": "Easy",
            "date": str(date.today()),
            "actual_duration_min": 45,
        },
    )
    assert resp.status_code == 422


def test_post_workout_actual_data_stored(api_client, auth_state):
    """actual_data dict preserved in response, sport injected."""
    resp = api_client.post(
        f"/athletes/{auth_state['athlete_id']}/workouts",
        headers=auth_state["headers"],
        json={
            "sport": "running",
            "workout_type": "Long run",
            "date": str(date.today()),
            "actual_duration_min": 90,
            "actual_data": {"distance_km": 15.0},
        },
    )
    body = resp.json()
    assert body["actual_data"]["distance_km"] == 15.0
    assert body["actual_data"]["sport"] == "running"
```

- [ ] **Step 2: Run to verify 6 tests fail**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/test_contract_workouts.py -v
```
Expected: 6 FAILED.

- [ ] **Step 3: Add schemas to `backend/app/schemas/session_log.py`**

Add these at the end (after `WeekSummary`):

```python
class ManualWorkoutRequest(BaseModel):
    sport: Sport
    workout_type: str
    date: date
    actual_duration_min: int = Field(..., ge=1, le=600)
    rpe: int | None = Field(default=None, ge=1, le=10)
    notes: str = ""
    actual_data: dict[str, Any] = Field(default_factory=dict)


class ManualWorkoutResponse(BaseModel):
    id: str
    session_id: str
    sport: Sport
    workout_type: str
    date: date
    actual_duration_min: int
    rpe: int | None
    notes: str
    actual_data: dict[str, Any]
    logged_at: datetime
```

- [ ] **Step 4: Add `POST /workouts` route to `backend/app/routes/sessions.py`**

Update the import from schemas:
```python
from ..schemas.session_log import (
    ManualWorkoutRequest,
    ManualWorkoutResponse,
    SessionDetailResponse,
    SessionLogRequest,
    SessionLogResponse,
    TodayResponse,
    WeekSummary,
)
```

Add route after `get_today`:

```python
@router.post("/{athlete_id}/workouts", response_model=ManualWorkoutResponse, status_code=201)
def log_manual_workout(
    athlete_id: str,
    req: ManualWorkoutRequest,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> ManualWorkoutResponse:
    if db.get(AthleteModel, athlete_id) is None:
        raise HTTPException(status_code=404, detail="Athlete not found")

    session_id = f"manual-{uuid.uuid4()}"
    actual_data = {"sport": req.sport.value, "workout_type": req.workout_type, **req.actual_data}

    log = SessionLogModel(
        id=str(uuid.uuid4()),
        athlete_id=athlete_id,
        plan_id=None,
        session_id=session_id,
        actual_duration_min=req.actual_duration_min,
        skipped=False,
        rpe=req.rpe,
        notes=req.notes,
        actual_data_json=json.dumps(actual_data),
        logged_at=datetime.now(timezone.utc),
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return ManualWorkoutResponse(
        id=log.id,
        session_id=log.session_id,
        sport=req.sport,
        workout_type=req.workout_type,
        date=req.date,
        actual_duration_min=log.actual_duration_min,
        rpe=log.rpe,
        notes=log.notes or "",
        actual_data=json.loads(log.actual_data_json),
        logged_at=log.logged_at,
    )
```

- [ ] **Step 5: Run workouts tests — all pass**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/test_contract_workouts.py -v
```
Expected: 6 PASSED.

- [ ] **Step 6: Full suite — no regressions**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -x -q
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/session_log.py backend/app/routes/sessions.py tests/backend/test_contract_workouts.py
git commit -m "feat(api): add POST /athletes/{id}/workouts — off-plan manual workout log"
```

---

## Task 6: Sync all connectors endpoint

**Files:**
- Modify: `backend/app/routes/connectors.py` (add `SyncAllResponse`, `POST /connectors/sync`)
- Create: `tests/backend/test_contract_sync.py`

- [ ] **Step 1: Write failing contract tests**

```python
# tests/backend/test_contract_sync.py
"""Contract tests — POST /athletes/{id}/connectors/sync."""


def test_sync_all_requires_auth(api_client, auth_state):
    resp = api_client.post(f"/athletes/{auth_state['athlete_id']}/connectors/sync")
    assert resp.status_code == 401


def test_sync_all_returns_200(api_client, auth_state):
    resp = api_client.post(
        f"/athletes/{auth_state['athlete_id']}/connectors/sync",
        headers=auth_state["headers"],
    )
    assert resp.status_code == 200


def test_sync_all_response_schema(api_client, auth_state):
    resp = api_client.post(
        f"/athletes/{auth_state['athlete_id']}/connectors/sync",
        headers=auth_state["headers"],
    )
    body = resp.json()
    assert "synced_at" in body
    assert "results" in body
    assert "errors" in body
    assert isinstance(body["results"], dict)
    assert isinstance(body["errors"], dict)


def test_sync_all_per_provider_valid_statuses(api_client, auth_state):
    """Every provider result is ok|skipped|error."""
    resp = api_client.post(
        f"/athletes/{auth_state['athlete_id']}/connectors/sync",
        headers=auth_state["headers"],
    )
    valid = {"ok", "skipped", "error"}
    for status in resp.json()["results"].values():
        assert status in valid


def test_sync_all_unconfigured_connectors_skipped(api_client, auth_state):
    """Fresh athlete with no connectors configured → all skipped."""
    resp = api_client.post(
        f"/athletes/{auth_state['athlete_id']}/connectors/sync",
        headers=auth_state["headers"],
    )
    body = resp.json()
    # strava, hevy, terra should all be skipped (no credentials stored)
    for provider in ("strava", "hevy", "terra"):
        assert body["results"].get(provider) == "skipped"


def test_sync_all_403_for_other_athlete(api_client, auth_state):
    resp = api_client.post(
        "/athletes/00000000-0000-0000-0000-000000000000/connectors/sync",
        headers=auth_state["headers"],
    )
    assert resp.status_code == 403
```

- [ ] **Step 2: Run to verify 6 tests fail**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/test_contract_sync.py -v
```
Expected: 6 FAILED.

- [ ] **Step 3: Add `SyncAllResponse` and route to `backend/app/routes/connectors.py`**

Add these imports at the top of the file (merge with existing):
```python
from datetime import datetime, timezone, timedelta  # datetime already imported; ensure timezone is there
from typing import Literal
```

Add `SyncAllResponse` schema near the top of the file (after other `BaseModel` classes):

```python
ProviderStatus = Literal["ok", "skipped", "error"]


class SyncAllResponse(BaseModel):
    synced_at: datetime
    results: dict[str, ProviderStatus]
    errors: dict[str, str]
```

Add route at the end of the file:

```python
@router.post("/{athlete_id}/connectors/sync", response_model=SyncAllResponse)
def sync_all(
    athlete_id: str,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> SyncAllResponse:
    results: dict[str, str] = {}
    errors: dict[str, str] = {}

    for provider, sync_fn in [
        ("strava", SyncService.sync_strava),
        ("hevy", SyncService.sync_hevy),
        ("terra", SyncService.sync_terra),
    ]:
        try:
            sync_fn(athlete_id, db)
            results[provider] = "ok"
        except ConnectorNotFoundError:
            results[provider] = "skipped"
        except Exception as exc:  # noqa: BLE001
            results[provider] = "error"
            errors[provider] = str(exc)

    return SyncAllResponse(
        synced_at=datetime.now(timezone.utc),
        results=results,
        errors=errors,
    )
```

- [ ] **Step 4: Run sync tests — all pass**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/test_contract_sync.py -v
```
Expected: 6 PASSED.

- [ ] **Step 5: Full suite — no regressions**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -x -q
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/routes/connectors.py tests/backend/test_contract_sync.py
git commit -m "feat(api): add POST /athletes/{id}/connectors/sync — unified connector sync"
```

---

## Task 7: OpenAPI export

**Files:**
- Create: `docs/backend/openapi.json`

- [ ] **Step 1: Export OpenAPI spec**

```bash
python -c "
import json, sys
sys.path.insert(0, 'backend')
from app.main import app
print(json.dumps(app.openapi(), indent=2))
" > docs/backend/openapi.json
```

- [ ] **Step 2: Verify export has all 5 new paths**

```bash
python -c "
import json
spec = json.load(open('docs/backend/openapi.json'))
paths = spec['paths']
required = [
    '/athletes/{athlete_id}/strain',
    '/athletes/{athlete_id}/today',
    '/athletes/{athlete_id}/nutrition-today',
    '/athletes/{athlete_id}/workouts',
    '/athletes/{athlete_id}/connectors/sync',
]
for p in required:
    assert p in paths, f'MISSING: {p}'
    print(f'OK: {p}')
print('All 5 new paths present.')
"
```
Expected output:
```
OK: /athletes/{athlete_id}/strain
OK: /athletes/{athlete_id}/today
OK: /athletes/{athlete_id}/nutrition-today
OK: /athletes/{athlete_id}/workouts
OK: /athletes/{athlete_id}/connectors/sync
All 5 new paths present.
```

- [ ] **Step 3: Commit**

```bash
git add docs/backend/openapi.json
git commit -m "docs(api): export OpenAPI spec — V1 mobile contract frozen"
```

---

## Task 8: Final validation

- [ ] **Step 1: Run all contract tests together**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/ -v
```
Expected: 29 PASSED (1 conftest + 5+5+6+6+6 tests across 5 files).

- [ ] **Step 2: Run complete test suite**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -q
```
Expected: all existing tests pass + 29 new.

- [ ] **Step 3: Verify no TypeScript errors (frontend unchanged, but sanity check)**

```bash
pnpm --filter @resilio/web typecheck
```
Expected: no errors.

---

## Self-Review Checklist

**Spec coverage:**
- ✅ `GET /strain` → Task 2
- ✅ `GET /today` → Task 3
- ✅ `GET /nutrition-today` → Task 4
- ✅ `POST /workouts` → Task 5
- ✅ `POST /connectors/sync` → Task 6
- ✅ OpenAPI export → Task 7
- ✅ Contract tests for all 5 → Tasks 2–6
- ✅ Auth pattern (uses existing `get_current_athlete_id`) → all route tasks

**Type consistency:**
- `MuscleStrainResponse.scores` is `dict[str, float]` → `strain.model_dump()` returns `dict[str, float]` ✅
- `TodayResponse.sessions` is `list[SessionDetailResponse]` → route builds `SessionDetailResponse` objects ✅
- `NutritionTodayResponse.day_type` is `DayType` → `_resolve_day_type()` returns `DayType` ✅
- `ManualWorkoutResponse.sport` is `Sport` → set from `req.sport` (same type) ✅
- `SyncAllResponse.results` is `dict[str, ProviderStatus]` → values are string literals from the loop ✅

**No placeholders:** All code blocks are complete. ✅
