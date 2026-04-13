# DB Migrations & Seed Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic seed data for dev and test environments, Poetry entry-point commands for all DB operations, a test DB lifecycle fixture, and comprehensive database documentation.

**Architecture:** Seed scripts live in `backend/scripts/` (importable via `pythonpath = ["backend"]`), exposed as `[project.scripts]` entry points via Poetry. Dev seed inserts two realistic athlete personas (Alice + Marc) with 6 weeks of history. Test seed inserts a minimal deterministic fixture. The `db_session` pytest fixture uses per-test savepoint rollback for full isolation against a separate test Postgres instance (port 5433).

**Tech Stack:** Python 3.13, SQLAlchemy 2.x, Alembic 1.13, passlib[bcrypt], PostgreSQL 16 (Docker), pytest 7.4.

---

## File Map

| File | Action |
|---|---|
| `docker-compose.yml` | Modify — add `db-test` service on port 5433 |
| `.gitignore` | Modify — add `*.db` entries |
| `backend/scripts/__init__.py` | Create — package marker |
| `backend/scripts/db_commands.py` | Create — `migrate()`, `seed_dev()`, `seed_test()`, `reset()` entry points |
| `backend/scripts/seed_data/__init__.py` | Create — package marker |
| `backend/scripts/seed_data/test_fixture.py` | Create — minimal deterministic fixture |
| `backend/scripts/seed_data/alice.py` | Create — Alice Dupont persona (recreational runner + lifting, female) |
| `backend/scripts/seed_data/marc.py` | Create — Marc Leblanc persona (competitive triathlete, male) |
| `pyproject.toml` | Modify — add `scripts` to packages, add 4 `[project.scripts]` entries |
| `tests/conftest.py` | Modify — add `db_engine`, `seed_db`, `db_session` fixtures |
| `tests/test_db/` | Create — integration tests for seed scripts |
| `tests/test_db/__init__.py` | Create — package marker |
| `tests/test_db/test_seed.py` | Create — integration tests (marked `db_integration`) |
| `docs/backend/DATABASE.md` | Create — schema, migration guide, seed guide, quickstart |

---

### Task 1: Infrastructure — docker-compose + .gitignore

**Files:**
- Modify: `docker-compose.yml`
- Modify: `.gitignore`

- [ ] **Step 1: Add `db-test` service to docker-compose.yml**

Open `docker-compose.yml`. It currently has `db` (port 5432) and `backend` and `frontend` services. Add the `db-test` service and update `volumes`:

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-resilio}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-resilio}
      POSTGRES_DB: ${POSTGRES_DB:-resilio_db}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U resilio -d resilio_db"]
      interval: 5s
      timeout: 5s
      retries: 5
    ports:
      - "5432:5432"

  db-test:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: resilio
      POSTGRES_PASSWORD: resilio
      POSTGRES_DB: resilio_test
    ports:
      - "5433:5432"
    tmpfs:
      - /var/lib/postgresql/data

  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app/backend
      - ./resilio:/app/resilio
      - ./.bmad-core:/app/.bmad-core
    environment:
      PYTHONPATH: /app/backend
      DATABASE_URL: postgresql+psycopg2://resilio:${POSTGRES_PASSWORD:-resilio}@db:5432/resilio_db
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      STRAVA_CLIENT_ID: ${STRAVA_CLIENT_ID:-}
      STRAVA_CLIENT_SECRET: ${STRAVA_CLIENT_SECRET:-}
      JWT_SECRET_KEY: ${JWT_SECRET_KEY:-dev-secret-change-in-production}
    depends_on:
      db:
        condition: service_healthy

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "4000:3000"
    volumes:
      - ./apps/web:/app
      - /app/node_modules
      - /app/.next
    environment:
      WATCHPACK_POLLING: "true"
    depends_on:
      - backend

volumes:
  postgres_data:
```

Note: `db-test` uses `tmpfs` (no volume) — ephemeral, wipes on container restart. No healthcheck needed for test use.

- [ ] **Step 2: Add `.db` entries to `.gitignore`**

Append to `.gitignore` (after the existing `# Resilio - LOCAL DATA` section):

```
# Local SQLite databases (should not exist, PostgreSQL is used, but just in case)
*.db
*.sqlite
data/resilio.db
```

- [ ] **Step 3: Verify docker-compose syntax**

```bash
cd C:\Users\simon\resilio-plus && docker compose config --quiet
```

Expected: no output (valid config). If Docker Desktop is not running, skip this step.

- [ ] **Step 4: Commit**

```bash
cd C:\Users\simon\resilio-plus && git add docker-compose.yml .gitignore && git commit -m "feat(infra): add db-test service and .gitignore db entries"
```

---

### Task 2: scripts/ package + Poetry entry points + db_commands.py

**Files:**
- Create: `backend/scripts/__init__.py`
- Create: `backend/scripts/seed_data/__init__.py`
- Create: `backend/scripts/db_commands.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Create package markers**

```bash
New-Item -ItemType Directory -Force C:\Users\simon\resilio-plus\backend\scripts\seed_data ; New-Item -ItemType File C:\Users\simon\resilio-plus\backend\scripts\__init__.py ; New-Item -ItemType File C:\Users\simon\resilio-plus\backend\scripts\seed_data\__init__.py
```

Both files remain empty.

- [ ] **Step 2: Write `backend/scripts/db_commands.py`**

```python
"""DB management entry points — exposed as Poetry scripts.

Commands:
  poetry run db-migrate     — alembic upgrade head
  poetry run db-seed        — insert dev seed data (Alice + Marc)
  poetry run db-seed-test   — insert minimal test fixture
  poetry run db-reset       — drop schema + migrate + seed-dev (requires --confirm)
"""
from __future__ import annotations

import os
import sys


def _require_db_url() -> str:
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg2://resilio:resilio@localhost:5432/resilio_db",
    )
    return url


def migrate() -> None:
    """Run alembic upgrade head."""
    from alembic.config import Config
    from alembic import command as alembic_cmd

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", _require_db_url())
    alembic_cmd.upgrade(cfg, "head")
    print("✓ Migrations applied.")


def seed_dev() -> None:
    """Insert dev seed data (Alice + Marc). Idempotent."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from scripts.seed_data.alice import insert_alice
    from scripts.seed_data.marc import insert_marc

    engine = create_engine(_require_db_url())
    with Session(engine) as session:
        insert_alice(session)
        insert_marc(session)
        session.commit()
    engine.dispose()
    print("✓ Dev seed data inserted (Alice + Marc).")


def seed_test() -> None:
    """Insert minimal test fixture. Idempotent."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from scripts.seed_data.test_fixture import insert_test_fixture

    url = os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+psycopg2://resilio:resilio@localhost:5433/resilio_test",
    )
    engine = create_engine(url)
    with Session(engine) as session:
        insert_test_fixture(session)
        session.commit()
    engine.dispose()
    print("✓ Test fixture inserted.")


