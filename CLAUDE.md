# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the Resilio Plus codebase.

## Quick Start

**What is this?** Resilio Plus is a multi-agent hybrid coaching platform for athletes who combine running, strength training, swimming, and cycling. A Head Coach AI orchestrates 7 specialist agents to create personalized, science-backed training and nutrition plans that adapt weekly based on real performance data.

**Tech Stack**: Python 3.13 (FastAPI backend), Next.js (frontend), PostgreSQL + psycopg2 (persistence), Poetry (dependency management), LangGraph (coaching orchestration).

**Master Architecture Doc**: `resilio-master-v3.md` (racine du repo) — référence unique V3.

**Key Principle**: Tools provide quantitative data; the agents provide domain expertise; the Head Coach provides integration and conflict resolution.

---

## Architecture

### 7 Coaching Agents

| Agent | File | Status | Specialty |
|---|---|---|---|
| Head Coach | `agents/head_coach.py` | ✅ Phase 7 | Orchestration, conflict resolution, goal-driven budget allocation |
| Running Coach | `agents/running_coach.py` | ✅ Phase 7 | VDOT, 80/20 TID, Daniels/Pfitzinger zones |
| Lifting Coach | `agents/lifting_coach.py` | ✅ Phase 7 | DUP periodization, MEV/MAV/MRV, SFR tiers |
| Swimming Coach | `agents/swimming_coach.py` | ✅ Phase 7 | CSS zones, SWOLF, propulsive efficiency |
| Biking Coach | `agents/biking_coach.py` | ✅ Phase 7 | FTP, Coggan zones, CTL/ATL/TSB |
| Nutrition Coach | `agents/nutrition_coach.py` | ✅ Phase 7 | Carb periodization by day type, protein, intra-effort |
| Recovery Coach | `agents/recovery_coach.py` | ✅ Phase 7 | HRV/RMSSD, readiness score, sleep banking |

All agents live in `backend/app/agents/`. The `_agent_factory.py` builds the active agent list dynamically from the athlete's sports profile.

System prompts for all 6 active agents are centralized in `backend/app/agents/prompts.py` (constants: `HEAD_COACH_PROMPT`, `RUNNING_COACH_PROMPT`, `LIFTING_COACH_PROMPT`, `RECOVERY_COACH_PROMPT`, `NUTRITION_COACH_PROMPT`, `ENERGY_COACH_PROMPT`). Clinical tone, zero encouragement, hard limits per agent. Recovery and Energy prompts contain non-overridable veto rules.

### Muscle Strain Index

`AthleteMetrics.muscle_strain: Optional[MuscleStrainScore]` — per-muscle-group fatigue score (0–100, 10 axes: quads, posterior_chain, glutes, calves, chest, upper_pull, shoulders, triceps, biceps, core).

Computed by `backend/app/core/strain.py` → `compute_muscle_strain(strava_activities, hevy_workouts, reference_date)`:
- Formula: `min(100, EWMA_7d / EWMA_28d × 100)`, capped at 100, = 0 when EWMA_28d == 0
- Cardio: `base_au = hours × IF² × 100` (IF = RPE/10, TSS-equivalent)
- Lifting: `set_load = weight_kg × reps × (rpe/10)`, distributed via `EXERCISE_MUSCLE_MAP`
- See `docs/backend/STRAIN-DEFINITION.md` for full ADR

**Radar chart thresholds:** 0–69% green, 70–84% orange, 85–100% red.

### Unified Fatigue Score (Head Coach Language)

All agents communicate via a shared `FatigueScore` (`backend/app/schemas/fatigue.py`):

```python
class FatigueScore:
    local_muscular: float    # Local muscle impact (0-100)
    cns_load: float          # Central nervous system cost (0-100)
    metabolic_cost: float    # Metabolic cost (0-100)
    recovery_hours: float    # Estimated recovery time
    affected_muscles: list   # Impacted muscle groups
```

### API Connectors

