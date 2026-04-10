# Resilio Plus — Merge C:\resilio-plus → C:\Users\simon\resilio-plus

**Date:** 2026-04-10
**Statut:** Approuvé

---

## Contexte

Deux projets Resilio coexistent sur la machine :

| Repo | Architecture | Statut |
|---|---|---|
| `C:\resilio-plus` | LangGraph + PostgreSQL + Alembic, 19 sessions, 235 tests | Complet mais stagnant |
| `C:\Users\simon\resilio-plus` | FastAPI + SQLite, Phases 0–8 complètes, 1243+ tests | Repo canonique actif |

Le repo canonique (`C:\Users\simon\resilio-plus`) est plus testé, a une logique core plus riche (goal_analysis, periodization, fatigue, readiness, conflict), et une roadmap Phases 9–11 définie. Le repo `C:\resilio-plus` contient des fonctionnalités complètes et testées qui manquent au repo canonique.

**Décision :** Garder `C:\Users\simon\resilio-plus` comme base et y porter les fonctionnalités complètes de `C:\resilio-plus`.

**Décisions architecturales :**
- **LangGraph** : Skip pour v2. La valeur réelle (streaming distribué, persistence externe, HiTL avancé) est une feature v3. L'architecture agents actuelle est fonctionnelle et bien testée.
- **PostgreSQL** : Migrer maintenant. Plus perturbateur plus tard, et nécessaire pour toute mise en production.

---

## Fonctionnalités à porter

### Depuis `C:\resilio-plus` → `C:\Users\simon\resilio-plus`

| Fonctionnalité | Source | Destination | Phase |
|---|---|---|---|
| PostgreSQL + Alembic | `models/db_session.py`, `alembic/` | `backend/app/db/database.py`, `alembic/` | 9 |
| Sync scheduler APScheduler | `core/sync_scheduler.py` | `backend/app/core/sync_scheduler.py` | 9 |
| Apple Health connector | `connectors/apple_health.py` | `backend/app/connectors/apple_health.py` | 9 |
| GPX file import | `connectors/gpx.py` | `backend/app/connectors/gpx.py` | 9 |
| FIT file import | `connectors/fit.py` | `backend/app/connectors/fit.py` | 9 |
| USDA + Open Food Facts | `connectors/food_search.py` | `backend/app/connectors/food_search.py` | 11 |
| FCÉN Santé Canada | `connectors/fcen.py` + `data/fcen_nutrients.csv` | `backend/app/connectors/fcen.py` + `data/` | 11 |
| Chat HiTL endpoint | Nouveau (inspiré de `api/v1/workflow.py`) | `backend/app/routes/chat.py` | 11 |
| Chat HiTL frontend | `frontend/src/app/dashboard/chat/page.tsx` | `frontend/src/app/chat/page.tsx` | 11 |
| `get_agent_view()` token economy | `models/views.py` | `backend/app/agents/base.py` | 11 |

---

## Section 1 : Base de données — PostgreSQL + Alembic

### Changements

**`backend/app/db/database.py`**
- `create_engine` synchrone SQLite → `create_async_engine` PostgreSQL via `asyncpg`
- `sessionmaker` → `async_sessionmaker`
- `DATABASE_URL` lue depuis `.env` : `postgresql+asyncpg://resilio:resilio@db:5432/resilio_db`

**`docker-compose.yml`**
- Service `db` ajouté : `postgres:16-alpine`, volume persistant, healthcheck
- Service `backend` : `depends_on: db: condition: service_healthy`

**`backend/app/db/models.py`**
- Schéma identique — 7 tables inchangées
- Types UUID : `String` → `UUID` natif PostgreSQL sur les champs `id`

**Alembic**
```
alembic.ini                    ← config principale
alembic/
├── env.py                     ← async PostgreSQL, tous les modèles importés
├── script.py.mako
└── versions/
    └── 0001_initial_schema.py ← migration générée depuis models.py
```

**`scripts/entrypoint.sh`**
```bash
#!/bin/bash
alembic upgrade head
exec uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

**`.env`**
```
DATABASE_URL=postgresql+asyncpg://resilio:resilio@db:5432/resilio_db
```

### Tests
Les 1243+ tests existants utilisent `sqlite+aiosqlite:///:memory:` via `conftest.py` — conservé pour la vitesse. Les tests E2E (7 scénarios) tournent contre PostgreSQL en Docker. Zéro test cassé.

---

## Section 2 : Connecteurs étendus + Sync Scheduler

### Apple Health (`backend/app/connectors/apple_health.py`)

Export JSON iOS → `POST /athletes/{id}/connectors/apple-health/upload`.

Données extraites : HRV (RMSSD), fréquence cardiaque au repos, pas quotidiens, sommeil (durée + phases si disponibles).

Coexistence avec Terra : si les deux sont connectés, on prend la donnée la plus récente pour chaque métrique. Le Recovery Coach consomme les deux sources sans distinction.

### GPX / FIT (`backend/app/connectors/gpx.py`, `backend/app/connectors/fit.py`)

Fallback Strava pour les athlètes non connectés.

- `POST /athletes/{id}/connectors/files/gpx` — parse GPX, extrait durée + distance + FC + paces → SessionLogModel
- `POST /athletes/{id}/connectors/files/fit` — parse FIT (fitparse), même extraction

Les sessions créées depuis GPX/FIT sont marquées `source: "gpx"` / `source: "fit"` dans `actual_data_json`.

### Sync Scheduler (`backend/app/core/sync_scheduler.py`)

APScheduler `AsyncIOScheduler`, 2 jobs :

```python
scheduler.add_job(sync_all_strava, "interval", hours=6, misfire_grace_time=300)
scheduler.add_job(sync_all_hevy,   "interval", hours=6, misfire_grace_time=300)
```

