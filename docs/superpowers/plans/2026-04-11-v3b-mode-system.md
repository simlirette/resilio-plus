# V3-B Mode System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a two-mode system (`full` | `tracking_only`) to Resilio+, including the DB schema for external plans, the ModeGuard FastAPI dependency, and the mode-switch endpoint.

**Architecture:** A single `coaching_mode` column on `AthleteModel` controls which routes are accessible. A `ModeGuard` dependency enforces this at the route level. New tables `external_plans` and `external_sessions` hold imported/manually-entered plans for Tracking Only athletes. Everything is wired via a new Alembic migration `0003`.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2 (sync psycopg2), Alembic, pytest + SQLite in-memory for tests.

---

## File Map

**Create:**
- `alembic/versions/0003_mode_and_external_plans.py` — migration: coaching_mode column, training_plans.status, external_plans table, external_sessions table, session_logs.external_session_id
- `backend/app/dependencies/mode_guard.py` — `require_full_mode()`, `require_tracking_mode()`
- `backend/app/routes/mode.py` — `PATCH /athletes/{id}/mode`
- `tests/backend/api/test_mode_system.py` — full test coverage

**Modify:**
- `backend/app/db/models.py` — add `coaching_mode` + `status` to `AthleteModel`/`TrainingPlanModel`; add `external_session_id` FK to `SessionLogModel`; add `external_plans` relationship to `AthleteModel`; import new models from schemas
- `backend/app/models/schemas.py` — add `ExternalPlanModel`, `ExternalSessionModel`
- `backend/app/schemas/athlete.py` — add `coaching_mode` to `AthleteProfile`, `AthleteCreate`, `AthleteUpdate`
- `backend/app/schemas/auth.py` — `OnboardingRequest` inherits `AthleteCreate` so gets `coaching_mode` automatically; no change needed
- `backend/app/routes/onboarding.py` — pass `coaching_mode` to `AthleteModel` constructor
- `backend/app/main.py` — mount `mode_router`

---

## Task 1: Alembic migration 0003

**Files:**
- Create: `alembic/versions/0003_mode_and_external_plans.py`

- [ ] **Step 1: Write the migration file**

```python
# alembic/versions/0003_mode_and_external_plans.py
"""Mode system + external plans

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-11 00:00:00.000000

Adds:
- athletes.coaching_mode          VARCHAR NOT NULL DEFAULT 'full'
- training_plans.status           VARCHAR NOT NULL DEFAULT 'active'
- external_plans table
- external_sessions table
- session_logs.external_session_id VARCHAR FK (nullable)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # athletes — add coaching_mode
    op.add_column(
        "athletes",
        sa.Column("coaching_mode", sa.String(), nullable=False, server_default="full"),
    )

    # training_plans — add status
    op.add_column(
        "training_plans",
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
    )

    # session_logs — add external_session_id FK (nullable)
    op.add_column(
        "session_logs",
        sa.Column("external_session_id", sa.String(), nullable=True),
    )
    op.create_foreign_key(
        "fk_session_logs_external_session",
        "session_logs",
        "external_sessions",
        ["external_session_id"],
        ["id"],
    )

    # external_plans
    op.create_table(
        "external_plans",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("athlete_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # external_sessions
    op.create_table(
        "external_sessions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("plan_id", sa.String(), nullable=False),
        sa.Column("athlete_id", sa.String(), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("sport", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("duration_min", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="planned"),
        sa.ForeignKeyConstraint(["plan_id"], ["external_plans.id"]),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("external_sessions")
    op.drop_table("external_plans")
    op.drop_constraint("fk_session_logs_external_session", "session_logs", type_="foreignkey")
    op.drop_column("session_logs", "external_session_id")
    op.drop_column("training_plans", "status")
    op.drop_column("athletes", "coaching_mode")
```

- [ ] **Step 2: Verify migration chains correctly**

```bash
cd C:/Users/simon/resilio-plus
alembic history
```

Expected output includes:
```
0003 -> (head), Mode system + external plans
0002 -> 0003, V3 AthleteState
0001 -> 0002, initial schema
```

- [ ] **Step 3: Commit**

```bash
git add alembic/versions/0003_mode_and_external_plans.py
git commit -m "feat(db): migration 0003 — mode system + external plans schema"
```

---

## Task 2: SQLAlchemy models

**Files:**
- Modify: `backend/app/models/schemas.py`
- Modify: `backend/app/db/models.py`