| Connector | Status | Location | Data |
|---|---|---|---|
| Strava | ✅ Active (OAuth2 V2) | `backend/app/integrations/strava/` | Running, cycling, swimming — encrypted tokens, incremental sync, `strava_activities` table |
| Hevy | ✅ Implemented (API key) | `backend/app/connectors/hevy.py` | Strength sets, reps, load |
| Terra | ✅ Implemented | `backend/app/connectors/terra.py` | HRV (RMSSD), sleep hours → Recovery Coach |
| FatSecret | ⚠️ Class only — out of scope | `backend/app/connectors/fatsecret.py` | Not used — nutrition calculated internally |

> **Nutrition approach:** Resilio calculates macros/calories internally via `NutritionCoach` + `nutrition_logic.py`. No external food tracking app needed.

---

## Repository Map

| Folder | Purpose | Phase |
|---|---|---|
| `resilio/` | Legacy Python CLI — read-only | Existing |
| `resilio/core/vdot/` | VDOT calculator — reused by Running Coach | Existing |
| `backend/app/agents/` | 7 coaching agents + base class | Phase 7 |
| `backend/app/core/` | Stateless logic: ACWR, fatigue, periodization, conflict, goal_analysis, running/lifting/swimming/biking/nutrition/recovery, **strain** | Phase 7 |
| `backend/app/routes/` | FastAPI routers: auth, onboarding, athletes, plans, reviews, sessions, nutrition, recovery, connectors, food_search, integrations | Phase 7-8 |
| `backend/app/schemas/` | Pydantic models: athlete, plan, fatigue, nutrition, session_log, review, **food** | Phase 7-8 |
| `backend/app/db/` | SQLAlchemy models + PostgreSQL engine | Phase 2+ |
| `backend/scripts/` | DB CLI entry points (migrate, seed, reset) + seed personas (Alice, Marc) + **load_fcen** | V3-K |
| `backend/app/connectors/` | Strava, Hevy, Terra, FatSecret (class) | Phase 2+ |
| `backend/app/integrations/hevy/` | Hevy CSV parser + importer (`POST /integrations/hevy/import`) | V3-P |
| `backend/app/integrations/strava/` | Strava OAuth V2: `oauth_service.py` (Fernet encryption), `activity_mapper.py`, `sync_service.py` (incremental) | V3-R |
| `backend/app/integrations/nutrition/` | USDA + OFF + FCÉN clients + unified cache-first search service | V3-P |
| `backend/app/jobs/` | APScheduler background jobs: `runner.py` (timeout wrapper + correlation_id + metrics), `registry.py` (per-athlete), `sync_jobs.py`, `compute_jobs.py`, `cleanup_jobs.py`, `scheduler.py` (global cron), `models.py` (`JobRunModel` + `AthleteStateSnapshotModel`) | V3-S |
| `backend/app/observability/` | JSON logging + PII filter + correlation ContextVars + in-memory metrics + conditional Sentry: `pii_filter.py`, `correlation.py` (ContextVar + middleware), `logging_config.py` (dictConfig), `metrics.py` (`Metrics` singleton + `MetricsMiddleware` + `track_agent_call`), `sentry.py` (conditional init) | V3-U |
| `backend/app/core/energy_patterns.py` | Pure functions: `detect_heavy_legs`, `detect_chronic_stress`, `detect_persistent_divergence`, `detect_reds_signal`, `detect_energy_patterns(db)` | V3-S (extracted from deleted `sync_scheduler.py`) |
| `frontend/src/app/` | Next.js pages: login, onboarding, dashboard, plan, review, session/[id], history | Phase 4-8 |
| `frontend/src/components/` | TopNav, ProtectedRoute, shadcn/ui components | Phase 4+ |
| `frontend/src/lib/` | api.ts (typed client), auth.tsx (JWT context) | Phase 4+ |
| `.bmad-core/data/` | JSON knowledge bases (exercise DB, nutrition targets) | Phase 1+ |
| `docs/superpowers/specs/` | Design specs (phase0–phase8) | Phase 0+ |
| `docs/superpowers/plans/` | Implementation plans | Phase 0+ |
| `tests/backend/` | Unit + integration tests (~47 backend-specific) | Phase 0+ |
| `tests/e2e/` | End-to-end workflow (71 tests across 14 files, including 8 scenario files) | Phase 6+ |
| `tests/fixtures/` | Shared E2E factories: `athlete_states.py` (Simon/Layla profiles, seed helpers) | V3-Q |

