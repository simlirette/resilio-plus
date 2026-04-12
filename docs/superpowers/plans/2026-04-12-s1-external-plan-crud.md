# S-1 ExternalPlan Backend CRUD — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement ExternalPlanService + 5 REST endpoints allowing Tracking Only athletes to manually create and manage an external training plan.

**Architecture:** Stateless service class (ExternalPlanService) operating on existing SQLAlchemy models (ExternalPlanModel, ExternalSessionModel from migration 0003). FastAPI router guards all routes with `require_tracking_mode`. Pydantic schemas handle request validation and response serialization.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 (sync), Pydantic v2, pytest + SQLite in-memory for tests.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `backend/app/schemas/external_plan.py` | Create | Pydantic request + response schemas |
| `backend/app/services/external_plan_service.py` | Create | Business logic (CRUD + XOR invariant) |
| `backend/app/routes/external_plan.py` | Create | FastAPI router — 5 endpoints |
| `backend/app/main.py` | Modify | Register new router |
| `tests/backend/services/test_external_plan_service.py` | Create | Service unit tests (SQLite in-memory) |
| `tests/backend/api/test_external_plan.py` | Create | API integration tests (TestClient) |
| `docs/superpowers/specs/2026-04-12-s1-external-plan-design.md` | Already created | Design reference |

---

### Task 1: Pydantic schemas

**Files:**
- Create: `backend/app/schemas/external_plan.py`

- [ ] **Step 1: Write the schemas file**

```python
# backend/app/schemas/external_plan.py
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class ExternalPlanCreate(BaseModel):
    title: str
    start_date: date | None = None
    end_date: date | None = None


class ExternalSessionCreate(BaseModel):
    session_date: date
    sport: str
    title: str
    description: str | None = None
    duration_min: int | None = None


class ExternalSessionUpdate(BaseModel):
    session_date: date | None = None
    sport: str | None = None
    title: str | None = None
    description: str | None = None
    duration_min: int | None = None
    status: Literal["planned", "completed", "skipped"] | None = None


class ExternalSessionOut(BaseModel):
    id: str
    plan_id: str
    athlete_id: str
    session_date: date
    sport: str
    title: str
    description: str | None
    duration_min: int | None
    status: str

    model_config = {"from_attributes": True}


class ExternalPlanOut(BaseModel):
    id: str
    athlete_id: str
    title: str
    source: str
    status: str
    start_date: date | None
    end_date: date | None
    created_at: datetime
    sessions: list[ExternalSessionOut]

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Verify import works**

```bash
cd backend && python -c "from app.schemas.external_plan import ExternalPlanCreate, ExternalPlanOut; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/external_plan.py
git commit -m "feat(s1): add ExternalPlan Pydantic schemas"
```

---

### Task 2: ExternalPlanService — write failing tests first

**Files:**
- Create: `tests/backend/services/test_external_plan_service.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/backend/services/test_external_plan_service.py
"""Unit tests for ExternalPlanService — TDD red phase."""
import uuid
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db import models as _models  # noqa: registers all ORM models
from app.db.models import AthleteModel
from app.models.schemas import ExternalPlanModel, ExternalSessionModel
from app.services.external_plan_service import ExternalPlanService


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _make_athlete(db, mode: str = "tracking_only") -> str:
    athlete_id = str(uuid.uuid4())
    athlete = AthleteModel(
        id=athlete_id,
        name="Test",
        age=30,
        sex="M",
        weight_kg=70.0,
        height_cm=175.0,
        primary_sport="running",
        hours_per_week=8.0,
        sports_json='["running"]',
        goals_json='["fitness"]',
        available_days_json='[0,2,4]',
        equipment_json='[]',
        coaching_mode=mode,
    )
    db.add(athlete)
    db.commit()
    return athlete_id


# ---------------------------------------------------------------------------
# create_plan
# ---------------------------------------------------------------------------

def test_create_plan_returns_active_plan(db):
    athlete_id = _make_athlete(db)
    plan = ExternalPlanService.create_plan(
        athlete_id=athlete_id,
        title="Coach Bob's Plan",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 7, 31),
        db=db,
    )
    assert plan.id is not None
    assert plan.athlete_id == athlete_id
    assert plan.title == "Coach Bob's Plan"
    assert plan.status == "active"
    assert plan.source == "manual"
    assert plan.start_date == date(2026, 5, 1)
    assert plan.end_date == date(2026, 7, 31)


