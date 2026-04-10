# AUDIT-RESILIO.md

**Date :** 2026-04-10  
**Scope :** `C:\resilio-plus` (local) · `C:\Users\simon\resilio-plus` (local + GitHub)  
**Repo GitHub :** https://github.com/simlirette/resilio-plus

---

## 1. ÉTAT DU REPO GITHUB

### Branches existantes

| Branche | Commits | Dernier commit | État |
|---------|---------|----------------|------|
| `main` | 365 | `472c3b3` — chore: add agent skill files, .gitignore | Actif — projet canonique |
| `master` | 118 | `376ef37` — fix: remove stale README section | Stale — 24 commits en retard sur le local |

### Branche `main` — fichiers clés présents

Architecture **FastAPI + SQLite + Phases 0–8** :

```
backend/app/
  agents/          — 7 agents (base, head, running, lifting, swimming, biking, nutrition, recovery)
  core/            — acwr, fatigue, periodization, goal_analysis, conflict, readiness, running/lifting/
                     swimming/biking/nutrition/recovery logic, security
  connectors/      — strava, hevy, terra, fatsecret (stub)
  routes/          — auth, athletes, onboarding, plans, reviews, sessions, nutrition, recovery, connectors
  schemas/         — athlete, auth, connector, fatigue, nutrition, plan, review, session_log
  db/              — database.py (SQLite), models.py (7 tables)
.bmad-core/
  agents/          — 7 agent .md (head, running, lifting, swimming, biking, nutrition, recovery)
  data/            — exercise-database.json, volume-landmarks.json, nutrition-targets.json,
                     running-zones.json, cycling-zones.json, swimming-benchmarks.json
frontend/src/app/  — login, onboarding, dashboard, plan, session/[id], review, history
tests/             — 89 fichiers test_*.py, 1243+ tests passing
docs/superpowers/
  specs/           — 2026-04-10-merge-resilio-design.md (nouveau)
  plans/           — phase8, phase9, phase10, phase11 (nouveaux)
.agents/skills/    — 8 skills (complete-setup, first-session, macro-plan-create, weekly-*)
.claude/skills/    — idem + bike-coach, head-coach, lift-coach, nutrition-coach, run-coach, swim-coach
```

**Fichiers absents de `main` (vs design `resilio-master-v2.md`) :**
- `resilio-master-v2.md` — document maître
- `data/vdot_paces.json` — table VDOT 20–85
- `data/muscle_overlap.json` — chevauchement musculaire
- `data/agent_view_map.json` — token economy mapping
- `data/food_database_cache.json` — cache aliments
- `core/config.py` — Pydantic SettingsConfigDict
- `agents/*/system_prompt.md` — system prompts agents (format master)
- `alembic/` — migrations PostgreSQL
- `resilio_docs/` — 9 fichiers JSON connaissances scientifiques
- `training_books/` — 5 livres résumés
- LangGraph : `agents/head_coach/graph.py`, `merger.py`, `resolver.py`, `weekly_nodes.py`

### Branche `master` — fichiers clés présents

Architecture **LangGraph + PostgreSQL + asyncpg** (sessions S1–S14) :

```
agents/
  base_agent.py, head_coach/, running_coach/, lifting_coach/, recovery_coach/
  (PAS biking_coach, swimming_coach, nutrition_coach — sessions S15–S19 non poussées)
api/v1/  — auth, athletes, connectors, apple_health, files, food, plan, workflow
core/    — config.py, acwr.py, vdot.py, constraint_matrix.py, security.py, weekly_review.py
models/  — database.py, schemas.py, views.py, athlete_state.py, weekly_review.py
connectors/ — strava, hevy, apple_health, gpx, fit, food_search
data/    — exercise_database.json (seul fichier de data/ sur master)
alembic/ — 3 migrations (initial schema, connector credentials, fatigue snapshot unique)
frontend/ — dashboard, calendar, chat, weekly-review, login, register, plan/running+lifting
tests/   — 40+ test files (S1–S14), ~157 tests
```

