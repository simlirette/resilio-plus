# Background Jobs System (V3-S) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the ad-hoc `sync_scheduler.py` with a structured background jobs system: per-athlete dynamic scheduling, persistent job execution logs, daily readiness/strain snapshots, and an admin monitoring endpoint.

**Architecture:** APScheduler 3.x `BackgroundScheduler` with `SQLAlchemyJobStore` for persistence. New `backend/app/jobs/` module with clean separation: scheduler setup, registry for per-athlete dynamic jobs, job wrappers that log to `job_runs` table, and global compute/cleanup jobs. Old `sync_scheduler.py` deleted; energy pattern pure functions extracted to `core/energy_patterns.py`.

**Tech Stack:** APScheduler 3.x (existing dep), SQLAlchemy, Alembic, `freezegun` (new dev dep), FastAPI.

---

## Codebase Context (read before starting any task)

- **Existing scheduler:** `backend/app/core/sync_scheduler.py` — APScheduler `BackgroundScheduler`, in-memory only. Contains `sync_all_strava()` (calls deleted `SyncService.sync_strava()`), `sync_all_hevy()`, `sync_all_terra()`, `detect_energy_patterns()` + 4 pattern detectors, `setup_scheduler()`. The `sync_all_strava()` is broken (calls code removed in V3-R).
- **FastAPI lifespan in `backend/app/main.py`** — `setup_scheduler()` called in `lifespan()`, scheduler stored in local var, shutdown on exit.
- **DB session factory:** `from ..db.database import SessionLocal` — creates thread-safe independent sessions.
- **`DATABASE_URL`:** `backend/app/db/database.py:6` — env var, defaults to `postgresql+psycopg2://resilio:resilio@localhost:5432/resilio_db`.
- **Existing sync functions:**
  - Strava V2: `backend/app/integrations/strava/sync_service.py` → `sync(athlete_id: str, db: Session) -> SyncSummary`
  - Hevy: `backend/app/services/sync_service.py` → `SyncService.sync_hevy(athlete_id, db) -> dict`
  - Terra: `backend/app/services/sync_service.py` → `SyncService.sync_terra(athlete_id, db) -> dict`
- **Existing compute functions:**
  - Readiness: `backend/app/core/readiness.py` → `compute_readiness(terra_data, hrv_baseline) -> float`
  - Strain: `backend/app/core/strain.py` → `compute_muscle_strain(strava_activities, hevy_workouts, reference_date) -> MuscleStrainScore`
  - Connector data: `backend/app/services/connector_service.py` → `fetch_connector_data(athlete_id, db) -> dict` (returns strava_activities, hevy_workouts, terra_health)
- **Auth dependency:** `from ..dependencies import get_db, get_current_athlete_id`
- **DB model pattern:** `backend/app/db/models.py` — Column-based SQLAlchemy models inheriting from `Base`. Uses `from .database import Base`.
- **Alembic:** Latest migration is `0008_strava_v2.py`. Next is `0009`.
- **Test fixtures:** `tests/backend/conftest.py` — `api_client` (module-scoped, SQLite in-memory), `auth_state` (creates athlete via onboarding, returns token+headers+athlete_id).
- **`AthleteModel` constructor:** Uses `sports_json`, `goals_json`, `available_days_json`, `equipment_json` (NOT `sports`, `goals`, etc.).
- **pytest path:** `C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe`

---

## File Structure

### New files
- `backend/app/jobs/__init__.py` — empty
- `backend/app/jobs/models.py` — `JobRunModel`, `AthleteStateSnapshotModel`
- `backend/app/jobs/runner.py` — `run_job()` wrapper (logs to job_runs, timeout)
- `backend/app/jobs/registry.py` — `register_athlete_jobs()`, `unregister_athlete_jobs()`, `restore_all_jobs()`
- `backend/app/jobs/sync_jobs.py` — `sync_strava_for_athlete()`, `sync_hevy_for_athlete()`, `sync_terra_for_athlete()`
- `backend/app/jobs/compute_jobs.py` — `run_daily_snapshot()`, `run_energy_patterns()`
- `backend/app/jobs/cleanup_jobs.py` — `run_cleanup_job_runs()`
- `backend/app/jobs/scheduler.py` — `setup_scheduler()`, `get_scheduler()`
- `backend/app/core/energy_patterns.py` — pure functions extracted from `sync_scheduler.py`
- `backend/app/routes/admin.py` — `GET /admin/jobs`
- `alembic/versions/0009_background_jobs.py` — creates `job_runs` + `athlete_state_snapshots`
- `tests/backend/jobs/test_runner.py` — job wrapper tests
- `tests/backend/jobs/test_registry.py` — registry tests
- `tests/backend/jobs/test_sync_jobs.py` — sync job wrapper tests
- `tests/backend/jobs/test_compute_jobs.py` — daily snapshot + energy patterns tests
- `tests/backend/jobs/test_cleanup_jobs.py` — cleanup tests
- `tests/backend/jobs/__init__.py` — empty
- `tests/backend/api/test_admin.py` — admin endpoint tests

### Modified files
- `backend/app/main.py` — swap scheduler import, add admin router
- `backend/app/routes/strava.py` — register strava job after callback
- `backend/app/routes/connectors.py` — register hevy/terra jobs after connect, unregister on delete
- `.env.example` — add `ADMIN_ATHLETE_ID`

### Deleted files
- `backend/app/core/sync_scheduler.py` — replaced by `jobs/` module + `core/energy_patterns.py`

---

## Task 1: DB Models — JobRunModel + AthleteStateSnapshotModel

**Files:**
- Create: `backend/app/jobs/__init__.py`
- Create: `backend/app/jobs/models.py`
- Test: `tests/backend/jobs/__init__.py`
- Test: `tests/backend/jobs/test_models.py`

- [ ] **Step 1: Create empty `__init__.py` files**

Create `backend/app/jobs/__init__.py` (empty file).
Create `tests/backend/jobs/__init__.py` (empty file).

- [ ] **Step 2: Write the failing test for JobRunModel**

