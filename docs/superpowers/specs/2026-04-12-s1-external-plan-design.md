# S-1 ExternalPlan Backend CRUD — Design Spec

**Date:** 2026-04-12  
**Branch:** session/s1-external-plan  
**Status:** Approved (autonomous session — spec derived from SESSION_REPORT.md S-1)

---

## Context

Resilio+ supports two modes: Full Coaching (Volet 1 + Volet 2) and Tracking Only (Volet 2 seul).

In Tracking Only mode, athletes follow an external coach's plan. S-1 implements the backend CRUD layer allowing these athletes to enter and manage their external plan manually.

Tables already exist (migration 0003): `external_plans`, `external_sessions`.

---

## Architecture

### New files

| File | Role |
|---|---|
| `backend/app/schemas/external_plan.py` | Pydantic request/response schemas |
| `backend/app/services/external_plan_service.py` | Business logic — ExternalPlanService |
| `backend/app/routes/external_plan.py` | FastAPI router (5 endpoints) |
| `tests/backend/services/test_external_plan_service.py` | Service unit tests |
| `tests/backend/api/test_external_plan.py` | API integration tests |

### Modified files

| File | Change |
|---|---|
| `backend/app/main.py` | Register external_plan router |

---

## Data Model (existing, no migration needed)

```python
ExternalPlanModel:
  id, athlete_id, title, source ("manual"|"file_import")
  status ("active"|"archived"), start_date, end_date, created_at

ExternalSessionModel:
  id, plan_id, athlete_id, session_date, sport, title
  description, duration_min, status ("planned"|"completed"|"skipped")
```

---

## Endpoints

All routes use `Depends(require_tracking_mode)` — 403 if athlete is in "full" mode.

| Method | Path | Action |
|---|---|---|
| POST | `/athletes/{id}/external-plan` | Create plan (archives previous active plan) |
| GET | `/athletes/{id}/external-plan` | Get active plan with sessions |
| POST | `/athletes/{id}/external-plan/sessions` | Add session to active plan |
| PATCH | `/athletes/{id}/external-plan/sessions/{session_id}` | Update session fields |
| DELETE | `/athletes/{id}/external-plan/sessions/{session_id}` | Hard-delete session |

---

## ExternalPlanService

```python
class ExternalPlanService:
    @staticmethod
    def create_plan(athlete_id, title, start_date, end_date, db) -> ExternalPlanModel:
        # 1. Archive any existing active external plan (status → "archived")
        # 2. Create new ExternalPlanModel(source="manual", status="active")
        # Returns the new plan

    @staticmethod
    def get_active_plan(athlete_id, db) -> ExternalPlanModel | None:
        # Query ExternalPlanModel where athlete_id=athlete_id AND status="active"
        # Returns first result or None

    @staticmethod
    def add_session(plan_id, athlete_id, data, db) -> ExternalSessionModel:
        # Verify plan belongs to athlete, status="active"
        # Create ExternalSessionModel
        # Returns new session

    @staticmethod
    def update_session(session_id, athlete_id, data, db) -> ExternalSessionModel:
        # Verify session belongs to athlete
        # Apply partial update (only provided fields)
        # Returns updated session

    @staticmethod
    def delete_session(session_id, athlete_id, db) -> None:
        # Verify session belongs to athlete
        # Hard-delete (session is user-entered data; plan itself is preserved)
        # Raises 404 if not found, 403 if wrong athlete
```

---

## XOR Invariant

Rule: "un seul plan actif (ExternalPlan XOR TrainingPlan)"

Since `require_tracking_mode` guards all external-plan routes, an athlete in tracking_only mode cannot reach Volet 1 endpoints that create TrainingPlans (`require_full_mode`). The mode switch endpoint (PATCH /mode) already archives active TrainingPlans when switching to tracking_only.

Therefore, within ExternalPlanService, the XOR is maintained by:
1. Athlete must be in tracking_only mode (enforced by ModeGuard)
2. `create_plan()` archives any existing active ExternalPlan before creating a new one

No cross-check against TrainingPlans needed at the service level (ModeGuard guarantees mutual exclusion at the HTTP layer).

---

## Pydantic Schemas

```python
# Request
class ExternalPlanCreate(BaseModel):
    title: str
    start_date: date | None = None
    end_date: date | None = None

class ExternalSessionCreate(BaseModel):
    session_date: date
    sport: str
    title: str
    description: str | None = None
    duration_min: int | None = None

class ExternalSessionUpdate(BaseModel):
    session_date: date | None = None
    sport: str | None = None
    title: str | None = None
    description: str | None = None
    duration_min: int | None = None
    status: Literal["planned", "completed", "skipped"] | None = None

# Response
class ExternalSessionOut(BaseModel):
    id: str
    plan_id: str
    athlete_id: str
    session_date: date
    sport: str
    title: str
    description: str | None
    duration_min: int | None
    status: str

class ExternalPlanOut(BaseModel):
    id: str
    athlete_id: str
    title: str
    source: str
    status: str
    start_date: date | None
    end_date: date | None
    created_at: datetime
    sessions: list[ExternalSessionOut]
```

---

## Error Handling

| Situation | HTTP Code |
|---|---|
| Athlete not in tracking_only | 403 |
| No active plan found (GET) | 404 |
| Plan not found / wrong athlete | 404 |
| Session not found / wrong athlete | 404 |

---

## Testing Strategy

**Service tests** (`tests/backend/services/test_external_plan_service.py`):
- SQLite in-memory, direct service calls
- create_plan → returns active plan
- create_plan when plan exists → archives old, creates new
- get_active_plan → returns active plan or None
- add_session → session belongs to plan
- update_session → partial update works
- delete_session → session removed from DB
- delete_session wrong athlete → 404

**API tests** (`tests/backend/api/test_external_plan.py`):
- Full HTTP roundtrip via TestClient
- Athlete in tracking_only mode: all 5 endpoints work
- Athlete in full mode: all 5 endpoints return 403
- POST plan → GET plan → POST session → PATCH session → DELETE session (full CRUD flow)
- GET plan with no active plan → 404

---

## Decisions

1. **Hard-delete for sessions**: Individual sessions are user-entered data within a plan. Deleting a session doesn't violate the "never archive" rule (which applies to plans, not individual training slots).
2. **No TrainingPlan XOR check at service level**: ModeGuard handles this at the HTTP layer, and mode switch already archives TrainingPlans.
3. **GET active plan returns 404 if none**: Clean sentinel for frontend — no ambiguity between "no plan" and "error".
4. **source always "manual"**: File import is S-2 scope.
