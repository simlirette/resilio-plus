# Session 3 — Connecteurs : Design Spec

**Date :** 2026-04-05
**Statut :** Approuvé
**Session suivante :** S4 — Connecteurs (USDA/Open Food Facts + Apple Health + fallbacks GPX/FIT)

---

## Contexte

S2 a livré les Pydantic schemas + `get_agent_view()` + la migration Alembic initiale (8 tables). Les tables `run_activities`, `lifting_sessions`, `lifting_sets` existent mais sont vides. S3 câble les deux sources de données primaires : Strava (course) et Hevy (musculation).

Les deux APIs sont disponibles avec de vraies credentials :
- **Strava** : `STRAVA_CLIENT_ID=215637`, `STRAVA_CLIENT_SECRET=<secret>` — OAuth2
- **Hevy** : API key UUID — header `api-key`

Approche choisie : service layer pur + router FastAPI minimal (sans JWT auth — S11). `athlete_id` en query param pour l'instant.

### État du repo en entrée de S3

| Élément | Statut |
|---|---|
| `models/database.py` — 8 tables | Existant — manque `connector_credentials` |
| `alembic/versions/55a168264480_initial_schema.py` | Existant |
| `connectors/` | Manquant → livré en S3 |
| `api/v1/connectors.py` | Manquant → livré en S3 |
| `api/main.py` | Manquant → stub minimal en S3 |
| `tests/test_strava_connector.py` | Manquant → livré en S3 |
| `tests/test_hevy_connector.py` | Manquant → livré en S3 |
| `tests/test_connector_routes.py` | Manquant → livré en S3 |

---

## Livrables S3

### 1. Table `connector_credentials` — `models/database.py`

Nouvelle table ajoutée à `models/database.py`. Relation inverse ajoutée sur `Athlete`.

```python
from sqlalchemy import UniqueConstraint

class ConnectorCredential(TimestampMixin, Base):
    __tablename__ = "connector_credentials"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    athlete_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("athletes.id"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # "strava" | "hevy"

    # OAuth tokens (Strava)
    access_token: Mapped[Optional[str]] = mapped_column(Text)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # API key (Hevy)
    api_key: Mapped[Optional[str]] = mapped_column(Text)

    # ID externe de l'athlète chez le provider (ex: Strava athlete ID)
    external_athlete_id: Mapped[Optional[str]] = mapped_column(String(100))

    # Un seul credential par provider par athlète
    __table_args__ = (UniqueConstraint("athlete_id", "provider"),)

    # Relation
    athlete: Mapped["Athlete"] = relationship(back_populates="connector_credentials")
```

Sur `Athlete`, ajouter :
```python
connector_credentials: Mapped[list["ConnectorCredential"]] = relationship(
    back_populates="athlete"
)
```

**Stockage des tokens en clair** : acceptable pour S3 (dev local). Le chiffrement at-rest est prévu en S14.

**Migration Alembic** : `alembic revision --autogenerate -m "add connector credentials"` après modification de `models/database.py`.

---

### 2. `connectors/strava.py` — StravaConnector

Classe de service pure — aucune dépendance FastAPI. Utilise `httpx.AsyncClient` pour les appels HTTP.

```python
class StravaConnector:
    BASE_URL = "https://www.strava.com/api/v3"
    AUTH_URL = "https://www.strava.com/oauth/authorize"
    TOKEN_URL = "https://www.strava.com/oauth/token"

    def __init__(self):
        self.client_id = settings.STRAVA_CLIENT_ID
        self.client_secret = settings.STRAVA_CLIENT_SECRET
        self.redirect_uri = settings.STRAVA_REDIRECT_URI

    def get_authorization_url(self) -> str:
        """Génère l'URL OAuth Strava."""
        # scope: activity:read_all
        # response_type: code
        # approval_prompt: auto

    async def exchange_code(
        self, code: str, athlete_id: uuid.UUID, db: AsyncSession
    ) -> ConnectorCredential:
        """Échange le code d'autorisation contre tokens. Stocke en DB."""
        # POST /oauth/token avec grant_type=authorization_code
        # Crée ou met à jour ConnectorCredential via upsert

    async def refresh_token_if_expired(
        self, cred: ConnectorCredential, db: AsyncSession
    ) -> ConnectorCredential:
        """Refresh si token expire dans moins de 5 minutes."""
        # Si token_expires_at <= now() + 5min :
        #   POST /oauth/token avec grant_type=refresh_token
        #   Met à jour cred en DB

    async def fetch_activities(
        self, cred: ConnectorCredential, since: datetime, limit: int = 50
    ) -> list[dict]:
        """GET /athlete/activities depuis `since`."""
        # after = int(since.timestamp())
        # Retourne la liste brute des activités Strava

    async def ingest_activities(
        self, athlete_id: uuid.UUID, activities: list[dict], db: AsyncSession
    ) -> int:
        """Convertit et insère les activités dans run_activities. Retourne le count ingéré."""
        # Pour chaque activité :
        #   - Filtre sur type "Run" | "Ride" | "Swim"
        #   - Calcule TRIMP = (duration_s/60) * (avg_hr/max_hr) * e^(1.92 * avg_hr/max_hr)
        #     Si avg_hr absent : TRIMP = distance_km * 1.0 (fallback distance-based)
        #   - Upsert sur strava_activity_id (ON CONFLICT DO UPDATE)
        #   - Stocke données brutes dans strava_raw (JSONB)
```

