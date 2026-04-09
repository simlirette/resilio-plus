# RESILIO+ — CLAUDE.md

> Ce fichier est lu par Claude Code au démarrage de chaque session.
> Il contient tout le contexte nécessaire pour travailler sur ce projet.
> Ne jamais modifier sans validation explicite.
> RÈGLE : Ce fichier documente uniquement l'état ACTUEL. L'état futur est dans le plan d'exécution.

---

## PROJET EN UNE LIGNE

Resilio+ est un orchestrateur multi-agents de performance sportive pour athlètes hybrides. Il génère des plans d'entraînement prescriptifs exacts (charges, allures, RPE) via un Head Coach IA qui coordonne des agents spécialistes, en gérant l'interférence métabolique (mTOR/AMPK), l'ACWR et la fatigue neuromusculaire.

---

## DÉCISIONS D'ARCHITECTURE — GRAVÉES DANS LE MARBRE

Ces décisions ne sont pas négociables. Ne jamais les remettre en question ni les contourner.

| Décision | Choix | Raison |
|----------|-------|--------|
| Orchestration agents | **LangGraph** (lite V1) | StateGraph, nodes, edges conditionnels uniquement |
| Backend | **FastAPI** (Python) | RESTful, OpenAPI/Swagger auto-généré, indépendant du frontend |
| Frontend | **Next.js** (React) | Consommateur de l'API uniquement |
| Prototype intermédiaire | **AUCUN** | Pas de Streamlit, pas de CLI-only — frontend dès le départ |
| Unité de poids | **kg uniquement** | Conversion lbs→kg à l'ingestion |
| Langue du code | **Anglais** | Variables, fonctions, commentaires en anglais |
| Langue des prompts agents | **Français** | Les agents parlent à l'utilisateur en français |
| AthleteState — écriture | **Head Coach uniquement** | Les autres agents lisent via `get_agent_view()` |
| AthleteState — lecture | **Vues filtrées** | Chaque agent reçoit uniquement sa sous-section |
| Gestion des edge cases | **Human-in-the-loop** | Le Head Coach recommande, l'utilisateur décide toujours |
| Ton des agents | **Clinique, zéro emoji, zéro encouragement** | Voir system_prompt.md par agent |
| Gestionnaire de paquets | **Poetry** | `pyproject.toml` — source de vérité unique dépendances + outils |
| Linter/formatter | **ruff** | Remplace black + flake8 + isort en un outil |
| Auth | **JWT (PyJWT + pwdlib[argon2])** | Multi-user dès le départ. pwdlib remplace passlib (abandonné) |
| Modèle Anthropic | **claude-sonnet-4-6** | Compétence générale + vitesse d'inférence optimale |

---

## DÉMARRAGE LOCAL

```bash
# 1. Démarrer PostgreSQL
docker compose up db -d

# 2. Vérifier que la DB est healthy
docker compose ps

# 3. Lancer le backend en mode dev
poetry run uvicorn api.main:app --reload

# 4. Lancer les tests
poetry run pytest tests/ -v

# 5. Linter
poetry run ruff check .
```

---

## ÉTAT D'AVANCEMENT — 19 SESSIONS