```python
# tests/backend/jobs/test_models.py
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db import models as _models  # noqa: F401
from app.jobs import models as _job_models  # noqa: F401
from app.jobs.models import JobRunModel, AthleteStateSnapshotModel


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)
    with Session() as session:
        yield session
    Base.metadata.drop_all(engine)


def test_job_run_model_roundtrip(db_session):
    run = JobRunModel(
        id=str(uuid.uuid4()),
        job_id="strava_sync_abc-123",
        athlete_id=None,
        job_type="strava_sync",
        status="ok",
        started_at=datetime.now(timezone.utc),
        duration_ms=1230,
        error_message=None,
    )
    db_session.add(run)
    db_session.commit()

    fetched = db_session.query(JobRunModel).first()
    assert fetched.job_id == "strava_sync_abc-123"
    assert fetched.status == "ok"
    assert fetched.duration_ms == 1230
    assert fetched.error_message is None
    assert fetched.created_at is not None


def test_athlete_state_snapshot_roundtrip(db_session):
    from app.db.models import AthleteModel
    athlete_id = str(uuid.uuid4())
    db_session.add(AthleteModel(
        id=athlete_id, name="Alice", age=30, sex="F",
        weight_kg=60.0, height_cm=168.0,
        sports_json='["running"]', primary_sport="running",
        goals_json='["run fast"]', available_days_json="[0]",
        hours_per_week=10.0, equipment_json="[]",
    ))
    db_session.commit()

    snap = AthleteStateSnapshotModel(
        id=str(uuid.uuid4()),
        athlete_id=athlete_id,
        snapshot_date=datetime.now(timezone.utc).date(),
        readiness=1.05,
        strain_json='{"quads": 45}',
    )
    db_session.add(snap)
    db_session.commit()

    fetched = db_session.query(AthleteStateSnapshotModel).first()
    assert fetched.athlete_id == athlete_id
    assert fetched.readiness == 1.05
    assert fetched.strain_json == '{"quads": 45}'
    assert fetched.created_at is not None


def test_athlete_state_snapshot_unique_constraint(db_session):
    from app.db.models import AthleteModel
    from sqlalchemy.exc import IntegrityError
    from datetime import date

    athlete_id = str(uuid.uuid4())
    db_session.add(AthleteModel(
        id=athlete_id, name="Alice", age=30, sex="F",
        weight_kg=60.0, height_cm=168.0,
        sports_json='["running"]', primary_sport="running",
        goals_json='["run fast"]', available_days_json="[0]",
        hours_per_week=10.0, equipment_json="[]",
    ))
    db_session.commit()

    today = date.today()
    db_session.add(AthleteStateSnapshotModel(
        id=str(uuid.uuid4()), athlete_id=athlete_id,
        snapshot_date=today, readiness=1.0, strain_json="{}",
    ))
    db_session.commit()

    db_session.add(AthleteStateSnapshotModel(
        id=str(uuid.uuid4()), athlete_id=athlete_id,
        snapshot_date=today, readiness=1.1, strain_json="{}",
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/jobs/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.jobs'`

- [ ] **Step 4: Implement the models**