**Champs mappés Strava → RunActivity :**

| Strava | RunActivity |
|---|---|
| `id` | `strava_activity_id` |
| `start_date` | `activity_date` |
| `type` | `activity_type` |
| `distance / 1000` | `distance_km` |
| `elapsed_time` | `duration_seconds` |
| `average_speed` → converti en sec/km | `avg_pace_sec_per_km` |
| `average_heartrate` | `avg_hr` |
| `max_heartrate` | `max_hr` |
| `total_elevation_gain` | `elevation_gain_m` |
| activité brute complète | `strava_raw` |

---

### 3. `connectors/hevy.py` — HevyConnector

Classe de service pure. API Hevy : `https://api.hevyapp.com`. Auth via header `api-key: <key>`.

```python
class HevyConnector:
    BASE_URL = "https://api.hevyapp.com"

    async def validate_api_key(self, api_key: str) -> bool:
        """GET /v1/workouts?page=1&pageSize=1 → 200 = valide, 401 = invalide."""

    async def fetch_workouts(
        self, api_key: str, page: int = 1, page_size: int = 10
    ) -> list[dict]:
        """GET /v1/workouts — retourne les workouts paginés."""

    async def fetch_all_since(self, api_key: str, since: datetime) -> list[dict]:
        """Pagine jusqu'à ce que updated_at < since ou page vide."""

    async def ingest_workouts(
        self, athlete_id: uuid.UUID, workouts: list[dict], db: AsyncSession
    ) -> int:
        """Convertit et insère les workouts dans lifting_sessions + lifting_sets."""
        # Pour chaque workout :
        #   - Upsert LiftingSession sur hevy_workout_id
        #   - Supprime et recrée les LiftingSet associés
        #   - Calcule total_volume_kg = Σ(weight_kg * reps)
        #   - Calcule total_sets = count(sets)
        #   - Conversion lbs→kg : weight_kg = weight_lbs * 0.453592
```

**Champs mappés Hevy → LiftingSession :**

| Hevy | LiftingSession |
|---|---|
| `title` | `hevy_title` |
| `start_time` | `start_time`, `session_date` |
| `end_time` | `end_time` |
| `(end - start).seconds / 60` | `duration_minutes` |
| `id` | `hevy_workout_id` |
| `"hevy_api"` | `source` |

**Champs mappés Hevy → LiftingSet :**

| Hevy | LiftingSet |
|---|---|
| `exercise.title` | `exercise_title` |
| `set.index` | `set_index` |
| `set.type` | `set_type` |
| `set.weight_kg` (ou `* 0.453592`) | `weight_kg` |
| `set.reps` | `reps` |
| `set.rpe` | `rpe` |