| Session | Module | Livrable | Statut |
|---------|--------|---------|--------|
| **S1** | Setup | pyproject.toml, Dockerfile, Alembic, config, exercise_database.json | ✅ FAIT |
| **S2** | Schémas | AthleteState Pydantic complet, modèles DB, migration initiale | ✅ FAIT |
| **S3** | Connecteurs | Strava OAuth + Hevy (API ou CSV fallback) | ✅ FAIT |
| **S4** | Connecteurs | USDA/Open Food Facts + Apple Health + fallbacks GPX/FIT | ✅ FAIT |
| **S5** | Agents base | Agent base class + Head Coach + `get_agent_view()` + edge cases | ✅ FAIT |
| **S6** | Running Coach | VDOT + zones + output format Runna/Garmin | ✅ FAIT |
| **S7** | Lifting Coach | Exercise DB (75+ exercices) + LiftingPrescriber (DUP) + LiftingCoachAgent + output format Hevy | ✅ FAIT |
| **S8** | Recovery Coach | Readiness score (5 facteurs) + gate keeper + RecoveryCoachAgent | ✅ FAIT |
| **S9** | Workflow | Constraint matrix + ConflictResolver + PlanMerger + graph stub nodes + workflow API | ✅ FAIT |
| **S10** | Workflow | WeeklyReviewLoop H1-H4 — TRIMP, ACWR recalc, ajustements + POST /weekly-review | ✅ FAIT |
| **S11** | Backend | FastAPI endpoints + OpenAPI docs + auth | ✅ FAIT |
| **S12** | Frontend | Next.js — Dashboard + calendrier + chat | ✅ FAIT |
| **S13** | Frontend | Next.js — Suivi hebdo + pages détail | ✅ FAIT |
| **S14** | Intégration | Docker + tests E2E + polish | ✅ FAIT |
| **S15** | Nutrition Coach | NutritionPrescriber + NutritionCoachAgent + POST /plan/nutrition | ✅ FAIT |
| **S16** | Swimming + Biking + Orchestration | SwimmingCoachAgent + BikingCoachAgent + LangGraph câblé | ✅ FAIT |
| **S17** | Sync scheduler | APScheduler 6h Strava + Hevy — pipeline auto vers DB | ✅ FAIT |
| **S18** | Finition backend | FCÉN Santé Canada + alembic entrypoint Docker + E2E Playwright étendu | ✅ FAIT |
| **S19** | Frontend complet | Chat HiTL + plan nutrition/swimming/biking + settings connecteurs + navbar | ✅ FAIT |

---

## STRUCTURE DU REPO — ÉTAT ACTUEL