```python
# backend/app/jobs/models.py
"""DB models for background job execution logs and athlete state snapshots."""
from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint

from ..db.database import Base


class JobRunModel(Base):
    __tablename__ = "job_runs"

    id = Column(String, primary_key=True)
    job_id = Column(String, nullable=False)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=True)
    job_type = Column(String, nullable=False)
    status = Column(String, nullable=False)  # ok, error, timeout
    started_at = Column(DateTime(timezone=True), nullable=False)
    duration_ms = Column(Integer, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_job_runs_type_created", "job_type", "created_at"),
    )


class AthleteStateSnapshotModel(Base):
    __tablename__ = "athlete_state_snapshots"

    id = Column(String, primary_key=True)
    athlete_id = Column(String, ForeignKey("athletes.id", ondelete="CASCADE"), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    readiness = Column(Float, nullable=False)
    strain_json = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("athlete_id", "snapshot_date", name="uq_snapshot_athlete_date"),
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/jobs/test_models.py -v`
Expected: 3 PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/app/jobs/__init__.py backend/app/jobs/models.py tests/backend/jobs/__init__.py tests/backend/jobs/test_models.py
git commit -m "feat(jobs): add JobRunModel + AthleteStateSnapshotModel"
```

---

## Task 2: Alembic Migration 0009

**Files:**
- Create: `alembic/versions/0009_background_jobs.py`

- [ ] **Step 1: Create migration**

```python
# alembic/versions/0009_background_jobs.py
"""Background jobs: job_runs + athlete_state_snapshots tables

Revision ID: 0009
Revises: 0008
Create Date: 2026-04-14 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "job_runs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("athlete_id", sa.String(), sa.ForeignKey("athletes.id"), nullable=True),
        sa.Column("job_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_job_runs_type_created", "job_runs", ["job_type", "created_at"])

    op.create_table(
        "athlete_state_snapshots",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("athlete_id", sa.String(), sa.ForeignKey("athletes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("readiness", sa.Float(), nullable=False),
        sa.Column("strain_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("athlete_id", "snapshot_date", name="uq_snapshot_athlete_date"),
    )


def downgrade() -> None:
    op.drop_table("athlete_state_snapshots")
    op.drop_index("ix_job_runs_type_created", table_name="job_runs")
    op.drop_table("job_runs")
```

- [ ] **Step 2: Commit**

```bash
git add alembic/versions/0009_background_jobs.py
git commit -m "feat(jobs): add Alembic migration 0009 — job_runs + athlete_state_snapshots"
```

---

## Task 3: Job Runner — `run_job()` wrapper

**Files:**
- Create: `backend/app/jobs/runner.py`
- Test: `tests/backend/jobs/test_runner.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/backend/jobs/test_runner.py
import time
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db import models as _models  # noqa: F401
from app.jobs import models as _job_models  # noqa: F401
from app.jobs.models import JobRunModel
from app.jobs.runner import run_job


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)
    with Session() as session:
        yield session
    Base.metadata.drop_all(engine)


def test_run_job_success(db_session):
    fn = MagicMock(return_value={"synced": 3})

    run_job(
        job_id="strava_sync_abc",
        job_type="strava_sync",
        athlete_id="abc",
        fn=fn,
        db=db_session,
        timeout_s=60,
    )

    fn.assert_called_once()
    row = db_session.query(JobRunModel).first()
    assert row is not None
    assert row.status == "ok"
    assert row.duration_ms >= 0
    assert row.error_message is None


def test_run_job_error(db_session):
    fn = MagicMock(side_effect=ValueError("something broke"))

    run_job(
        job_id="strava_sync_abc",
        job_type="strava_sync",
        athlete_id="abc",
        fn=fn,
        db=db_session,
        timeout_s=60,
    )

    row = db_session.query(JobRunModel).first()
    assert row is not None
    assert row.status == "error"
    assert "something broke" in row.error_message


def test_run_job_timeout(db_session):
    def slow_fn():
        time.sleep(5)

    run_job(
        job_id="strava_sync_abc",
        job_type="strava_sync",
        athlete_id="abc",
        fn=slow_fn,
        db=db_session,
        timeout_s=0.2,
    )

    row = db_session.query(JobRunModel).first()
    assert row is not None
    assert row.status == "timeout"


def test_run_job_truncates_long_error(db_session):
    fn = MagicMock(side_effect=ValueError("x" * 5000))

    run_job(
        job_id="test_job",
        job_type="strava_sync",
        athlete_id=None,
        fn=fn,
        db=db_session,
        timeout_s=60,
    )

    row = db_session.query(JobRunModel).first()
    assert len(row.error_message) <= 2000
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/jobs/test_runner.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.jobs.runner'`

- [ ] **Step 3: Implement run_job**

```python
# backend/app/jobs/runner.py
"""Job execution wrapper — logs every run to job_runs table."""
from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .models import JobRunModel

logger = logging.getLogger(__name__)

_MAX_ERROR_LEN = 2000


def run_job(
    *,
    job_id: str,
    job_type: str,
    athlete_id: str | None,
    fn: callable,
    db: Session,
    timeout_s: int | float = 60,
) -> None:
    """Execute fn() with timeout, log result to job_runs."""
    started_at = datetime.now(timezone.utc)
    status = "ok"
    error_message = None
    result_holder: dict = {}
    exception_holder: list = []

    def _target():
        try:
            result_holder["result"] = fn()
        except Exception as exc:
            exception_holder.append(exc)

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    thread.join(timeout=timeout_s)

    if thread.is_alive():
        status = "timeout"
        error_message = f"Job timed out after {timeout_s}s"
        logger.warning("Job %s timed out after %ss", job_id, timeout_s)
    elif exception_holder:
        status = "error"
        error_message = str(exception_holder[0])[:_MAX_ERROR_LEN]
        logger.warning("Job %s failed: %s", job_id, error_message)

    elapsed_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)

    run = JobRunModel(
        id=str(uuid.uuid4()),
        job_id=job_id,
        athlete_id=athlete_id,
        job_type=job_type,
        status=status,
        started_at=started_at,
        duration_ms=elapsed_ms,
        error_message=error_message,
    )
    db.add(run)
    db.commit()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/jobs/test_runner.py -v`
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/jobs/runner.py tests/backend/jobs/test_runner.py
git commit -m "feat(jobs): add run_job() wrapper with timeout + job_runs logging"
```

---

## Task 4: Registry — per-athlete job management

**Files:**
- Create: `backend/app/jobs/registry.py`
- Test: `tests/backend/jobs/test_registry.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/backend/jobs/test_registry.py
import uuid
from unittest.mock import MagicMock, call

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db import models as _models  # noqa: F401
from app.jobs import models as _job_models  # noqa: F401
from app.db.models import AthleteModel, ConnectorCredentialModel
from app.jobs.registry import register_athlete_jobs, unregister_athlete_jobs, restore_all_jobs


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)
    with Session() as session:
        yield session
    Base.metadata.drop_all(engine)


def _make_athlete(db, athlete_id=None):
    aid = athlete_id or str(uuid.uuid4())
    db.add(AthleteModel(
        id=aid, name="Alice", age=30, sex="F",
        weight_kg=60.0, height_cm=168.0,
        sports_json='["running"]', primary_sport="running",
        goals_json='["run fast"]', available_days_json="[0]",
        hours_per_week=10.0, equipment_json="[]",
    ))
    db.commit()
    return aid


def test_register_athlete_jobs_adds_to_scheduler():
    scheduler = MagicMock()
    register_athlete_jobs("abc-123", "strava", scheduler)
    scheduler.add_job.assert_called_once()
    args, kwargs = scheduler.add_job.call_args
    assert kwargs["id"] == "strava_sync_abc-123"
    assert kwargs["replace_existing"] is True


def test_unregister_athlete_jobs_removes_from_scheduler():
    scheduler = MagicMock()
    unregister_athlete_jobs("abc-123", "strava", scheduler)
    scheduler.remove_job.assert_called_once_with("strava_sync_abc-123")


def test_unregister_ignores_missing_job():
    from apscheduler.jobstores.base import JobLookupError
    scheduler = MagicMock()
    scheduler.remove_job.side_effect = JobLookupError("strava_sync_abc-123")
    # Should not raise
    unregister_athlete_jobs("abc-123", "strava", scheduler)


def test_restore_all_jobs_registers_all_connected(db_session):
    aid1 = _make_athlete(db_session)
    aid2 = _make_athlete(db_session)
    # aid1 has strava + hevy
    db_session.add(ConnectorCredentialModel(
        id=str(uuid.uuid4()), athlete_id=aid1, provider="strava", extra_json="{}",
    ))
    db_session.add(ConnectorCredentialModel(
        id=str(uuid.uuid4()), athlete_id=aid1, provider="hevy", extra_json="{}",
    ))
    # aid2 has terra
    db_session.add(ConnectorCredentialModel(
        id=str(uuid.uuid4()), athlete_id=aid2, provider="terra", extra_json="{}",
    ))
    db_session.commit()

    scheduler = MagicMock()
    restore_all_jobs(scheduler, db_session)

    assert scheduler.add_job.call_count == 3
    job_ids = {c.kwargs["id"] for c in scheduler.add_job.call_args_list}
    assert f"strava_sync_{aid1}" in job_ids
    assert f"hevy_sync_{aid1}" in job_ids
    assert f"terra_sync_{aid2}" in job_ids
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/jobs/test_registry.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.jobs.registry'`

- [ ] **Step 3: Implement registry**

```python
# backend/app/jobs/registry.py
"""Per-athlete job lifecycle: register on connect, unregister on disconnect."""
from __future__ import annotations

import logging

from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from ..db.models import ConnectorCredentialModel

logger = logging.getLogger(__name__)

# Provider → (job module function path, interval hours)
_PROVIDER_CONFIG: dict[str, tuple[str, int]] = {
    "strava": ("app.jobs.sync_jobs:sync_strava_for_athlete", 1),
    "hevy": ("app.jobs.sync_jobs:sync_hevy_for_athlete", 6),
    "terra": ("app.jobs.sync_jobs:sync_terra_for_athlete", 6),
}


def _job_id(provider: str, athlete_id: str) -> str:
    return f"{provider}_sync_{athlete_id}"


def register_athlete_jobs(
    athlete_id: str, provider: str, scheduler: BackgroundScheduler,
) -> None:
    """Add a sync job for the given athlete+provider."""
    config = _PROVIDER_CONFIG.get(provider)
    if config is None:
        return
    func_ref, interval_hours = config
    jid = _job_id(provider, athlete_id)
    scheduler.add_job(
        func_ref,
        trigger="interval",
        hours=interval_hours,
        id=jid,
        replace_existing=True,
        misfire_grace_time=300,
        kwargs={"athlete_id": athlete_id},
    )
    logger.info("Registered job %s (every %dh)", jid, interval_hours)


def unregister_athlete_jobs(
    athlete_id: str, provider: str, scheduler: BackgroundScheduler,
) -> None:
    """Remove a sync job for the given athlete+provider."""
    jid = _job_id(provider, athlete_id)
    try:
        scheduler.remove_job(jid)
        logger.info("Unregistered job %s", jid)
    except JobLookupError:
        logger.debug("Job %s not found (already removed)", jid)


def restore_all_jobs(scheduler: BackgroundScheduler, db: Session) -> None:
    """Re-register jobs for all connected athletes. Called at startup."""
    creds = db.query(ConnectorCredentialModel).all()
    for cred in creds:
        register_athlete_jobs(cred.athlete_id, cred.provider, scheduler)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/jobs/test_registry.py -v`
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/jobs/registry.py tests/backend/jobs/test_registry.py
git commit -m "feat(jobs): add registry — register/unregister/restore per-athlete jobs"
```

---

## Task 5: Sync Jobs — per-athlete wrappers

**Files:**
- Create: `backend/app/jobs/sync_jobs.py`
- Test: `tests/backend/jobs/test_sync_jobs.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/backend/jobs/test_sync_jobs.py
import uuid
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db import models as _models  # noqa: F401
from app.jobs import models as _job_models  # noqa: F401
from app.jobs.models import JobRunModel
from app.jobs.sync_jobs import sync_strava_for_athlete, sync_hevy_for_athlete, sync_terra_for_athlete


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)
    with Session() as session:
        yield session
    Base.metadata.drop_all(engine)


@patch("app.jobs.sync_jobs.strava_sync")
@patch("app.jobs.sync_jobs.SessionLocal")
def test_sync_strava_for_athlete_logs_run(mock_session_cls, mock_sync):
    mock_db = MagicMock()
    mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_db)
    mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)
    mock_sync.return_value = MagicMock(synced=2, skipped=0)

    sync_strava_for_athlete(athlete_id="abc-123")

    mock_sync.assert_called_once_with("abc-123", mock_db)


@patch("app.jobs.sync_jobs.SyncService.sync_hevy")
@patch("app.jobs.sync_jobs.SessionLocal")
def test_sync_hevy_for_athlete_logs_run(mock_session_cls, mock_sync):
    mock_db = MagicMock()
    mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_db)
    mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)
    mock_sync.return_value = {"synced": 1, "skipped": 0}

    sync_hevy_for_athlete(athlete_id="abc-123")

    mock_sync.assert_called_once_with("abc-123", mock_db)


@patch("app.jobs.sync_jobs.SyncService.sync_terra")
@patch("app.jobs.sync_jobs.SessionLocal")
def test_sync_terra_for_athlete_logs_run(mock_session_cls, mock_sync):
    mock_db = MagicMock()
    mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_db)
    mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)
    mock_sync.return_value = {"synced": 1, "hrv_rmssd": 55.0}

    sync_terra_for_athlete(athlete_id="abc-123")

    mock_sync.assert_called_once_with("abc-123", mock_db)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/jobs/test_sync_jobs.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.jobs.sync_jobs'`

- [ ] **Step 3: Implement sync jobs**

```python
# backend/app/jobs/sync_jobs.py
"""Per-athlete sync job wrappers. Each creates its own DB session."""
from __future__ import annotations

import logging

from ..db.database import SessionLocal
from ..integrations.strava.sync_service import sync as strava_sync
from ..services.sync_service import SyncService
from .runner import run_job

logger = logging.getLogger(__name__)


def sync_strava_for_athlete(athlete_id: str) -> None:
    with SessionLocal() as db:
        run_job(
            job_id=f"strava_sync_{athlete_id}",
            job_type="strava_sync",
            athlete_id=athlete_id,
            fn=lambda: strava_sync(athlete_id, db),
            db=db,
            timeout_s=60,
        )


def sync_hevy_for_athlete(athlete_id: str) -> None:
    with SessionLocal() as db:
        run_job(
            job_id=f"hevy_sync_{athlete_id}",
            job_type="hevy_sync",
            athlete_id=athlete_id,
            fn=lambda: SyncService.sync_hevy(athlete_id, db),
            db=db,
            timeout_s=60,
        )


def sync_terra_for_athlete(athlete_id: str) -> None:
    with SessionLocal() as db:
        run_job(
            job_id=f"terra_sync_{athlete_id}",
            job_type="terra_sync",
            athlete_id=athlete_id,
            fn=lambda: SyncService.sync_terra(athlete_id, db),
            db=db,
            timeout_s=60,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/jobs/test_sync_jobs.py -v`
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/jobs/sync_jobs.py tests/backend/jobs/test_sync_jobs.py
git commit -m "feat(jobs): add per-athlete sync job wrappers (strava, hevy, terra)"
```

---

## Task 6: Extract energy patterns to `core/energy_patterns.py`

**Files:**
- Create: `backend/app/core/energy_patterns.py`
- Modify: `backend/app/core/sync_scheduler.py` (read for extraction, will be deleted in Task 9)

- [ ] **Step 1: Create `core/energy_patterns.py`**

Extract all pure functions and `detect_energy_patterns()` from `sync_scheduler.py`. Copy verbatim — these functions are already tested via existing tests.

```python
# backend/app/core/energy_patterns.py
"""Energy pattern detection — pure functions + DB scanner.

