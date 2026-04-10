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

**Prerequisites:** Python 3.13+, Poetry, Node 20+

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
│  Head Coach │  ← Orchestrates all agents, resolves conflicts, allocates sport budgets
└──────┬──────┘
       │
  ┌────┴────────────────────────────────────┐
  │         Specialist Agents               │
  ├─────────────────────────────────────────┤
  │ Running Coach  │ Lifting Coach          │
  │ Swimming Coach │ Biking Coach           │
  │ Nutrition Coach│ Recovery Coach         │
  └────────────────┴────────────────────────┘
       │
       ▼
  Unified Fatigue Score → Weekly Plan → Session Logs → History
```

### Coaching Agents

| Agent | Specialty | Knowledge Base |
|---|---|---|
| Head Coach | Orchestration, conflict resolution, ACWR load management, goal-driven budget allocation | Blueprint §5.1 |
| Running Coach | VDOT, 80/20 TID, Daniels/Pfitzinger/FIRST methodologies | Blueprint §5.3 |
| Lifting Coach | MEV/MAV/MRV, DUP periodization, SFR tiers | Blueprint §5.2 |
| Swimming Coach | CSS-based zones, SWOLF, propulsive efficiency | Blueprint §5.5 |
| Biking Coach | FTP, Coggan zones, CTL/ATL/TSB | Blueprint §5.4 |
| Nutrition Coach | Carb periodization by day type, protein targets, intra-effort fueling | Blueprint §5.6 |
| Recovery Coach | HRV-guided load, Readiness Score, sleep banking | Blueprint §5.7 |

### API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/athletes/onboarding` | No | Register + create first plan |
| POST | `/auth/login` | No | Get JWT token |
| GET | `/athletes/{id}/week-status` | Bearer | Current week progress |
| GET | `/athletes/{id}/plan` | Bearer | Full training plan |
| POST | `/athletes/{id}/review` | Bearer | Submit weekly review |
| GET | `/athletes/{id}/sessions/{sid}` | Bearer | Session detail + fatigue breakdown |
| POST | `/athletes/{id}/sessions/{sid}/log` | Bearer | Log actual vs planned effort |
| GET | `/athletes/{id}/history` | Bearer | Past weeks (plans + completion %) |
| GET | `/athletes/{id}/nutrition-directives` | Bearer | Daily macro targets |
| GET | `/athletes/{id}/recovery-status` | Bearer | Readiness score + HRV trend |
| GET | `/athletes/{id}/connectors` | Bearer | Connected apps status |
| POST | `/athletes/{id}/connectors/strava/authorize` | Bearer | Start Strava OAuth |

Full interactive docs: http://localhost:8000/docs

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.13, FastAPI, SQLAlchemy, SQLite |
| Frontend | Next.js 16, TypeScript, Tailwind CSS 4, shadcn/ui |
| Auth | JWT (python-jose), bcrypt passwords |
| Testing | pytest (backend, 1243+ passing), Vitest + RTL (frontend) |
| Dev tools | Poetry, Docker Compose |

---

## Project Structure

```
resilio-plus/
├── backend/app/
│   ├── agents/           # Head Coach + 7 specialist agents
│   ├── core/             # Stateless logic: ACWR, fatigue, periodization,
│   │                     # goal_analysis, running/lifting/swimming/biking/
│   │                     # nutrition/recovery logic
│   ├── connectors/       # Strava (active), Hevy, Terra, FatSecret (class)
│   ├── routes/           # HTTP endpoints (auth, plans, sessions, reviews,
│   │                     # nutrition, recovery, connectors)
│   ├── schemas/          # Pydantic models
│   └── db/               # SQLAlchemy models (7 tables) + SQLite engine
├── frontend/src/
│   └── app/              # Next.js pages:
│       ├── login/        #   Authentication
│       ├── onboarding/   #   3-step profile setup
│       ├── dashboard/    #   Week status + coach recommendations
│       ├── plan/         #   Weekly training plan (clickable sessions)
│       ├── session/[id]/ #   Session detail + fatigue visualization
│       │   └── log/      #   Post-session logging form
│       ├── review/       #   Weekly review form
│       └── history/      #   Past weeks with completion bars
├── resilio/              # Legacy CLI (read-only — VDOT tools)
├── .bmad-core/data/      # JSON knowledge bases (exercise DB, nutrition targets)
├── tests/
│   ├── backend/          # Unit tests: agents, core, api, schemas, connectors
│   └── e2e/              # End-to-end workflow (7 scenarios: onboarding → log → history)
└── docker-compose.yml
```

---

## Development

```bash
# Run all backend tests
poetry run pytest tests/ -q

# Run only E2E tests
poetry run pytest tests/e2e/ -v

# Run frontend tests
cd frontend && npm test

# Backend with auto-reload
poetry run uvicorn backend.app.main:app --reload

# Format + lint
poetry run black backend/ && poetry run ruff check backend/

# Frontend TypeScript check
cd frontend && npx tsc --noEmit
```

---

## Connected Apps

| App | Data | Status |
|-----|------|--------|
| Strava | Running, cycling, swimming (GPS, HR, power) | ✅ Active (OAuth2) |
| Hevy | Strength training (sets, reps, load) | ✅ Implemented (API key) |
| Apple Health / Terra | HRV, sleep, steps | ✅ Implemented (feeds Recovery Coach) |

> **Nutrition** is calculated directly within Resilio — no external food tracking app required.

---

## Roadmap

| Phase | Scope | Status |
|-------|-------|--------|
| 0–8 | Core backend, all 7 agents, full frontend, session logging, history | ✅ Complete |
| 9 | Connector auto-sync (Hevy→logs, Terra→recovery, Strava improved) + Settings UI | 🔜 Next |
| 10 | Analytics dashboard (ACWR trend, CTL/ATL/TSB, sport breakdown, performance) | 🔜 Planned |
| 11 | Profile edit, plan customization, ACWR alerts, notifications | 🔜 Planned |

---

## License

MIT — see [LICENSE](LICENSE)