```
resilio-plus/
│
├── CLAUDE.md                          ← CE FICHIER
├── README.md
├── pyproject.toml                     ← ✅ S1 — Poetry, deps prod/dev, ruff/mypy/pytest
├── poetry.lock                        ← ✅ S1 — Lock file reproductible
├── Dockerfile                         ← ✅ S1 — Multi-stage (builder + runtime)
├── .dockerignore                      ← ✅ S1
├── docker-compose.yml                 ← ✅ Existant — PostgreSQL + API service
├── alembic.ini                        ← ✅ S1 — Config migrations
├── alembic/
│   ├── env.py                         ← ✅ S1 — Async PostgreSQL (asyncpg)
│   ├── script.py.mako                 ← ✅ S1
│   └── versions/                      ← ✅ S2 — 4 migrations (initial + connector_credentials + fatigue unique + email/password_hash)
│
├── resilio-master-v2.md               ← Document maître (lire en second)
├── resilio-nutrition-coach-section.md ← Section 6B Nutrition Coach
│
├── agents/
│   ├── __init__.py                    ← ✅ S5
│   ├── base_agent.py                  ← ✅ S5 — BaseAgent ABC
│   ├── head_coach/
│   │   ├── __init__.py                ← ✅ S5
│   │   ├── system_prompt.md           ← ✅ Existant
│   │   ├── graph.py                   ← ✅ S16 — + swimming/biking in _AGENT_REGISTRY + node_nutrition_prescription réel
│   │   ├── resolver.py                ← ✅ S9 — ConflictResolver (ACWR + overlap flags)
│   │   ├── merger.py                  ← ✅ S9 — PlanMerger (unified weekly plan)
│   │   ├── weekly_nodes.py            ← ✅ S10 — nodes H1-H4 (collect, analyze, adjust, report)
│   │   └── edge_cases/
│   │       ├── __init__.py            ← ✅ S5 — get_alternatives_for_conflict
│   │       ├── scenario_a_1rm_veto.py ← ✅ Existant
│   │       ├── scenario_b_schedule_conflict.py ← ✅ Existant
│   │       └── scenario_c_acwr_event.py ← ✅ Existant
│   ├── running_coach/
│   │   ├── __init__.py                ← ✅ S5
│   │   ├── agent.py                   ← ✅ S6 — RunningCoachAgent (prescriber + LLM)
│   │   ├── prescriber.py              ← ✅ S6 — RunningPrescriber (déterministe)
│   │   └── running_coach_system_prompt.md ← ✅ Existant
│   ├── lifting_coach/
│   │   ├── __init__.py                ← ✅ S5
│   │   ├── agent.py                   ← ✅ S7 — LiftingCoachAgent (prescriber + LLM notes)
│   │   ├── prescriber.py              ← ✅ S7 — LiftingPrescriber (DUP, MEV/MRV hybrid, Hevy output)
│   │   └── system_prompt.md           ← ✅ Existant
│   ├── nutrition_coach/
│   │   ├── __init__.py                ← ✅ S15
│   │   ├── prescriber.py              ← ✅ S15 — NutritionPrescriber (TDEE Mifflin-St Jeor, macros g/kg, 7-day schedule)
│   │   ├── agent.py                   ← ✅ S15 — NutritionCoachAgent (prescriber + LLM clinical note)
│   │   └── nutrition_coach_system_prompt.md ← ✅ Existant
│   ├── swimming_coach/
│   │   ├── __init__.py                ← ✅ S16
│   │   ├── prescriber.py              ← ✅ S16 — SwimmingPrescriber (CSS zones, technique/aerobic/threshold)
│   │   ├── agent.py                   ← ✅ S16 — SwimmingCoachAgent (prescriber + LLM note)
│   │   └── swimming_coach_system_prompt.md ← ✅ S16
│   ├── biking_coach/
│   │   ├── __init__.py                ← ✅ S16
│   │   ├── prescriber.py              ← ✅ S16 — BikingPrescriber (Coggan 7-zone FTP, endurance/tempo/vo2max)
│   │   ├── agent.py                   ← ✅ S16 — BikingCoachAgent (prescriber + LLM note)
│   │   └── biking_coach_system_prompt.md ← ✅ S16
│   └── recovery_coach/
│       ├── __init__.py                ← ✅ S8
│       ├── agent.py                   ← ✅ S8 — RecoveryCoachAgent (prescriber + LLM notes)
│       ├── prescriber.py              ← ✅ S8 — RecoveryPrescriber (5 facteurs, gate keeper)
│       └── recovery_coach_system_prompt.md ← ✅ Existant
│
├── api/
│   ├── __init__.py                    ← ✅ S3
│   ├── main.py                        ← ✅ S11 — + CORS + auth + athletes routers + OpenAPI metadata
│   ├── deps.py                        ← ✅ S11 — get_current_athlete dependency
│   ├── endpoints_design.md            ← ✅ Existant (design doc)
│   └── v1/
│       ├── __init__.py                ← ✅ S3
│       ├── auth.py                    ← ✅ S11 — POST /auth/register + /auth/login
│       ├── athletes.py                ← ✅ S11 — GET /athletes/me
│       ├── connectors.py             ← ✅ S3 — Strava OAuth + Hevy routes
│       ├── apple_health.py           ← ✅ S4 — POST /apple-health/upload
│       ├── files.py                  ← ✅ S4 — POST /files/gpx + /files/fit
│       ├── food.py                   ← ✅ S4 — GET /food/search + /food/barcode/{barcode}
│       ├── plan.py                   ← ✅ S6–S8+S15+S16 — POST /plan/running, /lifting, /recovery, /nutrition, /swimming, /biking
│       └── workflow.py               ← ✅ S10 — + POST /workflow/weekly-review
│
├── core/
│   ├── config.py                      ← ✅ S1 — Pydantic v2 SettingsConfigDict + validator
│   ├── acwr.py                        ← ✅ S5 — compute_ewma_acwr + acwr_zone
│   ├── vdot.py                        ← ✅ S6 — get_vdot_paces() + format_pace()
│   ├── constraint_matrix.py           ← ✅ S9 — build_constraint_matrix()
│   ├── security.py                    ← ✅ S11 — hash_password, verify_password, JWT create/decode
│   ├── weekly_review.py               ← ✅ S10 — WeeklyAnalyzer + WeeklyAdjuster
│   └── sync_scheduler.py              ← ✅ S17 — APScheduler 6h — sync_all_strava + sync_all_hevy
│
├── models/
│   ├── database.py                    ← ✅ S11 — + email + password_hash sur Athlete
│   ├── db_session.py                  ← ✅ Existant — Engine async + session factory
│   ├── schemas.py                     ← ✅ Existant — AthleteStateSchema Pydantic
│   ├── views.py                       ← ✅ Existant — get_agent_view() + AgentType
│   ├── athlete_state.py               ← ✅ S5 — AthleteState Pydantic (LangGraph state)
│   └── weekly_review.py               ← ✅ S10 — ActualWorkout + WeeklyReviewState
│
├── connectors/                        ← ✅ S3+S4 — Strava, Hevy, AppleHealth, GPX, FIT, FoodSearch
│
├── data/
│   ├── agent_view_map.json            ← ✅ Existant
│   ├── exercise_database.json         ← ✅ S7 — 75+ exercices (DUP, Tier 1-3, Hevy IDs)
│   ├── food_database_cache.json       ← ✅ Existant
│   └── fcen_nutrients.csv             ← ✅ S18 — 25 aliments canadiens (FCÉN Santé Canada)
│   ├── muscle_overlap.json            ← ✅ Existant
│   ├── nutrition_targets.json         ← ✅ Existant
│   ├── running_zones.json             ← ✅ Existant
│   ├── vdot_paces.json                ← ✅ Existant
│   └── volume_landmarks.json          ← ✅ Existant
│
├── resilio_docs/resilio_docs/         ← ✅ Existant — 9 JSON connaissances scientifiques
├── training_books/                    ← ✅ Existant — 5 livres résumés
│
├── tests/
│   ├── conftest.py                    ← ✅ S5 — simon_pydantic_state fixture ajoutée
│   ├── test_config.py                 ← ✅ S1 — 4 tests validator Pydantic v2
│   ├── test_exercise_database.py      ← ✅ S1 — 8 tests structure JSON
│   ├── test_acwr.py                   ← ✅ S5 — 5 tests ACWR EWMA
│   ├── test_athlete_state.py          ← ✅ S5 — 3 tests AthleteState Pydantic
│   ├── test_base_agent.py             ← ✅ S5 — 3 tests BaseAgent + stubs
│   ├── test_head_coach_graph.py       ← ✅ S16 — 8 tests graph nodes (incl. swimming/biking dispatch + nutrition node)
│   ├── test_vdot.py                   ← ✅ S6 — 6 tests VDOT lookup + formatters
│   ├── test_running_prescriber.py     ← ✅ S6 — 6 tests prescriber logic
│   ├── test_running_agent.py          ← ✅ S6 — 4 tests agent + mocked LLM
│   ├── test_plan_route.py             ← ✅ S8 — 9 tests API route (running + lifting + recovery)
│   ├── test_lifting_prescriber.py     ← ✅ S7 — 6 tests LiftingPrescriber
│   ├── test_lifting_agent.py          ← ✅ S7 — 4 tests LiftingCoachAgent
│   ├── test_recovery_prescriber.py    ← ✅ S8 — 8 tests RecoveryPrescriber
│   ├── test_recovery_agent.py         ← ✅ S8 — 4 tests RecoveryCoachAgent
│   ├── test_constraint_matrix.py      ← ✅ S9 — 5 tests build_constraint_matrix
│   ├── test_conflict_resolver.py      ← ✅ S9 — 4 tests ConflictResolver
│   ├── test_plan_merger.py            ← ✅ S9 — 3 tests PlanMerger
│   ├── test_workflow_route.py         ← ✅ S9 — 4 tests workflow API
│   ├── test_weekly_review.py          ← ✅ S10 — 6 tests WeeklyAnalyzer + WeeklyAdjuster
│   ├── test_weekly_review_route.py    ← ✅ S10 — 3 tests POST /weekly-review
│   ├── test_security.py               ← ✅ S11 — 4 tests security functions
│   ├── test_auth_route.py             ← ✅ S11 — 6 tests auth routes
│   ├── test_sync_scheduler.py         ← ✅ S17 — 6 tests sync scheduler (Strava + Hevy periodic)
│   ├── test_nutrition_prescriber.py   ← ✅ S15 — 8 tests NutritionPrescriber
│   ├── test_nutrition_agent.py        ← ✅ S15 — 4 tests NutritionCoachAgent
│   ├── test_swimming_prescriber.py    ← ✅ S16 — 11 tests SwimmingPrescriber (CSS zones)
│   ├── test_swimming_agent.py         ← ✅ S16 — 5 tests SwimmingCoachAgent
│   ├── test_biking_prescriber.py      ← ✅ S16 — 20 tests BikingPrescriber (Coggan FTP)
│   ├── test_biking_agent.py           ← ✅ S16 — 4 tests BikingCoachAgent
│   ├── test_fcen_connector.py         ← ✅ S18 — 7 tests FcenConnector (CSV FCÉN)
│   └── test_food_route.py             ← ✅ S18 — 2 tests GET /food/search/fcen (235 tests total)
│
├── docs/
│   └── superpowers/
│       ├── specs/
│       │   └── 2026-04-03-session1-setup-design.md
│       └── plans/
│           └── 2026-04-03-session1-setup.md
│
├── frontend/                          ← ✅ S14 — Full-stack Docker + Playwright E2E
│   ├── Dockerfile                     ← ✅ S14 — Multi-stage (deps → builder → runner)
│   ├── .dockerignore                  ← ✅ S14 — Exclude node_modules/.next from context
│   ├── playwright.config.ts           ← ✅ S14 — Playwright config (chromium, port 4321)
│   ├── .env.local.example             ← ✅ S14 — NEXT_PUBLIC_API_URL doc
│   ├── e2e/
│   │   ├── auth.spec.ts               ← ✅ S14 — Login + register render tests
│   │   ├── dashboard.spec.ts          ← ✅ S14 — Protected redirect tests (/dashboard, /calendar)
│   │   ├── protected-routes.spec.ts   ← ✅ S18 — Redirects: chat, weekly-review, plan/running, plan/lifting
│   │   └── public-pages.spec.ts       ← ✅ S18 — Register public + 404 handling
│   ├── package.json                   ← Next.js 15.5, React 19, Tailwind v4, Playwright
│   └── src/
│       ├── app/
│       │   ├── layout.tsx             ← Root layout (Inter font, dark bg)
│       │   ├── page.tsx               ← Redirect → /dashboard
│       │   ├── login/page.tsx         ← Login form → POST /auth/login
│       │   ├── register/page.tsx      ← Register form → POST /auth/register
│       │   └── dashboard/
│       │       ├── layout.tsx         ← Protected layout + Navbar
│       │       ├── page.tsx           ← Profile card (GET /athletes/me)
│       │       ├── calendar/page.tsx       ← ✅ S19 — Weekly grid + run/lift/swim/bike/nutrition links
│       │       ├── chat/page.tsx           ← ✅ S19 — Head Coach HiTL chat (POST /workflow/plan)
│       │       ├── settings/page.tsx       ← ✅ S19 — Strava OAuth + Hevy API key connect/disconnect
│       │       ├── weekly-review/page.tsx  ← ✅ S13 — Workout logger + ACWR report
│       │       └── plan/
│       │           ├── running/page.tsx    ← ✅ S13 — Running plan detail (sessions + paces)
│       │           ├── lifting/page.tsx    ← ✅ S13 — Lifting plan detail (Hevy exercise table)
│       │           ├── nutrition/page.tsx  ← ✅ S19 — 7-day macros/timing from NutritionCoachAgent
│       │           ├── swimming/page.tsx   ← ✅ S19 — CSS zones + technique/aerobic/threshold sessions
│       │           └── biking/page.tsx     ← ✅ S19 — FTP zones + blocks/TSS from BikingCoachAgent
│       ├── lib/api.ts                 ← Typed fetch wrapper + JWT localStorage
│       └── components/navbar.tsx      ← ✅ S19 — Top nav (Dashboard/Calendrier/Bilan/Chat/Paramètres + logout)
```

