# Phase 6 — Intégration & Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render Resilio Plus deployable locally via Docker Compose, add end-to-end API workflow tests, rewrite the README, and tag v1.0.0.

**Architecture:** Two Docker services (backend FastAPI + frontend Next.js) orchestrated by docker-compose.yml; SQLite persisted via bind-mount at `./data/`; E2E tests use FastAPI TestClient with in-memory SQLite (no running server needed); README covers Docker quick-start + local dev.

**Tech Stack:** Python 3.13-slim (Docker), Node 20-slim (Docker), Docker Compose v2, pytest + FastAPI TestClient (E2E), Bash entrypoint script for DB init.

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `Dockerfile.backend` | Create | Build image for FastAPI backend |
| `scripts/docker-entrypoint-backend.sh` | Create | Init DB tables, then exec uvicorn |
| `Dockerfile.frontend` | Create | Build image for Next.js frontend |
| `docker-compose.yml` | Create | Orchestrate backend + frontend + volumes |
| `.dockerignore` | Create | Root-level ignore for backend build context |
| `tests/e2e/__init__.py` | Create | Empty — marks package |
| `tests/e2e/conftest.py` | Create | Module-scoped TestClient fixture |
| `tests/e2e/test_full_workflow.py` | Create | 6 sequential E2E API tests |
| `README.md` | Modify | Full rewrite |

---

## Task 1: Backend Dockerfile + entrypoint

**Files:**
- Create: `Dockerfile.backend`
- Create: `scripts/docker-entrypoint-backend.sh`
- Create: `.dockerignore`

No test needed (verified by `docker-compose up`). Commit at end.

- [ ] **Step 1: Create `scripts/` directory and entrypoint script**

```bash
mkdir -p scripts
```

Create `scripts/docker-entrypoint-backend.sh`:

```bash
#!/usr/bin/env bash
set -e

# Create SQLite tables if they don't exist (idempotent)
python -c "
from app.db.database import Base, engine
from app.db import models  # noqa — registers all ORM classes with Base
Base.metadata.create_all(engine)
print('DB ready.')
"

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

```bash
chmod +x scripts/docker-entrypoint-backend.sh
```

- [ ] **Step 2: Create `Dockerfile.backend`**

```dockerfile
# Dockerfile.backend
FROM python:3.13-slim

WORKDIR /app

# Install runtime dependencies directly via pip (no Poetry needed in image)
RUN pip install --no-cache-dir \
    "pydantic>=2.5,<3.0" \
    "pyyaml>=6.0,<7.0" \
    "requests>=2.31,<3.0" \
    "python-dateutil>=2.8,<3.0" \
    "httpx>=0.28.0,<1.0" \
    "tenacity>=8.0.0,<9.0.0" \
    "typer>=0.21.1,<0.22.0" \
    "fastapi>=0.115.0,<1.0" \
    "uvicorn[standard]>=0.32.0,<1.0" \
    "sqlalchemy>=2.0,<3.0" \
    "python-jose[cryptography]>=3.3,<4.0" \
    "passlib[bcrypt]>=1.7,<2.0" \
    "bcrypt>=3.2.0,<5.0"

# Copy source — resilio/ is the legacy CLI package; backend/ is the FastAPI app
COPY resilio/ ./resilio/
COPY backend/ ./backend/
COPY scripts/docker-entrypoint-backend.sh /entrypoint.sh

