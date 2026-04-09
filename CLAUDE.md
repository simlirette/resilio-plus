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

## ÉTAT D'AVANCEMENT — 15 SESSIONS

| Session | Module | Livrable | Statut |
|---------|--------|---------|--------|
| **S1** | Setup | pyproject.toml, Dockerfile, Alembic, config, exercise_database.json | ✅ FAIT |
| **S2** | Schémas | AthleteState Pydantic complet, modèles DB, migration initiale | ⬜ À FAIRE |
| **S3** | Connecteurs | Strava OAuth + Hevy (API ou CSV fallback) | ✅ FAIT |
| **S4** | Connecteurs | USDA/Open Food Facts + Apple Health + fallbacks GPX/FIT | ✅ FAIT |
| **S5** | Agents base | Agent base class + Head Coach + `get_agent_view()` + edge cases | ✅ FAIT |
| **S6** | Running Coach | VDOT + zones + output format Runna/Garmin | ✅ FAIT |
| **S7** | Lifting Coach | Exercise DB (75+ exercices) + LiftingPrescriber (DUP) + LiftingCoachAgent + output format Hevy | ✅ FAIT |
| **S8** | Recovery Coach | Readiness score (5 facteurs) + gate keeper + RecoveryCoachAgent | ✅ FAIT |
| **S9** | Workflow | Onboarding 7 blocs + création de plan + audit conflits | ⬜ À FAIRE |
| **S10** | Workflow | Boucle hebdomadaire + matrice vivante + suivi | ⬜ À FAIRE |
| **S11** | Backend | FastAPI endpoints + OpenAPI docs + auth | ⬜ À FAIRE |
| **S12** | Frontend | Next.js — Dashboard + calendrier + chat | ⬜ À FAIRE |
| **S13** | Frontend | Next.js — Suivi hebdo + pages détail | ⬜ À FAIRE |
| **S14** | Intégration | Docker + tests E2E + polish | ⬜ À FAIRE |
| **S15** | Nutrition Coach | USDA/OFF/FCÉN + NLP meal input + macros + race-week | ⬜ À FAIRE |

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
│   └── versions/                      ← ⬜ Première migration en S2
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
│   │   ├── graph.py                   ← ✅ S5 — nodes complets (load, detect, delegate)
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
│   ├── nutrition_coach/system_prompt.md ← ✅ Existant
│   └── recovery_coach/
│       ├── __init__.py                ← ✅ S8
│       ├── agent.py                   ← ✅ S8 — RecoveryCoachAgent (prescriber + LLM notes)
│       ├── prescriber.py              ← ✅ S8 — RecoveryPrescriber (5 facteurs, gate keeper)
│       └── recovery_coach_system_prompt.md ← ✅ Existant
│
├── api/
│   ├── __init__.py                    ← ✅ S3
│   ├── main.py                        ← ✅ S3 — FastAPI stub + connectors router
│   ├── endpoints_design.md            ← ✅ Existant (design doc)
│   └── v1/
│       ├── __init__.py                ← ✅ S3
│       ├── connectors.py             ← ✅ S3 — Strava OAuth + Hevy routes
│       ├── apple_health.py           ← ✅ S4 — POST /apple-health/upload
│       ├── files.py                  ← ✅ S4 — POST /files/gpx + /files/fit
│       ├── food.py                   ← ✅ S4 — GET /food/search + /food/barcode/{barcode}
│       └── plan.py                   ← ✅ S6 — POST /plan/running
│
├── core/
│   ├── config.py                      ← ✅ S1 — Pydantic v2 SettingsConfigDict + validator
│   ├── acwr.py                        ← ✅ S5 — compute_ewma_acwr + acwr_zone
│   └── vdot.py                        ← ✅ S6 — get_vdot_paces() + format_pace()
│
├── models/
│   ├── database.py                    ← ✅ Existant — Schéma SQLAlchemy complet (8 tables)
│   ├── db_session.py                  ← ✅ Existant — Engine async + session factory
│   ├── schemas.py                     ← ✅ Existant — AthleteStateSchema Pydantic
│   ├── views.py                       ← ✅ Existant — get_agent_view() + AgentType
│   └── athlete_state.py               ← ✅ S5 — AthleteState Pydantic (LangGraph state)
│
├── connectors/                        ← ✅ S3+S4 — Strava, Hevy, AppleHealth, GPX, FIT, FoodSearch
│
├── data/
│   ├── agent_view_map.json            ← ✅ Existant
│   ├── exercise_database.json         ← ✅ S7 — 75+ exercices (DUP, Tier 1-3, Hevy IDs)
│   ├── food_database_cache.json       ← ✅ Existant
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
│   ├── test_head_coach_graph.py       ← ✅ S5 — 4 tests graph nodes
│   ├── test_vdot.py                   ← ✅ S6 — 6 tests VDOT lookup + formatters
│   ├── test_running_prescriber.py     ← ✅ S6 — 6 tests prescriber logic
│   ├── test_running_agent.py          ← ✅ S6 — 4 tests agent + mocked LLM
│   ├── test_plan_route.py             ← ✅ S8 — 9 tests API route (running + lifting + recovery)
│   ├── test_lifting_prescriber.py     ← ✅ S7 — 6 tests LiftingPrescriber
│   ├── test_lifting_agent.py          ← ✅ S7 — 4 tests LiftingCoachAgent
│   ├── test_recovery_prescriber.py    ← ✅ S8 — 8 tests RecoveryPrescriber
│   └── test_recovery_agent.py         ← ✅ S8 — 4 tests RecoveryCoachAgent (122 tests total)
│
├── docs/
│   └── superpowers/
│       ├── specs/
│       │   └── 2026-04-03-session1-setup-design.md
│       └── plans/
│           └── 2026-04-03-session1-setup.md
│
└── frontend/                          ← ⬜ S12-S13
```

---

## INTÉGRATIONS API — STATUT

| Service | Méthode primaire | Fallback | Statut |
|---------|-----------------|---------|--------|
| Hevy | API REST (si dispo) | CSV export → parser | ⬜ S3 |
| Strava | API OAuth | GPX / FIT file import | ⬜ S3 |
| Apple Health | HealthKit / Terra API | Input manuel JSON | ⬜ S4 |
| USDA FoodData | API REST gratuite | Cache local JSON | ⬜ S15 |
| Open Food Facts | API REST gratuite | Cache local JSON | ⬜ S15 |
| FCÉN Santé Canada | CSV téléchargeable | Cache local JSON | ⬜ S15 |

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