---

## Phase Status

| Phase | Scope | Status |
|---|---|---|
| 0–6 | Setup, schemas, agents v1, connectors, frontend, Docker, E2E | ✅ Complete — tagged v1.0.0 |
| 7 | Biking + Swimming + Nutrition + Recovery agents + core logic + endpoints | ✅ Complete |
| 8 | Session detail, logging, history (backend + frontend) | ✅ Complete |
| 9 | Connector sync (Hevy→SessionLog, Terra→Recovery, Strava improved) + Settings UI | ✅ Complete |
| V3-A | PostgreSQL + Alembic (4 migrations) | ✅ Complete |
| V3-B | ModeGuard + coaching_mode + PATCH /mode | ✅ Complete |
| V3-C | EnergyCycleService + check-in routes | ✅ Complete |
| V3-D | LangGraph coaching graph (11 nodes) + CoachingService + approve/revise | ✅ Complete |
| V3-E | ExternalPlan CRUD + import fichier (Claude Haiku) | ✅ Complete (S-1 + S-2) |
| V3-F | detect_energy_patterns() + challenges proactifs | ✅ Complete (S-4) |
| V3-G | Frontend check-in + energy card + tracking page | ✅ Complete (S-5 + S-6) |
| V3-H | E2E tests 2-volet + CLAUDE.md final | ✅ Complete (S-7) |
| V3-I | Agent system prompts (`prompts.py`) — 6 agents, clinical tone, hard limits | ✅ Complete (2026-04-13) |
| V3-J | Muscle Strain Index — `MuscleStrainScore`, `compute_muscle_strain()`, 20 tests | ✅ Complete (2026-04-13) |
| V3-K | DB Migrations + Seed Data (Docker db-test, 4 CLI commands, Alice + Marc personas, db_session fixture) | ✅ Complete (2026-04-13) |
| V3-L | Security Audit — CORS whitelist (env-driven), auth on `GET /athletes/`, `.gitignore` hardening, security docs (`docs/security/`) | ✅ Complete (2026-04-13) |
| V3-M | Book Extractions — 5 running books → structured agent-actionable extracts + INDEX.md (`docs/backend/books/`) | ✅ Complete (2026-04-13) |
| V3-N | Knowledge JSONs Audit — 9 JSON files enriched (111 rules total, 2→20 per file), common schema, 90 pytest tests, KNOWLEDGE-JSONS.md | ✅ Complete (2026-04-14) |
| V3-N2 | Knowledge JSONs Enrichment — book extractions as primary source, 9 files re-enriched (111→164 rules), source_books fields populated | ✅ Complete (2026-04-14) |
| V3-O | Auth System — refresh tokens, SMTP reset, /auth/me, /logout | ✅ Complete (2026-04-14) |
| V3-P | Hevy CSV Import (`POST /integrations/hevy/import`) + Nutrition Lookup Service (`GET /nutrition/search`, `GET /nutrition/food/{id}`) — USDA FDC + OFF + FCÉN, SQLite TTL cache, Alembic migration 0007 | ✅ Complete (2026-04-14) |
| V3-Q | E2E Coaching Scenarios — 8 scenario tests (CoachingService + HeadCoach.build_week), shared `athlete_states.py` fixtures, energy cap, RED-S veto, reject/revise, luteal phase, living spec `docs/backend/E2E-SCENARIOS.md` | ✅ Complete (2026-04-14) |
| V3-R | Strava OAuth V2 — Fernet-encrypted tokens, incremental sync (`last_sync_at`), `strava_activities` table, `/integrations/strava/{connect,callback,sync}`, Alembic 0008, old Strava routes removed | ✅ Complete (2026-04-14) |
| V3-S | Background Jobs — APScheduler 3.x, `backend/app/jobs/` (runner, registry, sync/compute/cleanup jobs, scheduler), `job_runs` + `athlete_state_snapshots` tables, Alembic 0009, `GET /admin/jobs` endpoint, `energy_patterns.py` extracted, old `sync_scheduler.py` deleted | ✅ Complete (2026-04-16) |
| V3-T | LangGraph Runtime Validation — SQLite checkpointer (replaces MemorySaver), `CoachingService` module-level singleton, `log_node` decorator + structured JSON logs, runtime test suite (`tests/runtime/`, 26 tests), debug endpoint `GET /athletes/{id}/coach/session/{thread_id}/state`, smoke script `scripts/smoke_test_runtime.py`, `docs/backend/LANGGRAPH-FLOW.md` | ✅ Complete (2026-04-14) |
| V3-U | Observability stack — `backend/app/observability/` (6 modules, 57 tests), JSON structured logging via dictConfig, PII filter (field-name blocklist + JWT/Bearer/email/hex regex scrubbers) attached at root logger, `CorrelationIdMiddleware` (reads/echoes `X-Request-ID`), `MetricsMiddleware` + `track_agent_call` context manager, `Metrics` singleton (HTTP/agent/job counters + bounded LatencySummary with p50/p95/p99), `GET /admin/metrics` (gated by `ADMIN_ATHLETE_ID`), conditional Sentry init (no-op without `SENTRY_DSN` or sentry-sdk), `run_job()` instrumented with `job-<uuid>` correlation + `contextvars.copy_context()` for worker thread, `HeadCoach.build_week` + specialist calls wrapped with `track_agent_call`, `docs/backend/OBSERVABILITY.md` | ✅ Complete (2026-04-16) |
| V3-V | Backend Deployment — multi-stage `Dockerfile.backend` (477MB, non-root UID 1000, `curl` HEALTHCHECK), `/health` + `/ready` + `/ready/deep` probes (`backend/app/routes/health.py`, 5 tests), gunicorn entrypoint with Alembic migration + WAL sqlite preload, `data/` JSONs baked in image, `/app/runtime` checkpoint volume (split from `/app/data`), `docker-compose.yml` (dev + env_file) + `docker-compose.prod.yml` (gunicorn + resource limits), exhaustive `.env.example` (ANTHROPIC_API_KEY, LANGGRAPH_CHECKPOINT_DB, process control), `scripts/start_dev.ps1` + `scripts/start_prod.sh`, `docs/backend/DEPLOYMENT.md` (Fly.io / Railway / VPS recipes + env table + pre-deploy checklist) | ✅ Complete (2026-04-16) |