def test_create_plan_archives_previous_active_plan(db):
    athlete_id = _make_athlete(db)
    first = ExternalPlanService.create_plan(
        athlete_id=athlete_id, title="Plan A", db=db,
    )
    second = ExternalPlanService.create_plan(
        athlete_id=athlete_id, title="Plan B", db=db,
    )
    db.refresh(first)
    assert first.status == "archived"
    assert second.status == "active"


def test_create_plan_no_cross_athlete_archiving(db):
    """Creating a plan for athlete A must not archive athlete B's plan."""
    a1 = _make_athlete(db)
    a2 = _make_athlete(db)
    plan_a = ExternalPlanService.create_plan(athlete_id=a1, title="A Plan", db=db)
    ExternalPlanService.create_plan(athlete_id=a2, title="B Plan", db=db)
    db.refresh(plan_a)
    assert plan_a.status == "active"


# ---------------------------------------------------------------------------
# get_active_plan
# ---------------------------------------------------------------------------

def test_get_active_plan_returns_plan(db):
    athlete_id = _make_athlete(db)
    ExternalPlanService.create_plan(athlete_id=athlete_id, title="Active", db=db)
    plan = ExternalPlanService.get_active_plan(athlete_id=athlete_id, db=db)
    assert plan is not None
    assert plan.title == "Active"
    assert plan.status == "active"


def test_get_active_plan_returns_none_when_no_plan(db):
    athlete_id = _make_athlete(db)
    result = ExternalPlanService.get_active_plan(athlete_id=athlete_id, db=db)
    assert result is None


def test_get_active_plan_returns_none_after_archiving(db):
    athlete_id = _make_athlete(db)
    # Create then manually archive
    plan = ExternalPlanService.create_plan(athlete_id=athlete_id, title="X", db=db)
    plan.status = "archived"
    db.commit()
    result = ExternalPlanService.get_active_plan(athlete_id=athlete_id, db=db)
    assert result is None


# ---------------------------------------------------------------------------
# add_session
# ---------------------------------------------------------------------------

def test_add_session_creates_session(db):
    athlete_id = _make_athlete(db)
    plan = ExternalPlanService.create_plan(athlete_id=athlete_id, title="Plan", db=db)
    session = ExternalPlanService.add_session(
        plan_id=plan.id,
        athlete_id=athlete_id,
        session_date=date(2026, 5, 3),
        sport="running",
        title="Easy 5k",
        description="Slow recovery run",
        duration_min=30,
        db=db,
    )
    assert session.id is not None
    assert session.plan_id == plan.id
    assert session.athlete_id == athlete_id
    assert session.sport == "running"
    assert session.title == "Easy 5k"
    assert session.status == "planned"


def test_add_session_to_wrong_athlete_raises(db):
    a1 = _make_athlete(db)
    a2 = _make_athlete(db)
    plan = ExternalPlanService.create_plan(athlete_id=a1, title="Plan", db=db)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        ExternalPlanService.add_session(
            plan_id=plan.id,
            athlete_id=a2,
            session_date=date(2026, 5, 3),
            sport="running",
            title="Sneaky run",
            db=db,
        )
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# update_session
# ---------------------------------------------------------------------------

def test_update_session_partial(db):
    athlete_id = _make_athlete(db)
    plan = ExternalPlanService.create_plan(athlete_id=athlete_id, title="Plan", db=db)
    sess = ExternalPlanService.add_session(
        plan_id=plan.id, athlete_id=athlete_id,
        session_date=date(2026, 5, 3), sport="running", title="Run", db=db,
    )
    updated = ExternalPlanService.update_session(
        session_id=sess.id,
        athlete_id=athlete_id,
        updates={"title": "Long Run", "duration_min": 60, "status": "completed"},
        db=db,
    )
    assert updated.title == "Long Run"
    assert updated.duration_min == 60
    assert updated.status == "completed"
    assert updated.sport == "running"  # unchanged