def reset() -> None:
    """Drop schema + migrate + seed-dev. Requires --confirm flag."""
    if "--confirm" not in sys.argv:
        print(
            "ERROR: db-reset is destructive. Re-run with --confirm to proceed.\n"
            "  poetry run db-reset --confirm"
        )
        sys.exit(1)

    from sqlalchemy import create_engine, text

    url = _require_db_url()
    engine = create_engine(url)

    print("Dropping all tables...")
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.commit()
    engine.dispose()

    migrate()
    seed_dev()
    print("✓ Database reset complete.")
```

- [ ] **Step 3: Update `pyproject.toml`**

Add `scripts` package and four entry points. Modify two sections:

```toml
[tool.poetry]
packages = [{include = "resilio"}, {include = "scripts", from = "backend"}]
```

```toml
[project.scripts]
resilio = "resilio.cli:app"
db-migrate   = "scripts.db_commands:migrate"
db-seed      = "scripts.db_commands:seed_dev"
db-seed-test = "scripts.db_commands:seed_test"
db-reset     = "scripts.db_commands:reset"
```

- [ ] **Step 4: Reinstall to register entry points**

```bash
cd C:\Users\simon\resilio-plus && poetry install
```

Expected: installs cleanly, registers the 4 new entry points.

- [ ] **Step 5: Verify entry points are importable**

```bash
cd C:\Users\simon\resilio-plus && poetry run python -c "from scripts.db_commands import migrate, seed_dev, seed_test, reset; print('OK')"
```

Expected: `OK`

- [ ] **Step 6: Verify --confirm guard**

```bash
cd C:\Users\simon\resilio-plus && poetry run db-reset
```

Expected output:
```
ERROR: db-reset is destructive. Re-run with --confirm to proceed.
  poetry run db-reset --confirm
```
Expected exit code: 1.

- [ ] **Step 7: Commit**

```bash
cd C:\Users\simon\resilio-plus && git add backend/scripts/__init__.py backend/scripts/seed_data/__init__.py backend/scripts/db_commands.py pyproject.toml && git commit -m "feat(scripts): add db_commands entry points and scripts package"
```

---

### Task 3: Test fixture seed data + conftest.py db_session

**Files:**
- Create: `backend/scripts/seed_data/test_fixture.py`
- Modify: `tests/conftest.py`
- Create: `tests/test_db/__init__.py`
- Create: `tests/test_db/test_seed.py` (first test only — the fixture test)

- [ ] **Step 1: Create `backend/scripts/seed_data/test_fixture.py`**

```python
"""Minimal deterministic test fixture.

Inserts one user, one athlete, one training plan, three session logs,
one energy snapshot, and one allostatic entry. Idempotent.
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone

from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.db.models import (
    AthleteModel,
    ConnectorCredentialModel,
    SessionLogModel,
    TrainingPlanModel,
    UserModel,
)
from app.models.schemas import AllostaticEntryModel, EnergySnapshotModel

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

TEST_USER_EMAIL = "test@resilio.dev"
TEST_ATHLETE_ID = "athlete-test-001"
TEST_PLAN_ID = "plan-test-001"


def _athlete_exists(session: Session) -> bool:
    return session.get(AthleteModel, TEST_ATHLETE_ID) is not None


def insert_test_fixture(session: Session) -> None:
    """Insert minimal test fixture. Safe to call multiple times."""
    if _athlete_exists(session):
        return

    today = date(2026, 4, 13)

    # Athlete
    athlete = AthleteModel(
        id=TEST_ATHLETE_ID,
        name="Test Athlete",
        age=28,
        sex="F",
        weight_kg=60.0,
        height_cm=168.0,
        primary_sport="running",
        hours_per_week=8.0,
        sleep_hours_typical=7.5,
        stress_level=3,
        job_physical=False,
        vdot=42.0,
        coaching_mode="active",
        sports_json=json.dumps(["running", "lifting"]),
        goals_json=json.dumps(["marathon_sub4"]),
        available_days_json=json.dumps([1, 3, 5, 6]),
        equipment_json=json.dumps([]),
    )
    session.add(athlete)

    # User
    user = UserModel(
        id=str(uuid.uuid4()),
        email=TEST_USER_EMAIL,
        hashed_password=_pwd_ctx.hash("testpass"),
        athlete_id=TEST_ATHLETE_ID,
        created_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
    )
    session.add(user)

    # Training plan
    plan = TrainingPlanModel(
        id=TEST_PLAN_ID,
        athlete_id=TEST_ATHLETE_ID,
        start_date=date(2026, 4, 7),
        end_date=date(2026, 4, 13),
        phase="base",
        total_weekly_hours=8.0,
        acwr=1.05,
        weekly_slots_json=json.dumps([
            {"day": 1, "sport": "running", "duration_min": 60, "session_type": "easy"},
            {"day": 3, "sport": "lifting", "duration_min": 60, "session_type": "strength"},
            {"day": 5, "sport": "running", "duration_min": 90, "session_type": "long"},
        ]),
        status="active",
        created_at=datetime(2026, 4, 7, tzinfo=timezone.utc),
    )
    session.add(plan)

    # Session logs (1 completed, 1 skipped, 1 pending)
    session.add(SessionLogModel(
        id=str(uuid.uuid4()),
        athlete_id=TEST_ATHLETE_ID,
        plan_id=TEST_PLAN_ID,
        session_id="slot-mon-easy",
        actual_duration_min=62,
        skipped=False,
        rpe=6,
        notes="Felt good.",
        actual_data_json=json.dumps({}),
        logged_at=datetime(2026, 4, 7, 8, 0, tzinfo=timezone.utc),
    ))
    session.add(SessionLogModel(
        id=str(uuid.uuid4()),
        athlete_id=TEST_ATHLETE_ID,
        plan_id=TEST_PLAN_ID,
        session_id="slot-wed-lift",
        actual_duration_min=None,
        skipped=True,
        rpe=None,
        notes="Sick.",
        actual_data_json=json.dumps({}),
        logged_at=datetime(2026, 4, 9, 8, 0, tzinfo=timezone.utc),
    ))
    session.add(SessionLogModel(
        id=str(uuid.uuid4()),
        athlete_id=TEST_ATHLETE_ID,
        plan_id=TEST_PLAN_ID,
        session_id="slot-fri-long",
        actual_duration_min=None,
        skipped=False,
        rpe=None,
        notes="",
        actual_data_json=json.dumps({}),
        logged_at=datetime(2026, 4, 11, 8, 0, tzinfo=timezone.utc),
    ))

    # Energy snapshot
    session.add(EnergySnapshotModel(
        id=str(uuid.uuid4()),
        athlete_id=TEST_ATHLETE_ID,
        timestamp=datetime(2026, 4, 13, 7, 0, tzinfo=timezone.utc),
        allostatic_score=28.0,
        cognitive_load=20.0,
        energy_availability=42.0,
        sleep_quality=82.0,
        recommended_intensity_cap=1.0,
        veto_triggered=False,
        legs_feeling="normal",
        stress_level="none",
    ))

    # Allostatic entry
    session.add(AllostaticEntryModel(
        id=str(uuid.uuid4()),
        athlete_id=TEST_ATHLETE_ID,
        entry_date=today,
        allostatic_score=28.0,
        components_json=json.dumps({"hrv": 20.0, "sleep": 30.0, "work": 25.0}),
        intensity_cap_applied=1.0,
    ))
```

- [ ] **Step 2: Write failing test**

Create `tests/test_db/__init__.py` (empty) and `tests/test_db/test_seed.py`:

```python
"""Integration tests for seed scripts — require live PostgreSQL on port 5433.

