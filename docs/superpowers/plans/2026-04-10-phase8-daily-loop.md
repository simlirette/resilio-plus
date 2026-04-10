# Phase 8 — Daily Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let athletes see session details and log actual vs planned effort, closing the feedback loop for adaptive coaching.

**Architecture:** Add `id: str` to `WorkoutSlot` for stable session references. New `SessionLogModel` table stores actual effort (duration, RPE, notes, sport-specific data). Four backend endpoints + three frontend pages. `_state` shared dict in E2E tests carries session_id across test_07.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy, SQLite, pytest. Next.js App Router, TypeScript, shadcn/ui. pytest venv: `C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\python.exe`

---

## File Map

| File | Action | Role |
|------|--------|------|
| `backend/app/schemas/plan.py` | Modify | Add `id: str` to `WorkoutSlot` |
| `backend/app/schemas/session_log.py` | Create | `SessionLogRequest`, `SessionLogResponse`, `SessionDetailResponse`, `WeekSummary`, `HistoryResponse` |
| `backend/app/db/models.py` | Modify | Add `SessionLogModel` table |
| `backend/app/routes/sessions.py` | Create | 4 endpoints: GET session, POST log, GET log, GET history |
| `backend/app/main.py` | Modify | Include sessions router |
| `frontend/src/lib/api.ts` | Modify | Add types + `getSession`, `logSession`, `getSessionLog`, `getHistory` |
| `frontend/src/app/plan/page.tsx` | Modify | Session cards → links, `✓ Logged` badge |
| `frontend/src/app/session/[id]/page.tsx` | Create | Session detail page |
| `frontend/src/app/session/[id]/log/page.tsx` | Create | Log form page |
| `frontend/src/app/history/page.tsx` | Create | History list page |
| `tests/backend/api/test_sessions.py` | Create | Route tests for all 4 endpoints |
| `tests/e2e/test_full_workflow.py` | Modify | Add test_07: log session + history |

---

## Task 1: Add `id` to `WorkoutSlot`

**Files:**
- Modify: `backend/app/schemas/plan.py`
- Test: `tests/backend/schemas/test_workout_slot_id.py`

- [ ] **Step 1: Write the failing test**

Create `tests/backend/schemas/test_workout_slot_id.py`:

```python
import json
from app.schemas.plan import WorkoutSlot
from app.schemas.fatigue import FatigueScore
from datetime import date


def _slot(**overrides):
    base = dict(
        date=date(2026, 4, 7),
        sport="running",
        workout_type="easy_z1",
        duration_min=45,
        fatigue_score=FatigueScore(
            local_muscular=20.0, cns_load=10.0, metabolic_cost=30.0,
            recovery_hours=12.0, affected_muscles=[],
        ),
    )
    return WorkoutSlot(**{**base, **overrides})


def test_workout_slot_has_id_by_default():
    slot = _slot()
    assert slot.id is not None
    assert isinstance(slot.id, str)
    assert len(slot.id) == 36  # UUID format


def test_two_slots_have_different_ids():
    a = _slot()
    b = _slot()
    assert a.id != b.id


def test_slot_id_roundtrips_through_json():
    slot = _slot()
    dumped = slot.model_dump(mode="json")
    restored = WorkoutSlot.model_validate(dumped)
    assert restored.id == slot.id


def test_slot_without_id_in_json_gets_new_id():
    """Backward compat: old JSON without 'id' field still deserializes."""
    raw = {
        "date": "2026-04-07",
        "sport": "running",
        "workout_type": "easy_z1",
        "duration_min": 45,
        "fatigue_score": {
            "local_muscular": 20.0, "cns_load": 10.0, "metabolic_cost": 30.0,
            "recovery_hours": 12.0, "affected_muscles": [],
        },
    }
    slot = WorkoutSlot.model_validate(raw)
    assert slot.id is not None  # gets a new UUID
```

- [ ] **Step 2: Run to verify failure**

```bash
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" tests/backend/schemas/test_workout_slot_id.py -v
```

Expected: `ValidationError` or attribute error — `id` doesn't exist yet.

- [ ] **Step 3: Add `id` to `WorkoutSlot`**

In `backend/app/schemas/plan.py`, replace the `WorkoutSlot` class:

```python
import json
from datetime import date
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .athlete import Sport
from .fatigue import FatigueScore


class WorkoutSlot(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    date: date
    sport: Sport
    workout_type: str
    duration_min: int = Field(..., gt=0)
    fatigue_score: FatigueScore
    notes: str = ""
```

Leave `TrainingPlan`, `TrainingPlanResponse`, and `from_model` unchanged.

- [ ] **Step 4: Run tests to verify they pass**

```bash
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" tests/backend/schemas/test_workout_slot_id.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Run existing tests to confirm no regression**

```bash
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" tests/backend/api/test_plans.py tests/e2e/ -v --tb=short
```

Expected: all previously passing tests still pass. The `id` field has a default — existing `WorkoutSlot` construction without it still works.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/plan.py tests/backend/schemas/test_workout_slot_id.py
git commit -m "feat: add stable id field to WorkoutSlot (backward-compatible)"
```

---

## Task 2: `SessionLogModel` + DB migration

**Files:**
- Modify: `backend/app/db/models.py`

- [ ] **Step 1: Add `SessionLogModel` to `backend/app/db/models.py`**

Add after the `ConnectorCredentialModel` class (before the final newline):