- [ ] **Step 1: Write failing test first**

```python
# tests/backend/api/test_mode_system.py
"""Tests for the mode system: coaching_mode field, ExternalPlan models."""
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db import models as _models  # noqa: registers all ORM classes


def _engine():
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def test_athlete_model_has_coaching_mode_column():
    engine = _engine()
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("athletes")}
    assert "coaching_mode" in columns, "athletes table missing coaching_mode column"


def test_training_plan_model_has_status_column():
    engine = _engine()
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("training_plans")}
    assert "status" in columns, "training_plans table missing status column"


def test_external_plans_table_exists():
    engine = _engine()
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    assert "external_plans" in inspector.get_table_names()


def test_external_sessions_table_exists():
    engine = _engine()
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    assert "external_sessions" in inspector.get_table_names()
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/backend/api/test_mode_system.py -v
```

Expected: 4 FAILED (columns and tables not yet added to ORM models)

- [ ] **Step 3: Add ExternalPlanModel + ExternalSessionModel to schemas.py**

Open `backend/app/models/schemas.py`. Append at the end (after the existing `AllostaticEntryModel`):

```python
# --- Add this at the end of backend/app/models/schemas.py ---

from datetime import datetime, timezone


class ExternalPlanModel(Base):
    """Training plan entered manually or imported from file by a Tracking Only athlete."""
    __tablename__ = "external_plans"

    id = Column(String, primary_key=True)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=False)
    title = Column(String, nullable=False)
    source = Column(String, nullable=False)          # "manual" | "file_import"
    status = Column(String, nullable=False, default="active")   # "active" | "archived"
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    athlete = relationship("AthleteModel", back_populates="external_plans")
    sessions = relationship(
        "ExternalSessionModel", back_populates="plan", cascade="all, delete-orphan"
    )


class ExternalSessionModel(Base):
    """A single session belonging to an external (non-AI) training plan."""
    __tablename__ = "external_sessions"

    id = Column(String, primary_key=True)
    plan_id = Column(String, ForeignKey("external_plans.id"), nullable=False)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=False)
    session_date = Column(Date, nullable=False)
    sport = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    duration_min = Column(Integer, nullable=True)
    status = Column(String, nullable=False, default="planned")  # "planned"|"completed"|"skipped"

    plan = relationship("ExternalPlanModel", back_populates="sessions")
    log = relationship(
        "SessionLogModel",
        back_populates="external_session",
        uselist=False,
    )
```

- [ ] **Step 4: Update AthleteModel + TrainingPlanModel + SessionLogModel in db/models.py**

Open `backend/app/db/models.py`. Make these three targeted changes:

**4a — Add `coaching_mode` to `AthleteModel` (after the `css_per_100m` line):**
```python
    css_per_100m = Column(Float, nullable=True)
    coaching_mode = Column(String, nullable=False, default="full")  # ADD THIS LINE
    # JSON-serialized list fields
```

**4b — Add `external_plans` relationship to `AthleteModel` (after the `allostatic_entries` relationship):**
```python
    allostatic_entries = relationship("AllostaticEntryModel", back_populates="athlete", cascade="all, delete-orphan")
    external_plans = relationship("ExternalPlanModel", back_populates="athlete", cascade="all, delete-orphan")  # ADD THIS LINE
```

**4c — Add `status` to `TrainingPlanModel` (after `weekly_slots_json`):**
```python
    weekly_slots_json = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="active")  # ADD THIS LINE
    created_at = Column(DateTime(timezone=True), ...
```

**4d — Add `external_session_id` FK and back-ref to `SessionLogModel` (after `logged_at`):**
```python
    logged_at = Column(DateTime(timezone=True), nullable=False,
                       default=lambda: datetime.now(timezone.utc))
    external_session_id = Column(String, ForeignKey("external_sessions.id"), nullable=True)  # ADD

    # Relationships
    athlete = relationship("AthleteModel", back_populates="session_logs")
    plan = relationship("TrainingPlanModel")
    external_session = relationship("ExternalSessionModel", back_populates="log")  # ADD
```

**4e — Update the bottom import in db/models.py to include the new models:**
```python
from app.models.schemas import (  # noqa: E402, F401
    AllostaticEntryModel,
    EnergySnapshotModel,
    HormonalProfileModel,
    ExternalPlanModel,      # ADD
    ExternalSessionModel,   # ADD
)
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/backend/api/test_mode_system.py -v
```