Run with: pytest tests/test_db/ -v -m db_integration
Skip if TEST_DATABASE_URL is not available: tests auto-skip.
"""
from __future__ import annotations

import os

import pytest


_TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://resilio:resilio@localhost:5433/resilio_test",
)

pytestmark = pytest.mark.db_integration


@pytest.fixture(scope="module")
def test_engine():
    """Create test DB engine and apply migrations once for this module."""
    pytest.importorskip("psycopg2", reason="psycopg2 not available")
    from sqlalchemy import create_engine
    from alembic.config import Config
    from alembic import command as alembic_cmd

    engine = create_engine(_TEST_DB_URL)
    try:
        with engine.connect():
            pass
    except Exception:
        pytest.skip("Test PostgreSQL not available on port 5433")

    # Apply migrations
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", _TEST_DB_URL)
    alembic_cmd.upgrade(cfg, "head")

    yield engine

    # Teardown: wipe schema
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.commit()
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    """Per-test transactional session with savepoint rollback."""
    from sqlalchemy.orm import Session

    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    yield session

    session.close()
    transaction.rollback()
    connection.close()


def test_test_fixture_inserts_expected_rows(db_session):
    from scripts.seed_data.test_fixture import insert_test_fixture, TEST_ATHLETE_ID
    from app.db.models import AthleteModel, UserModel, TrainingPlanModel, SessionLogModel
    from app.models.schemas import EnergySnapshotModel, AllostaticEntryModel

    insert_test_fixture(db_session)
    db_session.flush()

    assert db_session.get(AthleteModel, TEST_ATHLETE_ID) is not None
    assert db_session.query(UserModel).filter_by(athlete_id=TEST_ATHLETE_ID).count() == 1
    assert db_session.query(TrainingPlanModel).filter_by(athlete_id=TEST_ATHLETE_ID).count() == 1
    assert db_session.query(SessionLogModel).filter_by(athlete_id=TEST_ATHLETE_ID).count() == 3
    assert db_session.query(EnergySnapshotModel).filter_by(athlete_id=TEST_ATHLETE_ID).count() == 1
    assert db_session.query(AllostaticEntryModel).filter_by(athlete_id=TEST_ATHLETE_ID).count() == 1


def test_test_fixture_is_idempotent(db_session):
    from scripts.seed_data.test_fixture import insert_test_fixture, TEST_ATHLETE_ID
    from app.db.models import AthleteModel

    insert_test_fixture(db_session)
    insert_test_fixture(db_session)  # second call — must not raise or duplicate
    db_session.flush()

    count = db_session.query(AthleteModel).filter_by(id=TEST_ATHLETE_ID).count()
    assert count == 1
```

- [ ] **Step 3: Run test to confirm it fails (module not found)**

```bash
cd C:\Users\simon\resilio-plus && /c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/test_db/test_seed.py -v -m db_integration 2>&1 | head -20
```

Expected: either `SKIPPED` (if test DB not running) or failure due to missing `test_fixture.py` import. The test_fixture.py was already created in Step 1, so expect `SKIPPED` if Docker not running, `FAILED` on assertion if Docker is running.

- [ ] **Step 4: Add `db_integration` marker to `pyproject.toml`**

Add to `[tool.pytest.ini_options]`:

```toml
[tool.pytest.ini_options]
pythonpath = ["backend"]
testpaths = ["tests"]
markers = [
    "db_integration: marks tests that require a live PostgreSQL test instance (port 5433)",
]
```

- [ ] **Step 5: Update root `tests/conftest.py`**

Append to the end of `tests/conftest.py` (do not remove existing fixtures):

```python
# ---------------------------------------------------------------------------
# DB integration fixtures (opt-in — only active when db_session is requested)
# ---------------------------------------------------------------------------

import os as _os

_TEST_DB_URL = _os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://resilio:resilio@localhost:5433/resilio_test",
)


@pytest.fixture(scope="session")
def _db_engine_session():
    """Create test DB engine once per session. Skip if DB not available."""
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(_TEST_DB_URL)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception:
        return None


@pytest.fixture(scope="session")
def db_engine(_db_engine_session):
    """Session-scoped engine with migrations applied. Skip if DB unavailable."""
    if _db_engine_session is None:
        pytest.skip("Test PostgreSQL not available")
    from alembic.config import Config
    from alembic import command as alembic_cmd
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", _TEST_DB_URL)
    alembic_cmd.upgrade(cfg, "head")
    yield _db_engine_session
    from sqlalchemy import text
    with _db_engine_session.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.commit()
    _db_engine_session.dispose()


@pytest.fixture(scope="session")
def _seed_db(db_engine):
    """Seed test fixture once per session."""
    from sqlalchemy.orm import Session
    from scripts.seed_data.test_fixture import insert_test_fixture
    with Session(db_engine) as session:
        insert_test_fixture(session)
        session.commit()


@pytest.fixture
def db_session(db_engine, _seed_db):
    """Per-test transactional session. Rolls back after each test."""
    from sqlalchemy.orm import Session
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    transaction.rollback()
    connection.close()
```

- [ ] **Step 6: Run existing test suite — confirm zero regressions**

```bash
cd C:\Users\simon\resilio-plus && /c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/ -q --ignore=tests/test_db 2>&1 | tail -5
```

Expected: ≥2021 passed, 0 failed.

- [ ] **Step 7: Commit**

```bash
cd C:\Users\simon\resilio-plus && git add backend/scripts/seed_data/test_fixture.py tests/conftest.py tests/test_db/__init__.py tests/test_db/test_seed.py pyproject.toml && git commit -m "feat(seed): add test fixture and db_session conftest fixture"
```

---

### Task 4: Alice persona seed data

**Files:**
- Create: `backend/scripts/seed_data/alice.py`

Alice Dupont — 28y female, Run + Lifting, marathon_sub4, 8h/week. Hormonal tracking enabled. 6 weeks history ending 2026-04-13. Recovery dip in week 4 (HRV drop, veto triggered). Elevated muscle strain in week 5.

- [ ] **Step 1: Create `backend/scripts/seed_data/alice.py`**

```python
"""Seed data — Alice Dupont (recreational runner + lifting, female).