```python
class SessionLogModel(Base):
    __tablename__ = "session_logs"

    id = Column(String, primary_key=True)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=False)
    plan_id = Column(String, ForeignKey("training_plans.id"), nullable=False)
    session_id = Column(String, nullable=False, index=True)  # WorkoutSlot.id
    actual_duration_min = Column(Integer, nullable=True)
    skipped = Column(Boolean, nullable=False, default=False)
    rpe = Column(Integer, nullable=True)                    # 1–10
    notes = Column(Text, nullable=False, default="")
    actual_data_json = Column(Text, nullable=False, default="{}")
    logged_at = Column(DateTime(timezone=True), nullable=False,
                       default=lambda: datetime.now(timezone.utc))
    # Relationships
    athlete = relationship("AthleteModel", backref="session_logs")
    plan = relationship("TrainingPlanModel", backref="session_logs")

    __table_args__ = (UniqueConstraint("athlete_id", "session_id"),)
```

Also add `SessionLogModel` to `AthleteModel`'s cascade by adding this line inside `AthleteModel` after the existing `credentials` relationship:

```python
# In AthleteModel:
session_logs = relationship("SessionLogModel", backref="athlete_ref",
                            cascade="all, delete-orphan",
                            overlaps="athlete")
```

Wait — the `backref="athlete"` in `SessionLogModel` conflicts with AthleteModel's explicit `athlete` relationship. Use `foreign_keys` approach instead. The cleanest solution: do NOT add a `relationship` on `AthleteModel` for session_logs in this phase. The `backref` on `SessionLogModel` is enough to query.

**Revised `SessionLogModel`** (no backref conflicts):

```python
class SessionLogModel(Base):
    __tablename__ = "session_logs"

    id = Column(String, primary_key=True)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=False)
    plan_id = Column(String, ForeignKey("training_plans.id"), nullable=False)
    session_id = Column(String, nullable=False, index=True)
    actual_duration_min = Column(Integer, nullable=True)
    skipped = Column(Boolean, nullable=False, default=False)
    rpe = Column(Integer, nullable=True)
    notes = Column(Text, nullable=False, default="")
    actual_data_json = Column(Text, nullable=False, default="{}")
    logged_at = Column(DateTime(timezone=True), nullable=False,
                       default=lambda: datetime.now(timezone.utc))

    __table_args__ = (UniqueConstraint("athlete_id", "session_id"),)
```

- [ ] **Step 2: Verify the table is created in test DB**

```bash
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" tests/backend/api/test_plans.py -v --tb=short
```

Expected: all pass (the in-memory DB auto-creates all tables from `Base.metadata.create_all`).

- [ ] **Step 3: Commit**

```bash
git add backend/app/db/models.py
git commit -m "feat: add SessionLogModel table (athlete × session upsert)"
```

---

## Task 3: Session log Pydantic schemas

**Files:**
- Create: `backend/app/schemas/session_log.py`

- [ ] **Step 1: Create `backend/app/schemas/session_log.py`**

```python
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from .fatigue import FatigueScore
from .athlete import Sport


class SessionLogRequest(BaseModel):
    actual_duration_min: int | None = Field(default=None, ge=1)
    skipped: bool = False
    rpe: int | None = Field(default=None, ge=1, le=10)
    notes: str = ""
    actual_data: dict[str, Any] = Field(default_factory=dict)


class SessionLogResponse(BaseModel):
    id: str
    session_id: str
    actual_duration_min: int | None
    skipped: bool
    rpe: int | None
    notes: str
    actual_data: dict[str, Any]
    logged_at: datetime


class SessionDetailResponse(BaseModel):
    session_id: str
    plan_id: str
    date: date
    sport: Sport
    workout_type: str
    duration_min: int
    fatigue_score: FatigueScore
    notes: str
    log: SessionLogResponse | None = None


class WeekSummary(BaseModel):
    plan_id: str
    week_number: int
    start_date: date
    end_date: date
    phase: str
    planned_hours: float
    sessions_total: int
    sessions_logged: int
    completion_pct: float
```

- [ ] **Step 2: Verify import works**

```bash
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" --collect-only tests/backend/api/test_plans.py 2>&1 | tail -5
```

Expected: no import errors, tests collected normally.

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/session_log.py
git commit -m "feat: add SessionLog pydantic schemas"
```

---

## Task 4: `sessions.py` route — GET session + POST/GET log + GET history

**Files:**
- Create: `backend/app/routes/sessions.py`
- Create: `tests/backend/api/test_sessions.py`

- [ ] **Step 1: Write failing tests**

Create `tests/backend/api/test_sessions.py`:

```python
"""Tests for session detail, logging, and history endpoints."""
import json
from datetime import date

PLAN_BODY = {"start_date": "2026-03-30", "end_date": "2026-04-05"}


def _get_first_session_id(authed_client):
    """Helper: generate a plan and return its first session's id."""
    c, athlete_id = authed_client
    resp = c.post(f"/athletes/{athlete_id}/plan", json=PLAN_BODY)
    assert resp.status_code == 201
    sessions = resp.json()["sessions"]
    assert len(sessions) > 0
    return sessions[0]["id"], athlete_id


