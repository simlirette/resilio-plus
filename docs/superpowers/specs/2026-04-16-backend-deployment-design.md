# Backend Deployment — Design Spec

**Date:** 2026-04-16
**Status:** Approved
**Phase:** V3-U
**Scope:** Production-ready Docker image, dev/prod compose layout, exhaustive env var inventory, tiered health probes, start scripts, deployment docs.

---

## Context

After V3-O through V3-T (auth, Hevy, Strava OAuth V2, nutrition lookup, background jobs, LangGraph runtime), the backend has all the features it needs to deploy. Current state:

- `Dockerfile.backend` exists but is dev-only: hardcoded pip deps (drifted from `pyproject.toml`, missing `langgraph`, `anthropic`, `cryptography`, `langgraph-checkpoint-sqlite`), runs `uvicorn --reload`, no non-root user, no Docker `HEALTHCHECK`.
- `docker-compose.yml` exists: `db` + `db-test` + `backend` (bind-mounted source) + `frontend`. Fine for dev.
- `.env.example` incomplete: missing `ANTHROPIC_API_KEY`, `LANGGRAPH_CHECKPOINT_DB`; contains unused `FATSECRET_*`.
- No `/health` or `/ready` endpoint.
- `.dockerignore` minimal (11 patterns).
- Session parallèle works on observability (logging/middleware) — do NOT touch those layers.

V3-U fixes this so the backend can ship to Fly.io / Railway / VPS with a single `docker build` + env vars.

---

## Decisions Locked (Q&A)

| # | Question | Choice |
|---|---|---|
| 1 | Dockerfile strategy | **A** — Refactor existing into multi-stage; same image, compose override for dev vs prod |
| 2 | `/ready` scope | **C** — Tiered: `/health` liveness, `/ready` DB-only, `/ready/deep` DB + Anthropic (manual diagnostic) |
| 3 | Deps source in image | **A** — Poetry in builder stage, `poetry export` + `pip install` into a venv, venv copied to runtime |
| 4 | Hosting deliverable | **A** — Docs-only (`DEPLOYMENT.md`); no `fly.toml`/Railway configs committed |

---

## Deliverables

| # | Deliverable | Location |
|---|---|---|
| 1 | Multi-stage production Dockerfile | `Dockerfile.backend` (refactor) |
| 2 | Dev compose + prod override | `docker-compose.yml`, `docker-compose.prod.yml` (new) |
| 3 | Exhaustive env template | `.env.example` (rewrite) |
| 4 | Tiered health probes | `backend/app/routes/health.py` (new) + main.py wiring |
| 5 | Dispatching entrypoint + dev/prod scripts | `scripts/docker-entrypoint-backend.sh` (refactor), `scripts/start_dev.ps1` (new), `scripts/start_prod.sh` (new) |
| 6 | Deployment guide | `docs/backend/DEPLOYMENT.md` (new) |
| 7 | Extended ignore | `.dockerignore` (rewrite) |
| 8 | Dependency additions | `pyproject.toml` — add `gunicorn` |

---

## 1. Dockerfile (multi-stage)

**Path:** `Dockerfile.backend`

```dockerfile
# Stage 1: builder — Poetry exports deps into an isolated venv.
FROM python:3.13-slim AS builder
RUN pip install --no-cache-dir poetry==1.8.3
WORKDIR /build
COPY pyproject.toml poetry.lock ./
RUN python -m venv /venv && \
    /venv/bin/pip install --upgrade pip && \
    poetry export -f requirements.txt --only main --without-hashes -o /tmp/requirements.txt && \
    /venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt

# Stage 2: runtime — slim base, non-root, no Poetry.
FROM python:3.13-slim AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/* && \
    useradd --system --uid 1000 --home-dir /app --shell /bin/bash resilio
COPY --from=builder /venv /venv
ENV PATH=/venv/bin:$PATH \
    PYTHONPATH=/app/backend \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY alembic.ini ./
COPY alembic/ ./alembic/
COPY resilio/ ./resilio/
COPY backend/ ./backend/
COPY .bmad-core/ ./.bmad-core/
COPY scripts/docker-entrypoint-backend.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh && \
    mkdir -p /app/data && chown -R resilio:resilio /app
USER resilio
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1
ENTRYPOINT ["/entrypoint.sh"]
CMD ["prod"]
```

**Properties:**
- Builder stage discarded — runtime image does not contain Poetry.
- Non-root user `resilio` (UID 1000).
- `curl` installed (~5MB) for `HEALTHCHECK`.
- `/app/data` created + chowned for LangGraph SQLite persistence.
- `ENTRYPOINT` = dispatching script; `CMD` selects mode (`prod` default, `dev` via compose override).
- Target image size: **~250MB** (base 50 + venv 180 + source 15 + curl 5).