6 weeks of history ending 2026-04-13:
  - Weeks 1-3: normal training (4 runs + 2 lifts/week)
  - Week 4: recovery dip (sleep 5.5h, HRV drop, veto triggered day 22)
  - Week 5: recovery, reduced load
  - Week 6 (current): back to normal
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta, timezone

from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.db.models import (
    AthleteModel,
    NutritionPlanModel,
    SessionLogModel,
    TrainingPlanModel,
    UserModel,
    WeeklyReviewModel,
)
from app.models.schemas import (
    AllostaticEntryModel,
    EnergySnapshotModel,
    HeadCoachMessageModel,
    HormonalProfileModel,
)

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALICE_ID = "athlete-alice-001"
ALICE_EMAIL = "alice@resilio.dev"
ALICE_PLAN_ID = "plan-alice-001"
REF_DATE = date(2026, 4, 13)
WEEK_START = REF_DATE - timedelta(days=REF_DATE.weekday())  # Monday 2026-04-07


def _id() -> str:
    return str(uuid.uuid4())


def _already_inserted(session: Session) -> bool:
    return session.get(AthleteModel, ALICE_ID) is not None


def insert_alice(session: Session) -> None:
    """Insert Alice persona. Idempotent."""
    if _already_inserted(session):
        return

    # --- Athlete ---
    athlete = AthleteModel(
        id=ALICE_ID,
        name="Alice Dupont",
        age=28,
        sex="F",
        weight_kg=60.0,
        height_cm=168.0,
        primary_sport="running",
        target_race_date=date(2026, 10, 18),
        hours_per_week=8.0,
        sleep_hours_typical=7.5,
        stress_level=3,
        job_physical=False,
        max_hr=188,
        resting_hr=52,
        vdot=44.0,
        coaching_mode="active",
        sports_json=json.dumps(["running", "lifting"]),
        goals_json=json.dumps(["marathon_sub4"]),
        available_days_json=json.dumps([1, 3, 5, 6]),
        equipment_json=json.dumps(["barbell", "dumbbells"]),
    )
    session.add(athlete)

    # --- User ---
    session.add(UserModel(
        id=_id(),
        email=ALICE_EMAIL,
        hashed_password=_pwd_ctx.hash("alice2026"),
        athlete_id=ALICE_ID,
        created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
    ))

    # --- Hormonal profile ---
    session.add(HormonalProfileModel(
        id=_id(),
        athlete_id=ALICE_ID,
        enabled=True,
        cycle_length_days=28,
        current_cycle_day=7,
        current_phase="follicular",
        last_period_start=date(2026, 4, 7),
        tracking_source="manual",
    ))

    # --- Training plan (current 6-week block) ---
    plan_start = REF_DATE - timedelta(days=41)  # ~6 weeks ago
    plan = TrainingPlanModel(
        id=ALICE_PLAN_ID,
        athlete_id=ALICE_ID,
        start_date=plan_start,
        end_date=REF_DATE + timedelta(days=7),
        phase="base",
        total_weekly_hours=8.0,
        acwr=1.08,
        weekly_slots_json=json.dumps([
            {"day": 1, "sport": "running", "duration_min": 60, "session_type": "easy"},
            {"day": 3, "sport": "lifting", "duration_min": 60, "session_type": "strength"},
            {"day": 4, "sport": "running", "duration_min": 50, "session_type": "tempo"},
            {"day": 5, "sport": "lifting", "duration_min": 55, "session_type": "strength"},
            {"day": 6, "sport": "running", "duration_min": 90, "session_type": "long"},
            {"day": 7, "sport": "running", "duration_min": 45, "session_type": "easy"},
        ]),
        status="active",
        created_at=datetime(2026, 3, 2, tzinfo=timezone.utc),
    )
    session.add(plan)

    # --- Nutrition plan ---
    session.add(NutritionPlanModel(
        id=_id(),
        athlete_id=ALICE_ID,
        weight_kg=60.0,
        targets_json=json.dumps({
            "protein_g": 108,
            "carbs_g_easy": 200,
            "carbs_g_hard": 300,
            "fat_g": 65,
            "calories_rest": 1800,
            "calories_training": 2300,
        }),
    ))

    # --- Session logs (6 weeks × ~6 sessions) ---
    # Week difficulty pattern: rpe 5-7 normal, rpe 8-9 hard week 3, rpe 4-5 recovery week 4
    _sessions = [
        # (days_ago, session_type, sport, duration_min, rpe, skipped)
        (41, "easy", "running", 58, 5, False),
        (39, "strength", "lifting", 62, 7, False),
        (38, "tempo", "running", 52, 7, False),
        (37, "strength", "lifting", 58, 6, False),
        (36, "long", "running", 92, 6, False),
        (35, "easy", "running", 44, 5, False),
        # Week 2
        (34, "easy", "running", 60, 6, False),
        (32, "strength", "lifting", 65, 7, False),
        (31, "tempo", "running", 51, 7, False),
        (30, "strength", "lifting", 60, 7, False),
        (29, "long", "running", 95, 6, False),
        (28, "easy", "running", 45, 5, False),
        # Week 3 — heavy
        (27, "easy", "running", 62, 6, False),
        (25, "strength", "lifting", 68, 8, False),
        (24, "tempo", "running", 54, 8, False),
        (23, "strength", "lifting", 65, 8, False),
        (22, "long", "running", 100, 8, False),
        (21, "easy", "running", 50, 6, False),
        # Week 4 — recovery dip (sleep issue, skips one session)
        (20, "easy", "running", 40, 5, False),
        (18, "strength", "lifting", 0, None, True),   # skipped — too tired
        (17, "tempo", "running", 30, 4, False),        # cut short
        (16, "strength", "lifting", 45, 5, False),
        (15, "long", "running", 60, 5, False),         # reduced from 90
        (14, "easy", "running", 35, 4, False),
        # Week 5 — recovery, squat focus
        (13, "easy", "running", 55, 5, False),
        (11, "strength", "lifting", 65, 7, False),
        (10, "tempo", "running", 50, 6, False),
        (9, "strength", "lifting", 70, 8, False),      # heavy squat day
        (8, "long", "running", 88, 6, False),
        (7, "easy", "running", 43, 5, False),
        # Week 6 (current)
        (6, "easy", "running", 60, 6, False),
        (4, "strength", "lifting", 63, 7, False),
        (3, "tempo", "running", 52, 7, False),
        (2, "strength", "lifting", 60, 7, False),
        (1, "long", "running", 90, 6, False),
    ]
    for days_ago, stype, sport, dur, rpe, skipped in _sessions:
        log_date = REF_DATE - timedelta(days=days_ago)
        session.add(SessionLogModel(
            id=_id(),
            athlete_id=ALICE_ID,
            plan_id=ALICE_PLAN_ID,
            session_id=f"alice-{log_date.isoformat()}-{stype}",
            actual_duration_min=dur if not skipped else None,
            skipped=skipped,
            rpe=rpe,
            notes="" if not skipped else "Skipped — fatigue",
            actual_data_json=json.dumps({}),
            logged_at=datetime(log_date.year, log_date.month, log_date.day, 9, 0, tzinfo=timezone.utc),
        ))

    # --- Allostatic entries (28 days) ---
    # Normal: 25-35, dip week 4 → peak 72, recovery
    _allostatic_scores = [
        28, 30, 29, 32, 31, 28, 27,   # days 28-22 (normal)
        35, 38, 42, 55, 68, 72, 65,   # days 21-15 (week 4 dip)
        55, 45, 38, 32, 30, 28, 27,   # days 14-8 (week 5 recovery)
        26, 28, 30, 29, 31, 28, 27,   # days 7-1 (week 6 normal)
    ]
    for i, score in enumerate(_allostatic_scores):
        entry_date = REF_DATE - timedelta(days=27 - i)
        cap = 0.6 if score > 65 else (0.8 if score > 50 else 1.0)
        session.add(AllostaticEntryModel(
            id=_id(),
            athlete_id=ALICE_ID,
            entry_date=entry_date,
            allostatic_score=float(score),
            components_json=json.dumps({
                "hrv": max(0.0, float(score - 10)),
                "sleep": float(score * 0.8),
                "work": 20.0,
                "stress": 15.0,
            }),
            intensity_cap_applied=cap,
        ))

    # --- Energy snapshots (14 days) ---
    _hrv_values = [62, 58, 55, 42, 38, 35, 40, 48, 55, 60, 62, 64, 65, 63]
    _sleep_values = [7.5, 7.2, 6.8, 5.5, 5.8, 6.0, 6.5, 7.0, 7.2, 7.5, 7.5, 7.3, 7.5, 7.2]
    for i in range(14):
        snap_date = REF_DATE - timedelta(days=13 - i)
        hrv = _hrv_values[i]
        slp = _sleep_values[i]
        allostatic = _allostatic_scores[14 + i]
        veto = hrv < 40 or slp < 6.0
        session.add(EnergySnapshotModel(
            id=_id(),
            athlete_id=ALICE_ID,
            timestamp=datetime(snap_date.year, snap_date.month, snap_date.day, 7, 0, tzinfo=timezone.utc),
            allostatic_score=float(allostatic),
            cognitive_load=20.0,
            energy_availability=40.0 if veto else 42.0,
            cycle_phase="follicular" if i >= 7 else "menstrual",
            sleep_quality=float(slp / 9.0 * 100),
            recommended_intensity_cap=0.6 if veto else 1.0,
            veto_triggered=veto,
            veto_reason="HRV below 70% baseline and sleep below 6h" if veto else None,
            legs_feeling="heavy" if allostatic > 60 else "normal",
            stress_level="none",
        ))

    # --- Weekly reviews (weeks 5 and 6) ---
    session.add(WeeklyReviewModel(
        id=_id(),
        athlete_id=ALICE_ID,
        plan_id=ALICE_PLAN_ID,
        week_start=REF_DATE - timedelta(days=13),
        week_number=5,
        planned_hours=8.0,
        actual_hours=6.5,
        acwr=0.92,
        readiness_score=72.0,
        hrv_rmssd=55.0,
        sleep_hours_avg=7.0,
        athlete_comment="Recovery week, felt better by Thursday.",
        results_json=json.dumps({"completed": 5, "skipped": 1}),
    ))
    session.add(WeeklyReviewModel(
        id=_id(),
        athlete_id=ALICE_ID,
        plan_id=ALICE_PLAN_ID,
        week_start=WEEK_START,
        week_number=6,
        planned_hours=8.0,
        actual_hours=7.5,
        acwr=1.08,
        readiness_score=84.0,
        hrv_rmssd=63.0,
        sleep_hours_avg=7.4,
        athlete_comment="Back on track.",
        results_json=json.dumps({"completed": 5, "skipped": 0}),
    ))

    # --- Head Coach message (recovery dip alert) ---
    session.add(HeadCoachMessageModel(
        id=_id(),
        athlete_id=ALICE_ID,
        pattern_type="reds_signal",
        message=(
            "HRV dropped to 35ms (−44% from baseline) and sleep averaged 5.8h "
            "over 3 consecutive nights. Intensity cap set to 60% for the next 48h. "
            "Prioritize sleep and reduce training volume this week."
        ),
        created_at=datetime(2026, 3, 27, 8, 0, tzinfo=timezone.utc),
        is_read=False,
    ))
