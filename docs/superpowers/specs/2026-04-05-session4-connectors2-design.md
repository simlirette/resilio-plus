# Session 4 — Connecteurs 2 : Design Spec

**Date :** 2026-04-05
**Statut :** Approuvé
**Session suivante :** S5 — à définir

---

## Contexte

S3 a livré les connecteurs Strava (OAuth2 → RunActivity) et Hevy (API key → LiftingSession/LiftingSet), ainsi que les routes FastAPI associées. S4 ajoute quatre nouveaux connecteurs basés sur l'upload de fichiers et la recherche alimentaire :

- **Apple Health** : JSON exporté → `FatigueSnapshot` (HRV, HR repos, sommeil)
- **GPX** : fichier XML GPS → `RunActivity`
- **FIT** : fichier binaire Garmin/Polar → `RunActivity`
- **Food Search** : USDA FoodData Central (texte) + Open Food Facts (barcode) → retour JSON uniquement (pas de stockage en S4)

Une migration Alembic minimale est nécessaire : ajout d'un `UniqueConstraint("athlete_id", "snapshot_date")` sur `fatigue_snapshots` pour permettre l'upsert Apple Health.

### État du repo en entrée de S4

| Élément | Statut |
|---|---|
| `models/database.py` — 9 tables dont `connector_credentials` | Existant S3 |
| `connectors/strava.py`, `connectors/hevy.py` | Existant S3 |
| `api/main.py`, `api/v1/connectors.py` | Existant S3 |
| `connectors/apple_health.py` | Manquant → S4 |
| `connectors/gpx.py` | Manquant → S4 |
| `connectors/fit.py` | Manquant → S4 |
| `connectors/food_search.py` | Manquant → S4 |
| `api/v1/apple_health.py` | Manquant → S4 |
| `api/v1/files.py` | Manquant → S4 |
| `api/v1/food.py` | Manquant → S4 |
| Migration Alembic `add_fatigue_snapshot_unique_athlete_date` | Manquant → S4 |

---

## Livrables S4

### 1. Nouvelle dépendance — `python-fitparse`

Ajoutée à `pyproject.toml` :
```toml
fitparse = "^1.2.0"
```

Note : le package PyPI s'appelle `fitparse`, pas `python-fitparse`.

---

### 2. `connectors/apple_health.py` — AppleHealthConnector

Parse un export JSON Apple Health et insère un `FatigueSnapshot`.

**Format d'entrée attendu** (structure minimale acceptée) :
```json
{
  "hrv_rmssd": 62.4,
  "hr_rest": 54,
  "sleep_hours": 7.5,
  "sleep_quality_subjective": null,
  "snapshot_date": "2026-04-05"
}
```

Tous les champs sont optionnels sauf `snapshot_date`.

```python
class AppleHealthConnector:
    async def ingest_snapshot(
        self,
        athlete_id: uuid.UUID,
        data: dict,
        db: AsyncSession,
    ) -> FatigueSnapshot:
        """
        Parse les données Apple Health et upsert un FatigueSnapshot.
        Upsert sur (athlete_id, snapshot_date).
        Retourne le FatigueSnapshot créé ou mis à jour.
        """
```

**Champs mappés :**

| JSON Apple Health | FatigueSnapshot |
|---|---|
| `hrv_rmssd` | `hrv_rmssd` |
| `hr_rest` | `hr_rest` |
| `sleep_hours` | `sleep_hours` |
| `sleep_quality_subjective` | `sleep_quality_subjective` |
| `snapshot_date` | `snapshot_date` |

Les champs non présents dans l'entrée restent `NULL`. Les champs calculés (`acwr_*`, `fatigue_by_muscle`, etc.) conservent leur valeur existante en cas de mise à jour.

**Upsert strategy** : `ON CONFLICT (athlete_id, snapshot_date) DO UPDATE` — met à jour uniquement les colonnes non-NULL de l'entrée.