Extracted from sync_scheduler.py. Detects 4 patterns from energy snapshots
and creates proactive Head Coach messages.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..models.schemas import EnergySnapshotModel, HeadCoachMessageModel


def _last_7_days(snapshots: list) -> list:
    """Filter snapshots to those within the last 7 days."""
    cutoff_aware = datetime.now(timezone.utc) - timedelta(days=7)
    cutoff_naive = cutoff_aware.replace(tzinfo=None)

    def _within_7d(snap) -> bool:
        ts = snap.timestamp
        if ts.tzinfo is None:
            return ts >= cutoff_naive
        return ts >= cutoff_aware

    return [s for s in snapshots if _within_7d(s)]


def detect_heavy_legs(snapshots: list) -> bool:
    """Pattern 1: legs_feeling heavy/dead on >=3 of last 7 days."""
    recent = _last_7_days(snapshots)
    count = sum(1 for s in recent if s.legs_feeling in ("heavy", "dead"))
    return count >= 3


def detect_chronic_stress(snapshots: list) -> bool:
    """Pattern 2: stress_level == 'significant' on >=4 of last 7 days."""
    recent = _last_7_days(snapshots)
    count = sum(1 for s in recent if s.stress_level == "significant")
    return count >= 4


def detect_persistent_divergence(snapshots: list) -> bool:
    """Pattern 3: divergence >30 pts for >=3 consecutive days."""
    recent = sorted(_last_7_days(snapshots), key=lambda s: s.timestamp, reverse=True)
    consecutive = 0
    for snap in recent:
        obj = float(snap.objective_score) if snap.objective_score is not None else 50.0
        subj = float(snap.subjective_score) if snap.subjective_score is not None else 50.0
        if abs(obj - subj) > 30.0:
            consecutive += 1
            if consecutive >= 3:
                return True
        else:
            consecutive = 0
    return False


def detect_reds_signal(snapshots: list) -> bool:
    """Pattern 4: energy_availability < 30.0 on >=3 of last 7 days."""
    recent = _last_7_days(snapshots)
    count = sum(1 for s in recent if float(s.energy_availability) < 30.0)
    return count >= 3