def test_update_session_wrong_athlete_raises(db):
    a1 = _make_athlete(db)
    a2 = _make_athlete(db)
    plan = ExternalPlanService.create_plan(athlete_id=a1, title="Plan", db=db)
    sess = ExternalPlanService.add_session(
        plan_id=plan.id, athlete_id=a1,
        session_date=date(2026, 5, 3), sport="running", title="Run", db=db,
    )
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        ExternalPlanService.update_session(
            session_id=sess.id, athlete_id=a2,
            updates={"title": "Hacked"}, db=db,
        )
    assert exc.value.status_code == 404


def test_update_nonexistent_session_raises(db):
    athlete_id = _make_athlete(db)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        ExternalPlanService.update_session(
            session_id="ghost-id", athlete_id=athlete_id,
            updates={"title": "X"}, db=db,
        )
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# delete_session
# ---------------------------------------------------------------------------

def test_delete_session_removes_record(db):
    athlete_id = _make_athlete(db)
    plan = ExternalPlanService.create_plan(athlete_id=athlete_id, title="Plan", db=db)
    sess = ExternalPlanService.add_session(
        plan_id=plan.id, athlete_id=athlete_id,
        session_date=date(2026, 5, 3), sport="running", title="Run", db=db,
    )
    session_id = sess.id
    ExternalPlanService.delete_session(
        session_id=session_id, athlete_id=athlete_id, db=db,
    )
    result = db.get(ExternalSessionModel, session_id)
    assert result is None


def test_delete_session_wrong_athlete_raises(db):
    a1 = _make_athlete(db)
    a2 = _make_athlete(db)
    plan = ExternalPlanService.create_plan(athlete_id=a1, title="Plan", db=db)
    sess = ExternalPlanService.add_session(
        plan_id=plan.id, athlete_id=a1,
        session_date=date(2026, 5, 3), sport="running", title="Run", db=db,
    )
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        ExternalPlanService.delete_session(
            session_id=sess.id, athlete_id=a2, db=db,
        )
    assert exc.value.status_code == 404


def test_delete_nonexistent_session_raises(db):
    athlete_id = _make_athlete(db)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        ExternalPlanService.delete_session(
            session_id="ghost", athlete_id=athlete_id, db=db,
        )
    assert exc.value.status_code == 404
```

- [ ] **Step 2: Run tests — expect ImportError / FAIL (red)**

```bash
cd backend && C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/services/test_external_plan_service.py -v 2>&1 | head -30
```

Expected: `ImportError: cannot import name 'ExternalPlanService'` or similar — confirms red.

---

### Task 3: Implement ExternalPlanService (green)

**Files:**
- Create: `backend/app/services/external_plan_service.py`

- [ ] **Step 1: Implement the service**

```python
# backend/app/services/external_plan_service.py
"""ExternalPlanService — CRUD for manually entered external training plans.

Only used in Tracking Only mode (enforced at HTTP layer via require_tracking_mode).
"""
from __future__ import annotations

import uuid
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models.schemas import ExternalPlanModel, ExternalSessionModel