def test_session_detail_returns_200(authed_client):
    c, athlete_id = authed_client
    session_id, _ = _get_first_session_id((c, athlete_id))
    resp = c.get(f"/athletes/{athlete_id}/sessions/{session_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == session_id
    assert "sport" in body
    assert "duration_min" in body
    assert body["log"] is None  # not yet logged


def test_session_detail_wrong_athlete_returns_403(authed_client):
    c, _ = authed_client
    resp = c.get("/athletes/other-id/sessions/any-id")
    assert resp.status_code == 403


def test_session_detail_unknown_session_returns_404(authed_client):
    c, athlete_id = authed_client
    c.post(f"/athletes/{athlete_id}/plan", json=PLAN_BODY)
    resp = c.get(f"/athletes/{athlete_id}/sessions/nonexistent-session-id")
    assert resp.status_code == 404


def test_post_log_creates_log(authed_client):
    c, athlete_id = authed_client
    session_id, _ = _get_first_session_id((c, athlete_id))
    resp = c.post(
        f"/athletes/{athlete_id}/sessions/{session_id}/log",
        json={"actual_duration_min": 40, "rpe": 7, "notes": "Felt good"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["session_id"] == session_id
    assert body["actual_duration_min"] == 40
    assert body["rpe"] == 7
    assert body["skipped"] is False


def test_post_log_upserts(authed_client):
    """Posting twice updates instead of creating a duplicate."""
    c, athlete_id = authed_client
    session_id, _ = _get_first_session_id((c, athlete_id))
    c.post(f"/athletes/{athlete_id}/sessions/{session_id}/log",
           json={"actual_duration_min": 40, "rpe": 7})
    resp2 = c.post(f"/athletes/{athlete_id}/sessions/{session_id}/log",
                   json={"actual_duration_min": 35, "rpe": 8, "notes": "Updated"})
    assert resp2.status_code == 201
    assert resp2.json()["actual_duration_min"] == 35
    assert resp2.json()["notes"] == "Updated"


def test_post_log_skipped(authed_client):
    c, athlete_id = authed_client
    session_id, _ = _get_first_session_id((c, athlete_id))
    resp = c.post(
        f"/athletes/{athlete_id}/sessions/{session_id}/log",
        json={"skipped": True},
    )
    assert resp.status_code == 201
    assert resp.json()["skipped"] is True


def test_get_log_returns_log(authed_client):
    c, athlete_id = authed_client
    session_id, _ = _get_first_session_id((c, athlete_id))
    c.post(f"/athletes/{athlete_id}/sessions/{session_id}/log",
           json={"actual_duration_min": 40})
    resp = c.get(f"/athletes/{athlete_id}/sessions/{session_id}/log")
    assert resp.status_code == 200
    assert resp.json()["actual_duration_min"] == 40


def test_get_log_not_found_returns_404(authed_client):
    c, athlete_id = authed_client
    c.post(f"/athletes/{athlete_id}/plan", json=PLAN_BODY)
    resp = c.get(f"/athletes/{athlete_id}/sessions/no-log-yet/log")
    assert resp.status_code == 404


def test_session_detail_includes_log_after_logging(authed_client):
    c, athlete_id = authed_client
    session_id, _ = _get_first_session_id((c, athlete_id))
    c.post(f"/athletes/{athlete_id}/sessions/{session_id}/log",
           json={"actual_duration_min": 42, "rpe": 6})
    resp = c.get(f"/athletes/{athlete_id}/sessions/{session_id}")
    assert resp.status_code == 200
    assert resp.json()["log"] is not None
    assert resp.json()["log"]["actual_duration_min"] == 42


def test_history_returns_list(authed_client):
    c, athlete_id = authed_client
    resp = c.get(f"/athletes/{athlete_id}/history")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == 1  # onboarding creates 1 plan
    assert body[0]["sessions_total"] > 0


def test_history_shows_logged_count(authed_client):
    c, athlete_id = authed_client
    session_id, _ = _get_first_session_id((c, athlete_id))
    c.post(f"/athletes/{athlete_id}/sessions/{session_id}/log",
           json={"actual_duration_min": 30})
    resp = c.get(f"/athletes/{athlete_id}/history")
    assert resp.status_code == 200
    # The most recent plan should show 1 logged (out of N total)
    most_recent = max(resp.json(), key=lambda w: w["start_date"])
    assert most_recent["sessions_logged"] >= 1
```

- [ ] **Step 2: Run to verify failure**

```bash
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" tests/backend/api/test_sessions.py -v 2>&1 | tail -10
```

Expected: `ImportError` or 404 for all session routes — routes don't exist yet.

- [ ] **Step 3: Implement `backend/app/routes/sessions.py`**

```python
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..db.models import AthleteModel, SessionLogModel, TrainingPlanModel
from ..dependencies import get_db, get_current_athlete_id
from ..schemas.plan import WorkoutSlot
from ..schemas.session_log import (
    SessionDetailResponse,
    SessionLogRequest,
    SessionLogResponse,
    WeekSummary,
)

router = APIRouter(prefix="/athletes", tags=["sessions"])

DB = Annotated[Session, Depends(get_db)]


def _require_own(
    athlete_id: str,
    current_id: Annotated[str, Depends(get_current_athlete_id)],
) -> str:
    if current_id != athlete_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return athlete_id


def _get_latest_plan(athlete_id: str, db: Session) -> TrainingPlanModel:
    plan = (
        db.query(TrainingPlanModel)
        .filter(TrainingPlanModel.athlete_id == athlete_id)
        .order_by(desc(TrainingPlanModel.created_at))
        .first()
    )
    if plan is None:
        raise HTTPException(status_code=404, detail="No plan found")
    return plan


def _find_session(plan: TrainingPlanModel, session_id: str) -> WorkoutSlot | None:
    slots = [WorkoutSlot.model_validate(s) for s in json.loads(plan.weekly_slots_json)]
    for slot in slots:
        if slot.id == session_id:
            return slot
    return None


def _log_to_response(log: SessionLogModel) -> SessionLogResponse:
    return SessionLogResponse(
        id=log.id,
        session_id=log.session_id,
        actual_duration_min=log.actual_duration_min,
        skipped=log.skipped,
        rpe=log.rpe,
        notes=log.notes,
        actual_data=json.loads(log.actual_data_json),
        logged_at=log.logged_at,
    )


@router.get("/{athlete_id}/sessions/{session_id}", response_model=SessionDetailResponse)
def get_session_detail(
    athlete_id: str,
    session_id: str,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> SessionDetailResponse:
    plan = _get_latest_plan(athlete_id, db)
    slot = _find_session(plan, session_id)
    if slot is None:
        raise HTTPException(status_code=404, detail="Session not found in current plan")

    log_model = (
        db.query(SessionLogModel)
        .filter(
            SessionLogModel.athlete_id == athlete_id,
            SessionLogModel.session_id == session_id,
        )
        .first()
    )

    return SessionDetailResponse(
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


@router.post(
    "/{athlete_id}/sessions/{session_id}/log",
    response_model=SessionLogResponse,
    status_code=201,
)
def log_session(
    athlete_id: str,
    session_id: str,
    req: SessionLogRequest,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> SessionLogResponse:
    # Verify session exists in latest plan
    plan = _get_latest_plan(athlete_id, db)
    slot = _find_session(plan, session_id)
    if slot is None:
        raise HTTPException(status_code=404, detail="Session not found in current plan")

    # Upsert
    existing = (
        db.query(SessionLogModel)
        .filter(
            SessionLogModel.athlete_id == athlete_id,
            SessionLogModel.session_id == session_id,
        )
        .first()
    )

    if existing:
        existing.actual_duration_min = req.actual_duration_min
        existing.skipped = req.skipped
        existing.rpe = req.rpe
        existing.notes = req.notes
        existing.actual_data_json = json.dumps(req.actual_data)
        existing.logged_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        return _log_to_response(existing)

    log = SessionLogModel(
        id=str(uuid.uuid4()),
        athlete_id=athlete_id,
        plan_id=plan.id,
        session_id=session_id,
        actual_duration_min=req.actual_duration_min,
        skipped=req.skipped,
        rpe=req.rpe,
        notes=req.notes,
        actual_data_json=json.dumps(req.actual_data),
        logged_at=datetime.now(timezone.utc),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return _log_to_response(log)


@router.get("/{athlete_id}/sessions/{session_id}/log", response_model=SessionLogResponse)
def get_session_log(
    athlete_id: str,
    session_id: str,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> SessionLogResponse:
    log = (
        db.query(SessionLogModel)
        .filter(
            SessionLogModel.athlete_id == athlete_id,
            SessionLogModel.session_id == session_id,
        )
        .first()
    )
    if log is None:
        raise HTTPException(status_code=404, detail="No log found for this session")
    return _log_to_response(log)


@router.get("/{athlete_id}/history", response_model=list[WeekSummary])
def get_history(
    athlete_id: str,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> list[WeekSummary]:
    plans = (
        db.query(TrainingPlanModel)
        .filter(TrainingPlanModel.athlete_id == athlete_id)
        .order_by(desc(TrainingPlanModel.created_at))
        .all()
    )

    summaries: list[WeekSummary] = []
    for i, plan in enumerate(plans):
        slots = json.loads(plan.weekly_slots_json)
        sessions_total = len(slots)
        sessions_logged = (
            db.query(SessionLogModel)
            .filter(
                SessionLogModel.athlete_id == athlete_id,
                SessionLogModel.plan_id == plan.id,
            )
            .count()
        )
        completion_pct = (
            round(sessions_logged / sessions_total * 100, 1)
            if sessions_total > 0
            else 0.0
        )
        week_number = len(plans) - i  # oldest = 1
        summaries.append(
            WeekSummary(
                plan_id=plan.id,
                week_number=week_number,
                start_date=plan.start_date,
                end_date=plan.end_date,
                phase=plan.phase,
                planned_hours=round(plan.total_weekly_hours, 2),
                sessions_total=sessions_total,
                sessions_logged=sessions_logged,
                completion_pct=completion_pct,
            )
        )
    return summaries
```

- [ ] **Step 4: Wire sessions router in `backend/app/main.py`**

Add imports and `include_router` call:

```python
from .routes.sessions import router as sessions_router
```

After the existing `app.include_router(recovery_router)` line, add:

```python
app.include_router(sessions_router)
```

- [ ] **Step 5: Run session tests**

```bash
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" tests/backend/api/test_sessions.py -v --tb=short
```

Expected: all 12 tests pass.

- [ ] **Step 6: Run full suite to confirm no regression**

```bash
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" tests/ -q --tb=short 2>&1 | tail -5
```

Expected: ≥ 1243 passed (1227 + ~16 new).

- [ ] **Step 7: Commit**

```bash
git add backend/app/routes/sessions.py backend/app/main.py tests/backend/api/test_sessions.py
git commit -m "feat: add session detail, logging, and history endpoints"
```

---

## Task 5: E2E test_07 — log session + history

**Files:**
- Modify: `tests/e2e/test_full_workflow.py`

- [ ] **Step 1: Add test_07 to `tests/e2e/test_full_workflow.py`**

After `test_06_login_with_onboarding_credentials`, add:

```python
def test_07_log_session_and_history(e2e_client):
    """GET session → POST log → GET history shows 1 logged session."""
    headers = {"Authorization": f"Bearer {_state['token']}"}
    athlete_id = _state["athlete_id"]

    # Get the plan to find a session id
    plan_resp = e2e_client.get(f"/athletes/{athlete_id}/plan", headers=headers)
    assert plan_resp.status_code == 200
    sessions = plan_resp.json()["sessions"]
    assert len(sessions) > 0
    session_id = sessions[0]["id"]
    assert session_id  # must be a non-empty string

    # GET session detail — not yet logged
    detail_resp = e2e_client.get(
        f"/athletes/{athlete_id}/sessions/{session_id}", headers=headers
    )
    assert detail_resp.status_code == 200
    assert detail_resp.json()["log"] is None

    # POST log
    log_resp = e2e_client.post(
        f"/athletes/{athlete_id}/sessions/{session_id}/log",
        json={"actual_duration_min": 38, "rpe": 6, "notes": "Good session"},
        headers=headers,
    )
    assert log_resp.status_code == 201
    assert log_resp.json()["actual_duration_min"] == 38

    # GET session detail — now logged
    detail_resp2 = e2e_client.get(
        f"/athletes/{athlete_id}/sessions/{session_id}", headers=headers
    )
    assert detail_resp2.json()["log"] is not None

    # GET history
    history_resp = e2e_client.get(f"/athletes/{athlete_id}/history", headers=headers)
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert len(history) >= 1
    assert history[0]["sessions_logged"] >= 1
```

- [ ] **Step 2: Run E2E tests**

```bash
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" tests/e2e/ -v
```

Expected: 7 passed (test_01 through test_07).

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/test_full_workflow.py
git commit -m "test: add E2E test_07 — log session + history"
```

---

## Task 6: Frontend — update `api.ts`

**Files:**
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Add types and API methods to `frontend/src/lib/api.ts`**

Add the new types after the existing `WeeklyReviewResponse` interface:

```typescript
export interface WorkoutSlot {
  id: string           // NEW — stable session id
  date: string
  sport: Sport
  workout_type: string
  duration_min: number
  fatigue_score: FatigueScore
  notes: string
}

export interface SessionLogResponse {
  id: string
  session_id: string
  actual_duration_min: number | null
  skipped: boolean
  rpe: number | null
  notes: string
  actual_data: Record<string, unknown>
  logged_at: string
}

export interface SessionDetailResponse {
  session_id: string
  plan_id: string
  date: string
  sport: Sport
  workout_type: string
  duration_min: number
  fatigue_score: FatigueScore
  notes: string
  log: SessionLogResponse | null
}

export interface SessionLogRequest {
  actual_duration_min?: number
  skipped?: boolean
  rpe?: number
  notes?: string
  actual_data?: Record<string, unknown>
}

export interface WeekSummary {
  plan_id: string
  week_number: number
  start_date: string
  end_date: string
  phase: string
  planned_hours: number
  sessions_total: number
  sessions_logged: number
  completion_pct: number
}
```

**Important:** The existing `WorkoutSlot` interface (without `id`) must be replaced by the new one above. Find and replace the existing `WorkoutSlot` interface definition.

Add new API methods to the `api` object (after `submitReview`):

```typescript
  getSession: (athleteId: string, sessionId: string) =>
    request<SessionDetailResponse>(`/athletes/${athleteId}/sessions/${sessionId}`),

  logSession: (athleteId: string, sessionId: string, data: SessionLogRequest) =>
    request<SessionLogResponse>(`/athletes/${athleteId}/sessions/${sessionId}/log`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getSessionLog: (athleteId: string, sessionId: string) =>
    request<SessionLogResponse>(`/athletes/${athleteId}/sessions/${sessionId}/log`),

  getHistory: (athleteId: string) =>
    request<WeekSummary[]>(`/athletes/${athleteId}/history`),
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /c/Users/simon/resilio-plus/frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors. If `WorkoutSlot` was used elsewhere with the old definition (without `id`), TypeScript will still compile since `id` has a default on the backend — all existing API calls return objects that include `id`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/api.ts
git commit -m "feat: add session detail, log, and history types to api.ts"
```

---

## Task 7: Frontend — update `plan/page.tsx`

**Files:**
- Modify: `frontend/src/app/plan/page.tsx`

- [ ] **Step 1: Update session cards to be links with log badge**

Replace the entire `plan/page.tsx` content with:

```tsx
'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import { api, ApiError, type TrainingPlanResponse, type WorkoutSlot } from '@/lib/api'
import { ProtectedRoute } from '@/components/protected-route'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

const SPORT_COLORS: Record<string, string> = {
  running: 'bg-emerald-500/20 text-emerald-400',
  lifting: 'bg-purple-500/20 text-purple-400',
  swimming: 'bg-blue-500/20 text-blue-400',
  biking: 'bg-orange-500/20 text-orange-400',
}

function formatDate(iso: string): string {
  return new Date(iso + 'T12:00:00').toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })
}

function groupByDate(sessions: WorkoutSlot[]): [string, WorkoutSlot[]][] {
  const map = new Map<string, WorkoutSlot[]>()
  for (const s of sessions) {
    const arr = map.get(s.date) ?? []
    arr.push(s)
    map.set(s.date, arr)
  }
  return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b))
}

export default function PlanPage() {
  const { athleteId, logout } = useAuth()
  const router = useRouter()
  const [plan, setPlan] = useState<TrainingPlanResponse | null>(null)
  const [notFound, setNotFound] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!athleteId) return
    api.getPlan(athleteId)
      .then(setPlan)
      .catch(err => {
        if (err instanceof ApiError && err.status === 401) { logout(); router.replace('/login') }
        else if (err instanceof ApiError && err.status === 404) setNotFound(true)
        else setError('Failed to load plan.')
      })
  }, [athleteId, logout])

  return (
    <ProtectedRoute>
      {notFound && (
        <div className="flex flex-col items-center gap-4 py-20 text-center">
          <p className="text-muted-foreground">No plan active. Generate one first.</p>
          <Button asChild><Link href="/dashboard">Go to dashboard</Link></Button>
        </div>
      )}
      {error && <p className="text-destructive">{error}</p>}
      {!plan && !notFound && !error && <p className="animate-pulse text-muted-foreground">Loading…</p>}
      {plan && (
        <div className="space-y-6">
          <div>
            <p className="text-sm uppercase tracking-widest text-muted-foreground">
              {plan.phase.toUpperCase()} · {plan.start_date} — {plan.end_date}
            </p>
            <h1 className="text-3xl font-bold">Training Plan</h1>
            <p className="mt-1 text-muted-foreground">{plan.total_weekly_hours}h total · ACWR {plan.acwr.toFixed(2)}</p>
          </div>

          <div className="space-y-6">
            {groupByDate(plan.sessions).map(([date, sessions]) => (
              <div key={date}>
                <h2 className="mb-2 text-sm font-semibold uppercase tracking-wider text-muted-foreground">{formatDate(date)}</h2>
                <div className="space-y-2">
                  {sessions.map((s) => (
                    <Link key={s.id} href={`/session/${s.id}`} className="block">
                      <Card className="cursor-pointer transition-colors hover:bg-muted/50">
                        <CardHeader className="pb-2">
                          <div className="flex items-center justify-between gap-2">
                            <div className="flex items-center gap-2">
                              <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${SPORT_COLORS[s.sport] ?? ''}`}>{s.sport}</span>
                              <CardTitle className="text-base">{s.workout_type}</CardTitle>
                            </div>
                          </div>
                        </CardHeader>
                        <CardContent>
                          <p className="text-sm text-muted-foreground">{s.duration_min} min{s.notes ? ` · ${s.notes}` : ''}</p>
                        </CardContent>
                      </Card>
                    </Link>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </ProtectedRoute>
  )
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /c/Users/simon/resilio-plus/frontend && npx tsc --noEmit 2>&1 | head -10
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/plan/page.tsx
git commit -m "feat: plan page — session cards are now links to session detail"
```

---

## Task 8: Frontend — `session/[id]/page.tsx`

**Files:**
- Create: `frontend/src/app/session/[id]/page.tsx`

- [ ] **Step 1: Create `frontend/src/app/session/[id]/page.tsx`**

```tsx
'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import { api, ApiError, type SessionDetailResponse } from '@/lib/api'
import { ProtectedRoute } from '@/components/protected-route'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

const SPORT_COLORS: Record<string, string> = {
  running: 'bg-emerald-500/20 text-emerald-400',
  lifting: 'bg-purple-500/20 text-purple-400',
  swimming: 'bg-blue-500/20 text-blue-400',
  biking: 'bg-orange-500/20 text-orange-400',
}

function FatigueBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>{label}</span>
        <span>{value.toFixed(0)}/100</span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-muted">
        <div className="h-1.5 rounded-full bg-primary" style={{ width: `${value}%` }} />
      </div>
    </div>
  )
}

export default function SessionDetailPage() {
  const { athleteId, logout } = useAuth()
  const router = useRouter()
  const params = useParams<{ id: string }>()
  const sessionId = params?.id ?? ''

  const [session, setSession] = useState<SessionDetailResponse | null>(null)
  const [notFound, setNotFound] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!athleteId || !sessionId) return
    api.getSession(athleteId, sessionId)
      .then(setSession)
      .catch(err => {
        if (err instanceof ApiError && err.status === 401) { logout(); router.replace('/login') }
        else if (err instanceof ApiError && err.status === 404) setNotFound(true)
        else setError('Failed to load session.')
      })
  }, [athleteId, sessionId, logout])

  return (
    <ProtectedRoute>
      <div className="mx-auto max-w-lg space-y-6">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" asChild>
            <Link href="/plan">← Plan</Link>
          </Button>
        </div>

        {notFound && <p className="text-muted-foreground">Session not found.</p>}
        {error && <p className="text-destructive">{error}</p>}
        {!session && !notFound && !error && <p className="animate-pulse text-muted-foreground">Loading…</p>}

        {session && (
          <>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${SPORT_COLORS[session.sport] ?? ''}`}>
                  {session.sport}
                </span>
                {session.log && (
                  <Badge variant="outline" className="text-emerald-400 border-emerald-400/30">✓ Logged</Badge>
                )}
              </div>
              <h1 className="text-2xl font-bold capitalize">{session.workout_type.replace(/_/g, ' ')}</h1>
              <p className="text-muted-foreground">{session.date} · {session.duration_min} min planned</p>
            </div>

            {session.notes && (
              <Card>
                <CardHeader><CardTitle className="text-sm">Coach Notes</CardTitle></CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground whitespace-pre-line">{session.notes}</p>
                </CardContent>
              </Card>
            )}

            <Card>
              <CardHeader><CardTitle className="text-sm">Fatigue Impact</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <FatigueBar label="Local muscular" value={session.fatigue_score.local_muscular} />
                <FatigueBar label="CNS load" value={session.fatigue_score.cns_load} />
                <FatigueBar label="Metabolic cost" value={session.fatigue_score.metabolic_cost} />
                <p className="text-xs text-muted-foreground mt-2">
                  Recovery: ~{session.fatigue_score.recovery_hours}h
                  {session.fatigue_score.affected_muscles.length > 0 && ` · ${session.fatigue_score.affected_muscles.join(', ')}`}
                </p>
              </CardContent>
            </Card>

            {session.log ? (
              <Card className="border-emerald-500/20 bg-emerald-500/5">
                <CardHeader>
                  <CardTitle className="text-sm text-emerald-400">Session Logged</CardTitle>
                </CardHeader>
                <CardContent className="space-y-1 text-sm">
                  {session.log.skipped ? (
                    <p className="text-muted-foreground">Session skipped.</p>
                  ) : (
                    <>
                      {session.log.actual_duration_min != null && (
                        <p>Duration: <span className="font-medium">{session.log.actual_duration_min} min</span></p>
                      )}
                      {session.log.rpe != null && (
                        <p>RPE: <span className="font-medium">{session.log.rpe}/10</span></p>
                      )}
                      {session.log.notes && (
                        <p className="text-muted-foreground">{session.log.notes}</p>
                      )}
                    </>
                  )}
                  <Button variant="outline" size="sm" asChild className="mt-3">
                    <Link href={`/session/${sessionId}/log`}>Edit log</Link>
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <Button className="w-full" asChild>
                <Link href={`/session/${sessionId}/log`}>Log this session →</Link>
              </Button>
            )}
          </>
        )}
      </div>
    </ProtectedRoute>
  )
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /c/Users/simon/resilio-plus/frontend && npx tsc --noEmit 2>&1 | head -10
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/session
git commit -m "feat: add session detail page with fatigue bars and log status"
```

---

## Task 9: Frontend — `session/[id]/log/page.tsx`

**Files:**
- Create: `frontend/src/app/session/[id]/log/page.tsx`

- [ ] **Step 1: Create `frontend/src/app/session/[id]/log/page.tsx`**

```tsx
'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import { api, ApiError, type SessionDetailResponse } from '@/lib/api'
import { ProtectedRoute } from '@/components/protected-route'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

const RPE_LABELS: Record<number, string> = {
  1: 'Very Easy', 2: 'Easy', 3: 'Moderate', 4: 'Somewhat Hard',
  5: 'Hard', 6: 'Hard+', 7: 'Very Hard', 8: 'Very Hard+',
  9: 'Max Effort–', 10: 'Max Effort',
}

export default function LogSessionPage() {
  const { athleteId, logout } = useAuth()
  const router = useRouter()
  const params = useParams<{ id: string }>()
  const sessionId = params?.id ?? ''

  const [session, setSession] = useState<SessionDetailResponse | null>(null)
  const [skipped, setSkipped] = useState(false)
  const [duration, setDuration] = useState('')
  const [rpe, setRpe] = useState('')
  const [notes, setNotes] = useState('')
  // Sport-specific
  const [paceMin, setPaceMin] = useState('')
  const [paceSec, setPaceSec] = useState('')
  const [distanceKm, setDistanceKm] = useState('')
  const [avgPowerW, setAvgPowerW] = useState('')
  const [distanceM, setDistanceM] = useState('')

  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!athleteId || !sessionId) return
    api.getSession(athleteId, sessionId)
      .then(s => {
        setSession(s)
        // Pre-fill from existing log if any
        if (s.log) {
          setSkipped(s.log.skipped)
          if (s.log.actual_duration_min) setDuration(String(s.log.actual_duration_min))
          if (s.log.rpe) setRpe(String(s.log.rpe))
          if (s.log.notes) setNotes(s.log.notes)
        } else {
          // Pre-fill duration with planned
          setDuration(String(s.duration_min))
        }
      })
      .catch(err => {
        if (err instanceof ApiError && err.status === 401) { logout(); router.replace('/login') }
      })
  }, [athleteId, sessionId, logout])

  function buildActualData(): Record<string, unknown> {
    if (!session) return {}
    if (session.sport === 'running') {
      const pace = paceMin && paceSec ? parseInt(paceMin) * 60 + parseInt(paceSec) : undefined
      const dist = distanceKm ? parseFloat(distanceKm) : undefined
      return { ...(pace ? { avg_pace_s_km: pace } : {}), ...(dist ? { distance_km: dist } : {}) }
    }
    if (session.sport === 'biking') {
      return {
        ...(avgPowerW ? { avg_power_w: parseInt(avgPowerW) } : {}),
        ...(distanceKm ? { distance_km: parseFloat(distanceKm) } : {}),
      }
    }
    if (session.sport === 'swimming') {
      return distanceM ? { distance_m: parseInt(distanceM) } : {}
    }
    return {}
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!athleteId) return
    setError('')
    setLoading(true)
    try {
      await api.logSession(athleteId, sessionId, {
        actual_duration_min: skipped ? undefined : (duration ? parseInt(duration) : undefined),
        skipped,
        rpe: !skipped && rpe ? parseInt(rpe) : undefined,
        notes: notes.trim() || undefined,
        actual_data: buildActualData(),
      })
      router.push(`/session/${sessionId}`)
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) { logout(); router.replace('/login') }
      else if (err instanceof ApiError) setError(err.message)
      else setError('Something went wrong.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <ProtectedRoute>
      <div className="mx-auto max-w-lg space-y-6">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" asChild>
            <Link href={`/session/${sessionId}`}>← Session</Link>
          </Button>
        </div>

        <div>
          <h1 className="text-2xl font-bold">Log Session</h1>
          {session && (
            <p className="text-muted-foreground capitalize">
              {session.workout_type.replace(/_/g, ' ')} · {session.duration_min} min planned
            </p>
          )}
        </div>

        <Card>
          <CardContent className="pt-6">
            <form onSubmit={handleSubmit} className="space-y-5">

              <div className="flex items-center gap-3">
                <input
                  id="skipped"
                  type="checkbox"
                  checked={skipped}
                  onChange={e => setSkipped(e.target.checked)}
                  className="h-4 w-4 rounded border-input"
                />
                <Label htmlFor="skipped" className="cursor-pointer">Skip this session</Label>
              </div>

              {!skipped && (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="duration">Actual duration (min)</Label>
                    <Input
                      id="duration"
                      type="number"
                      min={1}
                      value={duration}
                      onChange={e => setDuration(e.target.value)}
                      placeholder="e.g. 45"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="rpe">
                      RPE <span className="text-muted-foreground text-xs">(1–10) {rpe ? `— ${RPE_LABELS[parseInt(rpe)] ?? ''}` : ''}</span>
                    </Label>
                    <Input
                      id="rpe"
                      type="range"
                      min={1}
                      max={10}
                      value={rpe || '5'}
                      onChange={e => setRpe(e.target.value)}
                      className="cursor-pointer"
                    />
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>1 · Easy</span><span>10 · Max</span>
                    </div>
                  </div>

                  {/* Sport-specific fields */}
                  {session?.sport === 'running' && (
                    <div className="space-y-3">
                      <Label>Avg pace (optional)</Label>
                      <div className="flex gap-2 items-center">
                        <Input type="number" min={0} max={30} placeholder="min" value={paceMin} onChange={e => setPaceMin(e.target.value)} className="w-20" />
                        <span className="text-muted-foreground">:</span>
                        <Input type="number" min={0} max={59} placeholder="sec" value={paceSec} onChange={e => setPaceSec(e.target.value)} className="w-20" />
                        <span className="text-sm text-muted-foreground">/km</span>
                      </div>
                      <div className="space-y-1">
                        <Label htmlFor="dist_run">Distance (km, optional)</Label>
                        <Input id="dist_run" type="number" step="0.1" value={distanceKm} onChange={e => setDistanceKm(e.target.value)} placeholder="e.g. 10.2" />
                      </div>
                    </div>
                  )}

                  {session?.sport === 'biking' && (
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-1">
                        <Label htmlFor="power">Avg power (W, optional)</Label>
                        <Input id="power" type="number" value={avgPowerW} onChange={e => setAvgPowerW(e.target.value)} placeholder="e.g. 185" />
                      </div>
                      <div className="space-y-1">
                        <Label htmlFor="dist_bike">Distance (km, optional)</Label>
                        <Input id="dist_bike" type="number" step="0.1" value={distanceKm} onChange={e => setDistanceKm(e.target.value)} placeholder="e.g. 40" />
                      </div>
                    </div>
                  )}

                  {session?.sport === 'swimming' && (
                    <div className="space-y-1">
                      <Label htmlFor="dist_swim">Distance (m, optional)</Label>
                      <Input id="dist_swim" type="number" value={distanceM} onChange={e => setDistanceM(e.target.value)} placeholder="e.g. 1500" />
                    </div>
                  )}

                  <div className="space-y-2">
                    <Label htmlFor="notes">Notes (optional)</Label>
                    <textarea
                      id="notes"
                      className="flex min-h-[80px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                      value={notes}
                      onChange={e => setNotes(e.target.value)}
                      placeholder="How did it feel?"
                    />
                  </div>
                </>
              )}

              {error && <p className="text-sm text-destructive">{error}</p>}

              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? 'Saving…' : 'Save log →'}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </ProtectedRoute>
  )
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /c/Users/simon/resilio-plus/frontend && npx tsc --noEmit 2>&1 | head -10
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/session
git commit -m "feat: add session log form page (duration, RPE, sport-specific data)"
```

---

## Task 10: Frontend — `history/page.tsx`

**Files:**
- Create: `frontend/src/app/history/page.tsx`

- [ ] **Step 1: Create `frontend/src/app/history/page.tsx`**

```tsx
'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import { api, ApiError, type WeekSummary } from '@/lib/api'
import { ProtectedRoute } from '@/components/protected-route'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'

function phaseLabel(phase: string) {
  return phase.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

export default function HistoryPage() {
  const { athleteId, logout } = useAuth()
  const router = useRouter()
  const [history, setHistory] = useState<WeekSummary[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!athleteId) return
    api.getHistory(athleteId)
      .then(setHistory)
      .catch(err => {
        if (err instanceof ApiError && err.status === 401) { logout(); router.replace('/login') }
        else setError('Failed to load history.')
      })
  }, [athleteId, logout])

  return (
    <ProtectedRoute>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Training History</h1>
          <p className="mt-1 text-muted-foreground">Past weeks, newest first.</p>
        </div>

        {error && <p className="text-destructive">{error}</p>}
        {!history && !error && <p className="animate-pulse text-muted-foreground">Loading…</p>}

        {history && history.length === 0 && (
          <p className="text-muted-foreground">No training weeks yet.</p>
        )}

        {history && history.length > 0 && (
          <div className="space-y-3">
            {history.map(week => (
              <Card key={week.plan_id}>
                <CardContent className="pt-4 pb-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-semibold text-muted-foreground">Week {week.week_number}</span>
                        <Badge variant="secondary" className="text-xs">{phaseLabel(week.phase)}</Badge>
                      </div>
                      <p className="text-xs text-muted-foreground mb-2">{week.start_date} — {week.end_date}</p>
                      <div className="space-y-1">
                        <div className="flex justify-between text-xs text-muted-foreground">
                          <span>{week.sessions_logged}/{week.sessions_total} sessions logged</span>
                          <span>{week.completion_pct}%</span>
                        </div>
                        <Progress value={week.completion_pct} className="h-1.5" />
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-lg font-bold">{week.planned_hours}h</p>
                      <p className="text-xs text-muted-foreground">planned</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </ProtectedRoute>
  )
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /c/Users/simon/resilio-plus/frontend && npx tsc --noEmit 2>&1 | head -10
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/history/page.tsx
git commit -m "feat: add training history page"
```

---

## Task 11: Add History link to nav + final verification

**Files:**
- Modify: `frontend/src/components/top-nav.tsx`
- Run: final test suite + push

- [ ] **Step 1: Add History link to top-nav**

Read `frontend/src/components/top-nav.tsx` first, then add a `History` link alongside the existing nav links (Plan, Review). The exact edit depends on the current nav structure — add `<Link href="/history">History</Link>` next to the other nav links.

- [ ] **Step 2: Run full backend test suite**

```bash
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" tests/ -q --tb=short 2>&1 | tail -6
```

Expected: ≥ 1248 passed (1227 existing + ~20 new schema/route/E2E tests), 9 skipped.

- [ ] **Step 3: Run frontend TypeScript check**

```bash
cd /c/Users/simon/resilio-plus/frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Run E2E**

```bash
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" tests/e2e/ -v
```

Expected: 7 passed (test_01 through test_07).

- [ ] **Step 5: Commit nav + push**

```bash
git add frontend/src/components/top-nav.tsx
git commit -m "feat: add History link to top nav"
git push origin main
```

---

## Final Verification Checklist

- [ ] `pytest tests/backend/schemas/test_workout_slot_id.py` → 4 passed
- [ ] `pytest tests/backend/api/test_sessions.py` → 12 passed
- [ ] `pytest tests/e2e/` → 7 passed (test_01–07)
- [ ] `npx tsc --noEmit` (frontend) → no errors
- [ ] `pytest tests/ -q` → ≥ 1248 passed, 9 skipped
- [ ] `git push origin main` → pushed