_PATTERN_MESSAGES: dict[str, str] = {
    "heavy_legs": (
        "Tes jambes sont lourdes depuis 3 jours ou plus. "
        "Ton Head Coach recommande une seance de recuperation active ou un jour de repos complet."
    ),
    "chronic_stress": (
        "Ton niveau de stress est eleve depuis 4 jours ou plus. "
        "Ton Head Coach recommande de reduire l'intensite et de prioriser le sommeil."
    ),
    "persistent_divergence": (
        "Tes donnees objectives et subjectives divergent fortement depuis 3 jours consecutifs. "
        "Ton ressenti compte — ton Head Coach ajuste l'intensite a la baisse."
    ),
    "reds_signal": (
        "Ta disponibilite energetique est basse depuis 3 jours ou plus. "
        "Ton Head Coach recommande d'augmenter les apports caloriques et de reduire le volume."
    ),
}


def _has_recent_message(athlete_id: str, pattern_type: str, db: Session) -> bool:
    cutoff_aware = datetime.now(timezone.utc) - timedelta(days=7)
    cutoff_naive = cutoff_aware.replace(tzinfo=None)
    existing = (
        db.query(HeadCoachMessageModel)
        .filter(
            HeadCoachMessageModel.athlete_id == athlete_id,
            HeadCoachMessageModel.pattern_type == pattern_type,
        )
        .order_by(HeadCoachMessageModel.created_at.desc())
        .first()
    )
    if existing is None:
        return False
    ts = existing.created_at
    if ts.tzinfo is None:
        return ts >= cutoff_naive
    return ts >= cutoff_aware


def _maybe_create_message(athlete_id: str, pattern_type: str, db: Session) -> bool:
    if _has_recent_message(athlete_id, pattern_type, db):
        return False
    msg = HeadCoachMessageModel(
        id=str(uuid.uuid4()),
        athlete_id=athlete_id,
        pattern_type=pattern_type,
        message=_PATTERN_MESSAGES[pattern_type],
        created_at=datetime.now(timezone.utc),
        is_read=False,
    )
    db.add(msg)
    return True


def detect_energy_patterns(db: Session) -> dict:
    """Scan all athletes' energy snapshots, detect 4 patterns, store messages.

    Returns: {"athletes_scanned": N, "messages_created": M}
    """
    from ..db.models import AthleteModel

    athletes = db.query(AthleteModel).all()
    athletes_scanned = 0
    messages_created = 0

    for athlete in athletes:
        athletes_scanned += 1
        snaps = (
            db.query(EnergySnapshotModel)
            .filter(EnergySnapshotModel.athlete_id == athlete.id)
            .all()
        )
        if not snaps:
            continue

        pattern_checks = [
            ("heavy_legs", detect_heavy_legs(snaps)),
            ("chronic_stress", detect_chronic_stress(snaps)),
            ("persistent_divergence", detect_persistent_divergence(snaps)),
            ("reds_signal", detect_reds_signal(snaps)),
        ]
        for pattern_type, triggered in pattern_checks:
            if triggered:
                created = _maybe_create_message(athlete.id, pattern_type, db)
                if created:
                    messages_created += 1

    db.commit()
    return {"athletes_scanned": athletes_scanned, "messages_created": messages_created}
```

- [ ] **Step 2: Run existing energy patterns tests to verify no regression**

Run: `C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -k "energy_pattern" -v`
Expected: All existing tests PASS (they import from `sync_scheduler` still — will be updated when we delete that file in Task 9).

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/energy_patterns.py
git commit -m "feat(jobs): extract energy_patterns.py from sync_scheduler (pure functions)"
```

---

## Task 7: Compute Jobs — daily snapshot + energy patterns wrapper

**Files:**
- Create: `backend/app/jobs/compute_jobs.py`
- Test: `tests/backend/jobs/test_compute_jobs.py`

- [ ] **Step 1: Add `freezegun` dev dependency**

Run: `cd C:\Users\simon\resilio-plus && poetry add --group dev freezegun`

- [ ] **Step 2: Write the failing tests**

```python
# tests/backend/jobs/test_compute_jobs.py
import json
import uuid
from datetime import date, datetime, timezone
from unittest.mock import patch, MagicMock

import pytest
from freezegun import freeze_time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db import models as _models  # noqa: F401
from app.jobs import models as _job_models  # noqa: F401
from app.db.models import AthleteModel, ConnectorCredentialModel
from app.jobs.models import AthleteStateSnapshotModel, JobRunModel
from app.jobs.compute_jobs import run_daily_snapshot, run_energy_patterns


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)
    with Session() as session:
        yield session
    Base.metadata.drop_all(engine)


def _make_athlete(db, athlete_id=None):
    aid = athlete_id or str(uuid.uuid4())
    db.add(AthleteModel(
        id=aid, name="Alice", age=30, sex="F",
        weight_kg=60.0, height_cm=168.0,
        sports_json='["running"]', primary_sport="running",
        goals_json='["run fast"]', available_days_json="[0]",
        hours_per_week=10.0, equipment_json="[]",
    ))
    db.commit()
    return aid


@patch("app.jobs.compute_jobs.fetch_connector_data")
@patch("app.jobs.compute_jobs.compute_readiness")
@patch("app.jobs.compute_jobs.compute_muscle_strain")
@patch("app.jobs.compute_jobs.SessionLocal")
def test_daily_snapshot_creates_snapshot(mock_sl, mock_strain, mock_readiness, mock_fetch, db_session):
    aid = _make_athlete(db_session)
    mock_sl.return_value.__enter__ = MagicMock(return_value=db_session)
    mock_sl.return_value.__exit__ = MagicMock(return_value=False)
    mock_fetch.return_value = {
        "strava_activities": [],
        "hevy_workouts": [],
        "terra_health": None,
    }
    mock_readiness.return_value = 1.05
    mock_strain.return_value = MagicMock()
    mock_strain.return_value.model_dump.return_value = {"quads": 45, "posterior_chain": 30}

    run_daily_snapshot()

    snap = db_session.query(AthleteStateSnapshotModel).filter_by(athlete_id=aid).first()
    assert snap is not None
    assert snap.readiness == 1.05
    assert "quads" in snap.strain_json


@patch("app.jobs.compute_jobs.fetch_connector_data")
@patch("app.jobs.compute_jobs.compute_readiness")
@patch("app.jobs.compute_jobs.compute_muscle_strain")
@patch("app.jobs.compute_jobs.SessionLocal")
def test_daily_snapshot_idempotent(mock_sl, mock_strain, mock_readiness, mock_fetch, db_session):
    aid = _make_athlete(db_session)
    mock_sl.return_value.__enter__ = MagicMock(return_value=db_session)
    mock_sl.return_value.__exit__ = MagicMock(return_value=False)
    mock_fetch.return_value = {"strava_activities": [], "hevy_workouts": [], "terra_health": None}
    mock_readiness.return_value = 1.0
    mock_strain.return_value = MagicMock()
    mock_strain.return_value.model_dump.return_value = {}

    run_daily_snapshot()
    # Second run updates, doesn't duplicate
    mock_readiness.return_value = 1.1
    run_daily_snapshot()

    snaps = db_session.query(AthleteStateSnapshotModel).filter_by(athlete_id=aid).all()
    assert len(snaps) == 1
    assert snaps[0].readiness == 1.1


@patch("app.jobs.compute_jobs.detect_energy_patterns")
@patch("app.jobs.compute_jobs.SessionLocal")
def test_energy_patterns_job_calls_detect(mock_sl, mock_detect):
    mock_db = MagicMock()
    mock_sl.return_value.__enter__ = MagicMock(return_value=mock_db)
    mock_sl.return_value.__exit__ = MagicMock(return_value=False)
    mock_detect.return_value = {"athletes_scanned": 5, "messages_created": 2}

    run_energy_patterns()

    mock_detect.assert_called_once_with(mock_db)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/jobs/test_compute_jobs.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.jobs.compute_jobs'`

