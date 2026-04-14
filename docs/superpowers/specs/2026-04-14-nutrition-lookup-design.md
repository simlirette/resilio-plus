# Nutrition Lookup Service Design — Resilio+

**Date:** 2026-04-14  
**Status:** Approved  
**Scope:** Unified food search + nutrition data retrieval from USDA FoodData Central, Open Food Facts, and Canadian Nutrient File (FCÉN), with SQLite-backed TTL cache.

---

## Context

Existing `routes/food.py` has a partial implementation:
- Static JSON file cache (`data/food_database_cache.json`)
- Basic USDA search via httpx
- OFF barcode lookup
- No TTL, no FCÉN bootstrap, no unified service layer

This design replaces that with a proper production-ready service.

---

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Search strategy | Cache-first, then parallel fan-out | Cache hit = instant; parallel fan-out faster than sequential |
| Cache storage | `food_cache` table in existing app DB | Reuses SQLAlchemy/Alembic infra; no second DB file |
| FCÉN storage | Permanent rows in `food_cache` (ttl_hours=NULL) | Static data — no TTL needed; bootstrap via script |
| USDA TTL | 7 days | Raw food nutrients change rarely |
| OFF TTL | 24 hours | Packaged product data changes more often |
| Food ID format | Source-prefixed: `usda_789`, `off_3017620422003`, `fcen_456` | Self-documenting, consistent with existing cache |
| Routes | Replace `food.py` with `routes/nutrition.py` | Old routes were primitive; new service strictly better |
| Auth | `get_current_athlete_id` from JWT (no path param) | Consistent with `/integrations/hevy/import` pattern |
| USDA key env var | `USDA_API_KEY` (replaces `FOOD_API_KEY`) | Clearer naming; missing key → USDA skipped gracefully |

---

## File Structure

```
backend/app/integrations/nutrition/
  __init__.py
  usda_client.py       — async: search(q) + fetch(fdc_id) → list[FoodItem] | FoodItem | None
  off_client.py        — async: search(q) + fetch(barcode) → list[FoodItem] | FoodItem | None
  fcen_loader.py       — sync: parse CSV → bulk-upsert into food_cache (permanent rows)
  unified_service.py   — NutritionLookupService: cache + fan-out + merge

backend/app/schemas/nutrition.py      — FoodItem Pydantic model
backend/app/db/models.py              — add FoodCacheModel
alembic/versions/0007_food_cache.py   — migration: CREATE TABLE food_cache
backend/app/routes/nutrition.py       — GET /nutrition/search, GET /nutrition/food/{food_id}
backend/app/main.py                   — swap food_router → nutrition_router

backend/scripts/load_fcen.py          — CLI: python -m scripts.load_fcen --csv path/to/FCEN.csv

tests/backend/integrations/nutrition/
  __init__.py
  test_usda_client.py
  test_off_client.py
  test_fcen_loader.py
  test_unified_service.py
tests/backend/api/test_nutrition.py
tests/fixtures/fcen_sample.csv        — 3-row minimal FCÉN CSV for loader tests

docs/backend/INTEGRATIONS.md         — add nutrition section
```

---

## Unified FoodItem Schema

```python
# backend/app/schemas/nutrition.py
class FoodItem(BaseModel):
    id: str                          # "usda_789", "off_3017620422003", "fcen_456"
    source: str                      # "usda" | "off" | "fcen"
    name: str                        # display name (name_fr if available, else name_en)
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

`name` field: use `name_fr` if present, else `name_en`. Missing nutrients → `None` (not `0.0` — zero is meaningful, absence is different).

---

## Database Model

```python
# FoodCacheModel — added to backend/app/db/models.py
class FoodCacheModel(Base):
    __tablename__ = "food_cache"

    id = Column(String, primary_key=True)         # "usda_789" etc.
    source = Column(String, nullable=False)        # "usda" | "off" | "fcen"
    name = Column(String, nullable=False)
    name_fr = Column(String, nullable=True)
    calories_per_100g = Column(Float, nullable=True)
    protein_g = Column(Float, nullable=True)
    carbs_g = Column(Float, nullable=True)
    fat_g = Column(Float, nullable=True)
    fiber_g = Column(Float, nullable=True)
    sodium_mg = Column(Float, nullable=True)
    sugar_g = Column(Float, nullable=True)
    cached_at = Column(DateTime(timezone=True), nullable=False)
    ttl_hours = Column(Integer, nullable=True)     # NULL = permanent (FCÉN)
```

Expiry helper:
```python
def is_expired(row: FoodCacheModel) -> bool:
    if row.ttl_hours is None:
        return False
    expiry = row.cached_at + timedelta(hours=row.ttl_hours)
    return datetime.now(timezone.utc) > expiry
```

---

## NutritionLookupService — Search Flow

```
search(q: str, db: Session) → list[FoodItem]:

1. Cache lookup
   SELECT * FROM food_cache
   WHERE name ILIKE %q% OR name_fr ILIKE %q%
   LIMIT 20

   Filter out expired rows (ttl_hours not null and cached_at + ttl_hours < now).
   If ≥ 1 non-expired result → return immediately.

2. Cache miss → parallel fan-out:
   - fcen results: re-query food_cache WHERE source='fcen' AND (name/name_fr ILIKE %q%) — always fresh
   - usda results: await usda_search(q)    — httpx, 10 results max
   - off results:  await off_search(q)     — httpx, 10 results max

