# Changelog

All notable changes to Resilio Plus are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [1.0.0] — 2026-04-10

### Summary

First production-ready release. All six development phases are complete: the
multi-agent coaching engine, full-stack web application, external connectors,
Docker infrastructure, Playwright E2E test suite, and this changelog.

---

### Phase 6 — Docker, E2E Tests, Docs (this release)

#### Added
- `docker-compose.yml`: three-service stack — `postgres:16-alpine`, FastAPI
  backend, and Next.js frontend — with health-checks and dependency ordering.
- `Dockerfile.backend`: `psycopg2-binary` added for PostgreSQL driver support.
- `backend/app/db/database.py`: reads `DATABASE_URL` env var; falls back to
  SQLite for local development and all tests. SQLite-only pragmas guarded.
- `.env.example`: documents `POSTGRES_PASSWORD`, `DATABASE_URL`, `JWT_SECRET`,
  and all connector credentials with inline comments.
- **Playwright E2E tests** (`frontend/e2e/`):
  - `login.spec.ts` — form render, invalid-credentials error, server error,
    success redirect to `/dashboard`, "Get started" navigation link.
  - `onboarding.spec.ts` — step-1 render, step 1→2 advance, back navigation,
    full 3-step wizard with API mock, 409 conflict error.
  - `dashboard.spec.ts` — week/completion display, stat cards (planned hours,
    actual hours, ACWR), next-session card, plan navigation link, auth guard.
  - `plan.spec.ts` — phase header, session list, sport badges, duration+notes,
    404 no-plan state, auth guard.
- `frontend/playwright.config.ts`: Chromium project, `webServer` starts
  `next dev`, all backend calls mocked via `page.route()`.
- `frontend/vitest.config.ts`: `exclude: ['e2e/**']` keeps Vitest from
  picking up Playwright spec files.
- `frontend/package.json`: `test:e2e` script, `@playwright/test` dev dep.
- `README.md`: Docker quick-start with `.env` copy step, environment variables
  table, local-dev SQLite note, Playwright install + run instructions,
  updated test counts and project structure.
- `CHANGELOG.md`: this file.

#### Changed
- `docker-compose.yml`: frontend port corrected to `3000:3000`; backend waits
  for postgres via `condition: service_healthy`; all connector secrets passed
  through as environment variables.
- `scripts/docker-entrypoint-backend.sh`: updated comment — table creation
  now works for both SQLite and PostgreSQL.

---

### Phase 5 — Frontend Application

#### Added
- Next.js 15 frontend with TypeScript, Tailwind CSS v4, and shadcn/ui.
- Pages: `/login`, `/onboarding` (3-step wizard), `/dashboard`, `/plan`,
  `/review`.
- `AuthProvider` with JWT token + athlete ID stored in `localStorage`.
- `ProtectedRoute` component — redirects unauthenticated visitors to `/login`.
- `TopNav` with active-link highlighting and logout button.
- `frontend/src/lib/api.ts`: typed API client covering all backend endpoints.
- 26 Vitest + React Testing Library unit tests covering all pages and
  components (all passing).
- `Dockerfile.frontend` and `.dockerignore`.

---

### Phase 4 — External Connector Framework

#### Added
- `backend/app/connectors/`: base class + four connector implementations.
  - `strava.py`: OAuth2 PKCE flow, activity sync (runs, rides, swims),
    webhook support.
  - `hevy.py`: Hevy Pro REST API, workout sync, set/rep/load mapping to
    `FatigueScore`.
  - `fatsecret.py`: FatSecret OAuth2, daily diary sync, macro extraction.
  - `terra.py`: Terra API gateway for Apple Health — HRV, sleep, steps.
- `backend/app/services/connector_service.py`: orchestrates multi-source sync.
- `backend/app/routes/connectors.py`: REST endpoints for connector CRUD and
  Strava OAuth redirect.
- `backend/app/schemas/connector.py` and `connector_api.py`: typed request /
  response models.
- Integration tests for all four connectors using `respx` HTTP mocking.

---

### Phase 3 — Core Backend Agents & API

#### Added
- **7 coaching agents** in `backend/app/agents/`:
  - `HeadCoach`: orchestrates specialist agents, resolves fatigue conflicts,
    enforces ACWR limits.
  - `RunningCoach`: VDOT lookup, 80/20 TID, Daniels/Pfitzinger/FIRST
    workout templates.
  - `LiftingCoach`: MEV/MAV/MRV volume landmarks, DUP periodization, SFR
    tier selection.
  - `SwimmingCoach`, `BikingCoach`, `NutritionCoach`, `RecoveryCoach`:
    sport-specific planning with shared `FatigueScore` protocol.
- `backend/app/core/`: `acwr.py` (EWMA), `fatigue.py`, `readiness.py`,
  `periodization.py`, `conflict.py`, `security.py` (JWT + bcrypt).
- **REST API** (`backend/app/routes/`): onboarding, auth, athletes,
  plans, reviews.
- SQLAlchemy ORM models + SQLite engine.
- 285+ pytest unit and integration tests (all passing).

---

### Phase 2 — Backend Scaffold

#### Added
- FastAPI application skeleton in `backend/app/main.py`.
- CORS middleware (permissive for development).
- Pydantic v2 schemas for all request/response types.
- Dependency injection: `get_db` session factory.
- `pyproject.toml` with Poetry: FastAPI, SQLAlchemy, python-jose,
  passlib/bcrypt, httpx, tenacity, respx (test).
- `conftest.py` with shared pytest fixtures (in-memory SQLite per test).
- Pytest configuration and directory structure under `tests/`.

---

### Phase 1 — Agent Definitions & Knowledge Base

#### Added
- `.bmad-core/agents/`: stub `.agent.md` files for all 7 coaching agents,
  each defining slash command, responsibilities, and knowledge sources.
- `.bmad-core/data/`: JSON knowledge bases — exercise database, volume
  landmark tables, zone definitions.
- `docs/coaching/methodology.md`: synthesis of 5 training books
  (Daniels, Pfitzinger Advanced, Pfitzinger Faster, Fitzgerald 80/20, FIRST).
- `docs/training_books/`: individual book summaries.
- `CLAUDE.md`: project guide for the Head Coach AI.

---

### Phase 0 — Legacy CLI & Initial Structure

#### Added
- `resilio/` legacy CLI package: VDOT calculator, Strava OAuth, CTL/ATL/TSB
  load computation, Pydantic schemas.
- `docs/superpowers/specs/` and `docs/superpowers/plans/`: design specs and
  implementation plans for all phases.
- Initial `pyproject.toml`, `.gitignore`, `LICENSE` (MIT).

---

[1.0.0]: https://github.com/simlirette/resilio-plus/releases/tag/v1.0.0
