# Intégrations externes — Référence technique

> Sources :  
> - `backend/app/integrations/hevy/` (csv_parser.py, importer.py)  
> - `backend/app/integrations/strava/` (oauth_service.py, activity_mapper.py, sync_service.py)  
> - `backend/app/integrations/nutrition/` (usda_client.py, off_client.py, fcen_loader.py, unified_service.py)

---

## Table des matières

1. [Hevy — Import CSV](#1-hevy--import-csv)
2. [Strava — OAuth V2](#2-strava--oauth-v2)
3. [Nutrition — Lookup Service](#3-nutrition--lookup-service)
4. [Apple Health — Placeholder](#4-apple-health--placeholder)

---

## 1. Hevy — Import CSV

**Endpoint** : `POST /integrations/hevy/import`  
**Auth** : JWT Bearer  
**Content-Type** : `multipart/form-data`

### 1.1 Paramètres

| Champ | Type | Requis | Description |
|-------|------|--------|-------------|
| `file` | File | oui | Export CSV Hevy (Settings → Export Data) |
| `unit` | string | non | `"kg"` (défaut) ou `"lbs"` |

### 1.2 Parser CSV — `csv_parser.py`

```python
def parse_hevy_csv(content: bytes, unit: str = "kg") -> list[HevyWorkout]:
```

**Colonnes requises** :
```python
_REQUIRED_COLUMNS = {"Date", "Workout Name", "Exercise Name", "Weight", "Reps", "RPE"}
```

**Comportement** :
- Décode `utf-8-sig` (BOM Windows)
- Groupe par `(Date, Workout Name)` en préservant l'ordre CSV
- Convertit `lbs → kg` si `unit == "lbs"` : `weight_kg = w * 0.453592`
- `rpe == 0.0` traité comme non-défini (None)
- Chaque workout a `duration_seconds=0` (non exporté par Hevy)
- Tous les sets ont `set_type="normal"`
- Workout ID généré : `"{date.isoformat()}-{slugify(workout_name)}"`

**Erreurs** (`ValueError`) :
- `unit` invalide
- Colonnes requises manquantes
- Aucune ligne de données
- Date non-ISO
- Donnée invalide pour un set

### 1.3 Importer — `importer.py`

```python
def import_hevy_workouts(
    athlete_id: str,
    workouts: list[HevyWorkout],
    db: Session,
) -> dict:
```

**Stratégie de matching** :
- Cherche un slot `{date: date_key, sport: "lifting"}` dans `plan.weekly_slots_json` du plan le plus récent
- Si trouvé → `session_id = plan_session_id`, lié au plan
- Si absent → `session_id = "hevy-standalone-{date}-{slug}"`, `plan_id = None`

**Upsert** : Si un `SessionLogModel` avec `(athlete_id, session_id)` existe déjà, met à jour `actual_data_json` et `logged_at`. Idempotent.

**Structure `actual_data_json`** :
```json
{
  "source": "hevy_csv",
  "hevy_workout_id": "2026-04-01-push-day-a",
  "exercises": [
    {
      "name": "Bench Press",
      "sets": [
        {"reps": 8, "weight_kg": 80.0, "rpe": 8.0, "set_type": "normal"}
      ]
    }
  ]
}
```

**Réponse** :
```json
{
  "total_workouts": 12,
  "matched": 5,
  "standalone": 7,
  "skipped": 0,
  "workouts": [
    {
      "date": "2026-04-01",
      "workout_name": "Push Day A",
      "session_id": "...",
      "matched": true,
      "sets_imported": 15
    }
  ]
}
```

### 1.4 Erreurs HTTP

| Status | Cause |
|--------|-------|
| `401` | Token Bearer manquant ou invalide |
| `422` | CSV malformé, colonnes manquantes, fichier vide, `unit` invalide |

### 1.5 Structure des modules

```
backend/app/integrations/hevy/
  csv_parser.py  — pur: bytes + unit → list[HevyWorkout]
  importer.py    — DB: list[HevyWorkout] + Session → upserts + résumé
```

---

## 2. Strava — OAuth V2

**Routes** :
- `GET /integrations/strava/connect` → retourne `auth_url`
- `GET /integrations/strava/callback?code=&state=` → échange code + stocke tokens
- `POST /integrations/strava/sync` → sync incrémentale

**Auth** : JWT Bearer sur connect + sync ; pas d'auth sur callback (redirect Strava).

### 2.1 Sécurité — chiffrement Fernet

Tokens Strava chiffrés avec **Fernet** (`cryptography`) avant stockage :

```python
def encrypt_token(plain: str, key: str) -> str:
    return Fernet(key.encode()).encrypt(plain.encode()).decode()

def decrypt_token(cipher: str, key: str) -> str:
    return Fernet(key.encode()).decrypt(cipher.encode()).decode()
```

Variable d'environnement requise : `STRAVA_ENCRYPTION_KEY` (clé Fernet base64).  
Lève `RuntimeError` si absente — fail fast à l'appel de `connect()`.

### 2.2 Flux de connexion

#### Étape 1 — `connect()`

```python
def connect(athlete_id: str, db: Session) -> dict:
    # Returns: {"auth_url": "https://www.strava.com/oauth/authorize?...&state=<token>"}
```

- Génère un `state` anti-CSRF : `secrets.token_urlsafe(16)`
- Persiste le `state` dans `ConnectorCredentialModel.extra_json`

#### Étape 2 — `callback()`

```python
def callback(code: str, state: str, db: Session) -> dict:
    # Returns: {"connected": True, "athlete_id": "..."}
```

- Valide le `state` contre la DB (protection CSRF) → `ValueError` si invalide
- Échange le `code` contre `access_token` + `refresh_token` + `expires_at` via Strava API
- Chiffre et persiste les tokens dans `ConnectorCredentialModel`
- Supprime le `state` de `extra_json` après échange réussi

#### Auto-refresh — `get_valid_credential()`

```python
def get_valid_credential(athlete_id: str, db: Session) -> ConnectorCredential:
```

- Déchiffre les tokens en mémoire (plaintext jamais persisté)
- **Auto-refresh** si `expires_at < now + 300s` (5 minutes)
- Met à jour la DB si refresh effectué
- Lève `ValueError` si aucune credential Strava pour cet athlète

### 2.3 Sync incrémentale — `sync_service.py`

```python
def sync(athlete_id: str, db: Session) -> SyncSummary:
```

| État `last_sync_at` | Comportement |
|---------------------|-------------|
| `NULL` (première sync) | Récupère les 90 derniers jours |
| Défini | Récupère depuis `last_sync_at` jusqu'à `now` |

**Filtrage sport** — seuls les types listés sont importés :

```python
SPORT_MAP: dict[str, str] = {
    "Run": "running",
    "TrailRun": "running",
    "VirtualRun": "running",
    "Ride": "biking",
    "VirtualRide": "biking",
    "EBikeRide": "biking",
    "Swim": "swimming",
}
```

Types non listés → comptés comme `skipped`.

**Upsert** : `db.merge(model)` — idempotent, re-syncer la même activité met à jour la ligne.

**Retour** :
```python
class SyncSummary(BaseModel):
    synced: int
    skipped: int
    sport_breakdown: dict[str, int]  # ex: {"running": 3, "biking": 1}
```

### 2.4 Mapping activité — `activity_mapper.py`

```python
def to_model(activity: StravaActivity, athlete_id: str) -> StravaActivityModel:
```

- `activity.id` format : `"strava_{int}"` → `strava_id = int(id.replace("strava_", ""))`
- `date → datetime` : minuit UTC
- `raw_json` : snapshot JSON complet (id, name, sport_type, date, duration, distance, elevation, HR, watts, RPE)

### 2.5 Variables d'environnement requises

| Variable | Usage |
|----------|-------|
| `STRAVA_ENCRYPTION_KEY` | Clé Fernet pour chiffrer/déchiffrer tokens |
| `STRAVA_CLIENT_ID` | Client ID app Strava |
| `STRAVA_CLIENT_SECRET` | Client secret app Strava |

### 2.6 Structure des modules

```
backend/app/integrations/strava/
  oauth_service.py    — connect/callback/auto-refresh, Fernet encrypt/decrypt
  activity_mapper.py  — StravaActivity → StravaActivityModel
  sync_service.py     — sync incrémentale, SPORT_MAP, upsert via db.merge()
```

---

## 3. Nutrition — Lookup Service

**Endpoints** :
- `GET /nutrition/search?q=<query>` → `list[FoodItem]`
- `GET /nutrition/food/{food_id}` → `FoodItem`

**Auth** : JWT Bearer

### 3.1 Architecture cache-first

```
search(q)
  └─► Cache SQLite (food_cache table, name LIKE %q%)
        ├── HIT (frais, ttl non expiré) → retourner items
        └── MISS
              ├── FCÉN (re-query DB, source_filter="fcen")
              ├── USDA FDC (API externe)  → upsert TTL 168h
              └── OFF (Open Food Facts)   → upsert TTL 24h
              └─► Merge fcen + usda + off (dédupliqué par id, max 20)
```

Expiration TTL : `ttl_hours == None` → jamais expiré (données FCÉN statiques).

### 3.2 FoodItem schema

```python
class FoodItem(BaseModel):
    id: str                    # "usda_{fdcId}" | "off_{barcode}" | "fcen_{foodId}"
    source: str                # "usda" | "off" | "fcen"
    name: str                  # display (name_fr si dispo, sinon name_en)
    name_en: str
    name_fr: Optional[str]
    calories_per_100g: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: Optional[float]
    sodium_mg: Optional[float]
    sugar_g: Optional[float]
```

### 3.3 USDA FDC — `usda_client.py`

**Base URL** : `https://api.nal.usda.gov/fdc/v1`  
**Env** : `USDA_API_KEY` (sans clé → warning + retour `[]`)  
**Timeout** : 8s

```python
def search(q: str) -> list[FoodItem]:   # GET /foods/search?query=q&pageSize=10
def fetch(fdc_id: str) -> FoodItem | None:  # GET /food/{fdc_id}
```

Extraction des nutriments — correspondances préfixes :

| Nutriment | Préfixe cherché | Champ |
|-----------|-----------------|-------|
| Calories | `"Energy"` | `calories_per_100g` |
| Protéines | `"Protein"` | `protein_g` |
| Glucides | `"Carbohydrate"` | `carbs_g` |
| Lipides | `"Total lipid"` | `fat_g` |
| Fibres | `"Fiber"` | `fiber_g` |
| Sodium | `"Sodium"` | `sodium_mg` |
| Sucres | `"Sugars"` | `sugar_g` |

Format search : liste plate (`foodNutrients[].nutrientName + value`).  
Format fetch : imbriqué (`foodNutrients[].nutrient.name + amount`).

### 3.4 Open Food Facts — `off_client.py`

**Base URL** : `https://world.openfoodfacts.org`  
**Timeout** : 8s  
**Pas de clé API**

```python
def search(q: str) -> list[FoodItem]:
    # GET /cgi/search.pl?search_terms=q&json=1&page_size=10

def fetch(barcode: str) -> FoodItem | None:
    # GET /api/v0/product/{barcode}.json
```

Champs nutriments : `energy-kcal_100g`, `proteins_100g`, `carbohydrates_100g`, `fat_100g`, `fiber_100g`, `sodium_100g` (× 1000 → mg), `sugars_100g`.  
Items sans `product_name` ignorés.

### 3.5 FCÉN (Fichier canadien sur les éléments nutritifs) — `fcen_loader.py`

Données statiques de Santé Canada (~6 000 aliments). Bootstrap une seule fois.

```python
def load_fcen(
    food_name_csv: Path,
    nutrient_amount_csv: Path,
    nutrient_name_csv: Path,
    db: Session,
) -> int:  # nombre de nouvelles lignes insérées (0 si re-run idempotent)
```

**Fichiers requis** (format multi-CSV officiel FCÉN) :
- `FOOD NAME.csv` — colonnes : `FoodID`, `FoodDescription`, `FoodDescriptionF`
- `NUTRIENT AMOUNT.csv` — colonnes : `FoodID`, `NutrientID`, `NutrientValue`
- `NUTRIENT NAME.csv` — colonnes : `NutrientID`

**NutrientIDs mappés** :
```python
_NUTRIENT_IDS: dict[str, str] = {
    "208": "energy",
    "203": "protein",
    "204": "fat",
    "205": "carbohydrate",
    "291": "fibre",
    "307": "sodium",
    "269": "sugars",
}
```

ID en DB : `"fcen_{FoodID}"`. TTL : `None` (permanent). Aliments sans valeur `energy` ignorés.

**Bootstrap CLI** :
```bash
python -m scripts.load_fcen \
    --food-csv path/to/FOOD_NAME.csv \
    --nutrient-amount-csv path/to/NUTRIENT_AMOUNT.csv \
    --nutrient-name-csv path/to/NUTRIENT_NAME.csv
```

### 3.6 Service unifié — `unified_service.py`

```python
def search(q: str, db: Session) -> list[FoodItem]:
def fetch(food_id: str, db: Session) -> FoodItem | None:
```

**Fetch par préfixe d'ID** :

| Préfixe | Source | TTL cache |
|---------|--------|-----------|
| `usda_` | USDA FDC | 168h (7 jours) |
| `off_`  | Open Food Facts | 24h |
| `fcen_` | FCÉN statique | None — si absent = non disponible |
| autre   | — | retourne `None` |

### 3.7 Variables d'environnement

| Variable | Usage |
|----------|-------|
| `USDA_API_KEY` | Clé USDA FDC (gratuite sur data.nal.usda.gov). Si absente, source USDA ignorée gracieusement. |

### 3.8 Structure des modules

```
backend/app/integrations/nutrition/
  usda_client.py     — USDA search + fetch (sync httpx)
  off_client.py      — OFF search + barcode fetch (sync httpx)
  fcen_loader.py     — JOIN 3 CSV FCÉN → bulk-upsert food_cache
  unified_service.py — cache-first search/fetch, merge, TTL
backend/app/routes/food_search.py  — FastAPI router (prefix: /nutrition)
backend/scripts/load_fcen.py       — CLI bootstrap FCÉN
```

---

## 4. Apple Health — Placeholder

Pas d'intégration active. Terra API (`backend/app/connectors/terra.py`) fournit HRV (RMSSD) et heures de sommeil pour le Recovery Coach.

---

## 5. Tableau récapitulatif

| Intégration | Transport | Auth | Table DB | Sync |
|-------------|-----------|------|----------|------|
| Hevy CSV | Upload fichier | JWT Bearer | `session_logs` | Manuel (import) |
| Strava | OAuth 2.0 | Fernet + JWT | `strava_activities`, `connector_credentials` | Incrémentale automatique (APScheduler 1h) |
| USDA FDC | HTTP REST | API key | `food_cache` (TTL 168h) | On-demand |
| Open Food Facts | HTTP REST | Aucune | `food_cache` (TTL 24h) | On-demand |
| FCÉN | CSV local | N/A | `food_cache` (permanent) | Bootstrap manuel |
| Terra | SDK | API key | N/A (lu via connecteur) | Polling APScheduler |
| Apple Health | — | — | — | Non implémenté |