**Dernières phases complétées (2026-04-16) :** V3-V livré — Backend dockerisé production-ready. Multi-stage build 477MB (<500MB cible), non-root user `resilio` UID 1000, HEALTHCHECK via `curl /health`. Entrypoint dispatches `prod` (gunicorn + UvicornWorker, `--timeout 120` pour LangGraph LLM calls) vs `dev` (uvicorn --reload). Triad de probes: `/health` (liveness), `/ready` (DB SELECT 1), `/ready/deep` (DB + Anthropic API via httpx). Trois bugs chassés pendant smoke test: (1) `.dockerignore` excluait `data/` entier → JSONs manquaient → fix `!data/*.json`; (2) volume checkpoint mount à `/app/data` shadow-ait les JSONs → split vers `/app/runtime`; (3) gunicorn workers racaient sur `PRAGMA journal_mode=WAL` (SQLITE_BUSY) → entrypoint pré-initialise checkpoint DB dans un process unique avant fork. Env vars exhaustives avec SENTRY_*. Compose base + prod override pattern. Scripts host launchers Windows (PS1) + POSIX (bash). DEPLOYMENT.md couvre Fly.io, Railway, VPS. 2378 tests passing (aucune régression).

**Dernières phases complétées (2026-04-16) :** V3-U livré — Observability stack. Structured JSON logs via `configure_logging()` (dictConfig, PII filter at ROOT logger level so it runs before pytest caplog / Sentry). Every HTTP request carries `X-Request-ID` echoed back; `correlation_id` + `athlete_id` ContextVars merged into every log line. In-memory metrics (reset on restart) at `GET /admin/metrics`: HTTP requests_total + latency_ms per `(method, path_template)`, agent calls_total + latency_ms per `(agent, ok/error)`, jobs runs_total per `(job_type, ok/error/timeout)`. `track_agent_call("head_coach")` wraps `build_week` body; specialist loop switches from list-comp to `for a in self.agents: with track_agent_call(f"{a.name}_coach"):`. `run_job()` uses `contextvars.copy_context()` so the worker thread inherits the correlation id. Sentry conditional: no-op when `SENTRY_DSN` empty or `sentry-sdk` missing (`sentry-sdk[fastapi]>=2.0` added to pyproject). `.env.example` adds `SENTRY_DSN`, `SENTRY_ENVIRONMENT`, `SENTRY_RELEASE`, `SENTRY_TRACES_SAMPLE_RATE`. 2378 tests passing (+57 new); 2 pre-existing unrelated failures unchanged.

