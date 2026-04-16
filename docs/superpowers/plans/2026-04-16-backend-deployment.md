# Backend Deployment (V3-U) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a production-ready, configurable backend container (Docker image < 500MB, non-root, healthchecked) with tiered probes, dev/prod compose layout, exhaustive env inventory, start scripts, and deployment docs.

**Architecture:** Multi-stage Dockerfile (Poetry export → venv → slim runtime). Dispatching entrypoint (`prod`/`dev`). Health routes added without touching middleware/logging (observability session owns those). Dev compose uses bind-mount + `uvicorn --reload`; prod compose override switches to `gunicorn` + UvicornWorker. Docs-only for hosting (Fly.io / Railway / VPS).

**Tech Stack:** Python 3.13-slim, Poetry 1.8.3, FastAPI, gunicorn + uvicorn workers, Alembic, PostgreSQL 16, httpx, Docker/Compose.

**Reference:** `docs/superpowers/specs/2026-04-16-backend-deployment-design.md`.

---

## Constraints

- **Do NOT touch** `backend/app/main.py` CORS middleware, lifespan, or logging config. The observability session owns those. Only add one import + one `include_router(health_router)` call.
- **Do NOT touch** `backend/app/integrations/strava/`.
- Every commit must be atomic (one logical change per commit).
- Windows host: use PowerShell `;` separators (not `&&`) in PowerShell scripts.
- Target image size < 500MB.

---

## File Structure

| File | Responsibility | Change type |
|---|---|---|
| `pyproject.toml` | Dependency manifest; add `gunicorn` | Modify |
| `backend/app/routes/health.py` | Liveness + readiness probes | New |
| `backend/app/main.py` | Wire health router (one line) | Modify |
| `tests/backend/api/test_health.py` | Probe tests | New |
| `scripts/docker-entrypoint-backend.sh` | Dispatch prod/dev inside container | Rewrite |
| `Dockerfile.backend` | Multi-stage build | Rewrite |
| `.dockerignore` | Trim build context | Rewrite |
| `docker-compose.yml` | Dev service layout | Refactor |
| `docker-compose.prod.yml` | Prod override (local prod-like run) | New |
| `.env.example` | Exhaustive env template | Rewrite |
| `scripts/start_dev.ps1` | Windows-host dev launcher (no Docker) | New |
| `scripts/start_prod.sh` | POSIX-host prod launcher (no Docker) | New |
| `docs/backend/DEPLOYMENT.md` | Deployment guide | New |
| `CLAUDE.md` | V3-U phase entry + test count bump | Modify |

---

## Task Execution Order

Tasks are ordered so each one leaves the repo in a working state. Tests run before Docker build changes so regressions surface quickly.

---

### Task 1: Add `gunicorn` dependency

**Files:**
- Modify: `pyproject.toml`
- Modify: `poetry.lock` (via `poetry lock`)

- [ ] **Step 1: Edit `pyproject.toml` — add gunicorn**

Locate the `dependencies = [ ... ]` list under `[project]`. Insert this line immediately after `"uvicorn[standard]>=0.32.0,<1.0",`:

```toml
    "gunicorn>=22.0,<24.0",
```

- [ ] **Step 2: Regenerate the lock file**

Run:
```bash
poetry lock --no-update
```
Expected: `Resolving dependencies... Writing lock file`. No error.

- [ ] **Step 3: Install the new dep into the venv**

Run:
```bash
poetry install --no-root
```
Expected: `gunicorn` appears in the install list (first run) or "No dependencies to install" if already cached.

- [ ] **Step 4: Verify import**

Run:
```bash
poetry run python -c "import gunicorn; print(gunicorn.__version__)"
```
Expected: prints a version `>= 22.0, < 24.0` (e.g., `23.0.0`).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml poetry.lock
git commit -m "chore(deps): add gunicorn for prod web server"
```

---

### Task 2: Health probes — write failing tests first

**Files:**
- Create: `tests/backend/api/test_health.py`

- [ ] **Step 1: Create the failing test file**

Write to `tests/backend/api/test_health.py`:

```python
"""Tests for /health, /ready, /ready/deep — not authenticated, no athlete scope."""
from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest


def test_health_returns_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_ready_returns_ok_when_db_up(client):
    resp = client.get("/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["db"] == "ok"


def test_ready_returns_503_when_db_down(client):
    from app.routes import health as health_module

    with patch.object(
        health_module.engine, "connect", side_effect=RuntimeError("db offline")
    ):
        resp = client.get("/ready")
    assert resp.status_code == 503
    assert "db unreachable" in resp.json()["detail"]


def test_ready_deep_returns_503_when_no_api_key(client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_API_KEY", raising=False)
    resp = client.get("/ready/deep")
    assert resp.status_code == 503
    detail = resp.json()["detail"]
    assert detail["anthropic"] == "no_key"


def test_ready_deep_returns_200_when_all_green(client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    def fake_get(self, url, headers=None, **kwargs):
        request = httpx.Request("GET", url)
        return httpx.Response(200, request=request)

    with patch.object(httpx.Client, "get", fake_get):
        resp = client.get("/ready/deep")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["db"] == "ok"
    assert body["anthropic"] == "ok"
```

- [ ] **Step 2: Run tests — expect all failures (404 because route does not exist)**

Run:
```bash
poetry run pytest tests/backend/api/test_health.py -v
```
Expected: 5 FAILED with `assert 404 == 200` (route not registered yet).

- [ ] **Step 3: Commit (red phase)**

```bash
git add tests/backend/api/test_health.py
git commit -m "test(api): add failing tests for /health and /ready probes"
```

---

### Task 3: Health probes — implement routes + wire into main

**Files:**
- Create: `backend/app/routes/health.py`
- Modify: `backend/app/main.py` (add import + `include_router`, nothing else)

- [ ] **Step 1: Create `backend/app/routes/health.py`**

Write to `backend/app/routes/health.py`:

```python
"""Liveness / readiness probes — not authenticated, not athlete-scoped."""
from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from ..db.database import engine

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness — returns 200 as long as the process is up. No external calls."""
    return {"status": "ok"}


@router.get("/ready")
def ready() -> dict[str, Any]:
    """Readiness — verifies DB reachable. Used by orchestrator probes."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"db unreachable: {type(exc).__name__}"
        )
    return {"status": "ready", "db": "ok"}


@router.get("/ready/deep")
def ready_deep() -> dict[str, Any]:
    """Deep readiness — DB + Anthropic reachability. Manual diagnostic only."""
    result: dict[str, Any] = {"status": "ready", "db": "unknown", "anthropic": "unknown"}

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        result["db"] = "ok"
    except Exception as exc:
        result["db"] = f"fail: {type(exc).__name__}"
        result["status"] = "degraded"

    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY", "")
    if not api_key:
        result["anthropic"] = "no_key"
        result["status"] = "degraded"
    else:
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(
                    "https://api.anthropic.com/v1/models",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                    },
                )
            result["anthropic"] = (
                "ok" if resp.status_code < 500 else f"http_{resp.status_code}"
            )
            if resp.status_code >= 500:
                result["status"] = "degraded"
        except Exception as exc:
            result["anthropic"] = f"fail: {type(exc).__name__}"
            result["status"] = "degraded"

    if result["status"] != "ready":
        raise HTTPException(status_code=503, detail=result)
    return result
```

- [ ] **Step 2: Wire router into `backend/app/main.py`**

Open `backend/app/main.py`. Find the block of `from .routes.XXX import router as XXX_router` imports (lines ~7–26). Add this line alphabetically (after `from .routes.food_search import router as food_search_router` or at the end of the import block — placement is cosmetic):

```python
from .routes.health import router as health_router
```

Find the block of `app.include_router(XXX_router)` calls (lines ~54–72). Add this line at the end of the block (order does not affect behavior — health routes have no overlap):

```python
app.include_router(health_router)
```

**Do not modify** anything else in `main.py`. Specifically, leave CORS, lifespan, scheduler setup, and existing routers alone.

- [ ] **Step 3: Run tests — expect 5/5 PASS**

Run:
```bash
poetry run pytest tests/backend/api/test_health.py -v
```
Expected: 5 passed.

- [ ] **Step 4: Run the full backend API test suite — no regression**

Run:
```bash
poetry run pytest tests/backend/api/ -q
```
Expected: all pre-existing passing tests still pass; new count = previous + 5.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routes/health.py backend/app/main.py
git commit -m "feat(api): add /health, /ready, /ready/deep probes"
```

---

### Task 4: Refactor `docker-entrypoint-backend.sh` — dispatch prod/dev

**Files:**
- Rewrite: `scripts/docker-entrypoint-backend.sh`

- [ ] **Step 1: Replace the entrypoint script body**

Write to `scripts/docker-entrypoint-backend.sh` (replace entire file content):

```bash
#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-prod}"

echo "[entrypoint] running alembic migrations..."
alembic upgrade head

case "$MODE" in
  prod)
    WORKERS="${WEB_CONCURRENCY:-2}"
    echo "[entrypoint] starting gunicorn with $WORKERS uvicorn workers..."
    exec gunicorn app.main:app \
      --worker-class uvicorn.workers.UvicornWorker \
      --workers "$WORKERS" \
      --bind "${HOST:-0.0.0.0}:${PORT:-8000}" \
      --timeout 60 \
      --graceful-timeout 30 \
      --access-logfile - \
      --error-logfile -
    ;;
  dev)
    echo "[entrypoint] starting uvicorn with --reload..."
    exec uvicorn app.main:app \
      --host "${HOST:-0.0.0.0}" \
      --port "${PORT:-8000}" \
      --reload
    ;;
  *)
    echo "[entrypoint] unknown mode: $MODE (expected: prod|dev)" >&2
    exit 2
    ;;
esac
```

Note: `alembic upgrade head` no longer needs `PYTHONPATH=/app/backend` because the new Dockerfile sets `PYTHONPATH=/app/backend` globally via `ENV`. Also, `exec` replaces the shell so signals (SIGTERM from Docker) reach gunicorn/uvicorn directly.

- [ ] **Step 2: Syntax check the script**

Run:
```bash
bash -n scripts/docker-entrypoint-backend.sh
```
Expected: no output (syntax OK).

- [ ] **Step 3: Commit**

```bash
git add scripts/docker-entrypoint-backend.sh
git commit -m "feat(deploy): dispatching entrypoint — prod (gunicorn) / dev (uvicorn)"
```

---

### Task 5: Rewrite `Dockerfile.backend` — multi-stage

**Files:**
- Rewrite: `Dockerfile.backend`

- [ ] **Step 1: Replace Dockerfile content**

Write to `Dockerfile.backend` (replace entire file content):

```dockerfile
# syntax=docker/dockerfile:1.7
# ======================================================================
# Stage 1 — builder: Poetry exports deps into an isolated venv.
# ======================================================================
FROM python:3.13-slim AS builder

RUN pip install --no-cache-dir poetry==1.8.3

WORKDIR /build
COPY pyproject.toml poetry.lock ./

RUN python -m venv /venv && \
    /venv/bin/pip install --upgrade pip && \
    poetry export -f requirements.txt --only main --without-hashes -o /tmp/requirements.txt && \
    /venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt

# ======================================================================
# Stage 2 — runtime: slim base, non-root, no Poetry in final image.
# ======================================================================
FROM python:3.13-slim AS runtime

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/* && \
    useradd --system --uid 1000 --home-dir /app --shell /bin/bash resilio

COPY --from=builder /venv /venv

ENV PATH=/venv/bin:$PATH \
    PYTHONPATH=/app/backend \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
COPY alembic.ini ./alembic.ini
COPY alembic/ ./alembic/
COPY resilio/ ./resilio/
COPY backend/ ./backend/
COPY .bmad-core/ ./.bmad-core/
COPY scripts/docker-entrypoint-backend.sh /entrypoint.sh

# Strip Windows CRLF, make executable, create runtime data dir, fix ownership.
RUN sed -i 's/\r$//' /entrypoint.sh && \
    chmod +x /entrypoint.sh && \
    mkdir -p /app/data && \
    chown -R resilio:resilio /app

USER resilio

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["prod"]
```

- [ ] **Step 2: Lint with hadolint (optional, skip if not installed)**

Run (if hadolint is available):
```bash
hadolint Dockerfile.backend
```
Expected: no errors. If hadolint not installed, skip this step.

- [ ] **Step 3: Build the image**

Run:
```bash
docker build -f Dockerfile.backend -t resilio-backend:test .
```
Expected: build completes. Last lines mention `naming to docker.io/library/resilio-backend:test`.

- [ ] **Step 4: Check image size**

Run:
```bash
docker images resilio-backend:test --format "{{.Size}}"
```
Expected: size < 500MB (target ~250MB; flag if > 500MB and investigate).

- [ ] **Step 5: Commit**

```bash
git add Dockerfile.backend
git commit -m "build(docker): multi-stage backend image (non-root, HEALTHCHECK)"
```

---

### Task 6: Rewrite `.dockerignore`

**Files:**
- Rewrite: `.dockerignore`

- [ ] **Step 1: Replace `.dockerignore`**

Write to `.dockerignore` (replace entire file content):

```gitignore
# VCS
.git
.gitignore
.gitattributes

# Secrets
.env
.env.*
!.env.example
*.pem
*.key

# Python build / cache
__pycache__
*.pyc
*.pyo
*.pyd
.pytest_cache
.mypy_cache
.ruff_cache
.coverage
htmlcov
dist
build
*.egg-info
.venv
venv

# Node / frontend workspace
node_modules
.pnpm-store
.next
apps/desktop
apps/mobile
apps/web/.next
apps/web/node_modules

# Tests (not shipped to runtime)
tests

# Docs (allow-list inline backend docs only)
docs
*.md
!README.md
!backend/app/**/*.md

# IDE
.idea
.vscode
*.swp

# OS
.DS_Store
Thumbs.db

# Local DBs / data
*.sqlite
*.sqlite-journal
*.db
data

# Workspace junk
FRONTEND_AUDIT.md
FRONTEND_VAGUE1_POSTMORTEM.md
BACKEND_V3_COMPLETE.md
resilio-master-*.md
frontend-master-*.md
docs/ui-audit-*.md
docs/archive
```

- [ ] **Step 2: Rebuild and confirm smaller context**

Run:
```bash
docker build -f Dockerfile.backend -t resilio-backend:test .
```
Expected: "transferring context" line shows a smaller size than before (e.g., a few MB instead of hundreds).

- [ ] **Step 3: Commit**

```bash
git add .dockerignore
git commit -m "build(docker): trim .dockerignore — exclude tests, docs, build artifacts"
```

---

### Task 7: Refactor `docker-compose.yml` — dev mode + env_file

**Files:**
- Rewrite: `docker-compose.yml`

- [ ] **Step 1: Replace `docker-compose.yml`**

Write to `docker-compose.yml` (replace entire file content):

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
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-resilio} -d ${POSTGRES_DB:-resilio_db}"]
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
    command: ["dev"]
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app/backend
      - ./resilio:/app/resilio
      - ./alembic:/app/alembic
      - ./.bmad-core:/app/.bmad-core
      - checkpoint_data:/app/data
    env_file:
      - .env
    environment:
      DATABASE_URL: postgresql+psycopg2://${POSTGRES_USER:-resilio}:${POSTGRES_PASSWORD:-resilio}@db:5432/${POSTGRES_DB:-resilio_db}
      LANGGRAPH_CHECKPOINT_DB: /app/data/checkpoints.sqlite
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
  checkpoint_data:
```

Key changes vs current file:
- `backend.command: ["dev"]` → entrypoint dispatches to `uvicorn --reload`.
- `env_file: [.env]` → loads local `.env` (contains `ANTHROPIC_API_KEY`, secrets, etc).
- `LANGGRAPH_CHECKPOINT_DB` set explicitly, persisted via `checkpoint_data` volume.
- `DATABASE_URL` uses `${POSTGRES_USER}` instead of hardcoding `resilio:`.
- Legacy hardcoded `ANTHROPIC_API_KEY`, `STRAVA_*`, `JWT_SECRET_KEY` removed — those flow via `env_file`.

- [ ] **Step 2: Validate compose file syntax**

Run:
```bash
docker compose config -q
```
Expected: no output (config valid). If `.env` is missing, expect a warning — fine.

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml
git commit -m "build(compose): dev mode uses entrypoint dispatch + env_file + checkpoint volume"
```

---

### Task 8: Create `docker-compose.prod.yml` — prod override

**Files:**
- Create: `docker-compose.prod.yml`

- [ ] **Step 1: Create the override file**

Write to `docker-compose.prod.yml`:

```yaml
# Usage: docker compose -f docker-compose.yml -f docker-compose.prod.yml up backend db
# Simulates production locally: gunicorn, no bind-mounts, no reload, resource limits.
services:
  backend:
    command: ["prod"]
    volumes:
      - checkpoint_data:/app/data
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: "1.0"

  frontend:
    profiles: ["donotrun"]
```