---

## INTÉGRATIONS API — STATUT

| Service | Méthode primaire | Fallback | Statut |
|---------|-----------------|---------|--------|
| Strava | OAuth2 (`connectors/strava.py`, routes dans `api/v1/connectors.py`) | GPX/FIT (`connectors/gpx.py`, `connectors/fit.py`) | ✅ Credentials + sync endpoint + pipeline auto 6h (`core/sync_scheduler.py`) |
| Hevy | API key (`connectors/hevy.py`, routes dans `api/v1/connectors.py`) | CSV export → parser | ✅ Credentials stockés + pipeline auto 6h (`core/sync_scheduler.py`) |
| Apple Health | JSON upload (`connectors/apple_health.py`) | — | ✅ POST /apple-health/upload opérationnel |
| USDA FoodData | API REST (`connectors/food_search.py`) | Cache local JSON | ✅ GET /food/search opérationnel |
| Open Food Facts | API REST (`connectors/food_search.py`) | — | ✅ GET /food/barcode/{barcode} opérationnel |
| FCÉN Santé Canada | CSV Santé Canada | — | ⬜ Non implémenté |

---

## CE QUI RESTE À FAIRE

### Backend

*Backend complet — aucun item restant.*

### Frontend

*Frontend complet — aucun item restant.*