3. Merge: deduplicate by id, order: fcen → usda → off, max 20 total

4. Upsert USDA results to cache (ttl_hours=168 / 7 days)
   Upsert OFF results to cache (ttl_hours=24)
   FCÉN rows already in cache — no write

5. Return merged list
```

```
fetch(food_id: str, db: Session) → FoodItem | None:

1. Check food_cache by id → return FoodItem if found and not expired
2. Parse source prefix: "usda_" → call usda_fetch(fdc_id)
                         "off_"  → call off_fetch(barcode)
                         "fcen_" → return None (FCÉN data is static; if not in cache, not available)
3. Cache result with appropriate TTL
4. Return FoodItem or None
```

**Graceful fallback:** USDA or OFF timeout/error → log warning, skip that source, continue with what resolved. If all sources fail → return `[]` (no 500).

---

## Endpoints

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

No `athlete_id` in path — `get_current_athlete_id` extracts from JWT.

`food.py` removed. `main.py` swaps `food_router` → `nutrition_router`.

---

## FCÉN Bootstrap Script

```
python -m scripts.load_fcen --csv path/to/FCEN.csv [--db-url sqlite:///...]
```

- Parses FCÉN CSV columns: `FoodID`, `FoodDescription`, `FoodDescriptionF`, `Energy_kcal`, `Protein_g`, `Fat_g`, `Carbohydrate_g`, `Fibre_g`, `Sodium_mg`, `Sugars_g`
- Bulk-upserts into `food_cache` with `source="fcen"`, `ttl_hours=NULL`
- Idempotent — safe to re-run
- Prints progress: `Loaded N FCÉN items.`
- Expected: ~6000 items, ~5s

---

## Environment Variables

```bash
# Added to .env.example
USDA_API_KEY=your_key_here   # Free tier: https://fdc.nal.usda.gov/api-key-signup.html
# OFF requires no key
```

Replaces `FOOD_API_KEY`. If `USDA_API_KEY` unset → USDA skipped, FCÉN + OFF still work.

---

## Testing Strategy

```
test_usda_client.py  — respx mock httpx responses
  - search returns list[FoodItem] with source="usda"
  - search returns [] on HTTP error
  - fetch returns FoodItem by fdc_id
  - fetch returns None on 404

test_off_client.py   — respx mock
  - search returns list[FoodItem] with source="off"
  - fetch by barcode returns FoodItem
  - fetch returns None when status != 1
  - fetch returns None on timeout

test_fcen_loader.py  — uses tests/fixtures/fcen_sample.csv (3 rows)
  - loads 3 items into db_session
  - idempotent: re-running does not duplicate
  - items have ttl_hours=None

test_unified_service.py — SQLite in-memory + respx
  - cache hit returns without calling APIs
  - cache miss fans out to all sources
  - expired row triggers refresh
  - USDA down → returns FCÉN + OFF results
  - all sources down → returns []

test_nutrition.py — API level
  - GET /nutrition/search?q=chicken → 200
  - GET /nutrition/search (no q) → 422
  - GET /nutrition/search unauthenticated → 401
  - GET /nutrition/food/usda_789 → 200
  - GET /nutrition/food/unknown_999 → 404
```

---

## Migration

`alembic/versions/0007_food_cache.py` — creates `food_cache` table. No destructive changes to existing tables.

`data/food_database_cache.json` — kept as-is (read-only legacy reference, not used by new service).

---

## Barcode Lookup

Barcode lookup is folded into `GET /nutrition/food/off_{barcode}`. The old dedicated `/food/barcode/{barcode}` route is removed with `food.py`. Clients use source-prefixed IDs: `off_3017620422003` triggers `off_client.fetch("3017620422003")`.

---

## FCÉN CSV Structure

The Health Canada FCÉN download is a **multi-file relational set**, not a single flat CSV:
- `FOOD NAME.csv` — `FoodID`, `FoodDescription` (EN), `FoodDescriptionF` (FR)
- `NUTRIENT AMOUNT.csv` — `FoodID`, `NutrientID`, `NutrientValue`
- `NUTRIENT NAME.csv` — `NutrientID`, `NutrientName` (maps IDs to names like "Energy", "Protein")

`fcen_loader.py` must JOIN these three files in memory:
1. Load food names → dict `{food_id: {name_en, name_fr}}`
2. Load nutrient names → dict `{nutrient_id: nutrient_name}`
3. Load nutrient amounts → pivot: `{food_id: {nutrient_name: value}}`
4. Upsert into `food_cache`

Key NutrientIDs: Energy=208 (kcal), Protein=203, Fat=204, Carbohydrate=205, Fibre=291, Sodium=307, Sugars=269.

---

## OFF Keyword Search

OFF provides a free keyword search API:
```
GET https://world.openfoodfacts.org/cgi/search.pl?search_terms=<q>&json=1&page_size=10
```
Response includes `products[]` array — same structure as barcode lookup. Reliability is lower than USDA (community-maintained). `off_client.py` implements both `search(q)` and `fetch(barcode)`.

---

## V2 Roadmap (out of scope)

- Serving language preference from athlete profile (FR vs EN name display)
- Rate limiting per athlete for external API calls
- Nutritional scoring / Nutri-Score from OFF metadata