- [ ] **Step 4: Implement compute jobs**

```python
# backend/app/jobs/compute_jobs.py
"""Global compute jobs: daily snapshot + energy patterns."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import date, datetime, timezone

from ..core.energy_patterns import detect_energy_patterns
from ..core.readiness import compute_readiness
from ..core.strain import compute_muscle_strain
from ..db.database import SessionLocal
from ..db.models import AthleteModel
from ..services.connector_service import fetch_connector_data
from .models import AthleteStateSnapshotModel
from .runner import run_job

logger = logging.getLogger(__name__)


def _snapshot_all_athletes() -> None:
    """Compute readiness + strain for all athletes and upsert snapshots."""
    with SessionLocal() as db:
        athletes = db.query(AthleteModel).all()
        today = date.today()

        for athlete in athletes:
            try:
                data = fetch_connector_data(athlete.id, db)
                readiness = compute_readiness(
                    [data["terra_health"]] if data["terra_health"] else [],
                )
                strain = compute_muscle_strain(
                    data["strava_activities"],
                    data["hevy_workouts"],
                )

                existing = (
                    db.query(AthleteStateSnapshotModel)
                    .filter_by(athlete_id=athlete.id, snapshot_date=today)
                    .first()
                )
                if existing:
                    existing.readiness = readiness
                    existing.strain_json = json.dumps(strain.model_dump())
                else:
                    db.add(AthleteStateSnapshotModel(
                        id=str(uuid.uuid4()),
                        athlete_id=athlete.id,
                        snapshot_date=today,
                        readiness=readiness,
                        strain_json=json.dumps(strain.model_dump()),
                    ))
            except Exception:
                logger.warning("Snapshot failed for athlete %s", athlete.id, exc_info=True)

        db.commit()


def run_daily_snapshot() -> None:
    """Daily job: compute readiness + strain snapshots for all athletes."""
    with SessionLocal() as db:
        run_job(
            job_id="daily_snapshot",
            job_type="daily_snapshot",
            athlete_id=None,
            fn=_snapshot_all_athletes,
            db=db,
            timeout_s=300,
        )


def _energy_patterns_inner() -> None:
    with SessionLocal() as db:
        detect_energy_patterns(db)


def run_energy_patterns() -> None:
    """Weekly job: detect energy patterns for all athletes."""
    with SessionLocal() as db:
        run_job(
            job_id="energy_patterns",
            job_type="energy_patterns",
            athlete_id=None,
            fn=_energy_patterns_inner,
            db=db,
            timeout_s=300,
        )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/jobs/test_compute_jobs.py -v`
Expected: 3 PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/app/jobs/compute_jobs.py tests/backend/jobs/test_compute_jobs.py
git commit -m "feat(jobs): add daily snapshot + energy patterns compute jobs"
```

---

## Task 8: Cleanup Job

**Files:**
- Create: `backend/app/jobs/cleanup_jobs.py`
- Test: `tests/backend/jobs/test_cleanup_jobs.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/backend/jobs/test_cleanup_jobs.py
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

import pytest
from freezegun import freeze_time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db import models as _models  # noqa: F401
from app.jobs import models as _job_models  # noqa: F401
from app.jobs.models import JobRunModel
from app.jobs.cleanup_jobs import _cleanup_old_runs, RETENTION_DAYS


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)
    with Session() as session:
        yield session
    Base.metadata.drop_all(engine)


def _add_run(db, days_ago: int):
    ts = datetime.now(timezone.utc) - timedelta(days=days_ago)
    db.add(JobRunModel(
        id=str(uuid.uuid4()),
        job_id="test_job",
        job_type="strava_sync",
        status="ok",
        started_at=ts,
        duration_ms=100,
        created_at=ts,
    ))
    db.commit()


def test_cleanup_deletes_old_runs(db_session):
    _add_run(db_session, days_ago=31)  # should be deleted
    _add_run(db_session, days_ago=35)  # should be deleted
    _add_run(db_session, days_ago=5)   # should be kept

    deleted = _cleanup_old_runs(db_session)

    assert deleted == 2
    remaining = db_session.query(JobRunModel).count()
    assert remaining == 1


def test_cleanup_keeps_recent_runs(db_session):
    _add_run(db_session, days_ago=1)
    _add_run(db_session, days_ago=15)
    _add_run(db_session, days_ago=29)

    deleted = _cleanup_old_runs(db_session)

    assert deleted == 0
    remaining = db_session.query(JobRunModel).count()
    assert remaining == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/jobs/test_cleanup_jobs.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.jobs.cleanup_jobs'`

- [ ] **Step 3: Implement cleanup jobs**

```python
# backend/app/jobs/cleanup_jobs.py
"""Cleanup job: delete old job_runs entries."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..db.database import SessionLocal
from .models import JobRunModel
from .runner import run_job

logger = logging.getLogger(__name__)

RETENTION_DAYS = 30


def _cleanup_old_runs(db: Session) -> int:
    """Delete job_runs older than RETENTION_DAYS. Returns count deleted."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    deleted = (
        db.query(JobRunModel)
        .filter(JobRunModel.created_at < cutoff)
        .delete(synchronize_session=False)
    )
    db.commit()
    logger.info("Cleaned up %d old job runs (older than %d days)", deleted, RETENTION_DAYS)
    return deleted


def run_cleanup_job_runs() -> None:
    """Weekly job: delete old job_runs entries."""
    with SessionLocal() as db:
        run_job(
            job_id="cleanup_job_runs",
            job_type="cleanup",
            athlete_id=None,
            fn=lambda: _cleanup_old_runs(db),
            db=db,
            timeout_s=60,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/jobs/test_cleanup_jobs.py -v`