**Fichiers sur `master` absents de `main` :**
- `resilio-master-v2.md`, `resilio-nutrition-coach-section.md`
- `agents/head_coach/graph.py` — LangGraph StateGraph (11 nodes S1–S10)
- `agents/head_coach/resolver.py`, `merger.py`, `weekly_nodes.py`, `edge_cases/`
- `core/config.py`, `core/constraint_matrix.py`, `core/weekly_review.py`
- `models/athlete_state.py`, `models/views.py` (get_agent_view)
- `api/v1/workflow.py` — POST /workflow/plan (HiTL)
- `alembic/` (3 migrations PostgreSQL)
- `docs/superpowers/plans/` sessions 1–10, 14

### Fichiers en double (même nom, contenu différent)

| Fichier | `main` | `master` | Différence |
|---------|--------|----------|------------|
| `CLAUDE.md` | Phases 0–8, SQLite, FastAPI | Sessions 1–14, PostgreSQL, LangGraph | Architectures incompatibles |
| `docker-compose.yml` | SQLite only (1 service) | PostgreSQL + API (2 services) | DB différente |
| `pyproject.toml` | Poetry, Python 3.13 | Poetry, Python 3.12 | Version Python |
| `frontend/src/lib/api.ts` | Next.js typed client, Phases 4–8 | Next.js typed client, S11–S13 | Routes API différentes |
| `tests/conftest.py` | SQLite StaticPool, fixtures Phases 0–8 | PostgreSQL/Simon fixtures | Incompatibles |

---

## 2. ÉTAT DES DOSSIERS LOCAUX

### `C:\resilio-plus` — Arborescence principale

```
C:\resilio-plus\
├── CLAUDE.md                          — Sessions 1–19 ✅ (projet 100% done selon S19)
├── resilio-master-v2.md               — Document maître V2 (NON committé sur master)
├── resilio-nutrition-coach-section.md — Section 6B (NON committé)
├── agents/
│   ├── base_agent.py
│   ├── head_coach/                    — graph.py, merger.py, resolver.py, weekly_nodes.py, edge_cases/
│   ├── running_coach/                 — agent.py, prescriber.py, running_coach_system_prompt.md*
│   ├── lifting_coach/                 — agent.py, prescriber.py, system_prompt.md.txt*
│   ├── recovery_coach/                — agent.py, prescriber.py, recovery_coach_system_prompt.md*
│   ├── nutrition_coach/               — agent.py, prescriber.py, nutrition_coach_system_prompt.md ✅ S15
│   ├── swimming_coach/                — agent.py, prescriber.py, swimming_coach_system_prompt.md ✅ S16
│   └── biking_coach/                  — agent.py, prescriber.py, biking_coach_system_prompt.md ✅ S16
├── api/
│   ├── main.py, deps.py, endpoints_design.md*
│   └── v1/  auth.py, athletes.py, connectors.py, apple_health.py, files.py, food.py, plan.py, workflow.py
├── connectors/  strava.py, hevy.py, apple_health.py, gpx.py, fit.py, food_search.py, fcen.py
├── core/  config.py, acwr.py, vdot.py, constraint_matrix.py, security.py, weekly_review.py, sync_scheduler.py
├── models/  athlete_state.py, database.py, db_session.py*, schemas.py, views.py, weekly_review.py
├── data/
│   ├── exercise_database.json         — ✅ committé sur master
│   ├── fcen_nutrients.csv             — ✅ S17
│   ├── agent_view_map.json*           — NON committé
│   ├── food_database_cache.json*      — NON committé
│   ├── muscle_overlap.json*           — NON committé
│   ├── nutrition_targets.json*        — NON committé
│   ├── running_zones.json*            — NON committé
│   ├── vdot_paces.json*               — NON committé
│   └── volume_landmarks.json*         — NON committé
├── alembic/versions/
│   ├── 55a168264480_initial_schema.py
│   ├── d54fb4efd721_add_connector_credentials.py
│   ├── 37168fe9feab_add_fatigue_snapshot_unique_athlete_date.py
│   └── a1b2c3d4e5f6_add_email_password_hash_to_athletes.py  ✅ S2 (NON pushé)
├── tests/  43 fichiers test_*.py (235 tests)
├── frontend/  Next.js complet (S11–S19), incluant chat, settings, plan nutrition/swim/bike
├── resilio_docs/resilio_docs/  9 JSON connaissances scientifiques (NON committés)
├── training_books/              5 livres résumés (NON committés)
├── docker-compose.yml           PostgreSQL + API
└── pyproject.toml               Python 3.12, LangGraph, asyncpg, APScheduler

* = fichier existant localement mais NON committé sur origin/master
```