```

- [ ] **Step 2: Add Alice test to `tests/test_db/test_seed.py`**

Append to `tests/test_db/test_seed.py`:

```python
def test_alice_inserts_expected_rows(db_session):
    from scripts.seed_data.alice import insert_alice, ALICE_ID
    from app.db.models import (
        AthleteModel, UserModel, TrainingPlanModel,
        SessionLogModel, WeeklyReviewModel, NutritionPlanModel,
    )
    from app.models.schemas import (
        AllostaticEntryModel, EnergySnapshotModel,
        HeadCoachMessageModel, HormonalProfileModel,
    )

    insert_alice(db_session)
    db_session.flush()

    assert db_session.get(AthleteModel, ALICE_ID) is not None
    assert db_session.query(UserModel).filter_by(athlete_id=ALICE_ID).count() == 1
    assert db_session.query(HormonalProfileModel).filter_by(athlete_id=ALICE_ID).count() == 1
    assert db_session.query(TrainingPlanModel).filter_by(athlete_id=ALICE_ID).count() == 1
    assert db_session.query(NutritionPlanModel).filter_by(athlete_id=ALICE_ID).count() == 1
    # 35 session logs (6 weeks × ~6 per week minus 1 skipped that still gets a row)
    assert db_session.query(SessionLogModel).filter_by(athlete_id=ALICE_ID).count() == 35
    assert db_session.query(AllostaticEntryModel).filter_by(athlete_id=ALICE_ID).count() == 28
    assert db_session.query(EnergySnapshotModel).filter_by(athlete_id=ALICE_ID).count() == 14
    assert db_session.query(WeeklyReviewModel).filter_by(athlete_id=ALICE_ID).count() == 2
    assert db_session.query(HeadCoachMessageModel).filter_by(athlete_id=ALICE_ID).count() == 1


def test_alice_is_idempotent(db_session):
    from scripts.seed_data.alice import insert_alice, ALICE_ID
    from app.db.models import AthleteModel

    insert_alice(db_session)
    insert_alice(db_session)
    db_session.flush()
    assert db_session.query(AthleteModel).filter_by(id=ALICE_ID).count() == 1
