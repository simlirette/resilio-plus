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
| Strava | ✅ Active (OAuth2) | `backend/app/connectors/strava.py` | Running, cycling, swimming (GPS, HR, power) |
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
| `backend/app/routes/` | FastAPI routers: auth, onboarding, athletes, plans, reviews, sessions, nutrition, recovery, connectors | Phase 7-8 |
| `backend/app/schemas/` | Pydantic models: athlete, plan, fatigue, nutrition, session_log, review | Phase 7-8 |
| `backend/app/db/` | SQLAlchemy models + PostgreSQL engine | Phase 2+ |
| `backend/scripts/` | DB CLI entry points (migrate, seed, reset) + seed personas (Alice, Marc) | V3-K |
| `backend/app/connectors/` | Strava, Hevy, Terra, FatSecret (class) | Phase 2+ |
| `frontend/src/app/` | Next.js pages: login, onboarding, dashboard, plan, review, session/[id], history | Phase 4-8 |
| `frontend/src/components/` | TopNav, ProtectedRoute, shadcn/ui components | Phase 4+ |
| `frontend/src/lib/` | api.ts (typed client), auth.tsx (JWT context) | Phase 4+ |
| `.bmad-core/data/` | JSON knowledge bases (exercise DB, nutrition targets) | Phase 1+ |
| `docs/superpowers/specs/` | Design specs (phase0–phase8) | Phase 0+ |
| `docs/superpowers/plans/` | Implementation plans | Phase 0+ |
| `tests/backend/` | Unit + integration tests (~47 backend-specific) | Phase 0+ |
| `tests/e2e/` | End-to-end workflow (33 tests across 6 files) | Phase 6+ |

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
| V3-O | Auth System — refresh tokens, SMTP reset, /auth/me, /logout | ✅ Complete (2026-04-14) |

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
   - `pytest tests/` must pass (≥2021 passing — état V3-J)
   - `npx tsc --noEmit` (frontend) must have no errors

**pytest path (Windows):** `C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe`

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