**Situation git de `C:\resilio-plus` :**
- Branche locale : `master`
- Remote : `origin` → `simlirette/resilio-plus`
- 142 commits locaux vs 118 sur `origin/master` → **24 commits non pushés**
- Commits locaux non pushés (S15–S19) : NutritionCoach, SwimmingCoach, BikingCoach, FCÉN, APScheduler, LangGraph wiring, frontend complet
- Fichiers modifiés non committés : `agents/running_coach/prescriber.py`, `alembic/env.py`, 4 fichiers test
- Fichiers jamais committés : `data/*.json` (7 fichiers), system prompts, `resilio-master-v2.md`, `resilio_docs/`, `training_books/`

### `C:\Users\simon\resilio-plus` — Arborescence principale

```
C:\Users\simon\resilio-plus\
├── CLAUDE.md                          — Phases 0–8, roadmap 9–11 définie
├── README.md
├── backend/app/
│   ├── agents/  base.py, head, running, lifting, swimming, biking, nutrition, recovery coaches
│   ├── core/    acwr, fatigue, periodization, goal_analysis, conflict, readiness, running/lifting/
│   │            swimming/biking/nutrition/recovery logic, security
│   ├── connectors/  strava, hevy, terra, fatsecret (stub) — PAS apple_health, gpx, fit
│   ├── routes/  auth, athletes, onboarding, plans, reviews, sessions, nutrition, recovery, connectors
│   ├── schemas/ athlete, auth, connector, fatigue, nutrition, plan, review, session_log
│   └── db/      database.py (SQLite sync), models.py (7 tables)
├── .bmad-core/data/
│   ├── exercise-database.json, volume-landmarks.json, nutrition-targets.json
│   ├── running-zones.json, cycling-zones.json, swimming-benchmarks.json
│   └── (PAS vdot_paces, muscle_overlap, agent_view_map, food_database_cache)
├── .bmad-core/agents/  7 agent .md files (head, running, lifting, swimming, biking, nutrition, recovery)
├── frontend/src/app/   login, onboarding, dashboard, plan, session/[id]/log, review, history
├── tests/              89 fichiers test_*.py, 1243+ tests
├── data/               UNIQUEMENT resilio.db (base de données SQLite de dev)
├── docs/superpowers/
│   ├── specs/  2026-04-10-merge-resilio-design.md
│   └── plans/  phase8, phase9, phase10, phase11
├── docker-compose.yml  SQLite, 2 services (backend + frontend)
└── pyproject.toml      Python 3.13, FastAPI, SQLite, synchronous SQLAlchemy
```

### Ce qui existe dans `C:\resilio-plus` mais PAS dans `C:\Users\simon\resilio-plus`