Note: `profiles: ["donotrun"]` is a common idiom to disable a service via override. With a profile that is never activated, the frontend service is skipped.

- [ ] **Step 2: Validate the override**

Run:
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml config -q
```
Expected: no output (config valid).

- [ ] **Step 3: Commit**

```bash
git add docker-compose.prod.yml
git commit -m "build(compose): add prod override (gunicorn, no reload, resource limits)"
```

---

### Task 9: Rewrite `.env.example` — exhaustive inventory

**Files:**
- Rewrite: `.env.example`

- [ ] **Step 1: Replace `.env.example`**

Write to `.env.example` (replace entire file content):

```bash
# ============================================================
# Resilio Plus Backend — Environment Variables
# Copy this file to .env and fill in real values before running.
# ============================================================

# --- Process control ---
ENV=development                 # development | production
HOST=0.0.0.0
PORT=8000
WEB_CONCURRENCY=2               # gunicorn workers (prod only)

# --- Database ---
# Compose default: postgresql+psycopg2://resilio:resilio@db:5432/resilio_db
DATABASE_URL=postgresql+psycopg2://resilio:resilio@localhost:5432/resilio_db
POSTGRES_USER=resilio
POSTGRES_PASSWORD=resilio
POSTGRES_DB=resilio_db

# --- Auth — JWT ---
# Generate: openssl rand -hex 32
JWT_SECRET=changeme-run-openssl-rand-hex-32
JWT_ACCESS_TTL_MINUTES=15
JWT_REFRESH_TTL_DAYS=30

# --- Auth — SMTP (password reset emails) ---
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=your-gmail-app-password
SMTP_FROM=noreply@resilio.app
APP_BASE_URL=http://localhost:3000

# --- CORS ---
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:4000,http://localhost:8081,http://localhost:19000

# --- LLM (Anthropic) ---
# Used by Head Coach + external plan import (Haiku).
ANTHROPIC_API_KEY=sk-ant-CHANGEME

# --- LangGraph checkpointer ---
# SQLite file path. Persist via mounted volume in prod.
LANGGRAPH_CHECKPOINT_DB=/app/data/checkpoints.sqlite

# --- Strava OAuth V2 ---
STRAVA_CLIENT_ID=CHANGEME
STRAVA_CLIENT_SECRET=CHANGEME
STRAVA_REDIRECT_URI=http://localhost:8000/integrations/strava/callback
# Fernet key — generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
STRAVA_ENCRYPTION_KEY=CHANGEME

# --- Hevy ---
HEVY_API_KEY=CHANGEME

# --- Terra ---
TERRA_API_KEY=CHANGEME
TERRA_DEV_ID=CHANGEME

# --- USDA FoodData Central ---
# Free tier: https://fdc.nal.usda.gov/api-key-signup.html
USDA_API_KEY=your_key_here