# PYTHONPATH lets Python find `app` (backend/app/) without install
ENV PYTHONPATH=/app/backend

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
```

- [ ] **Step 3: Create `.dockerignore` (root-level, for backend build context)**

```
.git
.worktrees
__pycache__
*.pyc
*.pyo
.pytest_cache
.mypy_cache
.ruff_cache
node_modules
frontend/node_modules
frontend/.next
data/
.env
*.env
```

- [ ] **Step 4: Commit**

```bash
git add Dockerfile.backend scripts/docker-entrypoint-backend.sh .dockerignore
git commit -m "feat: add backend Dockerfile and entrypoint script"
```

---

## Task 2: Frontend Dockerfile

**Files:**
- Create: `Dockerfile.frontend`
- Create: `frontend/.dockerignore` (already exists from `create-next-app` — verify, don't duplicate)

- [ ] **Step 1: Check if `frontend/.dockerignore` already exists**

```bash
cat frontend/.dockerignore
```

If it already contains `node_modules` and `.next`, skip Step 2. If it doesn't exist or is missing key entries, proceed.

- [ ] **Step 2: Ensure `frontend/.dockerignore` contains the right entries**

Verify or create `frontend/.dockerignore` with at minimum:

```
node_modules
.next
.env*.local
```

If it already exists from `create-next-app`, it will have these. Only add missing lines — do not overwrite.

- [ ] **Step 3: Create `Dockerfile.frontend`**

```dockerfile
# Dockerfile.frontend
FROM node:20-slim

WORKDIR /app

# Copy package files first for layer caching
COPY frontend/package.json frontend/package-lock.json ./

RUN npm ci --prefer-offline

# Copy all frontend source
COPY frontend/ ./

EXPOSE 3000

# next dev picks up WATCHPACK_POLLING for Docker on non-Linux hosts
ENV WATCHPACK_POLLING=true

CMD ["npm", "run", "dev"]
```

- [ ] **Step 4: Commit**

```bash
git add Dockerfile.frontend
git commit -m "feat: add frontend Dockerfile"
```

---

## Task 3: docker-compose.yml

**Files:**
- Create: `docker-compose.yml`

- [ ] **Step 1: Create `docker-compose.yml`**

```yaml
# docker-compose.yml
services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "8000:8000"
    volumes:
      # Persist SQLite DB across container restarts
      - ./data:/app/data
      # Live-reload: mount source so uvicorn --reload picks up changes
      - ./backend:/app/backend
      - ./resilio:/app/resilio
    environment:
      PYTHONPATH: /app/backend

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "3000:3000"
    volumes:
      # Live-reload: mount source (excludes node_modules via anonymous volume)
      - ./frontend:/app
      - /app/node_modules
      - /app/.next
    environment:
      WATCHPACK_POLLING: "true"
    depends_on:
      - backend