class ExternalPlanService:

    @staticmethod
    def create_plan(
        athlete_id: str,
        title: str,
        db: Session,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> ExternalPlanModel:
        """Create a new active external plan, archiving any previous active plan.

        Maintains the XOR invariant: only one active ExternalPlan per athlete.
        (The ModeGuard ensures no active TrainingPlan can coexist in tracking_only mode.)
        """
        # Archive existing active plan(s) for this athlete
        existing = (
            db.query(ExternalPlanModel)
            .filter(
                ExternalPlanModel.athlete_id == athlete_id,
                ExternalPlanModel.status == "active",
            )
            .all()
        )
        for old_plan in existing:
            old_plan.status = "archived"

        new_plan = ExternalPlanModel(
            id=str(uuid.uuid4()),
            athlete_id=athlete_id,
            title=title,
            source="manual",
            status="active",
            start_date=start_date,
            end_date=end_date,
        )
        db.add(new_plan)
        db.commit()
        db.refresh(new_plan)
        return new_plan

    @staticmethod
    def get_active_plan(
        athlete_id: str,
        db: Session,
    ) -> ExternalPlanModel | None:
        """Return the active ExternalPlan for the athlete, or None."""
        return (
            db.query(ExternalPlanModel)
            .filter(
                ExternalPlanModel.athlete_id == athlete_id,
                ExternalPlanModel.status == "active",
            )
            .first()
        )

    @staticmethod
    def add_session(
        plan_id: str,
        athlete_id: str,
        session_date: date,
        sport: str,
        title: str,
        db: Session,
        description: str | None = None,
        duration_min: int | None = None,
    ) -> ExternalSessionModel:
        """Add a session to an active external plan.

        Raises 404 if the plan is not found or doesn't belong to the athlete.
        """
        plan = db.get(ExternalPlanModel, plan_id)
        if not plan or plan.athlete_id != athlete_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="External plan not found",
            )

        session_obj = ExternalSessionModel(
            id=str(uuid.uuid4()),
            plan_id=plan_id,
            athlete_id=athlete_id,
            session_date=session_date,
            sport=sport,
            title=title,
            description=description,
            duration_min=duration_min,
            status="planned",
        )
        db.add(session_obj)
        db.commit()
        db.refresh(session_obj)
        return session_obj

    @staticmethod
    def update_session(
        session_id: str,
        athlete_id: str,
        updates: dict,
        db: Session,
    ) -> ExternalSessionModel:
        """Partially update an external session.

        Only keys present in `updates` are applied (None values are still applied).
        Raises 404 if session not found or doesn't belong to the athlete.
        """
        session_obj = db.get(ExternalSessionModel, session_id)
        if not session_obj or session_obj.athlete_id != athlete_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="External session not found",
            )

        allowed_fields = {"session_date", "sport", "title", "description", "duration_min", "status"}
        for field, value in updates.items():
            if field in allowed_fields and value is not None:
                setattr(session_obj, field, value)

        db.commit()
        db.refresh(session_obj)
        return session_obj

    @staticmethod
    def delete_session(
        session_id: str,
        athlete_id: str,
        db: Session,
    ) -> None:
        """Hard-delete an external session.

        Raises 404 if session not found or doesn't belong to the athlete.
        """
        session_obj = db.get(ExternalSessionModel, session_id)
        if not session_obj or session_obj.athlete_id != athlete_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="External session not found",
            )

        db.delete(session_obj)
        db.commit()
```

- [ ] **Step 2: Run service tests — expect green**

```bash
cd backend && C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/services/test_external_plan_service.py -v
```

Expected: all tests PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/external_plan_service.py tests/backend/services/test_external_plan_service.py
git commit -m "feat(s1): ExternalPlanService — CRUD + XOR invariant (TDD green)"
```

---

### Task 4: API routes — write failing tests first

**Files:**
- Create: `tests/backend/api/test_external_plan.py`

- [ ] **Step 1: Write the failing API tests**