**Dernières phases complétées (2026-04-14) :** V3-T livré — LangGraph runtime fix. `build_coaching_graph(checkpointer, ...)` requires explicit checkpointer (no more per-request `MemorySaver` losing state between create/approve). Production wires `SqliteSaver` at `LANGGRAPH_CHECKPOINT_DB` (default `data/checkpoints.sqlite`). `coaching_service` singleton in `app.services.coaching_service` shared across `workflow.py` endpoints. Every node wrapped with `log_node` (JSON enter/exit logs to `resilio.graph`). 26 runtime tests cover topology, checkpoint persistence, interrupt/resume, state transitions, revision loop. Found + fixed `_after_revise` routing bug (revision_count > 1 routes to `build_proposed_plan` not `present_to_athlete` because `revise_plan` clears `proposed_plan_dict`). 2310 tests passing (2 pre-existing unrelated failures: `test_history_shows_logged_count` flake, `test_high_continuity_no_breaks` date drift).

**Dernières phases complétées (2026-04-16) :** V3-S livré — APScheduler background jobs system. Per-athlete dynamic jobs (strava 1h, hevy/terra 6h) registered on connect. Global cron jobs (daily snapshot 4h UTC, energy patterns Mon 6h, cleanup Sun 3h). `run_job()` wrapper with threading timeout + DB logging. `GET /admin/jobs` (env-gated via `ADMIN_ATHLETE_ID`). Pure energy-pattern functions extracted to `core/energy_patterns.py`; `core/sync_scheduler.py` deleted. Alembic 0009 adds `job_runs` + `athlete_state_snapshots`. Docs at `docs/backend/JOBS.md`.

**Dernières phases complétées (2026-04-14) :** V3-R livré — Strava OAuth V2 with encrypted tokens (`cryptography.fernet`), incremental sync, `strava_activities` DB table, new routes at `/integrations/strava/`. Old plaintext Strava routes removed. Alembic migration 0008 renames columns (preserves data). 2271 tests passing.

**Dernières phases complétées (2026-04-14) :** V3-Q livré — 8 E2E scenario tests (38 tests), shared `athlete_states.py` fixtures, living spec `docs/backend/E2E-SCENARIOS.md`.

**Dernières phases complétées (2026-04-14) :** V3-P livré — Hevy CSV import (26 tests) + Nutrition Lookup Service (USDA/OFF/FCÉN, cache TTL, ~35 new tests). 2211 tests passing.

**Dernières phases complétées (2026-04-14) :** Knowledge JSONs V3-N2 livré — 9 fichiers enrichis (164 règles total, +53 vs V3-N), book extractions used as primary source. 90 tests passing.

**Dernières phases complétées (2026-04-14) :** Auth system V3-O livré — refresh tokens rotation, SMTP password reset, /auth/me + /auth/logout. ~2161 tests passing.

**Dernières phases complétées (2026-04-14) :** Knowledge JSONs audit livré — 9 fichiers enrichis (111 règles), JSON Schema, 90 tests parametrized. 2115 tests passing.