Expected: 4 PASSED

- [ ] **Step 6: Run full test suite — expect no regressions**

```bash
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/ -x -q
```

Expected: all previously passing tests still pass (new columns have defaults, new tables don't affect existing test flows)

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/schemas.py backend/app/db/models.py tests/backend/api/test_mode_system.py
git commit -m "feat(models): ExternalPlan + ExternalSession SQLAlchemy models + coaching_mode on AthleteModel"
```

---

## Task 3: Pydantic schemas

**Files:**
- Modify: `backend/app/schemas/athlete.py`

- [ ] **Step 1: Add failing test for schema field**

Add to `tests/backend/api/test_mode_system.py`:

```python
from app.schemas.athlete import AthleteCreate, AthleteProfile, AthleteUpdate


def test_athlete_create_has_coaching_mode_default():
    payload = {
        "name": "Bob",
        "age": 28,
        "sex": "M",
        "weight_kg": 75.0,
        "height_cm": 180.0,
        "sports": ["running"],
        "primary_sport": "running",
        "goals": ["run 10k"],
        "available_days": [1, 3, 5],
        "hours_per_week": 6.0,
    }
    athlete = AthleteCreate(**payload)
    assert athlete.coaching_mode == "full"


def test_athlete_create_accepts_tracking_only():
    payload = {
        "name": "Carol",
        "age": 35,
        "sex": "F",
        "weight_kg": 58.0,
        "height_cm": 165.0,
        "sports": ["running"],
        "primary_sport": "running",
        "goals": ["finish marathon"],
        "available_days": [0, 2, 5],
        "hours_per_week": 8.0,
        "coaching_mode": "tracking_only",
    }
    athlete = AthleteCreate(**payload)
    assert athlete.coaching_mode == "tracking_only"


def test_athlete_create_rejects_invalid_mode():
    from pydantic import ValidationError
    payload = {
        "name": "Dan",
        "age": 40,
        "sex": "M",
        "weight_kg": 80.0,
        "height_cm": 175.0,
        "sports": ["lifting"],
        "primary_sport": "lifting",
        "goals": ["bench 100kg"],
        "available_days": [1, 4],
        "hours_per_week": 5.0,
        "coaching_mode": "invalid_mode",
    }
    with pytest.raises(ValidationError):
        AthleteCreate(**payload)
```

- [ ] **Step 2: Run — expect FAIL**

```bash
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/backend/api/test_mode_system.py::test_athlete_create_has_coaching_mode_default tests/backend/api/test_mode_system.py::test_athlete_create_accepts_tracking_only tests/backend/api/test_mode_system.py::test_athlete_create_rejects_invalid_mode -v
```

Expected: 3 FAILED

- [ ] **Step 3: Add `coaching_mode` to schemas**

Open `backend/app/schemas/athlete.py`. Add `coaching_mode` to three classes:

**In `AthleteProfile` — add after `job_physical`:**
```python
    job_physical: bool = False
    coaching_mode: Literal["full", "tracking_only"] = "full"  # ADD THIS LINE
```

**In `AthleteCreate` — add after `job_physical`:**
```python
    job_physical: bool = False
    coaching_mode: Literal["full", "tracking_only"] = "full"  # ADD THIS LINE
```

**In `AthleteUpdate` — add after `job_physical`:**
```python
    job_physical: bool | None = None
    coaching_mode: Literal["full", "tracking_only"] | None = None  # ADD THIS LINE
```

The `Literal` import is already present at the top of the file.

- [ ] **Step 4: Run — expect PASS**

```bash
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/backend/api/test_mode_system.py -v
```

Expected: all schema tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/athlete.py tests/backend/api/test_mode_system.py
git commit -m "feat(schemas): add coaching_mode field to AthleteCreate/Profile/Update"
```

---

## Task 4: ModeGuard dependency

**Files:**
- Create: `backend/app/dependencies/__init__.py` (empty)
- Create: `backend/app/dependencies/mode_guard.py`

- [ ] **Step 1: Add failing tests**

Add to `tests/backend/api/test_mode_system.py`:

```python
from tests.backend.api.conftest import authed_client, onboarding_payload


def test_mode_guard_full_mode_passes(authed_client):
    """An athlete in full mode can access full-mode-only endpoints (200, not 403)."""
    client, athlete_id = authed_client
    # The /workflow/status endpoint is guarded by require_full_mode in Task 6
    # For now just verify the mode field is accessible in the athlete profile
    resp = client.get(f"/athletes/{athlete_id}")
    assert resp.status_code == 200
    assert resp.json()["coaching_mode"] == "full"


def test_mode_guard_tracking_only_blocks_full_routes(authed_client):
    """After switching to tracking_only, full-coaching routes return 403."""
    client, athlete_id = authed_client
    # Switch mode
    resp = client.patch(
        f"/athletes/{athlete_id}/mode",
        json={"coaching_mode": "tracking_only"},
    )
    assert resp.status_code == 200
    # Attempt to create a plan (full-mode only)
    resp = client.post(f"/athletes/{athlete_id}/workflow/create-plan", json={})
    assert resp.status_code == 403
```

Note: `test_mode_guard_tracking_only_blocks_full_routes` will fully pass after Task 6. For now it will fail on the PATCH (mode route doesn't exist yet). That's expected — we're writing tests top-down.

- [ ] **Step 2: Create `backend/app/dependencies/__init__.py`**

```python
# backend/app/dependencies/__init__.py
# Dependency package — re-exports for convenience
from .mode_guard import require_full_mode, require_tracking_mode

__all__ = ["require_full_mode", "require_tracking_mode"]
```

- [ ] **Step 3: Create `backend/app/dependencies/mode_guard.py`**

```python
# backend/app/dependencies/mode_guard.py
"""ModeGuard — FastAPI dependencies that enforce coaching_mode on routes.

Usage:
    @router.post("/create-plan")
    def create_plan(athlete: AthleteModel = Depends(require_full_mode)):
        ...

Both guards:
  1. Verify the JWT belongs to the requested athlete (ownership check)
  2. Verify the athlete is in the required mode
"""
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db.models import AthleteModel
from ..dependencies import get_db, get_current_athlete_id


def require_full_mode(
    athlete_id: str,
    current_id: Annotated[str, Depends(get_current_athlete_id)],
    db: Annotated[Session, Depends(get_db)],
) -> AthleteModel:
    """Return the AthleteModel if the caller owns it and is in 'full' mode.

    Raises 403 if mode is 'tracking_only'.
    Raises 403 if the JWT athlete_id doesn't match the path athlete_id.
    """
    athlete = db.get(AthleteModel, athlete_id)
    if not athlete or athlete.id != current_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if athlete.coaching_mode != "full":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires Full Coaching mode",
        )
    return athlete


def require_tracking_mode(
    athlete_id: str,
    current_id: Annotated[str, Depends(get_current_athlete_id)],
    db: Annotated[Session, Depends(get_db)],
) -> AthleteModel:
    """Return the AthleteModel if the caller owns it and is in 'tracking_only' mode.

    Raises 403 if mode is 'full'.
    """
    athlete = db.get(AthleteModel, athlete_id)
    if not athlete or athlete.id != current_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if athlete.coaching_mode != "tracking_only":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires Tracking Only mode",
        )
    return athlete
```

- [ ] **Step 4: Add unit tests for the guard logic**

Add to `tests/backend/api/test_mode_system.py`:

```python
from unittest.mock import MagicMock
from fastapi import HTTPException
import pytest

from app.dependencies.mode_guard import require_full_mode, require_tracking_mode
from app.db.models import AthleteModel


def _make_athlete(coaching_mode: str, athlete_id: str = "abc") -> AthleteModel:
    a = MagicMock(spec=AthleteModel)
    a.id = athlete_id
    a.coaching_mode = coaching_mode
    return a


def test_require_full_mode_passes_for_full():
    athlete = _make_athlete("full", "abc")
    db = MagicMock()
    db.get.return_value = athlete
    result = require_full_mode(athlete_id="abc", current_id="abc", db=db)
    assert result is athlete


def test_require_full_mode_raises_for_tracking_only():
    athlete = _make_athlete("tracking_only", "abc")
    db = MagicMock()
    db.get.return_value = athlete
    with pytest.raises(HTTPException) as exc_info:
        require_full_mode(athlete_id="abc", current_id="abc", db=db)
    assert exc_info.value.status_code == 403


def test_require_full_mode_raises_for_wrong_owner():
    athlete = _make_athlete("full", "abc")
    db = MagicMock()
    db.get.return_value = athlete
    with pytest.raises(HTTPException) as exc_info:
        require_full_mode(athlete_id="abc", current_id="xyz", db=db)
    assert exc_info.value.status_code == 403


def test_require_tracking_mode_passes_for_tracking_only():
    athlete = _make_athlete("tracking_only", "abc")
    db = MagicMock()
    db.get.return_value = athlete
    result = require_tracking_mode(athlete_id="abc", current_id="abc", db=db)
    assert result is athlete


def test_require_tracking_mode_raises_for_full():
    athlete = _make_athlete("full", "abc")
    db = MagicMock()
    db.get.return_value = athlete
    with pytest.raises(HTTPException) as exc_info:
        require_tracking_mode(athlete_id="abc", current_id="abc", db=db)
    assert exc_info.value.status_code == 403
```

- [ ] **Step 5: Run — expect PASS for unit tests**

```bash
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/backend/api/test_mode_system.py -k "require_full_mode or require_tracking_mode" -v
```

Expected: 5 PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/app/dependencies/ tests/backend/api/test_mode_system.py
git commit -m "feat(deps): ModeGuard — require_full_mode + require_tracking_mode dependencies"
```

---

## Task 5: Mode switch route

**Files:**
- Create: `backend/app/routes/mode.py`

- [ ] **Step 1: Write failing integration test**

Add to `tests/backend/api/test_mode_system.py`:

```python
def test_patch_mode_switches_to_tracking_only(authed_client):
    client, athlete_id = authed_client
    resp = client.patch(
        f"/athletes/{athlete_id}/mode",
        json={"coaching_mode": "tracking_only"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["coaching_mode"] == "tracking_only"


def test_patch_mode_switches_back_to_full(authed_client):
    client, athlete_id = authed_client
    # Switch to tracking_only first
    client.patch(f"/athletes/{athlete_id}/mode", json={"coaching_mode": "tracking_only"})
    # Switch back to full
    resp = client.patch(f"/athletes/{athlete_id}/mode", json={"coaching_mode": "full"})
    assert resp.status_code == 200
    assert resp.json()["coaching_mode"] == "full"


def test_patch_mode_rejects_invalid_value(authed_client):
    client, athlete_id = authed_client
    resp = client.patch(
        f"/athletes/{athlete_id}/mode",
        json={"coaching_mode": "coaching_only"},
    )
    assert resp.status_code == 422


def test_patch_mode_archives_active_plan_when_switching_to_tracking(authed_client):
    """Switching to tracking_only archives the active training plan."""
    client, athlete_id = authed_client
    # athlete_id already has a plan from onboarding (status='active')
    resp = client.patch(
        f"/athletes/{athlete_id}/mode",
        json={"coaching_mode": "tracking_only"},
    )
    assert resp.status_code == 200
    # Verify plan is now archived via the plans endpoint
    plans_resp = client.get(f"/athletes/{athlete_id}/plans")
    assert plans_resp.status_code == 200
    plans = plans_resp.json()
    if plans:  # onboarding creates a plan
        assert all(p.get("status", "active") == "archived" for p in plans), \
            "All plans should be archived after switching to tracking_only"


def test_patch_mode_requires_auth(client):
    resp = client.patch("/athletes/some-id/mode", json={"coaching_mode": "full"})
    assert resp.status_code == 401
```

- [ ] **Step 2: Run — expect FAIL (route does not exist)**

```bash
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/backend/api/test_mode_system.py -k "patch_mode" -v
```

Expected: FAILED with 404 or attribute errors

- [ ] **Step 3: Create `backend/app/routes/mode.py`**

```python
# backend/app/routes/mode.py
"""Mode switch endpoint — PATCH /athletes/{athlete_id}/mode

Allows an authenticated athlete to switch between 'full' and 'tracking_only'.

Side effects:
- full → tracking_only : archives all active TrainingPlan records
- tracking_only → full : no destructive action (data preserved)
"""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db.models import AthleteModel, TrainingPlanModel
from ..dependencies import get_db, get_current_athlete_id

router = APIRouter(prefix="/athletes", tags=["mode"])

DB = Annotated[Session, Depends(get_db)]


class ModeSwitchRequest(BaseModel):
    coaching_mode: Literal["full", "tracking_only"]


class ModeSwitchResponse(BaseModel):
    athlete_id: str
    coaching_mode: str
    message: str


@router.patch("/{athlete_id}/mode", response_model=ModeSwitchResponse)
def switch_mode(
    athlete_id: str,
    req: ModeSwitchRequest,
    db: DB,
    current_id: Annotated[str, Depends(get_current_athlete_id)],
) -> ModeSwitchResponse:
    athlete = db.get(AthleteModel, athlete_id)
    if not athlete or athlete.id != current_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    previous_mode = athlete.coaching_mode
    athlete.coaching_mode = req.coaching_mode

    # Side effect: archive active plans when switching away from full coaching
    if previous_mode == "full" and req.coaching_mode == "tracking_only":
        active_plans = (
            db.query(TrainingPlanModel)
            .filter(
                TrainingPlanModel.athlete_id == athlete_id,
                TrainingPlanModel.status == "active",
            )
            .all()
        )
        for plan in active_plans:
            plan.status = "archived"

    db.commit()
    db.refresh(athlete)

    return ModeSwitchResponse(
        athlete_id=athlete.id,
        coaching_mode=athlete.coaching_mode,
        message=f"Mode switched to {athlete.coaching_mode}",
    )
```

- [ ] **Step 4: Run — expect PASS**

```bash
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/backend/api/test_mode_system.py -k "patch_mode" -v
```

Expected: 5 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/routes/mode.py tests/backend/api/test_mode_system.py
git commit -m "feat(routes): PATCH /athletes/{id}/mode — mode switch with plan archival"
```

---

## Task 6: Wire into main.py + update onboarding

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/routes/onboarding.py`
- Modify: `backend/app/routes/workflow.py` (add ModeGuard to create-plan endpoint)

- [ ] **Step 1: Write failing test for onboarding with coaching_mode**

Add to `tests/backend/api/test_mode_system.py`:

```python
def test_onboarding_with_tracking_only_mode(client):
    """An athlete can register with tracking_only mode."""
    payload = {
        "name": "Eve",
        "age": 25,
        "sex": "F",
        "weight_kg": 55.0,
        "height_cm": 162.0,
        "sports": ["running"],
        "primary_sport": "running",
        "goals": ["stay active"],
        "available_days": [1, 3, 5],
        "hours_per_week": 5.0,
        "email": "eve@test.com",
        "password": "password123",
        "plan_start_date": "2026-05-01",
        "coaching_mode": "tracking_only",
    }
    resp = client.post("/athletes/onboarding", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["athlete"]["coaching_mode"] == "tracking_only"


def test_onboarding_defaults_to_full_mode(client):
    """Onboarding without coaching_mode defaults to full."""
    payload = {
        "name": "Frank",
        "age": 32,
        "sex": "M",
        "weight_kg": 78.0,
        "height_cm": 178.0,
        "sports": ["running", "lifting"],
        "primary_sport": "running",
        "goals": ["sub-25 5k"],
        "available_days": [0, 2, 4, 6],
        "hours_per_week": 8.0,
        "email": "frank@test.com",
        "password": "password123",
        "plan_start_date": "2026-05-01",
    }
    resp = client.post("/athletes/onboarding", json=payload)
    assert resp.status_code == 201
    assert resp.json()["athlete"]["coaching_mode"] == "full"
```

- [ ] **Step 2: Run — expect FAIL**

```bash
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/backend/api/test_mode_system.py -k "onboarding" -v
```

Expected: FAILED (coaching_mode not passed to AthleteModel in onboarding)

- [ ] **Step 3: Mount mode_router in main.py**

Open `backend/app/main.py`. Add the import and `include_router` call:

```python
# Add import after the other route imports:
from .routes.mode import router as mode_router

# Add include_router at the end of the router registrations:
app.include_router(mode_router)
```

- [ ] **Step 4: Pass coaching_mode in onboarding.py**

Open `backend/app/routes/onboarding.py`. Find the `AthleteModel(...)` constructor call (around line 29) and add `coaching_mode=req.coaching_mode`:

```python
    athlete_model = AthleteModel(
        id=athlete_id,
        name=req.name,
        age=req.age,
        sex=req.sex,
        weight_kg=req.weight_kg,
        height_cm=req.height_cm,
        primary_sport=req.primary_sport.value,
        target_race_date=req.target_race_date,
        hours_per_week=req.hours_per_week,
        sleep_hours_typical=req.sleep_hours_typical,
        stress_level=req.stress_level,
        job_physical=req.job_physical,
        max_hr=req.max_hr,
        resting_hr=req.resting_hr,
        ftp_watts=req.ftp_watts,
        vdot=req.vdot,
        css_per_100m=req.css_per_100m,
        sports_json=json.dumps([s.value for s in req.sports]),
        goals_json=json.dumps(req.goals),
        available_days_json=json.dumps(req.available_days),
        equipment_json=json.dumps(req.equipment),
        coaching_mode=req.coaching_mode,          # ADD THIS LINE
    )
```

- [ ] **Step 5: Expose coaching_mode in AthleteResponse**

`AthleteResponse = AthleteProfile` already has `coaching_mode` after Task 3. But `athlete_model_to_response()` in `routes/athletes.py` explicitly maps each field and needs `coaching_mode` added. Open `backend/app/routes/athletes.py` and update `athlete_model_to_response` (line 27–50) — add one line before the closing parenthesis:

```python
def athlete_model_to_response(m: AthleteModel) -> AthleteResponse:
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
        coaching_mode=m.coaching_mode,        # ADD THIS LINE
    )
```

- [ ] **Step 6: Add ModeGuard to create-plan endpoint**

Open `backend/app/routes/workflow.py`. The `create_plan_workflow` function at line 183 uses `_require_own`. Replace it with `require_full_mode`.

Add the import at the top of the file (after the existing imports):
```python
from ..dependencies.mode_guard import require_full_mode
```

At line 184–188, change the dependency on `create_plan_workflow`:
```python
# BEFORE:
@router.post("/{athlete_id}/workflow/create-plan", response_model=PlanCreateResponse)
def create_plan_workflow(
    athlete_id: str,
    req: PlanCreateRequest,
    athlete: Annotated[AthleteModel, Depends(_require_own)],
    db: DB,

# AFTER:
@router.post("/{athlete_id}/workflow/create-plan", response_model=PlanCreateResponse)
def create_plan_workflow(
    athlete_id: str,
    req: PlanCreateRequest,
    athlete: Annotated[AthleteModel, Depends(require_full_mode)],
    db: DB,
```

`require_full_mode` does the same ownership check as `_require_own` plus the mode check — no other changes needed in the function body.

- [ ] **Step 7: Run all mode tests — expect PASS**

```bash
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/backend/api/test_mode_system.py -v
```

Expected: all PASSED

- [ ] **Step 8: Run full test suite**

```bash
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/ -x -q
```

Expected: no regressions. If existing onboarding tests fail because `coaching_mode` unexpectedly appears in responses — check that `AthleteProfile.coaching_mode` has `default="full"` and that the serialization is backward-compatible (it is, since it's a new optional field with a default).

- [ ] **Step 9: Commit**

```bash
git add backend/app/main.py backend/app/routes/onboarding.py backend/app/routes/athletes.py backend/app/routes/workflow.py tests/backend/api/test_mode_system.py
git commit -m "feat(wiring): mount mode router + onboarding captures coaching_mode + ModeGuard on create-plan"
```

---

## Task 7: Apply Alembic migration to running DB

This task runs against the actual PostgreSQL instance (not tests), confirming the migration works.

- [ ] **Step 1: Ensure Docker PostgreSQL is running**

```bash
cd C:/Users/simon/resilio-plus
docker-compose up -d db
docker-compose ps
```

Expected: `db` service shows `healthy`

- [ ] **Step 2: Run the migration**

```bash
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade 0002 -> 0003, Mode system + external plans
```

- [ ] **Step 3: Verify schema in PostgreSQL**

```bash
docker-compose exec db psql -U resilio -d resilio_db -c "\d athletes"
```

Expected: `coaching_mode` column visible with `character varying` type and default `'full'`.

```bash
docker-compose exec db psql -U resilio -d resilio_db -c "\dt"
```

Expected: `external_plans` and `external_sessions` tables listed.

- [ ] **Step 4: Final commit**

```bash
git add .
git commit -m "chore: verify migration 0003 applies cleanly to PostgreSQL"
```

---

## Done ✓

After Task 7, the V3-B Mode System is complete:
- PostgreSQL schema has `coaching_mode`, `external_plans`, `external_sessions`
- `ModeGuard` enforces mode on coaching routes
- `PATCH /athletes/{id}/mode` switches mode with plan archival side effect
- Onboarding captures the chosen mode
- All new tests pass, no regressions in existing 1243+ tests

**Next plan:** V3-C — EnergyCycleService + routes (`POST /checkin`, `GET /readiness`, `GET /energy/history`)