```

- [ ] **Step 3: Run tests (skip if Docker unavailable)**

```bash
cd C:\Users\simon\resilio-plus && /c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/test_db/test_seed.py::test_alice_inserts_expected_rows tests/test_db/test_seed.py::test_alice_is_idempotent -v -m db_integration 2>&1 | tail -10
```

Expected: PASSED (if Docker running on port 5433) or SKIPPED (if not).

- [ ] **Step 4: Commit**

```bash
cd C:\Users\simon\resilio-plus && git add backend/scripts/seed_data/alice.py tests/test_db/test_seed.py && git commit -m "feat(seed): add Alice Dupont persona (runner + lifting, 6 weeks history)"
```

---

### Task 5: Marc persona seed data

**Files:**
- Create: `backend/scripts/seed_data/marc.py`

Marc Leblanc — 34y male, Run + Bike + Swim, ironman_70_3, 12h/week. ACWR spike week 3. High HRV baseline. Fake Strava token.

- [ ] **Step 1: Create `backend/scripts/seed_data/marc.py`**

```python
"""Seed data — Marc Leblanc (competitive triathlete, male).

6 weeks of history ending 2026-04-13:
  - Weeks 1-2: base build
  - Week 3: ACWR spike (1.4 — caution), volume too high
  - Weeks 4-5: normalization
  - Week 6 (current): stable at 1.1
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta, timezone

from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.db.models import (
    AthleteModel,
    ConnectorCredentialModel,
    NutritionPlanModel,
    SessionLogModel,
    TrainingPlanModel,
    UserModel,
    WeeklyReviewModel,
)
from app.models.schemas import AllostaticEntryModel, EnergySnapshotModel

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

MARC_ID = "athlete-marc-001"
MARC_EMAIL = "marc@resilio.dev"
MARC_PLAN_ID = "plan-marc-001"
REF_DATE = date(2026, 4, 13)
WEEK_START = REF_DATE - timedelta(days=REF_DATE.weekday())


def _id() -> str:
    return str(uuid.uuid4())


def _already_inserted(session: Session) -> bool:
    return session.get(AthleteModel, MARC_ID) is not None


def insert_marc(session: Session) -> None:
    """Insert Marc persona. Idempotent."""
    if _already_inserted(session):
        return

    # --- Athlete ---
    athlete = AthleteModel(
        id=MARC_ID,
        name="Marc Leblanc",
        age=34,
        sex="M",
        weight_kg=75.0,
        height_cm=180.0,
        primary_sport="running",
        target_race_date=date(2026, 9, 7),
        hours_per_week=12.0,
        sleep_hours_typical=7.0,
        stress_level=4,
        job_physical=False,
        max_hr=182,
        resting_hr=46,
        ftp_watts=265,
        vdot=52.0,
        coaching_mode="active",
        sports_json=json.dumps(["running", "cycling", "swimming"]),
        goals_json=json.dumps(["ironman_70_3"]),
        available_days_json=json.dumps([1, 2, 3, 4, 5, 6, 7]),
        equipment_json=json.dumps(["road_bike", "wetsuit", "power_meter"]),
    )
    session.add(athlete)

    # --- User ---
    session.add(UserModel(
        id=_id(),
        email=MARC_EMAIL,
        hashed_password=_pwd_ctx.hash("marc2026"),
        athlete_id=MARC_ID,
        created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
    ))

    # --- Strava connector credential (fake token) ---
    session.add(ConnectorCredentialModel(
        id=_id(),
        athlete_id=MARC_ID,
        provider="strava",
        access_token="fake_strava_access_token_marc_dev_only",
        refresh_token="fake_strava_refresh_token_marc_dev_only",
        expires_at=1800000000,  # far future Unix timestamp
        extra_json=json.dumps({"athlete_id": 99999999, "scope": "activity:read_all"}),
    ))

    # --- Training plan ---
    plan_start = REF_DATE - timedelta(days=41)
    plan = TrainingPlanModel(
        id=MARC_PLAN_ID,
        athlete_id=MARC_ID,
        start_date=plan_start,
        end_date=REF_DATE + timedelta(days=7),
        phase="build",
        total_weekly_hours=12.0,
        acwr=1.10,
        weekly_slots_json=json.dumps([
            {"day": 1, "sport": "running", "duration_min": 60, "session_type": "easy"},
            {"day": 2, "sport": "cycling", "duration_min": 90, "session_type": "base"},
            {"day": 3, "sport": "swimming", "duration_min": 45, "session_type": "technique"},
            {"day": 4, "sport": "running", "duration_min": 75, "session_type": "tempo"},
            {"day": 5, "sport": "cycling", "duration_min": 75, "session_type": "intervals"},
            {"day": 6, "sport": "running", "duration_min": 100, "session_type": "long"},
            {"day": 7, "sport": "swimming", "duration_min": 50, "session_type": "endurance"},
        ]),
        status="active",
        created_at=datetime(2026, 3, 2, tzinfo=timezone.utc),
    )
    session.add(plan)

    # --- Nutrition plan ---
    session.add(NutritionPlanModel(
        id=_id(),
        athlete_id=MARC_ID,
        weight_kg=75.0,
        targets_json=json.dumps({
            "protein_g": 135,
            "carbs_g_easy": 280,
            "carbs_g_hard": 420,
            "fat_g": 80,
            "calories_rest": 2400,
            "calories_training": 3200,
        }),
    ))

    # --- Session logs (6 weeks × 7 sessions, some skipped) ---
    # Pattern: 7 sessions/week, week 3 is heavy (long rides + run brick)
    _sessions = [
        # Week 1
        (41, "easy", "running", 62, 5, False),
        (40, "base", "cycling", 88, 6, False),
        (39, "technique", "swimming", 44, 5, False),
        (38, "tempo", "running", 74, 7, False),
        (37, "intervals", "cycling", 72, 7, False),
        (36, "long", "running", 98, 6, False),
        (35, "endurance", "swimming", 52, 5, False),
        # Week 2
        (34, "easy", "running", 60, 5, False),
        (33, "base", "cycling", 92, 6, False),
        (32, "technique", "swimming", 45, 5, False),
        (31, "tempo", "running", 76, 7, False),
        (30, "intervals", "cycling", 78, 8, False),
        (29, "long", "running", 105, 7, False),
        (28, "endurance", "swimming", 50, 6, False),
        # Week 3 — ACWR spike (volume surge)
        (27, "easy", "running", 70, 6, False),
        (26, "base", "cycling", 120, 7, False),   # +30min
        (25, "technique", "swimming", 60, 6, False),
        (24, "tempo", "running", 85, 8, False),
        (23, "intervals", "cycling", 95, 9, False),
        (22, "long", "running", 130, 8, False),    # +30min
        (21, "endurance", "swimming", 65, 7, False),
        # Week 4 — back off
        (20, "easy", "running", 55, 5, False),
        (19, "base", "cycling", 80, 6, False),
        (18, "technique", "swimming", 40, 5, False),
        (17, "tempo", "running", 65, 6, False),
        (16, "intervals", "cycling", 0, None, True),  # skipped — rest day
        (15, "long", "running", 90, 6, False),
        (14, "endurance", "swimming", 48, 5, False),
        # Week 5 — normalization
        (13, "easy", "running", 60, 6, False),
        (12, "base", "cycling", 88, 6, False),
        (11, "technique", "swimming", 44, 5, False),
        (10, "tempo", "running", 75, 7, False),
        (9, "intervals", "cycling", 75, 7, False),
        (8, "long", "running", 100, 7, False),
        (7, "endurance", "swimming", 50, 6, False),
        # Week 6 (current)
        (6, "easy", "running", 62, 6, False),
        (5, "base", "cycling", 90, 6, False),
        (4, "technique", "swimming", 45, 5, False),
        (3, "tempo", "running", 76, 7, False),
        (2, "intervals", "cycling", 76, 7, False),
        (1, "long", "running", 102, 7, False),
    ]
    for days_ago, stype, sport, dur, rpe, skipped in _sessions:
        log_date = REF_DATE - timedelta(days=days_ago)
        session.add(SessionLogModel(
            id=_id(),
            athlete_id=MARC_ID,
            plan_id=MARC_PLAN_ID,
            session_id=f"marc-{log_date.isoformat()}-{stype}",
            actual_duration_min=dur if not skipped else None,
            skipped=skipped,
            rpe=rpe,
            notes="" if not skipped else "Planned rest — high ACWR",
            actual_data_json=json.dumps({}),
            logged_at=datetime(log_date.year, log_date.month, log_date.day, 7, 30, tzinfo=timezone.utc),
        ))

    # --- Allostatic entries (28 days) — stable, mild spike week 3 ---
    _allostatic_scores = [
        28, 30, 29, 30, 32, 30, 28,   # days 28-22 (stable)
        35, 40, 45, 42, 38, 35, 32,   # days 21-15 (week 3 spike, mild)
        30, 28, 28, 27, 29, 28, 27,   # days 14-8 (normal)
        28, 30, 29, 31, 30, 28, 27,   # days 7-1 (current week)
    ]
    for i, score in enumerate(_allostatic_scores):
        entry_date = REF_DATE - timedelta(days=27 - i)
        session.add(AllostaticEntryModel(
            id=_id(),
            athlete_id=MARC_ID,
            entry_date=entry_date,
            allostatic_score=float(score),
            components_json=json.dumps({
                "hrv": max(0.0, float(score - 8)),
                "sleep": float(score * 0.75),
                "work": 18.0,
                "stress": 12.0,
            }),
            intensity_cap_applied=0.9 if score > 42 else 1.0,
        ))

    # --- Energy snapshots (14 days) ---
    _hrv_values = [70, 68, 65, 62, 58, 62, 65, 68, 70, 71, 70, 72, 71, 70]
    _sleep_values = [7.2, 7.0, 6.8, 7.0, 6.5, 7.0, 7.2, 7.2, 7.3, 7.0, 7.2, 7.1, 7.0, 7.2]
    for i in range(14):
        snap_date = REF_DATE - timedelta(days=13 - i)
        slp = _sleep_values[i]
        allostatic = _allostatic_scores[14 + i]
        session.add(EnergySnapshotModel(
            id=_id(),
            athlete_id=MARC_ID,
            timestamp=datetime(snap_date.year, snap_date.month, snap_date.day, 6, 30, tzinfo=timezone.utc),
            allostatic_score=float(allostatic),
            cognitive_load=18.0,
            energy_availability=48.0,
            cycle_phase=None,
            sleep_quality=float(slp / 9.0 * 100),
            recommended_intensity_cap=0.9 if allostatic > 42 else 1.0,
            veto_triggered=False,
            legs_feeling="normal",
            stress_level="none",
        ))

    # --- Weekly reviews ---
    session.add(WeeklyReviewModel(
        id=_id(),
        athlete_id=MARC_ID,
        plan_id=MARC_PLAN_ID,
        week_start=REF_DATE - timedelta(days=13),
        week_number=5,
        planned_hours=12.0,
        actual_hours=11.5,
        acwr=1.12,
        readiness_score=80.0,
        hrv_rmssd=68.0,
        sleep_hours_avg=7.1,
        athlete_comment="Good week. Legs felt heavy Tuesday but recovered by Thursday.",
        results_json=json.dumps({"completed": 6, "skipped": 1}),
    ))
    session.add(WeeklyReviewModel(
        id=_id(),
        athlete_id=MARC_ID,
        plan_id=MARC_PLAN_ID,
        week_start=WEEK_START,
        week_number=6,
        planned_hours=12.0,
        actual_hours=11.8,
        acwr=1.10,
        readiness_score=85.0,
        hrv_rmssd=70.0,
        sleep_hours_avg=7.1,
        athlete_comment="Strong week. Bike power up 8W vs last month.",
        results_json=json.dumps({"completed": 6, "skipped": 0}),
    ))
```

- [ ] **Step 2: Add Marc test to `tests/test_db/test_seed.py`**

Append to `tests/test_db/test_seed.py`:

```python
def test_marc_inserts_expected_rows(db_session):
    from scripts.seed_data.marc import insert_marc, MARC_ID
    from app.db.models import (
        AthleteModel, UserModel, TrainingPlanModel,
        SessionLogModel, WeeklyReviewModel, ConnectorCredentialModel,
    )
    from app.models.schemas import AllostaticEntryModel, EnergySnapshotModel

    insert_marc(db_session)
    db_session.flush()

    assert db_session.get(AthleteModel, MARC_ID) is not None
    assert db_session.query(UserModel).filter_by(athlete_id=MARC_ID).count() == 1
    assert db_session.query(ConnectorCredentialModel).filter_by(athlete_id=MARC_ID).count() == 1
    assert db_session.query(TrainingPlanModel).filter_by(athlete_id=MARC_ID).count() == 1
    # 41 session logs (6 weeks: 7+7+7+7+7+6 sessions)
    assert db_session.query(SessionLogModel).filter_by(athlete_id=MARC_ID).count() == 41
    assert db_session.query(AllostaticEntryModel).filter_by(athlete_id=MARC_ID).count() == 28
    assert db_session.query(EnergySnapshotModel).filter_by(athlete_id=MARC_ID).count() == 14
    assert db_session.query(WeeklyReviewModel).filter_by(athlete_id=MARC_ID).count() == 2


def test_marc_is_idempotent(db_session):
    from scripts.seed_data.marc import insert_marc, MARC_ID
    from app.db.models import AthleteModel

    insert_marc(db_session)
    insert_marc(db_session)
    db_session.flush()
    assert db_session.query(AthleteModel).filter_by(id=MARC_ID).count() == 1


def test_seed_dev_inserts_both_athletes(db_session):
    """seed_dev inserts Alice and Marc without errors."""
    from scripts.seed_data.alice import insert_alice, ALICE_ID
    from scripts.seed_data.marc import insert_marc, MARC_ID
    from app.db.models import AthleteModel

    insert_alice(db_session)
    insert_marc(db_session)
    db_session.flush()

    assert db_session.query(AthleteModel).filter_by(id=ALICE_ID).count() == 1
    assert db_session.query(AthleteModel).filter_by(id=MARC_ID).count() == 1


def test_db_reset_guard_requires_confirm(monkeypatch):
    """reset() exits with code 1 if --confirm not in argv."""
    import sys
    monkeypatch.setattr(sys, "argv", ["db-reset"])  # no --confirm
    with pytest.raises(SystemExit) as exc_info:
        from scripts.db_commands import reset
        reset()
    assert exc_info.value.code == 1
```

- [ ] **Step 3: Run all DB tests (skip if Docker unavailable)**

```bash
cd C:\Users\simon\resilio-plus && /c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/test_db/ -v -m db_integration 2>&1 | tail -15
```

Expected: all PASSED or SKIPPED (if test DB not running). The `test_db_reset_guard_requires_confirm` test does NOT require a DB and should always PASS.

- [ ] **Step 4: Run full suite — confirm no regressions**

```bash
cd C:\Users\simon\resilio-plus && /c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/ -q --ignore=tests/test_db 2>&1 | tail -5
```

Expected: ≥2021 passed, 0 failed.

- [ ] **Step 5: Commit**

```bash
cd C:\Users\simon\resilio-plus && git add backend/scripts/seed_data/marc.py tests/test_db/test_seed.py && git commit -m "feat(seed): add Marc Leblanc persona (triathlete, 6 weeks history) and seed tests"
```

---

### Task 6: DATABASE.md documentation

**Files:**
- Create: `docs/backend/DATABASE.md`

- [ ] **Step 1: Create `docs/backend/DATABASE.md`**

```markdown
# Database — Architecture, Conventions & Operations

**Engine:** PostgreSQL 16 (Docker Compose)
**ORM:** SQLAlchemy 2.x
**Migrations:** Alembic 1.13
**Current head:** `0005_energy_patterns`

---

## Schema Overview

13 tables across two model files:

### Core tables (`backend/app/db/models.py`)

| Table | Purpose |
|---|---|
| `users` | Auth credentials — email, hashed_password, athlete_id FK |
| `athletes` | Athlete profile — demographics, sports, goals, coaching mode |
| `training_plans` | Weekly training plans with JSON slot structure |
| `nutrition_plans` | Macro targets per athlete |
| `weekly_reviews` | Post-week summaries — actual hours, ACWR, HRV, notes |
| `connector_credentials` | OAuth tokens for Strava, Hevy, Terra |
| `session_logs` | Individual session results — RPE, duration, notes |

### V3 tables (`backend/app/models/schemas.py`)

| Table | Purpose |
|---|---|
| `energy_snapshots` | Daily Energy Coach output — allostatic score, veto, intensity cap |
| `hormonal_profiles` | Cycle tracking (1:1 with athletes) |
| `allostatic_entries` | 28-day rolling allostatic history |
| `external_plans` | Plans imported from file (tracking_only mode) |
| `external_sessions` | Individual sessions from external plans |
| `head_coach_messages` | Proactive coaching messages from pattern detection |

### FK relationships (simplified)

```
athletes ──< users (1:1)
athletes ──< training_plans
athletes ──< nutrition_plans
athletes ──< weekly_reviews ──> training_plans
athletes ──< connector_credentials (UC: athlete_id, provider)
athletes ──< session_logs ──> training_plans, external_sessions
athletes ──< energy_snapshots
athletes ──1 hormonal_profiles
athletes ──< allostatic_entries (UC: athlete_id, entry_date)
athletes ──< external_plans ──< external_sessions
athletes ──< head_coach_messages
```

---

## Migration History

| Revision | Description |
|---|---|
| `0001` | Initial schema — core 7 tables |
| `0002` | V3 energy tracking — energy_snapshots, hormonal_profiles, allostatic_entries |
| `0003` | Coaching mode + external plans — external_plans, external_sessions |
| `0004` | Energy scoring — adds objective_score, subjective_score to energy_snapshots |
| `0005` | Pattern detection — adds legs_feeling, stress_level; creates head_coach_messages |

---

## Creating a New Migration

1. Modify a SQLAlchemy model in `backend/app/db/models.py` or `backend/app/models/schemas.py`

2. Generate the migration:
   ```bash
   alembic revision --autogenerate -m "describe_your_change"
   ```
   This creates `alembic/versions/XXXX_describe_your_change.py`

3. **Always review the generated file.** Autogenerate misses: renamed columns, custom constraints, partial indexes. Edit if needed.

4. Test upgrade:
   ```bash
   poetry run db-migrate
   ```

5. Test downgrade:
   ```bash
   alembic downgrade -1
   alembic upgrade head
   ```

6. Commit the migration file with the model change in the same commit.

---

## DB Commands

| Command | What it does |
|---|---|
| `poetry run db-migrate` | Apply pending migrations (`alembic upgrade head`) |
| `poetry run db-seed` | Insert dev personas (Alice + Marc) — idempotent |
| `poetry run db-seed-test` | Insert minimal test fixture against TEST_DATABASE_URL |
| `poetry run db-reset --confirm` | **DESTRUCTIVE** — drop schema + migrate + seed-dev |

---

## Docker Compose Quickstart (new machine)

```bash
# 1. Start PostgreSQL
docker compose up db -d

# 2. Apply migrations
poetry run db-migrate

# 3. Seed dev data
poetry run db-seed

# App is ready. Start backend:
docker compose up backend
```

For tests (separate DB on port 5433):
```bash
docker compose up db-test -d
TEST_DATABASE_URL=postgresql+psycopg2://resilio:resilio@localhost:5433/resilio_test \
  pytest tests/test_db/ -m db_integration -v
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg2://resilio:resilio@localhost:5432/resilio_db` | Dev/prod DB |
| `TEST_DATABASE_URL` | `postgresql+psycopg2://resilio:resilio@localhost:5433/resilio_test` | Test DB (port 5433) |

Both variables are read by `db_commands.py`. `alembic.ini` has the dev default hardcoded as fallback.
```

- [ ] **Step 2: Verify full test suite still clean**

```bash
cd C:\Users\simon\resilio-plus && /c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/ -q --ignore=tests/test_db 2>&1 | tail -5
```

Expected: ≥2021 passed, 0 failed.

- [ ] **Step 3: Commit**

```bash
cd C:\Users\simon\resilio-plus && git add docs/backend/DATABASE.md && git commit -m "docs(backend): add DATABASE.md — schema, migration guide, seed guide, quickstart"
```

---

## Self-Review Checklist (for executor)

After completing all tasks, verify:

- [ ] `poetry install` succeeds
- [ ] `poetry run db-reset` (no flag) exits with code 1 and clear message
- [ ] `poetry run db-migrate` completes against local dev DB
- [ ] `poetry run db-seed` completes idempotently (run twice, no errors)
- [ ] `pytest tests/ --ignore=tests/test_db -q` shows ≥2021 passed, 0 failed
- [ ] `pytest tests/test_db/test_seed.py::test_db_reset_guard_requires_confirm -v` PASSES (no DB required)
- [ ] `docker compose config --quiet` valid
- [ ] `docs/backend/DATABASE.md` exists
- [ ] `docs/backend/STRAIN-DEFINITION.md` still exists (no regressions)