**Dernières phases complétées (2026-04-13) :** Agent system prompts centralisés + Muscle Strain Index + DB Migrations & Seed Data + Security Audit + Book Extractions livrés. 2024 tests passing.

**Dernières phases complétées (2026-04-12) :** Backend V3 finalisé — architecture 2-volets opérationnelle, 35 tests E2E, mode switch validé, invariants modularité prouvés. Voir `BACKEND_V3_COMPLETE.md` pour l'état consolidé.

**Vague 1 Frontend complétée 2026-04-12 —** 4 sessions parallèles consolidées en 2 merges. Desktop (Tauri), Mobile (Expo), ESLint rules, hex cleanup, API client généré — tous livrés. Voir `FRONTEND_VAGUE1_POSTMORTEM.md`.

---

## Running Coach Knowledge Base

The Running Coach has the richest existing knowledge base.

### Books (5) — summaries in `docs/training_books/`, synthesis in `docs/coaching/methodology.md`

- **Daniels' Running Formula** — VDOT, training zones (E/M/T/I/R paces)
- **Pfitzinger's Advanced Marathoning** — volume periodization, marathon-specific blocks
- **Pfitzinger's Faster Road Racing** — 5K to half-marathon training
- **Fitzgerald's 80/20 Running** — TID: 80% easy / 20% hard
- **FIRST's Run Less, Run Faster** — 3 quality sessions per week, intensity over volume

### Training Zones (Daniels/Seiler hybrid)

| Zone | %HRmax | Weekly Volume | Purpose |
|---|---|---|---|
| Z1 Easy | 60-74% | 75-80% | Base aerobic, mitochondrial adaptation |
| Z2 Tempo | 80-88% | 5-10% | Lactate threshold, economy |
| Z3 VO2max | 95-100% | 5-8% | Maximal aerobic capacity |
| Z4 Repetition | N/A | 2-5% | Running economy, fast-twitch recruitment |

### Progression Rules

- Never increase weekly volume >10% week-over-week
- Deload every 3-4 weeks: -20-30% volume
- Increase in order: frequency → duration → intensity

---

## Development Rules

1. **`resilio/` is read-only** — legacy CLI, do not modify
2. **New logic goes in `backend/`**
3. **TDD mandatory** — red → green → refactor on every feature
4. **Frequent atomic commits** — one commit per logical task
5. **Verify invariants after every task**:
   - `poetry install` must succeed
   - `pytest tests/` must pass (≥2378 passing — état V3-U; 2 pre-existing unrelated failures: `test_history_shows_logged_count` flake, `test_high_continuity_no_breaks` date drift)
   - `npx tsc --noEmit` (frontend) must have no errors

**pytest path (Windows):** `C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe`

---

## Docker / Deployment Gotchas (V3-V)

- **Module-relative data paths:** `backend/app/core/allostatic.py`, `energy_availability.py`, `running_logic.py` use `pathlib.Path(__file__).parents[3] / "data" / "*.json"` → image must `COPY data/ ./data/` AND `.dockerignore` must allow-list with `!data/*.json` (the `data` exclude rule would otherwise drop them).
- **Checkpoint volume ≠ data dir:** Mount the LangGraph SQLite checkpoint volume at `/app/runtime/` (not `/app/data/`) — mounting over `/app/data` shadows the baked-in JSONs. Default: `LANGGRAPH_CHECKPOINT_DB=/app/runtime/checkpoints.sqlite`.
- **SQLite WAL race with gunicorn:** Two workers calling `PRAGMA journal_mode=WAL` concurrently crashes with "database is locked". Fix: entrypoint pre-initializes the checkpointer in a single process before gunicorn forks. See `scripts/docker-entrypoint-backend.sh`.
- **Gunicorn timeout:** Must be ≥120s — LangGraph sync LLM calls exceed the default 60s and cause 502s.
- **Poetry 2.x required:** `pyproject.toml` uses PEP 621 `[project]` metadata which Poetry 1.8 rejects. Builder stage installs `poetry==2.3.3 poetry-plugin-export==1.8.0`.

