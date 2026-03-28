# API Endpoints — Phase 1 Design

## Overview

Add a FastAPI layer exposing athlete CRUD and weekly training plan generation to a web frontend. No authentication in this phase. All business logic (agents, core modules) is already implemented and tested.

## Scope

**In scope:**
- Athlete CRUD: list, create, get, update, delete
- Plan generation: POST to generate, GET to retrieve latest
- Full-stack integration test against real HeadCoach (no mocking)

**Out of scope:**
- Authentication / authorization
- OAuth connector flows (Strava, Hevy)
- Nutrition plan endpoints
- Weekly review endpoints
- Async / background job processing

## Architecture

Router-per-resource pattern using FastAPI `APIRouter`. Two routers (`athletes`, `plans`) mounted in `main.py`. DB session injected via `Depends(get_db)` from `dependencies.py`.

```
backend/app/
├── main.py                  # FastAPI app, router mounts, CORS
├── dependencies.py          # get_db() session dependency
└── routes/
    ├── __init__.py
    ├── athletes.py          # CRUD /athletes
    └── plans.py             # POST/GET /athletes/{id}/plan
```

## Endpoints

### Athletes

| Method | Path | Status codes |
|--------|------|--------------|
| `GET` | `/athletes` | 200 |
| `POST` | `/athletes` | 201 |
| `GET` | `/athletes/{id}` | 200, 404 |
| `PUT` | `/athletes/{id}` | 200, 404 |
| `DELETE` | `/athletes/{id}` | 204, 404 |

Schemas (already in `backend/app/schemas/`):
- Input: `AthleteCreate`, `AthleteUpdate`
- Output: `AthleteResponse`

JSON fields (`sports`, `goals`, `available_days`, `equipment`) are stored as strings in the DB. Route handlers serialize on write, deserialize on read via Pydantic validators.

### Plans

| Method | Path | Status codes |
|--------|------|--------------|
| `POST` | `/athletes/{id}/plan` | 201, 404 |
| `GET` | `/athletes/{id}/plan` | 200, 404 |

**`POST /athletes/{id}/plan` request body:**
```json
{ "start_date": "2026-03-30", "end_date": "2026-04-05" }
```

**Generation flow:**
1. Load athlete from DB → 404 if missing
2. Build `AgentContext` from athlete fields + empty connector data
3. Compute `week_number` from `start_date` (weeks since a reference start, defaulting to 1)
4. Compute `weeks_remaining` as `(athlete.target_race_date - start_date).days // 7` if athlete has target date, else `0`
5. Call `HeadCoach(db).analyze(context)` → `AgentRecommendation`
6. Persist as `TrainingPlanModel` row
7. Return `TrainingPlanResponse`

**`GET /athletes/{id}/plan`** returns the most recently created plan (ordered by `start_date DESC`, limit 1). 404 if none exists.

## Dependencies

`backend/app/dependencies.py` exposes:
```python
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

## Error Handling

- **404**: `HTTPException(status_code=404)` for missing athlete or plan
- **422**: Handled automatically by FastAPI/Pydantic validation
- No custom error middleware in this phase

## Testing

- Test client: FastAPI `TestClient` (wraps `httpx`) — no live server
- DB isolation: fresh in-memory SQLite per test, same pattern as `tests/backend/db/test_models.py`
- Dependency override: `app.dependency_overrides[get_db] = lambda: test_db_session`
- **No mocking of HeadCoach** — real agents called with empty connector data
- Test files:
  - `tests/backend/api/test_athletes.py` (~8 tests: CRUD happy paths, 404 cases, validation)
  - `tests/backend/api/test_plans.py` (~8 tests: generate, retrieve, 404, AgentContext round-trip)

## File Summary

| File | Action |
|------|--------|
| `backend/app/main.py` | Create |
| `backend/app/dependencies.py` | Create |
| `backend/app/routes/__init__.py` | Create |
| `backend/app/routes/athletes.py` | Create |
| `backend/app/routes/plans.py` | Create |
| `tests/backend/api/__init__.py` | Create |
| `tests/backend/api/test_athletes.py` | Create |
| `tests/backend/api/test_plans.py` | Create |