### Infrastructure

*Infrastructure complète — aucun item restant.*

---

## ATHLÈTE DE TEST — "SIMON"

Fixtures complètes dans `tests/conftest.py` :
- `simon_dict` — dict brut (sans DB)
- `simon_athlete` — Athlete persisté en DB de test
- `simon_state` — AthleteState en phase base_building, semaine 3, VDOT 38.2
- `simon_fatigue_normal` — ACWR 1.05, recovery_score 72, readiness VERT
- `simon_fatigue_red` — ACWR 1.61, recovery_score 38, readiness ROUGE
- `simon_agent_view_running` — Vue filtrée Running Coach
- `simon_agent_view_lifting` — Vue filtrée Lifting Coach

Profil Simon : 32 ans, 78.5kg, VDOT 38.2 (5k en 28:30), objectif sub-25 5k en 16 semaines.

---

## ORDRE DE LECTURE AU DÉMARRAGE DE CHAQUE SESSION

1. `CLAUDE.md` (ce fichier)
2. `resilio-master-v2.md` — architecture, AthleteState, connaissances agents
3. `resilio-nutrition-coach-section.md` — section 6B Nutrition Coach
4. Le(s) `system_prompt.md` des agents concernés par la session
5. Les fichiers existants du dossier de travail

Ne jamais commencer à coder avant d'avoir lu les documents 1 à 3.

---

## RÈGLES ABSOLUES POUR CLAUDE CODE

1. **Lire avant de coder** — toujours lire CLAUDE.md + master doc avant de toucher un fichier
2. **Pas de Streamlit** — jamais, pour aucune raison
3. **Poids en kg** — toute donnée entrante en lbs est convertie immédiatement à l'ingestion
4. **get_agent_view() est la seule porte d'entrée** vers l'AthleteState pour les agents
5. **Human-in-the-loop sur les edge cases** — le système propose, l'humain décide toujours
6. **Mettre à jour CLAUDE.md à la fin de chaque session** — uniquement l'état actuel
7. **Ne jamais casser les tests existants** — corriger avant de continuer si un test échoue
8. **Format de sortie respecté** — séances course en JSON Runna-compatible, lifting en JSON Hevy-compatible
9. **TDD** — écrire le test qui échoue avant d'écrire le code
10. **Commits atomiques** — un commit par tâche logique
11. **Auth** — utiliser `pwdlib[argon2]` (pas passlib, pas python-jose)
