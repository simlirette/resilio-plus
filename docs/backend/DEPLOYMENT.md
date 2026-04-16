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
| Writable volume | `/app/runtime` — LangGraph SQLite checkpoints (separate from `/app/data` which ships read-only JSON knowledge bases) |

### Stateful requirements

The container expects:
- An external PostgreSQL 16+ reachable via `DATABASE_URL`.
- A writable path at `/app/runtime` for the LangGraph SQLite checkpoint store (set via `LANGGRAPH_CHECKPOINT_DB`). Mount a volume here or checkpoints reset on restart.

---

## 2. Build

```bash
docker build -f Dockerfile.backend -t resilio-backend:latest .
docker images resilio-backend:latest --format "{{.Size}}"
```

Expect ~477MB. If over 500MB, investigate (likely a `.dockerignore` regression pulling in `tests/`, `docs/`, `node_modules/`, or build artifacts).

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
| `LANGGRAPH_CHECKPOINT_DB` | no | `data/checkpoints.sqlite` | SQLite path for LangGraph checkpoints. In Docker: set to `/app/runtime/checkpoints.sqlite`. |
| `STRAVA_CLIENT_ID` | Strava users | — | OAuth client ID. |
| `STRAVA_CLIENT_SECRET` | Strava users | — | OAuth client secret. |
| `STRAVA_REDIRECT_URI` | Strava users | — | Must match Strava app config. |
| `STRAVA_ENCRYPTION_KEY` | Strava users | — | Fernet key. Generate: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. |
| `HEVY_API_KEY` | Hevy users | — | Hevy Pro API key. |
| `TERRA_API_KEY` | Terra users | — | Terra API key. |
| `TERRA_DEV_ID` | Terra users | — | Terra dev ID. |
| `USDA_API_KEY` | nutrition | — | USDA FoodData Central key (free tier). |
| `ADMIN_ATHLETE_ID` | ops | — | Athlete UUID that can reach `/admin/jobs`. |
| `SENTRY_DSN` | no | — | Sentry DSN. Leave empty to disable. |
| `SENTRY_ENVIRONMENT` | no | `development` | Sentry environment tag. |
| `SENTRY_RELEASE` | no | — | Sentry release tag. |
| `SENTRY_TRACES_SAMPLE_RATE` | no | `0.0` | Sentry tracing sample rate. |

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
#     LANGGRAPH_CHECKPOINT_DB = "/app/runtime/checkpoints.sqlite"
#   [[mounts]]
#     source = "checkpoints"
#     destination = "/app/runtime"
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
- Attach a volume to `/app/runtime` for checkpoint persistence.
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
- [ ] `/app/runtime` mount writable by UID 1000 (`resilio` user).
- [ ] Container image built from `main` and tagged (e.g., `resilio-backend:v3-u`).
- [ ] Image size under 500MB (`docker images`).
- [ ] `/health` returns 200 immediately after boot.
- [ ] `/ready` returns 200 once the DB is reachable.
- [ ] Alembic migrations ran to head on first boot (check entrypoint logs).
- [ ] Backup schedule in place for Postgres + `/app/runtime` volume.

---

## 7. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Container exits with `permission denied: /app/runtime/checkpoints.sqlite` | Volume owner is root, container is UID 1000 | `chown -R 1000:1000 /path/to/volume` on host before re-running |
| `/ready` returns 503 | DB unreachable | Check `DATABASE_URL`; confirm Postgres is up; test with `psql` from host |
| `/ready/deep` returns 503 with `"anthropic": "no_key"` | `ANTHROPIC_API_KEY` not set | Populate the env var (not just `.env.example`) |
| `alembic upgrade head` fails at boot | Migration conflict or DB schema drift | Connect with `psql`, run `alembic current`; resolve manually |
| `gunicorn` crashes with `ModuleNotFoundError: app` | `PYTHONPATH` missing | Image sets it; if running outside Docker, `export PYTHONPATH=backend` first |
| `502 Bad Gateway` behind reverse proxy | Gunicorn `--timeout` too short for LLM calls | Raise `--timeout` in `scripts/docker-entrypoint-backend.sh` (current default: 120s) |
| Image size > 500MB | `.dockerignore` regression | Inspect `docker build` context line; add missing excludes |
| Signals not reaching gunicorn (slow shutdown) | Entrypoint not using `exec` | Confirm `exec gunicorn` in `scripts/docker-entrypoint-backend.sh` |

---

## 8. References

- Spec: `docs/superpowers/specs/2026-04-16-backend-deployment-design.md`
- Plan: `docs/superpowers/plans/2026-04-16-backend-deployment.md`
- LangGraph runtime: `docs/backend/LANGGRAPH-FLOW.md`
- Background jobs: `docs/backend/JOBS.md`
- Auth: `docs/backend/AUTH.md`
