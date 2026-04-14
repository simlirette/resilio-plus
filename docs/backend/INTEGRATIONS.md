# Integrations — Resilio+

File-based data import endpoints for athlete data. Distinct from API connectors (OAuth/API-key based sync in `routes/connectors.py`).

---

## Hevy CSV Import

**Endpoint:** `POST /integrations/hevy/import`
**Auth:** Bearer token required
**Content-Type:** `multipart/form-data`

### Query Parameters

| Param | Values | Default | Description |
|---|---|---|---|
| `unit` | `kg`, `lbs` | `kg` | Weight unit in the CSV file |

### CSV Format

Standard Hevy export (Settings → Export Data):

```
Date,Workout Name,Exercise Name,Set Order,Weight,Reps,Distance,Seconds,Notes,Workout Notes,RPE
2026-04-01,Push Day A,Bench Press,1,80,8,,,,,8
2026-04-01,Push Day A,Bench Press,2,82.5,6,,,,,9
```

- `Weight` — numeric or empty (bodyweight → stored as `null`)
- `RPE` — numeric 1–10 or empty; `0` is treated as empty (no rating)
- `Set Order` — used for row ordering, not stored separately

### Example Request

```bash
curl -X POST "http://localhost:8000/integrations/hevy/import?unit=kg" \
  -H "Authorization: Bearer <token>" \
  -F "file=@hevy_export.csv"
```

### Response

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
      "session_id": "abc-123",
      "matched": true,
      "sets_imported": 15
    }
  ]
}
```

- `matched` — workouts linked to a training plan lifting slot
- `standalone` — workouts stored without a plan slot (`session_id` prefix: `hevy-standalone-`)
- `skipped` — always 0 (import is idempotent — re-imports upsert)

### Behavior

**Duplicate handling:** Upsert by `(athlete_id, session_id)`. Re-importing the same file is safe — existing records are updated, not duplicated.

**Plan matching:** Each workout date is checked against the athlete's latest active training plan for a `lifting` slot on the same date. If found, the plan's `session_id` is used. If not, a deterministic standalone ID is generated: `hevy-standalone-{date}-{workout-name-slug}`.

**`actual_data_json` format:**
```json
{
  "source": "hevy_csv",
  "hevy_workout_id": "2026-04-01-push-day-a",
  "exercises": [
    {
      "name": "Bench Press",
      "sets": [{"reps": 8, "weight_kg": 80.0, "rpe": 8.0, "set_type": "normal"}]
    }
  ]
}
```

`source: "hevy_csv"` distinguishes CSV imports from API syncs (`source: "hevy"`).

### Error Responses

| Status | Cause |
|---|---|
| `401` | Missing or invalid Bearer token |
| `422` | Malformed CSV, missing required columns, empty file, invalid `unit` value |

---

## Module Structure

```
backend/app/integrations/
  hevy/
    csv_parser.py   — pure: bytes + unit → list[HevyWorkout]
    importer.py     — DB: list[HevyWorkout] + Session → upserts + summary
```

Both modules are independently testable. The route in `routes/integrations.py` composes them.

---

## Nutrition Lookup (V3-P)

Unified food search backed by three sources with TTL-cached SQLite storage.

### Sources

| Source | ID prefix | TTL | Key required |
|---|---|---|---|
| USDA FoodData Central | `usda_{fdcId}` | 7 days (168h) | `USDA_API_KEY` env var |
| Open Food Facts | `off_{barcode}` | 24 hours | None |
| Canadian Nutrient File (FCÉN) | `fcen_{FoodID}` | Permanent (NULL) | N/A — bootstrap script |

### Endpoints

```
GET /nutrition/search?q=<str>&limit=20
Authorization: Bearer <token>
→ 200: list[FoodItem]
→ 422: if q is empty

GET /nutrition/food/{food_id}
Authorization: Bearer <token>
→ 200: FoodItem
→ 404: if not found in cache or any source
```

### Search flow

1. Cache lookup (SQLite `food_cache` table, `name LIKE %q%`)
2. If ≥ 1 non-expired result → return immediately
3. Cache miss → fan-out: FCÉN (re-query DB) + USDA + OFF (sequential, graceful fallback)
4. Merge order: fcen → usda → off, deduplicate by id, max 20
5. Upsert USDA (168h TTL) and OFF (24h TTL) results to cache

### FoodItem schema

```python
class FoodItem(BaseModel):
    id: str                 # "usda_789", "off_3017620422003", "fcen_456"
    source: str             # "usda" | "off" | "fcen"
    name: str               # display name (name_fr if available, else name_en)
    name_en: str
    name_fr: str | None = None
    calories_per_100g: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float | None = None
    sodium_mg: float | None = None
    sugar_g: float | None = None
```

### FCÉN Bootstrap

Health Canada FCÉN is a multi-file relational dataset (~6000 foods). Bootstrap once:

```bash
python -m scripts.load_fcen \
    --food-csv path/to/FOOD_NAME.csv \
    --nutrient-amount-csv path/to/NUTRIENT_AMOUNT.csv \
    --nutrient-name-csv path/to/NUTRIENT_NAME.csv
```

Re-running is idempotent. FCÉN rows have `ttl_hours=NULL` (permanent, never re-fetched).

### Environment variables

| Variable | Purpose |
|---|---|
| `USDA_API_KEY` | USDA FDC API key. If unset, USDA source is skipped gracefully. |

### Module locations

| File | Responsibility |
|---|---|
| `backend/app/integrations/nutrition/usda_client.py` | USDA search + fetch (sync httpx) |
| `backend/app/integrations/nutrition/off_client.py` | OFF search + barcode fetch (sync httpx) |
| `backend/app/integrations/nutrition/fcen_loader.py` | JOIN 3 FCÉN CSVs → bulk-upsert |
| `backend/app/integrations/nutrition/unified_service.py` | Cache-first search/fetch orchestration |
| `backend/app/routes/food_search.py` | FastAPI router (prefix: `/nutrition`) |
| `backend/scripts/load_fcen.py` | CLI bootstrap script |
