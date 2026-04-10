# Resilio Plus

> AI-powered multi-agent coaching platform for hybrid athletes — running, lifting, swimming, cycling.

A **Head Coach AI** orchestrates 7 specialist agents to create personalized, periodized training and nutrition plans that adapt weekly based on real performance data.

---

## Quick Start — Docker

**Prerequisites:** Docker Desktop (or Docker Engine + Compose plugin)

```bash
git clone <repo-url> resilio-plus && cd resilio-plus

# 1. Copy environment file and set your secrets
cp .env.example .env
# Edit .env — at minimum set POSTGRES_PASSWORD and JWT_SECRET

# 2. Build and start all services
docker compose build
docker compose up
```

| Service | URL |
|---------|-----|
| Backend API + interactive docs | http://localhost:8000/docs |
| Frontend | http://localhost:3000 |
| PostgreSQL | localhost:5432 (user: resilio, db: resilio) |

Tables are created automatically on first startup. To stop: `docker compose down`.
To reset the database: `docker compose down -v` (removes the postgres volume).

---

## Quick Start — Local Development

**Prerequisites:** Python 3.11+, Poetry, Node 20+

```bash
# Backend
poetry install
# Create tables (SQLite, stored in data/resilio.db)
python -c "from backend.app.db.database import Base, engine; from backend.app.db import models; Base.metadata.create_all(engine)"
poetry run uvicorn backend.app.main:app --reload

# Frontend (new terminal)
cd frontend && npm install && npm run dev
```

The backend defaults to SQLite when `DATABASE_URL` is not set — no postgres needed for local dev.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the values before running docker compose.

| Variable | Required | Description |
|----------|----------|-------------|
| `POSTGRES_PASSWORD` | Yes (Docker) | Password for the postgres `resilio` user |
| `DATABASE_URL` | Auto-set | Full postgres DSN (set by docker-compose; leave blank for local SQLite) |
| `JWT_SECRET` | Yes | Secret key for JWT token signing — use a long random string in production |
| `STRAVA_CLIENT_ID` | Optional | Strava OAuth app client ID |
| `STRAVA_CLIENT_SECRET` | Optional | Strava OAuth app secret |
| `STRAVA_REDIRECT_URI` | Optional | Strava callback URL (default: `http://localhost:8000/auth/strava/callback`) |
| `HEVY_API_KEY` | Optional | Hevy Pro API key |
| `FATSECRET_CLIENT_ID` | Optional | FatSecret OAuth2 client ID |
| `FATSECRET_CLIENT_SECRET` | Optional | FatSecret OAuth2 client secret |
| `TERRA_API_KEY` | Optional | Terra API key (Apple Health gateway) |
| `TERRA_DEV_ID` | Optional | Terra developer ID |

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
| Backend | Python 3.11+, FastAPI, SQLAlchemy, PostgreSQL (Docker) / SQLite (local) |
| Frontend | Next.js 15, TypeScript, Tailwind CSS, shadcn/ui |
| Auth | JWT (python-jose), bcrypt passwords |
| Unit/Integration tests | pytest (backend, 291 tests), Vitest + RTL (frontend, 26 tests) |
| E2E tests | Playwright (browser), pytest (API workflow) |
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
│   └── db/               # SQLAlchemy models + engine (postgres/SQLite)
├── frontend/             # Next.js App Router
│   ├── src/app/          # login, onboarding, dashboard, plan, review pages
│   └── e2e/              # Playwright browser E2E tests
├── resilio/              # Legacy CLI (read-only — running coach tools)
├── .bmad-core/data/      # JSON knowledge bases (volume landmarks, exercise DB…)
├── tests/
│   ├── backend/          # Unit + integration tests (291 passing)
│   └── e2e/              # API workflow E2E tests (6 passing)
├── docker-compose.yml    # backend + frontend + postgres
├── Dockerfile.backend
├── Dockerfile.frontend
└── .env.example          # Template — copy to .env before docker compose
```

---

## Development

```bash
# Run all backend tests
poetry run pytest tests/ -q

# Run only E2E API workflow tests
poetry run pytest tests/e2e/ -v

# Run frontend unit tests
cd frontend && npm test

# Run Playwright browser E2E tests
cd frontend
npx playwright install --with-deps chromium   # first time only
npm run test:e2e

# Backend with auto-reload
poetry run uvicorn backend.app.main:app --reload

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