**Pas de fallback CSV en S3** (YAGNI — l'API key est disponible). Parser CSV ajouté en S7 si nécessaire.

---

### 4. FastAPI — `api/main.py` + `api/v1/connectors.py`

**`api/main.py`** — stub minimal (S11 le complètera) :
```python
from fastapi import FastAPI
from api.v1.connectors import router as connectors_router

app = FastAPI(title="Resilio+", version="0.1.0")
app.include_router(connectors_router, prefix="/api/v1/connectors", tags=["connectors"])
```

**`api/v1/connectors.py`** — routes sans JWT auth :

**Strava :**
```
GET  /strava/auth
     → JSONResponse: { "authorization_url": str }

GET  /strava/callback?code=str&athlete_id=UUID
     → Échange code → stocke ConnectorCredential
     → JSONResponse: { "connected": true, "strava_athlete_id": str }

POST /strava/sync?athlete_id=UUID&days=int(default=30)
     → Refresh token si expiré → fetch → ingest
     → JSONResponse: { "synced": int }

GET  /strava/status?athlete_id=UUID
     → JSONResponse: { "connected": bool, "last_sync": datetime|null, "token_expires_at": datetime|null }

DELETE /strava/disconnect?athlete_id=UUID
     → Supprime ConnectorCredential
     → JSONResponse: { "disconnected": true }
```

**Hevy :**
```
POST /hevy/connect?athlete_id=UUID
     Body: { "api_key": str }
     → Valide clé → stocke ConnectorCredential
     → JSONResponse: { "connected": true }

POST /hevy/sync?athlete_id=UUID&days=int(default=30)
     → Fetch workouts since (now - days) → ingest
     → JSONResponse: { "synced": int }

GET  /hevy/status?athlete_id=UUID
     → JSONResponse: { "connected": bool, "last_sync": datetime|null }

DELETE /hevy/disconnect?athlete_id=UUID
     → Supprime ConnectorCredential
     → JSONResponse: { "disconnected": true }
```

**Gestion des erreurs :**
- `athlete_id` invalide → 404
- Token expiré non-refreshable → 401 avec message clair
- Clé Hevy invalide → 400

---

### 5. Tests

**`tests/test_strava_connector.py`** — unitaires avec `httpx.MockTransport` :
- `test_get_authorization_url` : URL contient `client_id=215637`, `scope=activity:read_all`, `redirect_uri`
- `test_exchange_code_stores_credential` : mock POST `/oauth/token` → `ConnectorCredential` créé en DB test avec `access_token`, `refresh_token`, `token_expires_at`
- `test_refresh_token_when_expired` : credential avec `token_expires_at = now() - 1h` → mock refresh → nouveau token stocké
- `test_ingest_activities_upsert` : ingest 2x le même `strava_activity_id` → 1 seul `RunActivity` en DB
- `test_trimp_calculated_without_hr` : activité sans `average_heartrate` → `trimp = distance_km * 1.0`

**`tests/test_hevy_connector.py`** — unitaires avec `httpx.MockTransport` :
- `test_validate_api_key_valid` : mock GET `/v1/workouts` 200 → `True`
- `test_validate_api_key_invalid` : mock GET `/v1/workouts` 401 → `False`
- `test_ingest_workouts_upsert` : ingest 2x le même `hevy_workout_id` → 1 seul `LiftingSession` en DB
- `test_weight_conversion_lbs_to_kg` : poids en lbs → converti en kg dans `LiftingSet`
- `test_volume_calculated` : 3 sets × 80kg × 8 reps → `total_volume_kg = 1920.0`

**`tests/test_connector_routes.py`** — routes FastAPI avec `httpx.AsyncClient` :
- `test_strava_auth_returns_url` : `GET /strava/auth` → réponse contient `authorization_url`
- `test_hevy_connect_stores_credential` : `POST /hevy/connect` avec mock Hevy 200 → 200 + `connected: true`
- `test_hevy_status_not_connected` : athlète sans credential → `{ "connected": false }`

**Tous les tests HTTP externes** utilisent `httpx.MockTransport` — pas de vraies requêtes Strava/Hevy.
**Tests DB** utilisent `db_session` fixture de `conftest.py`.

---

### 6. `.env` — Mise à jour

Ajouter les vraies credentials dans `.env` (jamais dans le code) :
```bash
STRAVA_CLIENT_ID=215637
STRAVA_CLIENT_SECRET=31d0dea45c6a0c9ea7df168b03fbd13beae24fba
STRAVA_REDIRECT_URI=http://localhost:8000/api/v1/connectors/strava/callback
HEVY_API_KEY=fe874ad5-90b6-437a-ad0b-81162c850400
```

Ajouter `HEVY_API_KEY` à `core/config.py` dans la classe `Settings`.

---

## Ce que S3 ne fait PAS

- Pas de JWT auth sur les routes → S11
- Pas de parser CSV Hevy → S7 (si nécessaire)
- Pas de connecteurs USDA/Apple Health → S4
- Pas de streaming SSE → S11
- Pas de chiffrement des tokens → S14

---

## Structure des fichiers créés

```
connectors/
├── __init__.py
├── strava.py          ← StravaConnector
└── hevy.py            ← HevyConnector

api/
├── __init__.py
├── main.py            ← FastAPI app stub
└── v1/
    ├── __init__.py
    └── connectors.py  ← Router /connectors

tests/
├── test_strava_connector.py
├── test_hevy_connector.py
└── test_connector_routes.py
```

---

## Commandes de vérification post-S3

```bash
# Tests (sans requêtes réseau réelles)
poetry run pytest tests/test_strava_connector.py tests/test_hevy_connector.py tests/test_connector_routes.py -v

# Suite complète
poetry run pytest tests/ -v
# Expected: 42 passed (29 S1+S2 + 13 S3)

# Linter
poetry run ruff check .

# Migration appliquée
poetry run alembic current
# Expected: <nouveau hash> (head)

# Démarrer l'app localement (optionnel)
docker compose up db -d
poetry run uvicorn api.main:app --reload
# Tester: GET http://localhost:8000/api/v1/connectors/strava/auth
```

---

## Décisions prises

| Décision | Choix | Raison |
|---|---|---|
| Stockage tokens | Clair en DB (Text) | Dev local — chiffrement en S14 |
| Auth routes S3 | `athlete_id` query param | JWT en S11 — pas de sur-ingénierie prématurée |
| Fallback CSV Hevy | Non inclus | YAGNI — API key disponible |
| TRIMP sans HR | `distance_km * 1.0` | Fallback simple, corrigé si Apple Health disponible (S4) |
| HTTP client | `httpx.AsyncClient` | Compatible async FastAPI, mockable avec `MockTransport` |
| Upsert strategy | ON CONFLICT DO UPDATE sur external ID | Sync idempotente — pas de doublons si appelée plusieurs fois |