Note : `fatigue_by_muscle` est `NOT NULL` en DB (`JSONB`). À la création, passer `{}`.

---

### 3. `connectors/gpx.py` — GpxConnector

Parse un fichier GPX (XML) et insère une `RunActivity`.

```python
class GpxConnector:
    def parse_gpx(self, content: bytes) -> dict:
        """
        Parse le XML GPX et retourne un dictionnaire de données d'activité.
        Extrait : activity_date, distance_km, duration_seconds,
                  avg_pace_sec_per_km, elevation_gain_m.
        """

    async def ingest_gpx(
        self,
        athlete_id: uuid.UUID,
        content: bytes,
        db: AsyncSession,
    ) -> RunActivity:
        """
        Parse le GPX et insère une RunActivity.
        Pas d'upsert : chaque upload GPX crée un nouvel enregistrement.
        activity_type = "Run", source identifiable via strava_raw = {"source": "gpx"}.
        """
```

**Extraction depuis GPX :**
- `activity_date` : `<time>` du premier trackpoint ou `<metadata><time>`
- `distance_km` : calculé via formule haversine entre trackpoints consécutifs
- `duration_seconds` : `(last_time - first_time).total_seconds()`
- `avg_pace_sec_per_km` : `duration_seconds / distance_km` si distance > 0
- `elevation_gain_m` : somme des gains positifs d'élévation entre trackpoints (`<ele>`)

Namespace GPX standard : `http://www.topografix.com/GPX/1/1`