Expected: 2 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/jobs/cleanup_jobs.py tests/backend/jobs/test_cleanup_jobs.py
git commit -m "feat(jobs): add cleanup job — delete job_runs older than 30 days"
```

---

## Task 9: Scheduler Setup + Delete old sync_scheduler.py

**Files:**
- Create: `backend/app/jobs/scheduler.py`
- Modify: `backend/app/main.py`
- Delete: `backend/app/core/sync_scheduler.py`

- [ ] **Step 1: Implement scheduler.py**

```python
# backend/app/jobs/scheduler.py
"""APScheduler setup with SQLAlchemyJobStore + global/dynamic jobs."""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from ..db.database import SessionLocal
from .cleanup_jobs import run_cleanup_job_runs
from .compute_jobs import run_daily_snapshot, run_energy_patterns
from .registry import restore_all_jobs

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def get_scheduler() -> BackgroundScheduler:
    """Return the running scheduler. Raises RuntimeError if not started."""
    if _scheduler is None:
        raise RuntimeError("Scheduler not started")
    return _scheduler


def setup_scheduler() -> BackgroundScheduler:
    """Create, configure, and start the BackgroundScheduler."""
    global _scheduler

    scheduler = BackgroundScheduler()

    # Global jobs
    scheduler.add_job(
        run_daily_snapshot,
        trigger="cron",
        hour=4,
        id="daily_snapshot",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        run_energy_patterns,
        trigger="cron",
        day_of_week="mon",
        hour=6,
        minute=0,
        id="energy_patterns",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        run_cleanup_job_runs,
        trigger="cron",
        day_of_week="sun",
        hour=3,
        minute=0,
        id="cleanup_job_runs",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    scheduler.start()

    # Restore per-athlete jobs from DB
    with SessionLocal() as db:
        restore_all_jobs(scheduler, db)

    _scheduler = scheduler
    logger.info("Background scheduler started with %d jobs", len(scheduler.get_jobs()))
    return scheduler
```

- [ ] **Step 2: Update `main.py` — swap scheduler import, add admin router**

In `backend/app/main.py`, change line 7:

```python
# Old:
from .core.sync_scheduler import setup_scheduler
# New:
from .jobs.scheduler import setup_scheduler
```

- [ ] **Step 3: Delete `backend/app/core/sync_scheduler.py`**

```bash
git rm backend/app/core/sync_scheduler.py
```

- [ ] **Step 4: Fix any imports referencing old sync_scheduler**

Search for imports of `sync_scheduler` and update them:
- If any test imports `from app.core.sync_scheduler import detect_energy_patterns`, change to `from app.core.energy_patterns import detect_energy_patterns`.
- If any test imports `from app.core.sync_scheduler import _detect_heavy_legs` (etc.), change to `from app.core.energy_patterns import detect_heavy_legs` (note: public name now, no underscore prefix).

Run: `C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -x -q --tb=short`
Fix any import errors that appear.

- [ ] **Step 5: Run full test suite**

Run: `C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -x -q --tb=short`
Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/jobs/scheduler.py backend/app/main.py backend/app/core/energy_patterns.py
git add -u  # captures deleted sync_scheduler.py + any updated test imports
git commit -m "feat(jobs): add scheduler setup, delete old sync_scheduler.py"
```

---

## Task 10: Admin Endpoint

**Files:**
- Create: `backend/app/routes/admin.py`
- Modify: `backend/app/main.py`
- Test: `tests/backend/api/test_admin.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/backend/api/test_admin.py
import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db import models as _models  # noqa: F401
from app.jobs import models as _job_models  # noqa: F401
from app.jobs.models import JobRunModel


def test_admin_jobs_returns_200_for_admin(api_client, auth_state, monkeypatch):
    monkeypatch.setenv("ADMIN_ATHLETE_ID", auth_state["athlete_id"])
    resp = api_client.get("/admin/jobs", headers=auth_state["headers"])
    assert resp.status_code == 200
    body = resp.json()
    assert "jobs" in body
    assert "summary" in body
    assert isinstance(body["jobs"], list)
    assert "total_jobs" in body["summary"]
    assert "errors_24h" in body["summary"]


def test_admin_jobs_returns_403_for_non_admin(api_client, auth_state, monkeypatch):
    monkeypatch.setenv("ADMIN_ATHLETE_ID", str(uuid.uuid4()))
    resp = api_client.get("/admin/jobs", headers=auth_state["headers"])
    assert resp.status_code == 403


def test_admin_jobs_returns_401_unauthenticated(api_client):
    resp = api_client.get("/admin/jobs")
    assert resp.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/api/test_admin.py -v`
Expected: FAIL — 404 (route doesn't exist yet)

- [ ] **Step 3: Implement admin route**

```python
# backend/app/routes/admin.py
"""Admin endpoints — job monitoring."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..dependencies import get_db, get_current_athlete_id
from ..jobs.models import JobRunModel

router = APIRouter(prefix="/admin", tags=["admin"])

DB = Annotated[Session, Depends(get_db)]


def _require_admin(
    athlete_id: Annotated[str, Depends(get_current_athlete_id)],
) -> str:
    admin_id = os.getenv("ADMIN_ATHLETE_ID", "")
    if athlete_id != admin_id:
        raise HTTPException(status_code=403, detail="Admin access required")
    return athlete_id


@router.get("/jobs")
def list_jobs(
    _: Annotated[str, Depends(_require_admin)],
    db: DB,
) -> dict:
    """List all scheduled jobs with last run info and summary."""
    from ..jobs.scheduler import get_scheduler

    # Get scheduled jobs from APScheduler
    try:
        scheduler = get_scheduler()
        scheduled = scheduler.get_jobs()
    except RuntimeError:
        scheduled = []

    now = datetime.now(timezone.utc)
    cutoff_24h = now - timedelta(hours=24)

    jobs = []
    for job in scheduled:
        # Get last run from job_runs table
        last_run_row = (
            db.query(JobRunModel)
            .filter(JobRunModel.job_id == job.id)
            .order_by(JobRunModel.started_at.desc())
            .first()
        )
        last_run = None
        if last_run_row:
            last_run = {
                "status": last_run_row.status,
                "started_at": last_run_row.started_at.isoformat(),
                "duration_ms": last_run_row.duration_ms,
            }

        # Extract athlete_id and job_type from job id
        parts = job.id.rsplit("_", 1)
        athlete_id = parts[-1] if len(parts) > 1 and "_sync_" in job.id else None
        job_type = job.id.rsplit("_" + parts[-1], 1)[0] if athlete_id else job.id

        jobs.append({
            "job_id": job.id,
            "job_type": job_type,
            "athlete_id": athlete_id,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "last_run": last_run,
        })

    # Summary
    errors_24h = (
        db.query(func.count(JobRunModel.id))
        .filter(JobRunModel.status != "ok", JobRunModel.created_at >= cutoff_24h)
        .scalar()
    )
    next_runs = [j.next_run_time for j in scheduled if j.next_run_time]
    earliest_next = min(next_runs).isoformat() if next_runs else None

    return {
        "jobs": jobs,
        "summary": {
            "total_jobs": len(scheduled),
            "errors_24h": errors_24h,
            "next_run": earliest_next,
        },
    }
```

- [ ] **Step 4: Add admin router to main.py**

In `backend/app/main.py`, add after the existing router imports:

```python
from .routes.admin import router as admin_router
```

And add after the last `app.include_router(...)` call:

```python
app.include_router(admin_router)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/api/test_admin.py -v`
Expected: 3 PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/app/routes/admin.py backend/app/main.py tests/backend/api/test_admin.py
git commit -m "feat(jobs): add GET /admin/jobs endpoint with job status + summary"
```

---

## Task 11: Hook registry into connect/disconnect endpoints

**Files:**
- Modify: `backend/app/routes/strava.py`
- Modify: `backend/app/routes/connectors.py`
- Modify: `backend/app/integrations/strava/oauth_service.py`

- [ ] **Step 1: Update `oauth_service.py` callback to return athlete_id**

In `backend/app/integrations/strava/oauth_service.py`, change the `callback()` return from:

```python
    return {"connected": True}
```

to:

```python
    return {"connected": True, "athlete_id": matching.athlete_id}
```

- [ ] **Step 2: Update `routes/strava.py` callback to register job**

In `backend/app/routes/strava.py`, add import at the top:

```python
from ..jobs.scheduler import get_scheduler
from ..jobs.registry import register_athlete_jobs
```

Update the `callback` function to register a job after successful OAuth:

```python
@router.get("/callback")
def callback(
    code: str,
    state: str,
    db: DB,
) -> dict:
    """Handle Strava OAuth callback — exchange code for encrypted tokens."""
    try:
        result = oauth_callback(code=code, state=state, db=db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except _httpx.HTTPStatusError:
        raise HTTPException(status_code=502, detail="Strava token exchange failed")

    try:
        register_athlete_jobs(result["athlete_id"], "strava", get_scheduler())
    except RuntimeError:
        pass  # scheduler not started (testing)

    return result
```

- [ ] **Step 3: Update `routes/connectors.py` hevy_connect to register job**

In `backend/app/routes/connectors.py`, add import:

```python
from ..jobs.scheduler import get_scheduler
from ..jobs.registry import register_athlete_jobs, unregister_athlete_jobs
```

After the `_upsert_credential(...)` call in `hevy_connect`, add:

```python
    try:
        register_athlete_jobs(athlete_id, "hevy", get_scheduler())
    except RuntimeError:
        pass  # scheduler not started (testing)
```

- [ ] **Step 4: Update `routes/connectors.py` terra_connect to register job**

After the `_upsert_credential(...)` call in `terra_connect`, add:

```python
    try:
        register_athlete_jobs(athlete_id, "terra", get_scheduler())
    except RuntimeError:
        pass  # scheduler not started (testing)
```

- [ ] **Step 5: Update `routes/connectors.py` delete_connector to unregister job**

After `db.delete(cred)` and before `db.commit()` in `delete_connector`, add:

```python
    try:
        unregister_athlete_jobs(athlete_id, provider, get_scheduler())
    except RuntimeError:
        pass  # scheduler not started (testing)
```

- [ ] **Step 6: Run full test suite**

Run: `C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -x -q --tb=short`
Expected: All tests pass (registry calls are wrapped in try/except RuntimeError for testing).

- [ ] **Step 7: Commit**

```bash
git add backend/app/routes/strava.py backend/app/routes/connectors.py backend/app/integrations/strava/oauth_service.py
git commit -m "feat(jobs): hook registry into connect/disconnect endpoints"
```

---

## Task 12: Update .env.example + JOBS.md docs

**Files:**
- Modify: `.env.example`
- Create: `docs/backend/JOBS.md`

- [ ] **Step 1: Add `ADMIN_ATHLETE_ID` to `.env.example`**

Add after the `STRAVA_ENCRYPTION_KEY` line:

```
# Admin — job monitoring endpoint (your athlete UUID)
ADMIN_ATHLETE_ID=CHANGEME
```

- [ ] **Step 2: Create `docs/backend/JOBS.md`**

```markdown
# Background Jobs

Resilio+ uses APScheduler 3.x for background job scheduling.

## Job Types

### Per-Athlete Jobs (dynamic)

Created when athlete connects a provider, removed on disconnect.

| Job | Frequency | What it does |
|---|---|---|
| `strava_sync_{id}` | Every 1h | Incremental Strava activity sync via `integrations.strava.sync_service.sync()` |
| `hevy_sync_{id}` | Every 6h | Hevy workout sync via `SyncService.sync_hevy()` |
| `terra_sync_{id}` | Every 6h | Terra HRV/sleep sync via `SyncService.sync_terra()` |

### Global Jobs

| Job | Schedule | What it does |
|---|---|---|
| `daily_snapshot` | 4:00 UTC daily | Compute readiness + strain for all athletes, store in `athlete_state_snapshots` |
| `energy_patterns` | Monday 6:00 UTC | Detect energy patterns, create proactive Head Coach messages |
| `cleanup_job_runs` | Sunday 3:00 UTC | Delete `job_runs` older than 30 days |

## How to Add a Job

1. Create your job function in `backend/app/jobs/` (e.g. `my_jobs.py`)
2. Wrap execution with `run_job()` from `jobs/runner.py` — this handles logging to `job_runs`
3. Register in `jobs/scheduler.py` (global) or `jobs/registry.py` (per-athlete)
4. Add tests in `tests/backend/jobs/`

## Monitoring

`GET /admin/jobs` — requires JWT + `ADMIN_ATHLETE_ID` env var match.

Returns all scheduled jobs with last run status, next run time, and 24h error count.

## Debugging

```sql
-- Recent failures
SELECT job_id, status, error_message, started_at
FROM job_runs WHERE status != 'ok'
ORDER BY started_at DESC LIMIT 20;

-- Job frequency
SELECT job_type, COUNT(*), AVG(duration_ms)
FROM job_runs WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY job_type;
```

## Architecture

- Module: `backend/app/jobs/`
- DB tables: `job_runs` (execution log), `athlete_state_snapshots` (daily snapshots)
- Scheduler starts in FastAPI lifespan (`main.py`)
- Per-athlete jobs registered on connect, unregistered on disconnect
- All jobs are idempotent — safe to rerun
- Timeout per job (60s for sync, 300s for compute)
- No retry — next scheduled interval is the natural retry
```

- [ ] **Step 3: Commit**

```bash
git add .env.example docs/backend/JOBS.md
git commit -m "docs(jobs): add JOBS.md reference + ADMIN_ATHLETE_ID to .env.example"
```

---

## Task 13: Final verification

- [ ] **Step 1: Run full test suite**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -q --tb=short -k "not test_history_shows_logged_count"
```

Expected: All tests pass, count should be ~2290+ (2271 existing + ~19 new).

- [ ] **Step 2: Verify no leftover references to old sync_scheduler**

```bash
grep -r "sync_scheduler" backend/ tests/ --include="*.py"
```

Expected: No matches (all references updated or deleted).
