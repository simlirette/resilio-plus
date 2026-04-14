# Mobile API Contract — V1 Business Endpoints

**Date:** 2026-04-14  
**Status:** Approved  
**Scope:** 5 new endpoints filling gaps for mobile home screen. Existing endpoints remain unchanged. Auth handled by `get_current_athlete_id` (JWT Bearer, already live). Prompt 8 adds `/auth/*` routes only.

---

## Context

Backend already has: readiness, check-in, recovery-status, nutrition-directives, plan, session log, per-connector sync, connectors list, analytics, energy history.

Mobile home screen needs 5 things not yet exposed:

| Gap | Endpoint |
|---|---|
| Muscle strain radar | `GET /athletes/{id}/strain` |
| Today's sessions | `GET /athletes/{id}/today` |
| Today's resolved macros | `GET /athletes/{id}/nutrition-today` |
| Off-plan workout log | `POST /athletes/{id}/workouts` |
| Sync all connectors | `POST /athletes/{id}/connectors/sync` |

---

## Endpoint Specifications

### 1. `GET /athletes/{id}/strain`

Returns the 10-axis muscle strain index (0–100 per group). Calls `compute_muscle_strain()` from `backend/app/core/strain.py` with Strava + Hevy data from `fetch_connector_data()`.

**Auth:** `get_current_athlete_id`, `_require_own`  
**Tags:** `["strain"]`

**Response 200 — `MuscleStrainResponse`:**
```json
{
  "computed_at": "2026-04-14",
  "scores": {
    "quads": 72.4,
    "posterior_chain": 45.1,
    "glutes": 38.0,
    "calves": 61.2,
    "chest": 12.0,
    "upper_pull": 25.3,
    "shoulders": 18.6,
    "triceps": 9.0,
    "biceps": 7.5,
    "core": 33.1
  },
  "peak_group": "quads",
  "peak_score": 72.4
}
```

**Schema (`MuscleStrainResponse`):**
```python
class MuscleStrainResponse(BaseModel):
    computed_at: date
    scores: dict[str, float]   # muscle → 0–100
    peak_group: str
    peak_score: float
```

**Errors:**
- `404` — athlete not found
- `403` — not own athlete

**Implementation note:** `MuscleStrainScore` (from `models/athlete_state.py`) already has all 10 fields. `MuscleStrainResponse` wraps it and adds `computed_at`, `peak_group`, `peak_score` for UI convenience. New route file: `backend/app/routes/strain.py`.

---

### 2. `GET /athletes/{id}/today`

Returns today's sessions from the current active plan (filtered by `date == today`). Returns an empty list on rest days — never 404.

**Auth:** `get_current_athlete_id`, `_require_own`  
**Tags:** `["sessions"]`  
**Query params:** `date: date = Query(default=date.today())` (allows testing with a specific date)

**Response 200 — `TodayResponse`:**
```json
{
  "date": "2026-04-14",
  "is_rest_day": false,
  "plan_id": "abc123",
  "sessions": [
    {
      "id": "slot-uuid",
      "date": "2026-04-14",
      "sport": "running",
      "workout_type": "Easy aerobic",
      "duration_min": 60,
      "fatigue_score": { "local_muscular": 30, "cns_load": 20, "metabolic_cost": 25, "recovery_hours": 12, "affected_muscles": ["quads"] },
      "notes": "Z1 easy run",
      "log": null
    }
  ]
}
```

**Schema:**
```python
class TodayResponse(BaseModel):
    date: date
    is_rest_day: bool
    plan_id: str | None     # None if no active plan
    sessions: list[SessionDetailResponse]
```

`SessionDetailResponse` already exists in `schemas/session_log.py` — reused directly.

**Errors:**
- `404` — athlete not found
- `403` — not own athlete
- No 404 for missing plan — returns `{ is_rest_day: true, plan_id: null, sessions: [] }`

**Implementation note:** Added to `backend/app/routes/sessions.py` (existing file). Queries latest plan, parses `weekly_slots_json`, filters by `slot.date == query_date`, fetches logs for each slot.

---

### 3. `GET /athletes/{id}/nutrition-today`

Returns macros for today, resolving the day_type from today's plan sessions. If no plan or no sessions today → day_type = `rest`.

**Auth:** `get_current_athlete_id`, `_require_own`  
**Tags:** `["nutrition"]`  
**Query params:** `date: date = Query(default=date.today())`

**Response 200 — `NutritionTodayResponse`:**
```json
{
  "date": "2026-04-14",
  "day_type": "endurance_short",
  "macro_target": {
    "carbs_g_per_kg": 5.5,
    "protein_g_per_kg": 1.8,
    "fat_g_per_kg": 1.2,
    "calories_total": 2650
  },
  "intra_effort_carbs_g_per_h": null,
  "sodium_mg_per_h": null
}
```

**Schema:**
```python
class NutritionTodayResponse(BaseModel):
    date: date
    day_type: DayType
    macro_target: MacroTarget
    intra_effort_carbs_g_per_h: float | None
    sodium_mg_per_h: float | None
```

`MacroTarget` and `DayType` already exist.

**Day type resolution logic:**
1. Get today's sessions from plan (same as `/today` logic)
2. Map sport → day_type: any `running`/`biking`/`swimming` session > 60 min → `endurance_long`, ≤ 60 min → `endurance_short`, any `lifting` → `strength`, race session → `race`, no sessions → `rest`
3. If multiple sessions conflict, use highest-load day_type (race > endurance_long > endurance_short > strength > rest)

**Implementation note:** Added to `backend/app/routes/nutrition.py` (existing file). Reuses `compute_nutrition_directives()` — calls it then looks up the resolved day_type.

---

### 4. `POST /athletes/{id}/workouts`