**Pas de déduplication GPX** : chaque upload est une nouvelle activité (pas d'ID externe unique).

---

### 4. `connectors/fit.py` — FitConnector

Parse un fichier FIT binaire (Garmin, Polar, Wahoo) et insère une `RunActivity`.

```python
class FitConnector:
    def parse_fit(self, content: bytes) -> dict:
        """
        Parse le fichier FIT via fitparse et retourne les données d'activité.
        Utilise io.BytesIO(content) pour éviter les fichiers temporaires.
        """

    async def ingest_fit(
        self,
        athlete_id: uuid.UUID,
        content: bytes,
        db: AsyncSession,
    ) -> RunActivity:
        """
        Parse le FIT et insère une RunActivity.
        Pas d'upsert : chaque upload crée un nouvel enregistrement.
        """
```

**Messages FIT utilisés :**
- Message `session` : `total_distance` (m→km), `total_elapsed_time` (s), `avg_heart_rate`, `max_heart_rate`, `total_ascent` (m), `sport` (→ activity_type), `start_time`
- Fallback si pas de message `session` : agréger les messages `record`

**Mapping FIT → RunActivity :**

| FIT | RunActivity |
|---|---|
| `start_time` | `activity_date` |
| `sport` ou `"Run"` | `activity_type` |
| `total_distance / 1000` | `distance_km` |
| `total_elapsed_time` | `duration_seconds` |
| calculé | `avg_pace_sec_per_km` |
| `avg_heart_rate` | `avg_hr` |
| `max_heart_rate` | `max_hr` |
| `total_ascent` | `elevation_gain_m` |
| `{"source": "fit"}` | `strava_raw` |

**TRIMP** : même formule que S3 — `(duration_s/60) * (avg_hr/max_hr) * exp(1.92 * avg_hr/max_hr)`, fallback `distance_km * 1.0` si pas de HR.

---

### 5. `connectors/food_search.py` — FoodSearchConnector

Deux méthodes de recherche, pas de stockage en DB en S4.

```python
class FoodSearchConnector:
    USDA_BASE_URL = "https://api.nal.usda.gov/fdc/v1"
    OFF_BASE_URL = "https://world.openfoodfacts.org/api/v2"

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport

    async def search_usda(self, query: str, page_size: int = 5) -> list[dict]:
        """
        GET /fdc/v1/foods/search?query=...&pageSize=...&api_key=USDA_API_KEY
        Retourne une liste de { fdcId, description, nutrients: {protein_g, carbs_g, fat_g, calories} }
        """

    async def search_barcode(self, barcode: str) -> dict | None:
        """
        GET /api/v2/product/{barcode}?fields=nutriments,product_name
        Retourne { name, nutrients: {protein_g, carbs_g, fat_g, calories} } ou None si 404.
        """
```

**Normalisation nutriments USDA** (nutrients par 100g, nutrient IDs) :
- Énergie : nutrientId 1008 (kcal)
- Protéines : nutrientId 1003
- Lipides : nutrientId 1004
- Glucides : nutrientId 1005

**Normalisation nutriments Open Food Facts** (champs `nutriments`) :
- `energy-kcal_100g` → `calories`
- `proteins_100g` → `protein_g`
- `fat_100g` → `fat_g`
- `carbohydrates_100g` → `carbs_g`

**`USDA_API_KEY`** : déjà dans `core/config.py` (vérifié en entrée de session).

---

### 6. FastAPI — Nouveaux routers

**`api/v1/apple_health.py`** :
```
POST /apple-health/upload?athlete_id=UUID
     Body: JSON (multipart/form-data ou application/json)
     → JSONResponse: { "snapshot_date": str, "hrv_rmssd": float|null, ... }
```

**`api/v1/files.py`** :
```
POST /files/gpx?athlete_id=UUID
     Body: multipart/form-data, champ "file" (.gpx)
     → JSONResponse: { "activity_date": str, "distance_km": float, "duration_seconds": int }

POST /files/fit?athlete_id=UUID
     Body: multipart/form-data, champ "file" (.fit)
     → JSONResponse: { "activity_date": str, "distance_km": float, "duration_seconds": int }
```

**`api/v1/food.py`** :
```
GET  /food/search?q=str&page_size=int(default=5)
     → JSONResponse: { "results": list[{ fdcId, description, nutrients }] }

GET  /food/barcode/{barcode}
     → JSONResponse: { "name": str, "nutrients": {...} } ou 404
```

**Montage dans `api/main.py`** :
```python
from api.v1.apple_health import router as apple_health_router
from api.v1.files import router as files_router
from api.v1.food import router as food_router

app.include_router(apple_health_router, prefix="/api/v1/connectors", tags=["apple-health"])
app.include_router(files_router, prefix="/api/v1/connectors", tags=["files"])
app.include_router(food_router, prefix="/api/v1/connectors", tags=["food"])
```

**Gestion des erreurs communes :**
- `athlete_id` invalide → 404
- Fichier GPX/FIT malformé → 400 avec message descriptif
- Barcode non trouvé → 404
- USDA API key manquante → 503

---

### 7. Tests

**`tests/test_apple_health_connector.py`** :
- `test_ingest_snapshot_creates_fatigue_snapshot` : JSON complet → FatigueSnapshot en DB avec bons champs
- `test_ingest_snapshot_partial_data` : JSON avec seulement `snapshot_date` et `sleep_hours` → autres champs NULL
- `test_ingest_snapshot_upsert` : deux ingestions même date → 1 seul FatigueSnapshot mis à jour

**`tests/test_gpx_connector.py`** :
- `test_parse_gpx_extracts_distance` : GPX avec 3 trackpoints → distance calculée correctement (haversine)
- `test_parse_gpx_extracts_duration` : timestamp début/fin → duration_seconds correct
- `test_ingest_gpx_creates_run_activity` : GPX valide → RunActivity en DB avec activity_type="Run"

**`tests/test_fit_connector.py`** :
- `test_parse_fit_session_message` : FIT avec message `session` → distance_km, duration_seconds, avg_hr corrects
- `test_ingest_fit_creates_run_activity` : FIT valide → RunActivity en DB

**`tests/test_food_search_connector.py`** — avec `httpx.MockTransport` :
- `test_search_usda_returns_results` : mock GET → liste avec protein_g, carbs_g, fat_g, calories
- `test_search_barcode_found` : mock GET → dict avec name et nutrients
- `test_search_barcode_not_found` : mock 404 → retourne None

**`tests/test_file_routes.py`** — routes FastAPI avec `httpx.AsyncClient` :
- `test_upload_gpx_returns_activity` : POST /files/gpx → 200 + activity_date
- `test_upload_fit_returns_activity` : POST /files/fit → 200 + activity_date
- `test_food_search_returns_list` : GET /food/search → 200 + results

**Total tests S4 : ~13 nouveaux → ~55 total (42 S3 + 13 S4)**

Tous les tests HTTP externes utilisent `httpx.MockTransport`. Tests FIT utilisent de vrais mini-fichiers FIT créés avec `fitparse` ou des bytes hardcodés valides.

---

### 8. Migration Alembic

Ajouter `UniqueConstraint("athlete_id", "snapshot_date")` à `FatigueSnapshot` dans `models/database.py`, puis générer :

```bash
poetry run alembic revision --autogenerate -m "add fatigue snapshot unique athlete date"
poetry run alembic upgrade head
```

---

## Ce que S4 ne fait PAS

- Pas de stockage des données alimentaires en DB → S5
- Pas de déduplication GPX/FIT par hash ou date → acceptable (re-upload = nouvelle activité)
- Pas de support Apple Health XML (export complet) → JSON structuré uniquement
- Pas de streaming de gros fichiers → les fichiers sont lus en mémoire (taille raisonnable ≤ 50MB)
- Pas de JWT auth sur les routes → S11

---

## Structure des fichiers créés/modifiés

```
connectors/
├── apple_health.py    ← AppleHealthConnector (NEW)
├── gpx.py             ← GpxConnector (NEW)
├── fit.py             ← FitConnector (NEW)
└── food_search.py     ← FoodSearchConnector (NEW)

api/v1/
├── apple_health.py    ← Router /apple-health (NEW)
├── files.py           ← Router /files (NEW)
└── food.py            ← Router /food (NEW)

api/main.py            ← Montage des 3 nouveaux routers (MODIFIED)
pyproject.toml         ← fitparse dependency (MODIFIED)
models/database.py     ← UniqueConstraint sur FatigueSnapshot (MODIFIED)

alembic/versions/
└── <hash>_add_fatigue_snapshot_unique_athlete_date.py  (NEW)

tests/
├── test_apple_health_connector.py  (NEW)
├── test_gpx_connector.py           (NEW)
├── test_fit_connector.py           (NEW)
├── test_food_search_connector.py   (NEW)
└── test_file_routes.py             (NEW)
```

---

## Commandes de vérification post-S4

```bash
# Tests S4 uniquement
poetry run pytest tests/test_apple_health_connector.py tests/test_gpx_connector.py \
  tests/test_fit_connector.py tests/test_food_search_connector.py tests/test_file_routes.py -v

# Suite complète
poetry run pytest tests/ -v
# Expected: ~55 passed

# Linter
poetry run ruff check .
```

---

## Décisions prises

| Décision | Choix | Raison |
|---|---|---|
| Format Apple Health | JSON structuré (pas XML natif) | Export Apple Health XML est complexe — JSON simplifié suffit pour S4 |
| Déduplication GPX/FIT | Aucune | Pas d'ID externe unique → chaque upload = nouvelle activité |
| Stockage alimentaire | Pas de DB en S4 | Retour JSON direct — stockage en S5 quand le besoin est mieux défini |
| USDA vs Open Food Facts | Les deux | Complémentaires : USDA pour texte, OFF pour barcode |
| FitConnector transport | Injectable (comme S3) | Testabilité sans vraies requêtes réseau |
| FatigueSnapshot upsert | ON CONFLICT (athlete_id, snapshot_date) via UniqueConstraint | Un seul snapshot par athlète par jour — nécessite migration Alembic |
| Taille max fichier | Pas de limite en S4 | Validation taille prévue en S11 avec middleware |