| Catégorie | Fichiers dans `C:\resilio-plus` uniquement |
|-----------|---------------------------------------------|
| LangGraph | `agents/head_coach/graph.py`, `merger.py`, `resolver.py`, `weekly_nodes.py`, `edge_cases/` |
| Models | `models/athlete_state.py` (LangGraph state), `models/views.py` (get_agent_view), `models/db_session.py` (asyncpg) |
| Core | `core/config.py`, `core/constraint_matrix.py`, `core/weekly_review.py`, `core/sync_scheduler.py` |
| Connectors | `connectors/apple_health.py`, `connectors/gpx.py`, `connectors/fit.py`, `connectors/food_search.py`, `connectors/fcen.py` |
| Data JSON | `data/vdot_paces.json`, `data/muscle_overlap.json`, `data/agent_view_map.json`, `data/food_database_cache.json`, `data/nutrition_targets.json`, `data/running_zones.json`, `data/volume_landmarks.json`, `data/fcen_nutrients.csv` |
| API | `api/v1/workflow.py` (POST /workflow/plan), `api/v1/food.py`, `api/v1/apple_health.py`, `api/v1/files.py` |
| Alembic | `alembic/`, `alembic.ini` (4 migrations PostgreSQL) |
| Knowledge | `resilio_docs/resilio_docs/` (9 JSON scientifiques), `training_books/` (5 livres) |
| Docs | `resilio-master-v2.md`, `resilio-nutrition-coach-section.md`, system prompts agents |

### Ce qui existe dans `C:\Users\simon\resilio-plus` mais PAS dans `C:\resilio-plus`

| Catégorie | Fichiers dans `C:\Users\simon\resilio-plus` uniquement |
|-----------|-------------------------------------------------------|
| Core logic | `core/fatigue.py`, `core/periodization.py`, `core/goal_analysis.py`, `core/conflict.py`, `core/readiness.py`, `core/biking_logic.py`, `core/swimming_logic.py`, `core/nutrition_logic.py`, `core/recovery_logic.py`, `core/running_logic.py`, `core/lifting_logic.py` |
| Schemas | `schemas/session_log.py`, `schemas/review.py`, `schemas/connector_api.py` |
| Routes | `routes/onboarding.py`, `routes/sessions.py`, `routes/reviews.py`, `routes/nutrition.py`, `routes/recovery.py`, `routes/_agent_factory.py` |
| DB | 7-table SQLite schema (UserModel, AthleteModel, TrainingPlanModel, NutritionPlanModel, WeeklyReviewModel, ConnectorCredentialModel, SessionLogModel) |
| Tests | 1243+ tests vs 235 — notamment: agents, core logic, schemas, api, E2E (7 scenarios) |
| Frontend | `session/[id]/`, `session/[id]/log/`, `history/`, `review/` |
| Docs plans | Plans phases 9, 10, 11 (merge roadmap) |

---

## 3. FICHIERS ATTENDUS VS PRÉSENTS

Les fichiers suivants sont définis dans `CLAUDE.md` de `C:\resilio-plus` (architecture `resilio-master-v2.md`). L'évaluation porte sur les deux repos.