Logs an off-plan manual workout. Not tied to a plan session. Creates a `SessionLogModel` with `plan_id = None` and `session_id = "manual-{uuid}"`.

**Auth:** `get_current_athlete_id`, `_require_own`  
**Tags:** `["sessions"]`  
**Status:** `201`

**Request body — `ManualWorkoutRequest`:**
```json
{
  "sport": "running",
  "workout_type": "Easy run",
  "date": "2026-04-14",
  "actual_duration_min": 45,
  "rpe": 6,
  "notes": "Bonus recovery jog",
  "actual_data": {
    "distance_km": 7.2,
    "avg_pace_sec_per_km": 375
  }
}
```

**Schema:**
```python
class ManualWorkoutRequest(BaseModel):
    sport: Sport
    workout_type: str
    date: date
    actual_duration_min: int = Field(..., ge=1, le=600)
    rpe: int | None = Field(default=None, ge=1, le=10)
    notes: str = ""
    actual_data: dict[str, Any] = Field(default_factory=dict)
```

**Response 201 — `ManualWorkoutResponse`:**
```json
{
  "id": "uuid",
  "session_id": "manual-uuid",
  "sport": "running",
  "workout_type": "Easy run",
  "date": "2026-04-14",
  "actual_duration_min": 45,
  "rpe": 6,
  "notes": "Bonus recovery jog",
  "actual_data": { "distance_km": 7.2 },
  "logged_at": "2026-04-14T09:12:00Z"
}
```

**Schema:**
```python
class ManualWorkoutResponse(BaseModel):
    id: str
    session_id: str
    sport: Sport
    workout_type: str
    date: date
    actual_duration_min: int
    rpe: int | None
    notes: str
    actual_data: dict[str, Any]
    logged_at: datetime
```

**Errors:**
- `404` — athlete not found
- `403` — not own athlete
- `422` — validation (duration out of range, invalid sport)

**Implementation note:** New route in `backend/app/routes/sessions.py`. `plan_id = None` is already nullable in `SessionLogModel`. `actual_data` stores `sport` and `workout_type` keys alongside user-provided data so analytics can read them.

---

### 5. `POST /athletes/{id}/connectors/sync`

Fires sync for all configured connectors in sequence. Returns per-provider status. Always 200 — partial failures included in response body, not as HTTP errors.

**Auth:** `get_current_athlete_id`, `_require_own`  
**Tags:** `["connectors"]`  
**Status:** `200`

**Response 200 — `SyncAllResponse`:**
```json
{
  "synced_at": "2026-04-14T09:15:00Z",
  "results": {
    "strava": "ok",
    "hevy": "skipped",
    "terra": "error"
  },
  "errors": {
    "terra": "Terra connector not connected"
  }
}
```

**Status values per provider:**
- `"ok"` — sync succeeded
- `"skipped"` — connector not configured for this athlete
- `"error"` — sync threw exception (detail in `errors` dict)

**Schema:**
```python
ProviderStatus = Literal["ok", "skipped", "error"]

class SyncAllResponse(BaseModel):
    synced_at: datetime
    results: dict[str, ProviderStatus]
    errors: dict[str, str]   # only populated entries for "error" providers
```

**Implementation note:** Added to `backend/app/routes/connectors.py`. Calls `SyncService.sync_strava`, `SyncService.sync_hevy`, `SyncService.sync_terra` in sequence inside try/except per provider. `ConnectorNotFoundError` → `"skipped"`, other exceptions → `"error"`.

---

## Auth Pattern (all 5 endpoints)

All endpoints use the existing pattern — no placeholder needed:

```python
from ..dependencies import get_db, get_current_athlete_id

def _require_own(
    athlete_id: str,
    current_id: Annotated[str, Depends(get_current_athlete_id)],
) -> str:
    if current_id != athlete_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return athlete_id
```

`get_current_athlete_id` decodes JWT Bearer token → `payload["sub"]` (athlete UUID). Already live. No changes needed for Prompt 8 compatibility — Prompt 8 adds `/auth/login` and `/auth/register` which issue these tokens.

---

## OpenAPI Export

After implementation, export via:
```bash
python -c "
import json
from backend.app.main import app
import asyncio
print(json.dumps(app.openapi(), indent=2))
" > docs/backend/openapi.json
```

The `/auth/*` section will be populated once Prompt 8 merges. The business endpoints are independent.

---

## Contract Tests

One test file per new endpoint: `tests/backend/test_contract_{endpoint}.py`. Each test:
1. Creates a test athlete + JWT token
2. Calls the endpoint
3. Validates response against the schema using `pydantic.TypeAdapter.validate_python()`
4. Validates HTTP status code

No mocking of business logic — tests hit real DB (db_session fixture from V3-K).

---

## Files Created/Modified

| File | Action |
|---|---|
| `backend/app/routes/strain.py` | **New** — strain endpoint |
| `backend/app/routes/sessions.py` | **Modify** — add `/today` and `POST /workouts` |
| `backend/app/routes/nutrition.py` | **Modify** — add `/nutrition-today` |
| `backend/app/routes/connectors.py` | **Modify** — add `POST /connectors/sync` |
| `backend/app/main.py` | **Modify** — include strain router |
| `docs/backend/openapi.json` | **New** — exported OpenAPI spec |
| `tests/backend/test_contract_strain.py` | **New** |
| `tests/backend/test_contract_today.py` | **New** |
| `tests/backend/test_contract_nutrition_today.py` | **New** |
| `tests/backend/test_contract_workouts.py` | **New** |
| `tests/backend/test_contract_sync.py` | **New** |

---

## Out of Scope

- `/auth/*` endpoints — Prompt 8 session
- Changes to existing endpoint schemas — contract freeze
- Connector OAuth flows — already exist, unchanged