## Testing Gotchas

- **Mocking httpx in FastAPI tests:** `TestClient` extends `httpx.Client`, so `patch.object(httpx.Client, "get", ...)` intercepts the TestClient's own ASGI dispatch. Use `respx.mock(base_url="https://api.example.com")` to scope the patch to the real external URL. Example: `tests/backend/api/test_health.py::test_ready_deep_all_green`.

---

## ACWR Rule (applies to coaching logic AND load planning)

ACWR (Acute:Chronic Workload Ratio) = 7-day load / 28-day rolling average:
- **0.8–1.3**: Safe zone
- **1.3–1.5**: Caution — flag to athlete
- **>1.5**: Danger zone — significant injury risk, must reduce load

Use EWMA (Exponentially Weighted Moving Average) rather than simple rolling average.
Never increase total weekly load >10% in one step (applies across ALL sports combined).

---

## Key References

- **Master Architecture V3**: `resilio-master-v3.md` ← RÉFÉRENCE PRINCIPALE BACKEND
- **Master Frontend V1**: `frontend-master-v1.md` ← RÉFÉRENCE PRINCIPALE FRONTEND
- **Frontend Audit Session 0**: `FRONTEND_AUDIT.md`
- **Roadmap Phases 9–11**: `docs/superpowers/specs/2026-04-09-phases7-11-roadmap.md`
- **Architecture Modulaire 2-Volets**: `docs/superpowers/specs/2026-04-11-modular-architecture-design.md`
- **Phase 8 Design**: `docs/superpowers/specs/2026-04-10-phase8-design.md`
- **Coaching Methodology**: `docs/coaching/methodology.md`
- **Strain Index ADR**: `docs/backend/STRAIN-DEFINITION.md`
- **Database Guide**: `docs/backend/DATABASE.md`
- **Agent Prompts Spec**: `docs/superpowers/specs/2026-04-13-agent-prompts-design.md`
- **Muscle Strain Spec**: `docs/superpowers/specs/2026-04-13-muscle-strain-design.md`
- **Security Audit (2026-04-13)**: `docs/security/AUDIT-2026-04-13.md` — findings + status
- **Manual Security Actions**: `docs/security/MANUAL-ACTIONS.md` — credential rotation (Strava + Hevy) + BFG plan
- **Security Checklist**: `docs/security/SECURITY-CHECKLIST.md` — pre-PR security gates
- **Book Extractions Index**: `docs/backend/books/INDEX.md` — coverage matrix, conflicts, JSON + prompt candidates
- **Book Extraction Spec**: `docs/superpowers/specs/2026-04-13-book-extraction-design.md`
- **Knowledge JSONs Reference**: `docs/backend/KNOWLEDGE-JSONS.md` — coverage table, schema, validation command
- **Knowledge JSONs Audit Spec**: `docs/superpowers/specs/2026-04-13-knowledge-jsons-audit-design.md`
- **Knowledge JSONs Schema**: `docs/knowledge/schemas/common_rule.schema.json`
- **Auth System**: `docs/backend/AUTH.md` — endpoints, flows, curl/TypeScript examples
- **Integrations Reference**: `docs/backend/INTEGRATIONS.md` — Hevy CSV import + Nutrition Lookup (USDA/OFF/FCÉN, TTL cache, FCÉN bootstrap)
- **Strava OAuth V2 Spec**: `docs/superpowers/specs/2026-04-14-strava-oauth-design.md`
- **Strava OAuth V2 Plan**: `docs/superpowers/plans/2026-04-14-strava-oauth.md`
- **Background Jobs Reference**: `docs/backend/JOBS.md` — job types, scheduling, debugging SQL, monitoring endpoint
- **Background Jobs Spec**: `docs/superpowers/specs/2026-04-14-background-jobs-design.md`
- **Background Jobs Plan**: `docs/superpowers/plans/2026-04-14-background-jobs.md`
- **LangGraph Flow Reference**: `docs/backend/LANGGRAPH-FLOW.md` — graph topology, node table, conditional edges, interrupt + checkpoint lifecycle, debug endpoint
- **LangGraph Runtime Spec**: `docs/superpowers/specs/2026-04-14-langgraph-runtime-design.md`
- **LangGraph Runtime Plan**: `docs/superpowers/plans/2026-04-14-langgraph-runtime.md`
- **Observability Reference**: `docs/backend/OBSERVABILITY.md` — log format, correlation IDs, `/admin/metrics`, PII filter, Sentry env vars, cheat sheet
- **Observability Spec**: `docs/superpowers/specs/2026-04-16-observability-design.md`
- **Observability Plan**: `docs/superpowers/plans/2026-04-16-observability.md`
- **Deployment Reference**: `docs/backend/DEPLOYMENT.md` — Dockerfile, compose, env vars, Fly.io / Railway / VPS recipes, pre-deploy checklist, troubleshooting
- **API Contract**: `docs/backend/API-CONTRACT.md` — tous les endpoints (méthode, path, auth, schemas request/response, codes d'erreur), interfaces TypeScript exactes, exemples curl+TS, Quick Start frontend
- **Athlete State Model**: `docs/backend/ATHLETE-STATE.md` — AthleteState schema complet, AgentView matrice d'accès (8 agents × 9 sections), règles de mise à jour, états typiques, formule Strain EWMA
- **Deployment Spec**: `docs/superpowers/specs/2026-04-16-backend-deployment-design.md`
- **Deployment Plan**: `docs/superpowers/plans/2026-04-16-backend-deployment.md`
- **Master V2 (archivé)**: `docs/archive/resilio-master-v2_archived_2026-04-12.md`

---

## Workspace Structure (Monorepo pnpm — Session 0, 2026-04-12)

```
resilio-plus/
├── apps/
│   ├── web/        — @resilio/web    — Next.js 16 (prod)
│   ├── desktop/    — @resilio/desktop — Tauri (scaffold Vague 1)
│   └── mobile/     — @resilio/mobile  — Expo iOS (scaffold Vague 1)
├── packages/
│   ├── design-tokens/ — @resilio/design-tokens
│   ├── ui-web/        — @resilio/ui-web
│   ├── ui-mobile/     — @resilio/ui-mobile
│   ├── api-client/    — @resilio/api-client
│   ├── shared-logic/  — @resilio/shared-logic
│   └── brand/         — @resilio/brand
├── backend/        — FastAPI Python (inchangé)
├── pnpm-workspace.yaml
└── package.json    — root scripts
```

**Commandes clés :**
- `pnpm install` — installe tout le workspace
- `pnpm --filter @resilio/web dev` — lance le Next.js
- `pnpm --filter @resilio/web typecheck` — vérifie les types
- `pnpm --filter @resilio/web build` — build production

---

## Règles absolues frontend (8)

1. **Jamais d'import direct de `lucide-react`** en dehors de `packages/ui-web/`
2. **Jamais d'import direct de `lucide-react-native`** en dehors de `packages/ui-mobile/`
3. **Jamais de valeur de couleur hardcodée** en dehors de `packages/design-tokens/` — utiliser CSS vars (`var(--card)`, `var(--foreground)`, etc.)
4. **Toujours passer par `@resilio/api-client`** pour les appels backend (migration en cours)
5. **Tailwind `dark:` variants obligatoires** sur toute nouvelle classe Tailwind colorée + CSS variables pour inline styles
6. **Commits conventionnels obligatoires** : `feat(web)`, `feat(desktop)`, `feat(mobile)`, `chore(tokens)`, `fix(web)`, etc.
7. **Tests non négociables** pour `shared-logic` et `api-client`
8. **Pas de logique métier dans les composants UI** — toujours dans `shared-logic` ou dans l'app
9. **Pour toute session parallèle future, utiliser `git worktree add`** pour isoler les working trees. Ne jamais lancer 2+ sessions dans le même dossier local.

---

**Agents provide domain expertise. The Head Coach provides integration. Tools provide data. You provide judgment.**