# --- Admin ---
# Your athlete UUID — gates /admin/* routes.
ADMIN_ATHLETE_ID=CHANGEME
```

- [ ] **Step 2: Verify every `os.getenv` / `os.environ.get` in the backend has a matching key**

Run:
```bash
grep -rE "os\.(getenv|environ(\.get)?)" backend/app/ | grep -oE "['\"][A-Z_]+['\"]" | sort -u
```
Expected output (sorted): key names listed. Manually cross-check that each key appears in `.env.example`. Exceptions allowed:
- `CLAUDE_API_KEY` (alias of `ANTHROPIC_API_KEY`, documented in `DEPLOYMENT.md`).
- Optional internals that default gracefully (e.g., `PYTHONPATH`).

If any key is missing, add it to `.env.example` before committing.

- [ ] **Step 3: Commit**

```bash
git add .env.example
git commit -m "chore(env): exhaustive .env.example — adds ANTHROPIC_API_KEY, LANGGRAPH_CHECKPOINT_DB, process control"
```

---

### Task 10: Create `scripts/start_dev.ps1`

**Files:**
- Create: `scripts/start_dev.ps1`

- [ ] **Step 1: Verify `scripts/*.ps1` is not blocked by `.gitignore`**

Run:
```bash
grep -E "^(!?scripts/|!?\*\.ps1)" .gitignore || echo "no relevant scripts rule"
```
If you see `scripts/*` (with no `!scripts/*.ps1` exception), add an exception line in `.gitignore`:
```
!scripts/start_dev.ps1
```
If no rule mentions `scripts/`, skip this step.

- [ ] **Step 2: Write the script**

Write to `scripts/start_dev.ps1`:

```powershell
# Start backend in dev mode on the Windows host (no Docker).
# Requires: Poetry installed, PostgreSQL reachable at $DATABASE_URL.
$ErrorActionPreference = "Stop"

if (-not (Test-Path ".env")) {
    Write-Error ".env file missing. Copy .env.example to .env and fill in values."
}

Write-Host "[dev] installing dependencies via poetry..."
poetry install --no-root

Write-Host "[dev] running alembic migrations..."
$env:PYTHONPATH = "backend"
poetry run alembic upgrade head

Write-Host "[dev] starting uvicorn on http://localhost:8000 ..."
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- [ ] **Step 3: Verify the script parses**

Run:
```bash
powershell -NoProfile -Command "Get-Command -Syntax ./scripts/start_dev.ps1 2>&1 | Out-Null; if ($?) { 'ok' } else { 'parse fail' }"
```
Expected: `ok`. If PowerShell is not on PATH (rare on the target dev box), skip this step.

- [ ] **Step 4: Commit**

```bash
git add scripts/start_dev.ps1 .gitignore
git commit -m "feat(deploy): add scripts/start_dev.ps1 — Windows-host dev launcher"
```

(If `.gitignore` was not modified in Step 1, drop it from the `git add` line.)

---

### Task 11: Create `scripts/start_prod.sh`

**Files:**
- Create: `scripts/start_prod.sh`

- [ ] **Step 1: Verify `scripts/*.sh` is not blocked by `.gitignore`**

Run:
```bash
grep -E "^(!?scripts/|!?\*\.sh)" .gitignore || echo "no relevant scripts rule"
```
If needed, add the exception line:
```
!scripts/start_prod.sh
```

- [ ] **Step 2: Write the script**

Write to `scripts/start_prod.sh`:

```bash
#!/usr/bin/env bash
# Start backend in prod mode on a POSIX host (VPS, CI). No Docker.
# Requires: venv with deps installed, .env populated, PostgreSQL reachable.
set -euo pipefail

if [ ! -f .env ]; then
  echo ".env file missing. Copy .env.example to .env and fill in values." >&2
  exit 1
fi

# Load .env into environment.
set -a
. ./.env
set +a

echo "[prod] running alembic migrations..."
PYTHONPATH=backend alembic upgrade head

WORKERS="${WEB_CONCURRENCY:-2}"
echo "[prod] starting gunicorn with $WORKERS uvicorn workers on ${HOST:-0.0.0.0}:${PORT:-8000}..."
PYTHONPATH=backend exec gunicorn app.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers "$WORKERS" \
  --bind "${HOST:-0.0.0.0}:${PORT:-8000}" \
  --timeout 60 \
  --graceful-timeout 30 \
  --access-logfile - \
  --error-logfile -
```

- [ ] **Step 3: Make it executable + syntax check**

Run:
```bash
chmod +x scripts/start_prod.sh
bash -n scripts/start_prod.sh
```
Expected: no output (syntax OK).

- [ ] **Step 4: Commit**

```bash
git add scripts/start_prod.sh .gitignore
git commit -m "feat(deploy): add scripts/start_prod.sh — POSIX-host prod launcher"
```

(Drop `.gitignore` if unchanged.)

---

### Task 12: Write `docs/backend/DEPLOYMENT.md`

**Files:**
- Create: `docs/backend/DEPLOYMENT.md`

- [ ] **Step 1: Create the deployment guide**

Write to `docs/backend/DEPLOYMENT.md`:

```markdown
# Backend Deployment Guide

**Applies to:** Resilio Plus backend (FastAPI + LangGraph + Alembic) — V3-U and later.

This document covers building the Docker image, running it locally in prod-like mode, the full environment variable contract, and recipes for Fly.io / Railway / a plain Linux VPS.

---

## 1. Image Overview

| Property | Value |
|---|---|
| Base | `python:3.13-slim` |
| User | `resilio` (UID 1000, non-root) |
| Entrypoint | `/entrypoint.sh` (dispatches `prod` or `dev`) |
| Default CMD | `prod` (gunicorn + UvicornWorker) |
| Port | `8000` |
| Healthcheck | `curl -fsS http://localhost:8000/health` every 30s |
| Target size | ~250MB (stop the line if > 500MB) |
| Writable volume | `/app/data` — LangGraph SQLite checkpoints |

### Stateful requirements

The container expects:
- An external PostgreSQL 16+ reachable via `DATABASE_URL`.
- A writable path at `/app/data` for the LangGraph SQLite checkpoint store (set via `LANGGRAPH_CHECKPOINT_DB`). Mount a volume here or checkpoints reset on restart.

---

## 2. Build

```bash
docker build -f Dockerfile.backend -t resilio-backend:latest .
docker images resilio-backend:latest --format "{{.Size}}"
```

Expect ~250MB. If over 500MB, investigate (likely a `.dockerignore` regression pulling in `tests/`, `docs/`, `node_modules/`, or build artifacts).

---

## 3. Run locally

### 3.1 Dev (hot reload, bind mounts)

```bash
docker compose up backend db
```

Backend listens on `http://localhost:8000`. Code changes in `backend/` trigger uvicorn reload.

### 3.2 Prod-like (gunicorn, no reload)

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up backend db
```

Verify probes from the host:
```bash
curl -fsS http://localhost:8000/health          # → {"status":"ok"}
curl -fsS http://localhost:8000/ready           # → {"status":"ready","db":"ok"}
curl -fsS http://localhost:8000/ready/deep      # → DB + Anthropic status
```

---

## 4. Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `ENV` | no | `development` | `development` or `production`. Advisory. |
| `HOST` | no | `0.0.0.0` | Bind host for uvicorn/gunicorn. |
| `PORT` | no | `8000` | Bind port. |
| `WEB_CONCURRENCY` | no | `2` | Gunicorn worker count (prod only). |
| `DATABASE_URL` | **yes** | — | SQLAlchemy URL, e.g. `postgresql+psycopg2://user:pw@host:5432/db`. |
| `POSTGRES_USER` | compose only | `resilio` | Used by the compose `db` service. |
| `POSTGRES_PASSWORD` | compose only | `resilio` | Used by the compose `db` service. |
| `POSTGRES_DB` | compose only | `resilio_db` | Used by the compose `db` service. |
| `JWT_SECRET` | **yes** | — | 32-byte hex. Generate: `openssl rand -hex 32`. |
| `JWT_ACCESS_TTL_MINUTES` | no | `15` | Access token lifetime. |
| `JWT_REFRESH_TTL_DAYS` | no | `30` | Refresh token lifetime. |
| `SMTP_HOST` | password reset | — | SMTP server. |
| `SMTP_PORT` | password reset | `587` | SMTP port. |
| `SMTP_USER` | password reset | — | SMTP username. |
| `SMTP_PASSWORD` | password reset | — | SMTP password (Gmail: app password). |
| `SMTP_FROM` | password reset | — | From header on password reset emails. |
| `APP_BASE_URL` | password reset | `http://localhost:3000` | Used to build password reset links. |
| `ALLOWED_ORIGINS` | **yes** | — | Comma-separated CORS origins. Tighten for prod. |
| `ANTHROPIC_API_KEY` | **yes** | — | Claude API key. Alias: `CLAUDE_API_KEY` (either works). |
| `LANGGRAPH_CHECKPOINT_DB` | no | `data/checkpoints.sqlite` | SQLite path for LangGraph checkpoints. |
| `STRAVA_CLIENT_ID` | Strava users | — | OAuth client ID. |
| `STRAVA_CLIENT_SECRET` | Strava users | — | OAuth client secret. |
| `STRAVA_REDIRECT_URI` | Strava users | — | Must match Strava app config. |
| `STRAVA_ENCRYPTION_KEY` | Strava users | — | Fernet key. Generate: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. |
| `HEVY_API_KEY` | Hevy users | — | Hevy Pro API key. |
| `TERRA_API_KEY` | Terra users | — | Terra API key. |
| `TERRA_DEV_ID` | Terra users | — | Terra dev ID. |
| `USDA_API_KEY` | nutrition | — | USDA FoodData Central key (free tier). |
| `ADMIN_ATHLETE_ID` | ops | — | Athlete UUID that can reach `/admin/jobs`. |

Any variable marked "**yes**" missing at boot will cause either a startup failure or a runtime failure at first use. Populate `.env` from `.env.example` before running.

---

## 5. Hosting Recipes

### 5.1 Fly.io (recommended)

```bash
# 1. Create app.
fly launch --no-deploy --name resilio-backend --dockerfile Dockerfile.backend

# 2. Set secrets (repeat per variable).
fly secrets set \
  JWT_SECRET="$(openssl rand -hex 32)" \
  ANTHROPIC_API_KEY="sk-ant-..." \
  DATABASE_URL="postgresql+psycopg2://..." \
  ALLOWED_ORIGINS="https://your-frontend.example.com" \
  STRAVA_ENCRYPTION_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')" \
  # ... other variables from the table above

# 3. Mount a volume for LangGraph checkpoints.
fly volumes create checkpoints --size 1 --region cdg

# 4. Edit fly.toml (excerpt):
#   [env]
#     LANGGRAPH_CHECKPOINT_DB = "/app/data/checkpoints.sqlite"
#   [[mounts]]
#     source = "checkpoints"
#     destination = "/app/data"
#   [[services.http_checks]]
#     path = "/ready"
#     interval = "30s"

# 5. Deploy.
fly deploy
```

Use Fly Postgres (`fly postgres create`) for `DATABASE_URL`.

### 5.2 Railway

- New project → "Deploy from Dockerfile" → point at `Dockerfile.backend`.
- Add a Postgres plugin, copy the connection string into `DATABASE_URL` (remember to prefix with `postgresql+psycopg2://`).
- Set all other variables from the table as service variables.
- Attach a volume to `/app/data` for checkpoint persistence.
- Railway auto-wires the healthcheck via the Docker `HEALTHCHECK` directive.

### 5.3 Plain VPS (docker compose)

```bash
# On the server:
git clone <repo> && cd resilio-plus
cp .env.example .env && $EDITOR .env         # fill in all secrets

# Pull / build once, then run.
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d backend db

# Put nginx/Caddy in front for TLS — terminate TLS there, proxy to :8000.
```

Back up the `postgres_data` and `checkpoint_data` Docker volumes on a schedule.

---

## 6. Pre-Deployment Checklist

- [ ] `JWT_SECRET` set to a fresh 32-byte hex value (not the `.env.example` placeholder).
- [ ] `ANTHROPIC_API_KEY` set and active.
- [ ] `DATABASE_URL` points at a persistent, backed-up Postgres (not a local container on the host).
- [ ] `STRAVA_ENCRYPTION_KEY` generated and stored (losing it makes existing Strava tokens unreadable).
- [ ] `ALLOWED_ORIGINS` tightened to the actual production frontend origin(s).
- [ ] `APP_BASE_URL` points at the production frontend (used in password reset emails).
- [ ] `LANGGRAPH_CHECKPOINT_DB` path backed by a persistent volume (not container-local).
- [ ] `/app/data` mount writable by UID 1000 (`resilio` user).
- [ ] Container image built from `main` and tagged (e.g., `resilio-backend:v3-u`).
- [ ] Image size under 500MB (`docker images`).
- [ ] `/health` returns 200 immediately after boot.
- [ ] `/ready` returns 200 once the DB is reachable.
- [ ] Alembic migrations ran to head on first boot (check entrypoint logs).
- [ ] Backup schedule in place for Postgres + `/app/data` volume.

---

## 7. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Container exits with `permission denied: /app/data/checkpoints.sqlite` | Volume owner is root, container is UID 1000 | `chown -R 1000:1000 /path/to/volume` on host before re-running |
| `/ready` returns 503 | DB unreachable | Check `DATABASE_URL`; confirm Postgres is up; test with `psql` from host |
| `/ready/deep` returns 503 with `"anthropic": "no_key"` | `ANTHROPIC_API_KEY` not set | Populate the env var (not just `.env.example`) |
| `alembic upgrade head` fails at boot | Migration conflict or DB schema drift | Connect with `psql`, run `alembic current`; resolve manually |
| `gunicorn` crashes with `ModuleNotFoundError: app` | `PYTHONPATH` missing | Image sets it; if running outside Docker, `export PYTHONPATH=backend` first |
| `502 Bad Gateway` behind reverse proxy | Gunicorn `--timeout` too short for LLM calls | Raise `--timeout` in `scripts/docker-entrypoint-backend.sh` |
| Image size > 500MB | `.dockerignore` regression | Inspect `docker build` context line; add missing excludes |
| Signals not reaching gunicorn (slow shutdown) | Entrypoint not using `exec` | Confirm `exec gunicorn` in `scripts/docker-entrypoint-backend.sh` |

---

## 8. References

- Spec: `docs/superpowers/specs/2026-04-16-backend-deployment-design.md`
- Plan: `docs/superpowers/plans/2026-04-16-backend-deployment.md`
- LangGraph runtime: `docs/backend/LANGGRAPH-FLOW.md`
- Background jobs: `docs/backend/JOBS.md`
- Auth: `docs/backend/AUTH.md`
```

- [ ] **Step 2: Commit**

```bash
git add docs/backend/DEPLOYMENT.md
git commit -m "docs(backend): add DEPLOYMENT.md — build, run, env, hosting, checklist"
```

---

### Task 13: End-to-end Docker validation

**Files:** none modified — validation only.

- [ ] **Step 1: Clean rebuild from scratch**

Run:
```bash
docker build --no-cache -f Dockerfile.backend -t resilio-backend:test .
```
Expected: build completes without errors.

- [ ] **Step 2: Check image size**

Run:
```bash
docker images resilio-backend:test --format "{{.Repository}}:{{.Tag}} {{.Size}}"
```
Expected: size < 500MB. If over, inspect layers:
```bash
docker history resilio-backend:test
```
and fix `.dockerignore` or Dockerfile before proceeding.

- [ ] **Step 3: Run container against the dev Postgres**

Ensure the dev DB is up:
```bash
docker compose up -d db
```

Start the backend image with explicit env (bypassing `.env` for this smoke test):
```bash
docker run --rm -d \
  --name resilio-backend-smoke \
  --network resilio-plus_default \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql+psycopg2://resilio:resilio@db:5432/resilio_db \
  -e JWT_SECRET=smoketest \
  -e ANTHROPIC_API_KEY=dummy \
  resilio-backend:test
```
(The compose network name may vary — check with `docker network ls`.)

- [ ] **Step 4: Verify `/health` returns 200**

Wait ~5s for migrations + gunicorn boot, then:
```bash
curl -fsS http://localhost:8000/health
```
Expected: `{"status":"ok"}`.

- [ ] **Step 5: Verify `/ready` returns 200**

```bash
curl -fsS http://localhost:8000/ready
```
Expected: `{"status":"ready","db":"ok"}`.

- [ ] **Step 6: Verify Docker HEALTHCHECK reports healthy**

```bash
docker inspect --format='{{.State.Health.Status}}' resilio-backend-smoke
```
Expected: `healthy` (may take up to 30s after boot).

- [ ] **Step 7: Tear down smoke container**

```bash
docker stop resilio-backend-smoke
```
Expected: container ID printed.

- [ ] **Step 8: Run the full Python test suite — no regressions**

Run:
```bash
poetry run pytest tests/ -q
```
Expected: new probe tests pass; known pre-existing failures (`test_history_shows_logged_count` flake, `test_high_continuity_no_breaks` date drift) may still fail per CLAUDE.md — that's acceptable. New failures are not.

- [ ] **Step 9: No commit — validation only**

No files changed in this task.

---

### Task 14: Update `CLAUDE.md` — V3-U phase entry

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add V3-U phase row**

Open `CLAUDE.md`. Find the phase status table. Immediately after the `V3-T` row, insert:

```markdown
| V3-U | Backend Deployment — multi-stage Dockerfile (~250MB, non-root, HEALTHCHECK), dev/prod compose layout, exhaustive `.env.example`, `/health` + `/ready` + `/ready/deep` probes, dispatching entrypoint, `DEPLOYMENT.md` | ✅ Complete (2026-04-16) |
```

- [ ] **Step 2: Add a "Dernières phases complétées" summary line**

Above the existing "Dernières phases complétées (2026-04-14) :" V3-T line, insert a new block:

```markdown
**Dernières phases complétées (2026-04-16) :** V3-U livré — backend dockerisé et déployable. Multi-stage `Dockerfile.backend` (builder Poetry → runtime `python:3.13-slim`, non-root UID 1000, curl pour HEALTHCHECK). Dispatching entrypoint (`prod` → gunicorn + UvicornWorker, `dev` → uvicorn --reload). Override `docker-compose.prod.yml` pour tester le mode prod localement. Probes tiered : `/health` (liveness), `/ready` (DB), `/ready/deep` (DB + Anthropic, manuel). `.env.example` exhaustif (20+ vars, ANTHROPIC_API_KEY + LANGGRAPH_CHECKPOINT_DB documentés). Guide `docs/backend/DEPLOYMENT.md` (Fly.io / Railway / VPS recipes). Aucune modification de `backend/app/main.py` au-delà de l'ajout du router (middleware / logging / lifespan inchangés — session observabilité).
```

- [ ] **Step 3: Bump the test count invariant**

Find the line `pytest tests/` must pass (≥2310 passing — état V3-T…`. Update the number to reflect the new count:

```markdown
   - `pytest tests/` must pass (≥2315 passing — état V3-U; 2 pre-existing unrelated failures: `test_history_shows_logged_count` flake, `test_high_continuity_no_breaks` date drift)
```

(If you actually added more or fewer than 5 tests, adjust accordingly — the number equals the previous V3-T baseline plus the net new tests.)

- [ ] **Step 4: Add `DEPLOYMENT.md` to Key References**

In the "Key References" section, add:

```markdown
- **Deployment Guide**: `docs/backend/DEPLOYMENT.md` — Docker build, env vars, Fly.io / Railway / VPS recipes
- **Deployment Spec**: `docs/superpowers/specs/2026-04-16-backend-deployment-design.md`
- **Deployment Plan**: `docs/superpowers/plans/2026-04-16-backend-deployment.md`
```

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(claude): add V3-U Backend Deployment phase entry"
```

---

### Task 15: Push to main

**Files:** none.

- [ ] **Step 1: Pull-rebase to pick up any concurrent commits**

Run:
```bash
git pull --rebase origin main
```
Expected: "Current branch main is up to date" OR a clean rebase.

- [ ] **Step 2: Push**

Run:
```bash
git push origin main
```
Expected: push accepted.

---

## Self-Review (ran before finalizing this plan)

**Spec coverage:** every spec section has a corresponding task.
- §1 Dockerfile → Task 5.
- §2 Compose → Tasks 7 + 8.
- §3 `.env.example` → Task 9.
- §4 Health probes → Tasks 2 (tests) + 3 (impl).
- §5 Scripts → Tasks 4 (entrypoint) + 10 (`start_dev.ps1`) + 11 (`start_prod.sh`).
- §6 `DEPLOYMENT.md` → Task 12.
- §7 `.dockerignore` → Task 6.
- §8 `pyproject.toml` → Task 1.
- §"Files NOT Touched" → enforced in Task 3 Step 2 instructions.
- §"Success Criteria" → exercised in Task 13.

**Placeholder scan:** no "TBD", "TODO", "fill in details", "add error handling", or vague references. Every code step has full content inlined.

**Type consistency:** `health_router` used consistently; router file path `backend/app/routes/health.py` matches import `from ..db.database import engine`; `engine` is the prod module-level engine (verified present at `backend/app/db/database.py:11`). Compose service name `db` matches host used in `DATABASE_URL` in Tasks 7 and 13.
