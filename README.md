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
poetry run uvicorn backend.app.main:app --reload

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
| Frontend | Next.js 15, TypeScript, Tailwind CSS, shadcn/ui |
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
# Run all backend tests
poetry run pytest tests/ -q

# Run frontend tests
cd frontend && npm test

# Run only E2E tests
poetry run pytest tests/e2e/ -v

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
