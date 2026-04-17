# Backend Contract V1 — Resilio+

**Version:** 1.0.0  
**Frozen:** 2026-04-17  
**Branch:** `session/backend-final-audit`

This document defines the invariants the backend V1 guarantees.
Any change that violates one of these invariants is a **breaking change** requiring
a version bump (V2) and a documented migration plan.

---

## Invariants d'Architecture

### 1. Hub-and-Spoke Orchestration

The Head Coach is the **sole orchestrator**. All specialist coaches (Running, Lifting,
Swimming, Biking, Nutrition, Recovery, Energy) are called exclusively through
`HeadCoach.build_week()` via `_agent_factory.py`.

No specialist coach invokes another specialist coach directly.

**Test:** `tests/e2e/test_agents_integration.py`

### 2. HITL Universal Pattern

The coaching workflow **always** interrupts at `present_to_athlete` before applying a plan.
No plan is applied without explicit athlete confirmation (`POST /workflow/plans/{thread_id}/approve`).

Sequence: `build_proposed_plan` → `present_to_athlete` **[INTERRUPT]** → athlete approves/revises → `finalize_plan`.

**Tests:** `tests/runtime/test_coaching_graph_runtime.py`

### 3. 2-Volet Architecture

Volet 1 (LangGraph coaching) and Volet 2 (Energy Cycle) are **independent**.

- Volet 2 operates without an active coaching plan
- Volet 2 never invokes LangGraph
- Flow is unidirectional: graph reads energy snapshot, never writes to EnergyCycle

**Tests:** `tests/e2e/test_volet2_standalone.py`

### 4. Mode Guard

- `full_mode`: Can create coaching plans. Cannot create external plans.
- `tracking_only`: Can create external plans. Cannot create coaching plans.
- Mode switch archives (does not delete) existing plans.

**Tests:** `tests/e2e/test_mode_switch.py`, `tests/e2e/test_tracking_only_workflow.py`

### 5. Authentication Pattern

All athlete-scoped endpoints (`/athletes/{id}/*`) require:
- Valid Bearer token in `Authorization` header
- Token `sub` must match the `{id}` in the path (ownership check via `_require_own`)

**Exceptions (intentional V1):**
- `GET /athletes/` — public (pre-auth listing for onboarding)
- `POST /athletes/onboarding` — public (registration)
- `GET /nutrition/search`, `GET /nutrition/food/{id}` — public (nutrition lookup)
- `GET /health`, `GET /ready`, `GET /ready/deep` — public (health probes)

### 6. Data Access — AgentView (Documented, Not Enforced)

`get_agent_view(state, agent)` in `backend/app/models/athlete_state.py` defines the
access matrix for agent state access. This function is **tested** but **not called** in the
production graph at V1. Agents receive the full `AthleteCoachingState`.

This is a V1 known limitation. Enforcement is a V2 feature.

---

## Invariants d'API

### Stable Endpoints (V1 Contracts)

| Method | Path | Auth | Stability |
|--------|------|------|---------|
| `POST` | `/auth/login` | Public | Stable |
| `POST` | `/auth/refresh` | Public | Stable |
| `POST` | `/auth/logout` | Bearer | Stable |
| `GET` | `/auth/me` | Bearer | Stable |
| `POST` | `/athletes/onboarding` | Public | Stable |
| `GET` | `/athletes/{id}` | Bearer | Stable |
| `PUT` | `/athletes/{id}` | Bearer | Stable |
| `PATCH` | `/athletes/{id}/mode` | Bearer | Stable |
| `POST` | `/athletes/{id}/checkin` | Bearer | Stable |
| `GET` | `/athletes/{id}/readiness` | Bearer | Stable |
| `GET` | `/athletes/{id}/energy/history` | Bearer | Stable |
| `PATCH` | `/athletes/{id}/hormonal-profile` | Bearer | Stable |
| `POST` | `/athletes/{id}/plan` | Bearer | Stable |
| `GET` | `/athletes/{id}/plans` | Bearer | Stable |
| `GET` | `/athletes/{id}/plan` | Bearer | Stable |
| `GET` | `/athletes/{id}/sessions/{session_id}` | Bearer | Stable |
| `POST` | `/athletes/{id}/sessions/{session_id}/log` | Bearer | Stable |
| `GET` | `/athletes/{id}/history` | Bearer | Stable |
| `GET` | `/athletes/{id}/today` | Bearer | Stable |
| `POST` | `/athletes/{id}/review` | Bearer | Stable |
| `GET` | `/athletes/{id}/week-status` | Bearer | Stable |
| `POST` | `/athletes/{id}/workflow/create-plan` | Bearer | Stable |
| `POST` | `/athletes/{id}/workflow/plans/{thread_id}/approve` | Bearer | Stable |
| `POST` | `/athletes/{id}/workflow/plans/{thread_id}/revise` | Bearer | Stable |
| `POST` | `/athletes/{id}/external-plan` | Bearer | Stable |
| `GET` | `/athletes/{id}/external-plan` | Bearer | Stable |
| `POST` | `/integrations/hevy/import` | Bearer | Stable |
| `POST` | `/integrations/apple-health/import` | Bearer | Stable (feature-flagged) |
| `GET` | `/health` | Public | Stable |
| `GET` | `/ready` | Public | Stable |
| `GET` | `/ready/deep` | Public | Stable |

### Response Shape Guarantees

- All 4xx responses return `{"detail": "..."}` (FastAPI default)
- All 2xx responses match Pydantic `response_model` in router decorator
- Auth errors return `403 Forbidden` (not 401) for ownership mismatches

---

## Invariants de Données

### Stable Tables

All 20 tables listed in `docs/backend-audit-2026-04-17.md § 1a` are stable.

### Migration Policy

- Alembic migrations are append-only at V1
- No `DROP COLUMN`, `DROP TABLE`, `TRUNCATE` migrations at V1
- Adding columns requires `nullable=True` or `server_default` to support rolling deploys

### Sequence

10 migrations (0001 → 0010) are committed. All must run before the app starts.
Entrypoint (`docker-entrypoint-backend.sh`) runs `alembic upgrade head` before gunicorn forks.

---

## Invariants de Tests

- **Command:** `pytest tests/ -v --tb=short`
- **Target passing:** ≥ 2430 (as of 2026-04-17 freeze)
- **Target skipped:** ≤ 16 (db_integration marker requiring live PG on port 5433)
- **Flakes accepted:** 0 (both pre-existing flakes resolved in this session)
- **Mypy:** 0 errors (`--strict`, 135 files)
- **Ruff lint:** 0 violations
- **Ruff format:** 0 reformats needed

---

## Procédure de Modification Post-Gel

1. Document justification: "nouvelle feature X" or "bug Y in production"
2. Create design doc: `docs/backend-v2/<feature>.md`
3. Branch: `git checkout -b session/backend-<feature>`
4. Apply superpowers pipeline: brainstorming → writing-plans → executing-plans
5. All invariants above must still hold after change, OR a new major version must be declared

See `BACKEND_FROZEN.md` for governance details.