| Fichier | `C:\resilio-plus` (master) | `C:\Users\simon\resilio-plus` (main) |
|---------|---------------------------|--------------------------------------|
| `CLAUDE.md` | ✅ PRÉSENT (S19, projet complet) | ✅ PRÉSENT (Phases 0–8, roadmap 9–11) |
| `resilio-master-v2.md` | ✅ PRÉSENT (non committé) | ❌ MANQUANT |
| `graph.py` (LangGraph, 11 nodes) | ✅ PRÉSENT `agents/head_coach/graph.py` | ❌ MANQUANT (décision délibérée — LangGraph écarté pour V2) |
| `agents/head_coach/system_prompt.md` | ✅ PRÉSENT (non committé) | ⚠️ INCOMPLET — dans `.bmad-core/agents/head-coach.agent.md` (format différent) |
| `agents/running_coach/system_prompt.md` | ✅ PRÉSENT (non committé) | ⚠️ INCOMPLET — dans `.bmad-core/agents/running-coach.agent.md` |
| `agents/lifting_coach/system_prompt.md` | ✅ PRÉSENT (non committé, `.txt`) | ⚠️ INCOMPLET — dans `.bmad-core/agents/lifting-coach.agent.md` |
| `agents/recovery_coach/system_prompt.md` | ✅ PRÉSENT (non committé) | ⚠️ INCOMPLET — dans `.bmad-core/agents/recovery-coach.agent.md` |
| `agents/nutrition_coach/system_prompt.md` | ✅ PRÉSENT S15 | ⚠️ INCOMPLET — dans `.bmad-core/agents/nutrition-coach.agent.md` |
| `data/vdot_paces.json` | ✅ PRÉSENT (non committé) | ❌ MANQUANT dans `data/` — présent nulle part |
| `data/volume_landmarks.json` | ✅ PRÉSENT (non committé) | ⚠️ INCOMPLET — dans `.bmad-core/data/volume-landmarks.json` (format différent) |
| `data/muscle_overlap.json` | ✅ PRÉSENT (non committé) | ❌ MANQUANT |
| `data/agent_view_map.json` | ✅ PRÉSENT (non committé) | ❌ MANQUANT — `_get_view()` implémenté en Python dans Phase 11 plan |
| `data/nutrition_targets.json` | ✅ PRÉSENT (non committé) | ⚠️ INCOMPLET — dans `.bmad-core/data/nutrition-targets.json` |
| `data/running_zones.json` | ✅ PRÉSENT (non committé) | ⚠️ INCOMPLET — dans `.bmad-core/data/running-zones.json` |
| `data/food_database_cache.json` | ✅ PRÉSENT (non committé) | ❌ MANQUANT |
| `core/config.py` | ✅ PRÉSENT — Pydantic SettingsConfigDict | ❌ MANQUANT — pas de config.py centralisé dans main |
| `docker-compose.yml` | ✅ PRÉSENT — PostgreSQL + API | ✅ PRÉSENT — SQLite (Phase 9 doit le migrer vers PostgreSQL) |
| `requirements.txt` | ❌ MANQUANT — remplacé par `pyproject.toml` (correct) | ❌ MANQUANT — remplacé par `pyproject.toml` (correct) |
| `conftest.py` | ✅ PRÉSENT — Simon fixtures (dict, state, agent_views, fatigue vert/rouge) | ✅ PRÉSENT — SQLite StaticPool + fixtures Phases 0–8 |
| `resilio_docs/*.json` (9 fichiers scientifiques) | ✅ PRÉSENT `resilio_docs/resilio_docs/` (non committé) | ❌ MANQUANT |
| `training_books/` (5 livres) | ✅ PRÉSENT (non committé) | ❌ MANQUANT |

**Note sur `requirements.txt` :** Les deux projets utilisent `pyproject.toml` + `poetry.lock` — c'est la bonne pratique. `requirements.txt` n'est pas attendu.

---

## 4. RECOMMANDATION

### 4.1 Quelle version est la plus complète et alignée avec `CLAUDE.md` ?

**`C:\resilio-plus` (branche `master`)** est architecturalement la plus fidèle au `resilio-master-v2.md` :
- LangGraph graph.py opérationnel (11 nodes)
- `get_agent_view()` implémenté via `models/views.py`
- `AthleteState` Pydantic complet
- Alembic + PostgreSQL opérationnels
- `core/config.py` Pydantic SettingsConfigDict
- Format de sortie Hevy-compatible et Runna-compatible implémenté dans les prescribers
- Sessions S15–S19 complètes localement (non pushées) : NutritionCoach, SwimmingCoach, BikingCoach, APScheduler, frontend complet

**`C:\Users\simon\resilio-plus` (branche `main`)** est plus robuste en termes de tests et de logique core :
- 1243+ tests vs 235 (5× plus)
- Logic stateless riche : `fatigue.py`, `periodization.py`, `goal_analysis.py`, `conflict.py`, `readiness.py`
- 7 E2E scenarios complets
- Meilleure couverture : schemas, routes, agents, core, connectors

**Décision déjà prise (2026-04-10) :** `C:\Users\simon\resilio-plus` (`main`) est la base canonique. Les fonctionnalités de `C:\resilio-plus` sont portées via les plans Phase 9–11.

### 4.2 Ce qu'il faut récupérer de `C:\resilio-plus`