`sync_all_strava()` : requête tous les `ConnectorCredential` Strava actifs → refresh token si expiré → fetch activités 7 derniers jours → `ingest_activities()` → `SessionLogModel`. Isolation par athlète : `try/except` par athlète, l'échec d'un n'arrête pas les autres.

`sync_all_hevy()` : même pattern, filtre `api_key IS NOT NULL`.

Démarrage/arrêt dans le lifespan FastAPI :
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_scheduler()
    yield
    scheduler.shutdown(wait=False)
```

### Settings UI étendue

`frontend/src/app/settings/connectors/page.tsx` affiche tous les connecteurs :
- Strava (OAuth), Hevy (API key), Terra (token), Apple Health (upload), GPX/FIT (upload)
- Statut : connecté/déconnecté, dernière sync
- Boutons : connect / disconnect / sync manuel

---

## Section 3 : Food Databases

### Sources

| Source | Endpoint | Méthode |
|---|---|---|
| USDA FoodData Central | `GET /athletes/{id}/food/search?q=` | API REST (clé gratuite) |
| Open Food Facts | `GET /athletes/{id}/food/search?q=` | API REST (pas de clé) |
| Open Food Facts barcode | `GET /athletes/{id}/food/barcode/{barcode}` | API REST |
| FCÉN Santé Canada | `GET /athletes/{id}/food/search/fcen?q=` | CSV local |

Les deux premières sources sont interrogées en parallèle (`asyncio.gather`) sur `/food/search`. Résultats normalisés vers un format commun :
```json
{
  "name": "Riz basmati cuit",
  "calories_per_100g": 130,
  "carbs_g": 28.2,
  "protein_g": 2.7,
  "fat_g": 0.3,
  "source": "usda"
}
```

### Relation avec NutritionCoach

La nutrition reste calculée en interne (`nutrition_logic.py` — macros cibles par type de journée). Les food databases ajoutent une couche de recherche d'aliments concrets pour atteindre ces cibles. L'athlète voit ses macros cibles du jour et peut chercher quels aliments y contribuent. Complémentaire, pas un remplacement.

### Fichiers

- `backend/app/connectors/food_search.py` — USDA + Open Food Facts
- `backend/app/connectors/fcen.py` — CSV FCÉN, chargement au démarrage du module
- `data/fcen_nutrients.csv` — 25+ aliments canadiens
- `backend/app/routes/food.py` — 3 endpoints
- `FOOD_API_KEY` ajouté à `.env` (USDA FoodData Central)

---

## Section 4 : Chat HiTL + Token Economy

### Chat Head Coach

**Backend** : `POST /athletes/{id}/chat`

```python
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    action: Literal["regenerate_plan", None] = None
```

Flow : message utilisateur → Head Coach reçoit athlete state complet + message → appel Anthropic → retourne réponse textuelle + action optionnelle. Si `action = "regenerate_plan"`, le plan est recalculé automatiquement (appel interne au même endpoint que `POST /athletes/{id}/plan`).

Pas de multi-turn — consultation ponctuelle. Le contexte inclut : profil athlète, plan actuel, ACWR, dernières sessions loggées.

**Frontend** : `frontend/src/app/chat/page.tsx`

Interface simple : textarea + bouton envoi → affiche réponse Head Coach. Si l'action est `regenerate_plan`, badge "Plan mis à jour" + lien vers `/plan`. Navigation Top Nav : lien "Coach" ajouté.

### `get_agent_view()` — Token Economy

**`backend/app/agents/base.py`** — méthode `_get_view(athlete_data: dict) → dict` ajoutée à `BaseAgent`. Chaque agent override pour retourner uniquement sa sous-section :

```python
class RunningCoachAgent(BaseAgent):
    def _get_view(self, athlete_data: dict) -> dict:
        return {
            "profile": athlete_data["profile"],
            "vdot": athlete_data.get("vdot"),
            "running_sessions": athlete_data.get("running_sessions", []),
            "acwr": athlete_data.get("acwr"),
            "readiness": athlete_data.get("readiness"),
        }
```

Les agents Biking, Swimming, Lifting, Nutrition, Recovery ont leurs propres vues filtrées. Le Head Coach seul reçoit l'état complet. Réduction estimée : 30–40% de tokens par appel LLM.

---

## Phases révisées

| Phase | Scope | Contenu | Status |
|---|---|---|---|
| 9 | Full stack | PostgreSQL + Alembic + connecteurs (Hevy/Terra/Strava/Apple Health/GPX/FIT) + sync scheduler + Settings UI | ❌ À faire |
| 10 | Frontend | Analytics dashboard (ACWR, CTL/ATL/TSB, sport breakdown, performance) | ❌ À faire |
| 11 | Full stack | Profil, customisation, alertes + food databases + Chat HiTL + token economy | ❌ À faire |

---

## Ce qui ne change pas

- Architecture agents (classes Python, pas LangGraph)
- Schémas Pydantic (`backend/app/schemas/`)
- Logique core (`goal_analysis.py`, `periodization.py`, `fatigue.py`, `readiness.py`, `conflict.py`, etc.)
- Frontend Phases 0–8 (login, onboarding, dashboard, plan, session/[id], review, history)
- 1243+ tests existants (tous doivent rester verts)
- `C:\resilio-plus` devient référence en lecture seule

---

## Dépendances

```
PostgreSQL + Alembic (Phase 9, premier) → tous les connecteurs → sync scheduler
Food databases (Phase 11) → indépendant du reste
Chat HiTL (Phase 11) → dépend de PostgreSQL
get_agent_view() (Phase 11) → indépendant du reste
```