```python
# tests/backend/api/test_external_plan.py
"""API integration tests for ExternalPlan endpoints.

Fixtures from conftest.py:
  - authed_client → (TestClient, athlete_id) — athlete in full mode by default
  - client → unauthenticated TestClient
"""
import pytest
from .conftest import authed_client, client, onboarding_payload  # noqa: re-export for pytest discovery


# ---------------------------------------------------------------------------
# Helper: register + login a tracking_only athlete
# ---------------------------------------------------------------------------

def _register_tracking_athlete(client):
    """Register a tracking_only athlete and return (token, athlete_id)."""
    payload = onboarding_payload(
        email="tracker@test.com",
        coaching_mode="tracking_only",
    )
    resp = client.post("/athletes/onboarding", json=payload)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return body["access_token"], body["athlete"]["id"]


# ---------------------------------------------------------------------------
# Mode guard — full mode must be rejected
# ---------------------------------------------------------------------------

def test_create_plan_rejected_for_full_mode_athlete(authed_client):
    c, athlete_id = authed_client
    resp = c.post(
        f"/athletes/{athlete_id}/external-plan",
        json={"title": "Coach Plan"},
    )
    assert resp.status_code == 403


def test_get_plan_rejected_for_full_mode_athlete(authed_client):
    c, athlete_id = authed_client
    resp = c.get(f"/athletes/{athlete_id}/external-plan")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /athletes/{id}/external-plan — create plan
# ---------------------------------------------------------------------------

def test_create_external_plan_success(client):
    token, athlete_id = _register_tracking_athlete(client)
    client.headers.update({"Authorization": f"Bearer {token}"})
    resp = client.post(
        f"/athletes/{athlete_id}/external-plan",
        json={"title": "My Coach Plan", "start_date": "2026-05-01", "end_date": "2026-07-31"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["title"] == "My Coach Plan"
    assert body["status"] == "active"
    assert body["source"] == "manual"
    assert body["start_date"] == "2026-05-01"
    assert body["sessions"] == []


def test_create_second_plan_archives_first(client):
    token, athlete_id = _register_tracking_athlete(client)
    client.headers.update({"Authorization": f"Bearer {token}"})
    client.post(
        f"/athletes/{athlete_id}/external-plan",
        json={"title": "Plan A"},
    )
    resp2 = client.post(
        f"/athletes/{athlete_id}/external-plan",
        json={"title": "Plan B"},
    )
    assert resp2.status_code == 201
    # GET should now return Plan B
    get_resp = client.get(f"/athletes/{athlete_id}/external-plan")
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "Plan B"


# ---------------------------------------------------------------------------
# GET /athletes/{id}/external-plan — get active plan
# ---------------------------------------------------------------------------

def test_get_active_plan_returns_404_when_none(client):
    token, athlete_id = _register_tracking_athlete(client)
    client.headers.update({"Authorization": f"Bearer {token}"})
    resp = client.get(f"/athletes/{athlete_id}/external-plan")
    assert resp.status_code == 404


def test_get_active_plan_returns_plan_with_sessions(client):
    token, athlete_id = _register_tracking_athlete(client)
    client.headers.update({"Authorization": f"Bearer {token}"})
    # Create plan
    client.post(f"/athletes/{athlete_id}/external-plan", json={"title": "Plan"})
    # Add session
    client.post(
        f"/athletes/{athlete_id}/external-plan/sessions",
        json={"session_date": "2026-05-05", "sport": "running", "title": "Easy 5k"},
    )
    resp = client.get(f"/athletes/{athlete_id}/external-plan")
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Plan"
    assert len(body["sessions"]) == 1
    assert body["sessions"][0]["title"] == "Easy 5k"


# ---------------------------------------------------------------------------
# POST /athletes/{id}/external-plan/sessions — add session
# ---------------------------------------------------------------------------

def test_add_session_requires_tracking_mode(authed_client):
    c, athlete_id = authed_client
    resp = c.post(
        f"/athletes/{athlete_id}/external-plan/sessions",
        json={"session_date": "2026-05-05", "sport": "running", "title": "Run"},
    )
    assert resp.status_code == 403


def test_add_session_without_active_plan_returns_404(client):
    token, athlete_id = _register_tracking_athlete(client)
    client.headers.update({"Authorization": f"Bearer {token}"})
    resp = client.post(
        f"/athletes/{athlete_id}/external-plan/sessions",
        json={"session_date": "2026-05-05", "sport": "running", "title": "Run"},
    )
    assert resp.status_code == 404


def test_add_session_success(client):
    token, athlete_id = _register_tracking_athlete(client)
    client.headers.update({"Authorization": f"Bearer {token}"})
    client.post(f"/athletes/{athlete_id}/external-plan", json={"title": "Plan"})
    resp = client.post(
        f"/athletes/{athlete_id}/external-plan/sessions",
        json={
            "session_date": "2026-05-05",
            "sport": "running",
            "title": "Easy 5k",
            "description": "Recovery run",
            "duration_min": 30,
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["sport"] == "running"
    assert body["title"] == "Easy 5k"
    assert body["duration_min"] == 30
    assert body["status"] == "planned"


# ---------------------------------------------------------------------------
# PATCH /athletes/{id}/external-plan/sessions/{session_id} — update session
# ---------------------------------------------------------------------------

def test_update_session_partial(client):
    token, athlete_id = _register_tracking_athlete(client)
    client.headers.update({"Authorization": f"Bearer {token}"})
    client.post(f"/athletes/{athlete_id}/external-plan", json={"title": "Plan"})
    add_resp = client.post(
        f"/athletes/{athlete_id}/external-plan/sessions",
        json={"session_date": "2026-05-05", "sport": "running", "title": "Run"},
    )
    session_id = add_resp.json()["id"]
    resp = client.patch(
        f"/athletes/{athlete_id}/external-plan/sessions/{session_id}",
        json={"title": "Long Run", "duration_min": 90, "status": "completed"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["title"] == "Long Run"
    assert body["duration_min"] == 90
    assert body["status"] == "completed"
    assert body["sport"] == "running"  # unchanged


def test_update_session_wrong_owner_returns_404(client):
    token1, a1 = _register_tracking_athlete(client)
    # Register second tracking athlete
    from .conftest import onboarding_payload
    p2 = onboarding_payload(email="tracker2@test.com", coaching_mode="tracking_only")
    r2 = client.post("/athletes/onboarding", json=p2)
    token2 = r2.json()["access_token"]

    client.headers.update({"Authorization": f"Bearer {token1}"})
    client.post(f"/athletes/{a1}/external-plan", json={"title": "Plan"})
    sess_resp = client.post(
        f"/athletes/{a1}/external-plan/sessions",
        json={"session_date": "2026-05-05", "sport": "running", "title": "Run"},
    )
    session_id = sess_resp.json()["id"]

    # Athlete 2 tries to update athlete 1's session
    a2 = r2.json()["athlete"]["id"]
    client.headers.update({"Authorization": f"Bearer {token2}"})
    resp = client.patch(
        f"/athletes/{a2}/external-plan/sessions/{session_id}",
        json={"title": "Hacked"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /athletes/{id}/external-plan/sessions/{session_id} — delete session
# ---------------------------------------------------------------------------

def test_delete_session_success(client):
    token, athlete_id = _register_tracking_athlete(client)
    client.headers.update({"Authorization": f"Bearer {token}"})
    client.post(f"/athletes/{athlete_id}/external-plan", json={"title": "Plan"})
    sess_resp = client.post(
        f"/athletes/{athlete_id}/external-plan/sessions",
        json={"session_date": "2026-05-05", "sport": "running", "title": "Run"},
    )
    session_id = sess_resp.json()["id"]
    resp = client.delete(
        f"/athletes/{athlete_id}/external-plan/sessions/{session_id}"
    )
    assert resp.status_code == 204
    # Verify it's gone — GET plan should show 0 sessions
    get_resp = client.get(f"/athletes/{athlete_id}/external-plan")
    assert get_resp.json()["sessions"] == []


def test_delete_session_not_found_returns_404(client):
    token, athlete_id = _register_tracking_athlete(client)
    client.headers.update({"Authorization": f"Bearer {token}"})
    client.post(f"/athletes/{athlete_id}/external-plan", json={"title": "Plan"})
    resp = client.delete(
        f"/athletes/{athlete_id}/external-plan/sessions/ghost-session-id"
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Unauthenticated requests
# ---------------------------------------------------------------------------

def test_unauthenticated_requests_rejected(client):
    resp = client.get("/athletes/some-id/external-plan")
    assert resp.status_code == 401
```

