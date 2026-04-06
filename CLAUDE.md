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
| **S5** | Agents base | Agent base class + Head Coach + `get_agent_view()` + edge cases | ⬜ À FAIRE |
| **S6** | Running Coach | VDOT + zones + output format Runna/Garmin | ⬜ À FAIRE |
| **S7** | Lifting Coach | Exercise DB complet (400+) + Volume Landmarks + output format Hevy | ⬜ À FAIRE |
| **S8** | Recovery Coach | Readiness score + gate keeper + HRV pipeline | ⬜ À FAIRE |
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
│   ├── head_coach/
│   │   ├── system_prompt.md           ← ✅ Existant
│   │   ├── graph.py                   ← ✅ Existant (LangGraph stub)
│   │   └── edge_cases/                ← ✅ Existant (3 scénarios)
│   ├── lifting_coach/system_prompt.md ← ✅ Existant
│   ├── running_coach/system_prompt.md ← ✅ Existant
│   ├── nutrition_coach/system_prompt.md ← ✅ Existant
│   └── recovery_coach/system_prompt.md  ← ✅ Existant
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
│       └── food.py                   ← ✅ S4 — GET /food/search + /food/barcode/{barcode}
│
├── core/
│   └── config.py                      ← ✅ S1 — Pydantic v2 SettingsConfigDict + validator
│
├── models/
│   ├── database.py                    ← ✅ Existant — Schéma SQLAlchemy complet (8 tables)
│   └── db_session.py                  ← ✅ Existant — Engine async + session factory
│   (athlete_state.py Pydantic → S2)
│
├── connectors/                        ← ✅ S3+S4 — Strava, Hevy, AppleHealth, GPX, FIT, FoodSearch
│
├── data/
│   ├── agent_view_map.json            ← ✅ Existant
│   ├── exercise_database.json         ← ✅ S1 — 23 exercices-clés (400+ en S7)
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
│   ├── conftest.py                    ← ✅ Existant + S1 (os.environ.setdefault SECRET_KEY)
│   ├── test_config.py                 ← ✅ S1 — 4 tests validator Pydantic v2
│   └── test_exercise_database.py      ← ✅ S1 — 8 tests structure JSON
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