---

## 2. docker-compose layout

### `docker-compose.yml` (dev — bind-mount + hot reload)

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
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-resilio}"]
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
      - checkpoint_data:/app/data
    env_file: [.env]
    environment:
      DATABASE_URL: postgresql+psycopg2://resilio:${POSTGRES_PASSWORD:-resilio}@db:5432/resilio_db
      LANGGRAPH_CHECKPOINT_DB: /app/data/checkpoints.sqlite
    depends_on:
      db: { condition: service_healthy }

  frontend:
    build: { context: ., dockerfile: Dockerfile.frontend }
    ports: ["4000:3000"]
    volumes:
      - ./apps/web:/app
      - /app/node_modules
      - /app/.next
    environment: { WATCHPACK_POLLING: "true" }
    depends_on: [backend]

volumes:
  postgres_data:
  checkpoint_data:
```

### `docker-compose.prod.yml` (override — test prod image locally)

```yaml
services:
  backend:
    command: ["prod"]
    volumes:
      - checkpoint_data:/app/data
    restart: unless-stopped
    deploy:
      resources:
        limits: { memory: 1G, cpus: "1.0" }

  frontend:
    profiles: ["donotrun"]
```

**Usage:**
- Dev: `docker compose up backend db`
- Prod-like local: `docker compose -f docker-compose.yml -f docker-compose.prod.yml up backend db`

---

## 3. `.env.example`

Complete rewrite — exhaustive, commented by group:

```bash
# ============================================================
# Resilio Plus Backend — Environment Variables
# Copy this file to .env and fill in real values.
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

**Key additions vs current file:** `ENV`, `HOST`, `PORT`, `WEB_CONCURRENCY`, `DATABASE_URL` (explicit), `POSTGRES_*` (for compose), `LANGGRAPH_CHECKPOINT_DB`, `ANTHROPIC_API_KEY`.

**Removed:** `FATSECRET_CLIENT_ID/SECRET` (class-only, hors scope per CLAUDE.md).

**NOT added (deliberately):**
- `SENTRY_DSN` — observability session will add it.
- `CLAUDE_API_KEY` — keep as code-level fallback, documented in `DEPLOYMENT.md` as alias of `ANTHROPIC_API_KEY`.

---

## 4. Health probes

### New file `backend/app/routes/health.py`

```python
"""Liveness / readiness probes — not authenticated, not athlete-scoped."""
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
        raise HTTPException(status_code=503, detail=f"db unreachable: {type(exc).__name__}")
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
                    headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
                )
            result["anthropic"] = "ok" if resp.status_code < 500 else f"http_{resp.status_code}"
            if resp.status_code >= 500:
                result["status"] = "degraded"
        except Exception as exc:
            result["anthropic"] = f"fail: {type(exc).__name__}"
            result["status"] = "degraded"

    if result["status"] != "ready":
        raise HTTPException(status_code=503, detail=result)
    return result
```

### Wiring

`backend/app/main.py` — add one import + one `include_router` at the end of the existing route list. **Does not touch** CORS middleware, logging config, or lifespan (observability session owns those).

### Tests

`tests/backend/api/test_health.py`:
1. `GET /health` → 200 `{"status": "ok"}`.
2. `GET /ready` (DB up) → 200 `{"status": "ready", "db": "ok"}`.
3. `GET /ready` (engine patched to raise) → 503.
4. `GET /ready/deep` with no API key → 503 + `"anthropic": "no_key"`.
5. `GET /ready/deep` (DB up, Anthropic mocked 200) → 200.

---

## 5. Scripts

### `scripts/docker-entrypoint-backend.sh` (refactor — dispatches prod/dev)

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

### `scripts/start_dev.ps1` (Windows host dev)

```powershell
# Start backend in dev mode (no Docker). Requires Poetry + local PostgreSQL.
$ErrorActionPreference = "Stop"

if (-not (Test-Path ".env")) {
    Write-Error ".env file missing. Copy .env.example and fill values."
}

Write-Host "[dev] installing dependencies via poetry..."
poetry install

Write-Host "[dev] running alembic migrations..."
Push-Location backend
try {
    poetry run alembic upgrade head
} finally {
    Pop-Location
}

Write-Host "[dev] starting uvicorn on http://localhost:8000 ..."
$env:PYTHONPATH = "backend"
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### `scripts/start_prod.sh` (POSIX host prod — VPS / CI)

```bash
#!/usr/bin/env bash
set -euo pipefail