| Priorité | Élément | Destination | Phase |
|----------|---------|-------------|-------|
| 🔴 Phase 9 | `connectors/apple_health.py`, `gpx.py`, `fit.py`, `food_search.py`, `fcen.py` | `backend/app/connectors/` | 9 |
| 🔴 Phase 9 | `core/sync_scheduler.py` (APScheduler) | `backend/app/core/` | 9 |
| 🔴 Phase 9 | `alembic/` + `docker-compose.yml` PostgreSQL | racine | 9 |
| 🔴 Phase 9 | `data/fcen_nutrients.csv` | `data/` | 9 |
| 🟡 Phase 11 | `data/vdot_paces.json`, `muscle_overlap.json`, `agent_view_map.json`, `food_database_cache.json`, `nutrition_targets.json`, `running_zones.json`, `volume_landmarks.json` | `data/` | 11 |
| 🟡 Phase 11 | `api/v1/food.py`, `api/v1/workflow.py` | `backend/app/routes/` | 11 |
| 🟢 Toujours | `resilio_docs/resilio_docs/*.json` (9 fichiers connaissances) | `docs/knowledge/` | Now |
| 🟢 Toujours | `training_books/*.md` (5 livres) | `docs/training_books/` | Now |
| 🟢 Toujours | `resilio-master-v2.md` | racine | Now |
| 🔵 Info | `agents/head_coach/system_prompt.md`, `agents/*/system_prompt.md` | référence | Now |

### 4.3 Fichiers manquants à recréer

| Fichier | Statut | Action |
|---------|--------|--------|
| `backend/app/core/config.py` | Absent dans main | Créer en Phase 9 (centraliser DATABASE_URL, ANTHROPIC_API_KEY, etc.) |
| `data/vdot_paces.json` (table VDOT 20–85) | Absent dans main | Récupérer de `C:\resilio-plus\data\vdot_paces.json` |
| `data/muscle_overlap.json` | Absent dans main | Récupérer de `C:\resilio-plus\data\muscle_overlap.json` |
| `data/agent_view_map.json` | Absent dans main | Récupérer ou recréer en Phase 11 |
| `resilio-master-v2.md` | Absent dans main | Copier depuis `C:\resilio-plus` (lecture seule, référence) |

### 4.4 Prochaine session Superpowers à exécuter

Selon le plan de 15 sessions de `resilio-master-v2.md` et la roadmap des phases 9–11 :

> **Phase 9 — Task 1 : PostgreSQL + Alembic**
> Fichier de plan : `docs/superpowers/plans/2026-04-10-phase9-merge.md`

**État actuel :**
- Plans Phases 9, 10, 11 : ✅ Écrits et commités
- Implémentation : ❌ Pas encore commencée

**Prochaine action immédiate :**
```
Exécuter docs/superpowers/plans/2026-04-10-phase9-merge.md
→ Task 1 : Migrer backend/app/db/database.py vers PostgreSQL + psycopg2
→ Task 2 : Initialiser Alembic + migration 0001_initial_schema
→ Task 3 : Mettre à jour docker-compose.yml (service db PostgreSQL)
```

Approche recommandée : **Subagent-Driven Development** (un subagent par tâche, double review spec + qualité).

---

### 4.5 Situation branche `master` — Action requise

`C:\resilio-plus` a 24 commits non pushés sur `origin/master` (S15–S19 : NutritionCoach, SwimmingCoach, BikingCoach, APScheduler, frontend complet) ainsi que des fichiers importants jamais committés (7 JSON data/, 4 system prompts, resilio-master-v2.md, resilio_docs/, training_books/).

**Recommandation :** Avant de commencer Phase 9, pousser les commits manquants de `C:\resilio-plus` vers `origin/master` et commiter les fichiers non trackés — pour avoir un état de référence complet sur GitHub. Cette branche devient alors une **archive de référence en lecture seule**.

---

*Audit produit le 2026-04-10. Ne touche à aucun fichier de code.*