- [ ] **Step 2: Run API tests — expect FAIL (red) because router not registered yet**

```bash
cd backend && C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/api/test_external_plan.py -v 2>&1 | head -40
```

Expected: 404 on all route calls (router not yet registered).

---

### Task 5: Implement external_plan routes (green)

**Files:**
- Create: `backend/app/routes/external_plan.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create the router**

```python
# backend/app/routes/external_plan.py
"""ExternalPlan routes — Tracking Only mode only.

All endpoints require require_tracking_mode (403 if athlete is in 'full' mode).

Endpoints:
  POST   /athletes/{id}/external-plan                          → create plan
  GET    /athletes/{id}/external-plan                          → get active plan
  POST   /athletes/{id}/external-plan/sessions                 → add session
  PATCH  /athletes/{id}/external-plan/sessions/{session_id}    → update session
  DELETE /athletes/{id}/external-plan/sessions/{session_id}    → delete session
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db.models import AthleteModel
from ..dependencies import get_db
from ..dependencies.mode_guard import require_tracking_mode
from ..schemas.external_plan import (
    ExternalPlanCreate,
    ExternalPlanOut,
    ExternalSessionCreate,
    ExternalSessionOut,
    ExternalSessionUpdate,
)
from ..services.external_plan_service import ExternalPlanService

router = APIRouter(prefix="/athletes", tags=["external-plan"])

DB = Annotated[Session, Depends(get_db)]
TrackingAthlete = Annotated[AthleteModel, Depends(require_tracking_mode)]


@router.post(
    "/{athlete_id}/external-plan",
    response_model=ExternalPlanOut,
    status_code=status.HTTP_201_CREATED,
)
def create_external_plan(
    athlete_id: str,
    body: ExternalPlanCreate,
    athlete: TrackingAthlete,
    db: DB,
) -> ExternalPlanOut:
    """Create a new external plan (archives any previous active plan)."""
    plan = ExternalPlanService.create_plan(
        athlete_id=athlete_id,
        title=body.title,
        start_date=body.start_date,
        end_date=body.end_date,
        db=db,
    )
    # Eagerly load sessions (empty on creation)
    db.refresh(plan)
    return ExternalPlanOut.model_validate(plan)


@router.get(
    "/{athlete_id}/external-plan",
    response_model=ExternalPlanOut,
)
def get_active_external_plan(
    athlete_id: str,
    athlete: TrackingAthlete,
    db: DB,
) -> ExternalPlanOut:
    """Get the athlete's active external plan with all sessions."""
    plan = ExternalPlanService.get_active_plan(athlete_id=athlete_id, db=db)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active external plan found",
        )
    return ExternalPlanOut.model_validate(plan)