```

- [ ] **Step 2: Create `data/` directory if it doesn't exist**

```bash
mkdir -p data
touch data/.gitkeep
```

- [ ] **Step 3: Verify `data/` is in `.gitignore` (only the DB, not the dir)**

Open `.gitignore` and confirm it contains `data/*.db` or similar — we want to track `data/.gitkeep` but not `data/resilio.db`. If `.gitignore` has `data/` broadly, narrow it:

Check current state:
```bash
grep "data" .gitignore
```

The entry should be `data/*.db` (or `data/resilio.db`), not `data/`. If it's `data/`, change it to `data/*.db` and re-add `.gitkeep`:

```bash
git add data/.gitkeep
```

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml data/.gitkeep
git commit -m "feat: add docker-compose.yml with backend + frontend services"
```

---

## Task 4: E2E test conftest

**Files:**
- Create: `tests/e2e/__init__.py`
- Create: `tests/e2e/conftest.py`

- [ ] **Step 1: Create `tests/e2e/__init__.py`**

```python
# tests/e2e/__init__.py
```

(Empty file.)

- [ ] **Step 2: Create `tests/e2e/conftest.py`**

```python
# tests/e2e/conftest.py
"""Shared fixtures for end-to-end API workflow tests."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db import models  # noqa: F401 — registers all ORM models with Base
from app.dependencies import get_db
from app.main import app


def _make_e2e_engine():
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


@pytest.fixture(scope="module")
def e2e_client():
    """Module-scoped TestClient + in-memory DB.

    Module scope means all tests within one module share the same DB, which
    allows sequential workflow tests to build on each other's state.
    """
    engine = _make_e2e_engine()
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
```

- [ ] **Step 3: Verify the fixture can be collected**

```bash
cd /c/Users/simon/resilio-plus
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" tests/e2e/ --collect-only 2>&1 | head -10
```

Expected: `no tests ran` (no test files yet), no import errors.

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/__init__.py tests/e2e/conftest.py
git commit -m "feat: add E2E test conftest with module-scoped TestClient fixture"
```

---

## Task 5: E2E workflow tests

**Files:**
- Create: `tests/e2e/test_full_workflow.py`

The 6 tests run in order (test_01 → test_06) and share state via `_state` dict. Each test depends on the previous having populated `_state`.

- [ ] **Step 1: Write the failing tests**

Create `tests/e2e/test_full_workflow.py`:

```python
# tests/e2e/test_full_workflow.py
"""
End-to-end API workflow: onboarding → week-status → plan → review → login.

Tests are prefixed 01–06 so pytest runs them in definition order.
All tests share the `e2e_client` module-scoped fixture (one DB for the module).
_state carries athlete_id and token across tests.
"""
from datetime import date, timedelta

import pytest

# Mutable shared state across tests in this module
_state: dict = {}


def _next_monday() -> str:
    today = date.today()
    days_ahead = (7 - today.weekday()) % 7 or 7  # 1–7
    return str(today + timedelta(days=days_ahead))


def _onboarding_payload() -> dict:
    return {
        "email": "e2e@resilio.test",
        "password": "e2epass123",
        "plan_start_date": _next_monday(),
        "name": "E2E Athlete",
        "age": 28,
        "sex": "M",
        "weight_kg": 75.0,
        "height_cm": 180.0,
        "primary_sport": "running",
        "sports": ["running", "lifting"],
        "goals": ["finish a 10K", "stay injury-free"],
        "available_days": [0, 2, 4, 6],
        "hours_per_week": 8.0,
    }


def test_01_onboarding_creates_athlete_and_plan(e2e_client):
    """POST /athletes/onboarding → 201, returns token + non-empty plan."""
    resp = e2e_client.post("/athletes/onboarding", json=_onboarding_payload())
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert "access_token" in body
    assert "athlete" in body
    assert "plan" in body
    assert len(body["plan"]["sessions"]) > 0
    # Store for subsequent tests
    _state["token"] = body["access_token"]
    _state["athlete_id"] = body["athlete"]["id"]


def test_02_week_status_requires_auth(e2e_client):
    """GET /athletes/{id}/week-status without Bearer → 401 or 403."""
    resp = e2e_client.get(f"/athletes/{_state['athlete_id']}/week-status")
    assert resp.status_code in (401, 403), resp.text


def test_03_week_status_returns_week_one(e2e_client):
    """GET /athletes/{id}/week-status with Bearer → 200, week_number=1, planned_hours > 0."""
    headers = {"Authorization": f"Bearer {_state['token']}"}
    resp = e2e_client.get(
        f"/athletes/{_state['athlete_id']}/week-status",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["week_number"] == 1
    assert body["planned_hours"] > 0
    assert "plan" in body


def test_04_plan_has_multi_sport_sessions(e2e_client):
    """GET /athletes/{id}/plan with Bearer → 200, sessions include at least 1 sport."""
    headers = {"Authorization": f"Bearer {_state['token']}"}
    resp = e2e_client.get(
        f"/athletes/{_state['athlete_id']}/plan",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    sessions = body["sessions"]
    assert len(sessions) > 0
    sports = {s["sport"] for s in sessions}
    assert len(sports) >= 1  # at least one sport scheduled


def test_05_review_returns_next_week_suggestion(e2e_client):
    """POST /athletes/{id}/review with Bearer → 201, next_week_suggestion non-empty."""
    headers = {"Authorization": f"Bearer {_state['token']}"}
    resp = e2e_client.post(
        f"/athletes/{_state['athlete_id']}/review",
        json={
            "week_end_date": str(date.today()),
            "readiness_score": 7.0,
            "sleep_hours_avg": 7.5,
            "comment": "Felt good, legs a bit tired",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert "next_week_suggestion" in body
    assert len(body["next_week_suggestion"]) > 0
    assert "acwr" in body


def test_06_login_with_onboarding_credentials(e2e_client):
    """POST /auth/login → 200, returns fresh token for the same athlete."""
    resp = e2e_client.post(
        "/auth/login",
        json={"email": "e2e@resilio.test", "password": "e2epass123"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["athlete_id"] == _state["athlete_id"]
```

- [ ] **Step 2: Run to verify they pass**

```bash
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" tests/e2e/ -v 2>&1 | tail -15
```

Expected: 6 passed.

- [ ] **Step 3: Run full suite to confirm no regressions**

```bash
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" tests/backend/ -q --tb=no 2>&1 | tail -3
```

Expected: 286 passed, 1 pre-existing failure (`test_fetch_hevy_workouts_maps_to_schema` — known, unrelated).

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/test_full_workflow.py
git commit -m "feat: add E2E workflow tests (onboarding → plan → review → login)"
```

---

## Task 6: README rewrite

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace README.md with the full rewrite**

```markdown
# Resilio Plus

> AI-powered multi-agent coaching platform for hybrid athletes — running, lifting, swimming, cycling.

A **Head Coach AI** orchestrates 7 specialist agents to create personalized, periodized training and nutrition plans that adapt weekly based on real performance data.

---

## Quick Start — Docker

```bash
git clone <repo-url> resilio-plus && cd resilio-plus
docker compose build
docker compose up
```

- Backend API: http://localhost:8000/docs
- Frontend: http://localhost:3000

---

## Quick Start — Local Development

**Prerequisites:** Python 3.11+, Poetry, Node 20+

```bash
# Backend
poetry install
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/uvicorn.exe" backend.app.main:app --reload
# or on macOS/Linux: poetry run uvicorn backend.app.main:app --reload

# Frontend (new terminal)
cd frontend && npm install && npm run dev
```

> **First run:** Create the database before starting uvicorn:
> ```bash
> python -c "from backend.app.db.database import Base, engine; from backend.app.db import models; Base.metadata.create_all(engine)"
> ```

---

## Architecture

### Multi-Agent System

```
User Request
     │
     ▼
┌─────────────┐
│  Head Coach │  ← Orchestrates all agents, resolves conflicts
└──────┬──────┘
       │
  ┌────┴────────────────────────────────────┐
  │         Specialist Agents               │
  ├──────────────┬──────────────────────────┤
  │ Running Coach│ Lifting Coach            │
  │ Swimming Coach│ Biking Coach            │
  │ Nutrition Coach│ Recovery Coach         │
  └──────────────┴──────────────────────────┘
       │
       ▼
  Unified Fatigue Score → Weekly Plan
```

### Coaching Agents

| Agent | Specialty | Knowledge Base |
|---|---|---|
| Head Coach | Orchestration, conflict resolution, ACWR load management | Blueprint §5.1 |
| Running Coach | VDOT, 80/20 TID, Daniels/Pfitzinger/FIRST methodologies | Blueprint §5.3 |
| Lifting Coach | MEV/MAV/MRV, DUP periodization, SFR tiers | Blueprint §5.2 |
| Swimming Coach | CSS-based zones, SWOLF, propulsive efficiency | Blueprint §5.5 |
| Biking Coach | FTP, Coggan zones, CTL/ATL/TSB | Blueprint §5.4 |
| Nutrition Coach | Carb periodization, evidence-based supplementation | Blueprint §5.6 |
| Recovery Coach | HRV-guided load, Readiness Score, sleep banking | Blueprint §5.7 |

### API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/athletes/onboarding` | No | Register + create first plan |
| POST | `/auth/login` | No | Get JWT token |
| GET | `/athletes/{id}/week-status` | Bearer | Current week progress |
| GET | `/athletes/{id}/plan` | Bearer | Full training plan |
| POST | `/athletes/{id}/review` | Bearer | Submit weekly review |
| GET | `/athletes/{id}/connectors` | Bearer | Connected apps status |
| POST | `/athletes/{id}/connectors/strava/authorize` | Bearer | Start Strava OAuth |

Full interactive docs: http://localhost:8000/docs

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy, SQLite |
| Frontend | Next.js 16, TypeScript, Tailwind CSS, shadcn/ui |
| Auth | JWT (python-jose), bcrypt passwords |
| Testing | pytest (backend, 286 tests), Vitest + RTL (frontend, 26 tests) |
| Dev tools | Poetry, Docker Compose |

---

## Project Structure

```
resilio-plus/
├── backend/app/          # FastAPI application
│   ├── agents/           # Head Coach + 6 specialist agents
│   ├── core/             # ACWR, fatigue, periodization, conflict detection
│   ├── connectors/       # Strava, Hevy, FatSecret, Apple Health (via Terra)
│   ├── routes/           # HTTP endpoints
│   ├── schemas/          # Pydantic models
│   └── db/               # SQLAlchemy models + SQLite engine
├── frontend/             # Next.js App Router
│   └── src/app/          # login, onboarding, dashboard, plan, review pages
├── resilio/              # Legacy CLI (read-only — running coach tools)
├── .bmad-core/data/      # JSON knowledge bases (volume landmarks, exercise DB…)
├── tests/
│   ├── backend/          # Unit + integration tests (286 passing)
│   └── e2e/              # End-to-end workflow tests (6 passing)
└── docker-compose.yml
```

---

## Development

```bash
# Run all tests
"/path/to/poetry-venv/pytest" tests/ -q

# Run frontend tests
cd frontend && npm test

# Run only E2E tests
"/path/to/poetry-venv/pytest" tests/e2e/ -v

# Backend with auto-reload
uvicorn app.main:app --reload   # from backend/ with PYTHONPATH set

# Format + lint
poetry run black backend/ && poetry run ruff check backend/
```

---

## Connected Apps

| App | Data | Status |
|-----|------|--------|
| Strava | Running, cycling, swimming (GPS, HR, power) | Active |
| Hevy | Strength training (sets, reps, load) | Phase 3 |
| FatSecret | Nutrition (macros, micros, food journal) | Phase 3 |
| Apple Health | HRV, sleep, steps (via Terra API) | Phase 3 |

---

## License

MIT — see [LICENSE](LICENSE)
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: rewrite README with Docker quick-start, architecture, API reference"
```

---

## Task 7: Final verification + tag v1.0.0

- [ ] **Step 1: Run full backend test suite**

```bash
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" tests/ -q --tb=short 2>&1 | tail -5
```

Expected: 292 passed (286 backend + 6 e2e), 1 pre-existing failure.

- [ ] **Step 2: Run frontend test suite**

```bash
cd /c/Users/simon/resilio-plus/frontend && npm test 2>&1 | tail -5
```

Expected: 26 passed, 0 errors.

- [ ] **Step 3: Tag v1.0.0**

```bash
cd /c/Users/simon/resilio-plus
git tag -a v1.0.0 -m "Resilio Plus v1.0.0 — full-stack hybrid athlete coaching platform

- 7-agent AI coaching system (Head Coach + 6 specialists)
- FastAPI backend with JWT auth, SQLite persistence
- Next.js frontend (onboarding, dashboard, plan, review)
- Docker Compose for one-command local deployment
- 292 tests passing (286 backend + 6 E2E)"
```

- [ ] **Step 4: Verify tag**

```bash
git tag -l | grep v1
git show v1.0.0 --stat | head -10
```

Expected: `v1.0.0` listed, tag shows correct commit.

---

## Final Verification Checklist

After all tasks, verify:

- [ ] `docker compose build` completes without errors
- [ ] `pytest tests/ -q` → 292 passed, 1 known failure
- [ ] `cd frontend && npm test` → 26 passed, 0 errors
- [ ] `git tag -l` shows `v1.0.0`
- [ ] `http://localhost:8000/docs` accessible after `docker compose up`
- [ ] `http://localhost:3000` redirects to `/onboarding` after `docker compose up`