if [ ! -f .env ]; then
  echo ".env file missing. Copy .env.example and fill values." >&2
  exit 1
fi
set -a; . ./.env; set +a

echo "[prod] running alembic migrations..."
PYTHONPATH=backend alembic upgrade head

WORKERS="${WEB_CONCURRENCY:-2}"
echo "[prod] starting gunicorn with $WORKERS workers on ${HOST:-0.0.0.0}:${PORT:-8000}..."
PYTHONPATH=backend exec gunicorn app.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers "$WORKERS" \
  --bind "${HOST:-0.0.0.0}:${PORT:-8000}" \
  --timeout 60 \
  --graceful-timeout 30 \
  --access-logfile - \
  --error-logfile -
```

---

## 6. `docs/backend/DEPLOYMENT.md`

Full content specified in Section 6 of working brief. Sections:

1. **Overview** — image characteristics, stateful requirements.
2. **Build** — `docker build -f Dockerfile.backend -t resilio-backend:latest .`, size check.
3. **Run locally** — dev + prod-like compose commands, probe curl examples.
4. **Environment variables** — exhaustive table (20+ vars) with Required/Default/Description columns.
5. **Hosting recommendations** — Fly.io (primary), Railway, VPS.
6. **Pre-deployment checklist** — 13 items covering secrets, CORS, DB, volumes, migrations, probes, logs, backups, image size.
7. **Troubleshooting** — common failure modes.

---

## 7. `.dockerignore` extended

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

---

## 8. `pyproject.toml` change

Add one dependency under `[project.dependencies]`:

```toml
"gunicorn>=22.0,<24.0",
```

Required by `scripts/docker-entrypoint-backend.sh` prod mode and `scripts/start_prod.sh`. Uvicorn is already present and used as the worker class.

---

## Files Modified

| File | Change |
|---|---|
| `Dockerfile.backend` | Rewrite — multi-stage (builder + runtime), non-root, HEALTHCHECK, venv-packed |
| `docker-compose.yml` | Refactor — `command: ["dev"]`, `env_file: [.env]`, `LANGGRAPH_CHECKPOINT_DB`, `checkpoint_data` volume |
| `docker-compose.prod.yml` | **New** — `command: ["prod"]`, resource limits, frontend disabled |
| `.env.example` | Rewrite — exhaustive, grouped, commented |
| `.dockerignore` | Rewrite — 70+ patterns |
| `pyproject.toml` | Add `gunicorn>=22.0,<24.0` |
| `scripts/docker-entrypoint-backend.sh` | Refactor — `prod` / `dev` dispatch |
| `scripts/start_dev.ps1` | **New** — Windows host dev |
| `scripts/start_prod.sh` | **New** — POSIX host prod |
| `backend/app/routes/health.py` | **New** — `/health`, `/ready`, `/ready/deep` |
| `backend/app/main.py` | Add `health_router` import + `include_router` (no middleware / logging changes) |
| `tests/backend/api/test_health.py` | **New** — probe tests |
| `docs/backend/DEPLOYMENT.md` | **New** — deployment guide |
| `CLAUDE.md` | V3-U phase entry + test count bump + DEPLOYMENT.md reference |

---

## Files NOT Touched

- `backend/app/` — no middleware, logging, CORS, lifespan changes (observability session owns those).
- `backend/app/integrations/strava/` — excluded per user rules.
- `Dockerfile.frontend` — frontend out of prod deploy scope for this phase.
- `poetry.lock` — `gunicorn` addition regenerates lock automatically via `poetry add`.

---

## Out of Scope

- Sentry / observability / structured logging — parallel session owns.
- `fly.toml` / `railway.json` committed configs — docs only (decision A).
- TLS termination / reverse proxy config — DEPLOYMENT.md mentions, does not prescribe.
- Autoscaling rules — hosting-specific, outside image concerns.
- Backup automation for Postgres / checkpoint volume — manual per-host.
- Frontend deployment — separate concern.

---

## Success Criteria

1. `docker build -f Dockerfile.backend -t resilio-backend:test .` succeeds.
2. Resulting image < 500MB (`docker images resilio-backend:test`).
3. `docker run --rm resilio-backend:test` starts gunicorn; `curl localhost:8000/health` returns 200 (with mapped port + DB).
4. `docker compose up backend db` works in dev (hot reload on code change).
5. `docker compose -f docker-compose.yml -f docker-compose.prod.yml up backend db` works (prod mode, no reload).
6. All existing tests still pass (2310+).
7. New health route tests pass (5 tests).
8. `.env.example` has an entry for every env var the code reads (`os.getenv` / `os.environ.get`).