@router.post(
    "/{athlete_id}/external-plan/sessions",
    response_model=ExternalSessionOut,
    status_code=status.HTTP_201_CREATED,
)
def add_external_session(
    athlete_id: str,
    body: ExternalSessionCreate,
    athlete: TrackingAthlete,
    db: DB,
) -> ExternalSessionOut:
    """Add a session to the athlete's active external plan."""
    plan = ExternalPlanService.get_active_plan(athlete_id=athlete_id, db=db)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active external plan. Create a plan first.",
        )
    session_obj = ExternalPlanService.add_session(
        plan_id=plan.id,
        athlete_id=athlete_id,
        session_date=body.session_date,
        sport=body.sport,
        title=body.title,
        description=body.description,
        duration_min=body.duration_min,
        db=db,
    )
    return ExternalSessionOut.model_validate(session_obj)


@router.patch(
    "/{athlete_id}/external-plan/sessions/{session_id}",
    response_model=ExternalSessionOut,
)
def update_external_session(
    athlete_id: str,
    session_id: str,
    body: ExternalSessionUpdate,
    athlete: TrackingAthlete,
    db: DB,
) -> ExternalSessionOut:
    """Partially update an external session."""
    updates = body.model_dump(exclude_none=True)
    session_obj = ExternalPlanService.update_session(
        session_id=session_id,
        athlete_id=athlete_id,
        updates=updates,
        db=db,
    )
    return ExternalSessionOut.model_validate(session_obj)


@router.delete(
    "/{athlete_id}/external-plan/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_external_session(
    athlete_id: str,
    session_id: str,
    athlete: TrackingAthlete,
    db: DB,
) -> None:
    """Hard-delete an external session."""
    ExternalPlanService.delete_session(
        session_id=session_id,
        athlete_id=athlete_id,
        db=db,
    )
```

- [ ] **Step 2: Register router in main.py**

Add after `from .routes.checkin import router as checkin_router`:
```python
from .routes.external_plan import router as external_plan_router
```

Add after `app.include_router(checkin_router)`:
```python
app.include_router(external_plan_router)
```

- [ ] **Step 3: Run API tests — expect green**

```bash
cd backend && C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/api/test_external_plan.py -v
```

Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/app/routes/external_plan.py backend/app/main.py tests/backend/api/test_external_plan.py
git commit -m "feat(s1): ExternalPlan routes + API tests (TDD green)"
```

---

### Task 6: Full test suite — invariant ≥ 1243

- [ ] **Step 1: Run full suite**

```bash
cd backend && C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -v --tb=short 2>&1 | tail -20
```

Expected: `passed` count ≥ 1243, 0 failures.

- [ ] **Step 2: If failures, investigate and fix before proceeding**

- [ ] **Step 3: Commit design doc + plan**

```bash
git add docs/superpowers/specs/2026-04-12-s1-external-plan-design.md docs/superpowers/plans/2026-04-12-s1-external-plan-crud.md
git commit -m "docs(s1): design spec + implementation plan"
```

---

### Task 7: Write SESSION_REPORT.md and push

- [ ] **Step 1: Update SESSION_REPORT.md with S-1 completion**

Append S-1 completed section to SESSION_REPORT.md.

- [ ] **Step 2: Final commit**

```bash
git add SESSION_REPORT.md SESSION_PLAN.md
git commit -m "docs(s1): session report — ExternalPlan CRUD complete"
```

- [ ] **Step 3: Push branch**

```bash
git push -u origin session/s1-external-plan
```
