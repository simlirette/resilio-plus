# Phase 8 — Daily Loop Design Spec

**Date:** 2026-04-10
**Status:** Approved
**Depends on:** Phase 7 (all 6 agents, sport_budgets, enriched sessions)

---

## Goal

Close the athlete feedback loop: see session details, log actual vs planned, view training history. This data feeds back into the Recovery Coach (readiness) and future ACWR computation.

---

## Problem Statement

Sessions in a `TrainingPlanModel` are stored as a JSON blob (`weekly_slots_json`). `WorkoutSlot` has no stable `id` field, making it impossible to reference individual sessions for logging. Phase 8 fixes this and adds the logging layer.

---

## Architecture

### 1. Session Identification — Add `id` to `WorkoutSlot`

`WorkoutSlot` gains an optional `id: str` field (default: `uuid4()`). The field is generated at plan creation time and stored inside `weekly_slots_json`.

**Backward compatibility:** Existing plans without session IDs in their JSON remain valid — `WorkoutSlot.id` defaults to `uuid4()` on deserialization (stable within a request, not persistent). The plan page falls back to index-based routing for old sessions. New plans always have IDs.

### 2. New DB Table: `SessionLogModel`

```
session_logs
├── id          String PK
├── athlete_id  FK → athletes.id
├── plan_id     FK → training_plans.id
├── session_id  String (FK by convention to WorkoutSlot.id in weekly_slots_json)
├── actual_duration_min  Integer | None
├── skipped     Boolean default=False
├── rpe         Integer | None  (1–10)
├── notes       Text default=""
├── actual_data_json  Text default="{}"   -- sport-specific payload
└── logged_at   DateTime(timezone=True)
```

`actual_data_json` schema by sport:
- **Running:** `{"avg_pace_s_km": 320, "distance_km": 10.2}`
- **Lifting:** `{"sets": [{"exercise": "squat", "reps": 5, "load_kg": 80}]}`
- **Biking:** `{"avg_power_w": 185, "distance_km": 40.5}`
- **Swimming:** `{"distance_m": 1500, "css_pace_s": 102}`

### 3. New API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/athletes/{id}/sessions/{session_id}` | Session detail from current plan |
| `POST` | `/athletes/{id}/sessions/{session_id}/log` | Create or update session log |
| `GET`  | `/athletes/{id}/sessions/{session_id}/log` | Get log for a session |
| `GET`  | `/athletes/{id}/history` | Past weeks (plans + reviews + completion %) |

All endpoints require JWT auth + `athlete_id == current_user`.

**Session detail response:**
```json
{
  "session_id": "uuid",
  "plan_id": "uuid",
  "date": "2026-04-10",
  "sport": "running",
  "workout_type": "tempo_z2",
  "duration_min": 45,
  "fatigue_score": {...},
  "notes": "VDOT 48 | T-pace 4:12/km",
  "log": null | { ...SessionLog }
}
```

**Log request body (Standard — option B):**
```json
{
  "actual_duration_min": 40,
  "skipped": false,
  "rpe": 7,
  "notes": "Felt good, kept pace",
  "actual_data": {"avg_pace_s_km": 253}
}
```

**POST log:** Upserts — if a log exists for this `session_id`, update it.

**History response:** Array of `WeekSummary`:
```json
[
  {
    "plan_id": "...",
    "week_number": 3,
    "start_date": "2026-03-31",
    "end_date": "2026-04-06",
    "phase": "general_prep",
    "planned_hours": 9.5,
    "actual_hours": 8.2,
    "completion_pct": 86.3,
    "acwr": 1.05,
    "sessions_logged": 4,
    "sessions_total": 6
  }
]
```

### 4. New Routes File

`backend/app/routes/sessions.py` — handles all session and history endpoints. Registered in `main.py`.

### 5. Frontend Pages

**Updated: `plan/page.tsx`**
- Each session `Card` becomes a `Link` to `/session/[id]`
- If a `SessionLog` exists for this session: show a green `✓ Logged` badge + actual duration
- `WorkoutSlot.id` is used for routing; falls back to plan_id+index for legacy sessions

**New: `session/[id]/page.tsx`**
- Shows full session detail: sport badge, workout type, duration, coach notes, fatigue score breakdown (local/CNS/metabolic bars)
- "Log this session" button → `/session/[id]/log`
- If already logged: shows log summary + "Edit log" button
- Back link → `/plan`

**New: `session/[id]/log/page.tsx`**
- Form fields:
  - Duration (number input, pre-filled with planned)
  - "Skip this session" toggle (hides other fields when checked)
  - RPE slider (1–10) with label (1=Very Easy, 10=Max Effort)
  - Notes textarea
  - Sport-specific section (conditional on `session.sport`):
    - Running: avg pace (min:sec/km), distance
    - Lifting: simple text "X sets × Y reps at Z kg" (freeform, stored as notes in actual_data for MVP)
    - Biking: avg power (W), distance
    - Swimming: distance (m)
- Submit → POST log → redirect to `/session/[id]`

**New: `history/page.tsx`**
- List of past weeks, newest first
- Each row: week dates, phase badge, completion bar (actual/planned hours), ACWR badge, sessions logged X/Y
- No pagination for MVP (athletes rarely have >20 weeks)

---

## Data Flow

```
Plan generation → WorkoutSlot.id generated → stored in weekly_slots_json
     │
     ▼
Frontend plan/page → links to /session/[id]
     │
     ▼
/session/[id]/log → POST /sessions/{id}/log → upsert SessionLogModel
     │
     ▼
/athletes/{id}/history → joins TrainingPlanModel + WeeklyReviewModel + SessionLogModel
```

---

## DB Migration

New `session_logs` table via SQLAlchemy model addition. No existing tables modified. SQLite `CREATE TABLE IF NOT EXISTS` pattern (same as existing migrations).

---

## Schema Changes

`WorkoutSlot` in `backend/app/schemas/plan.py`:
```python
from uuid import uuid4

class WorkoutSlot(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))   # NEW
    date: date
    sport: Sport
    workout_type: str
    duration_min: int = Field(..., gt=0)
    fatigue_score: FatigueScore
    notes: str = ""
```

New `SessionLog` Pydantic schema in `backend/app/schemas/session_log.py`.

---

## Error Handling

- `GET /sessions/{session_id}` — 404 if session_id not found in current plan
- `POST /sessions/{session_id}/log` — 404 if session_id not found; 400 if `rpe` out of [1,10]
- `GET /history` — returns `[]` if no plans exist (never 404)
- Frontend: same error/loading pattern as existing pages (ApiError → logout if 401, error message otherwise)

---

## Testing

**Backend:**
- `tests/backend/routes/test_sessions.py` — all 4 endpoints, auth checks, upsert behavior, 404 cases
- `tests/backend/schemas/test_workout_slot_id.py` — verify `id` generated on deserialization

**Frontend:**
- `src/app/session/__tests__/` — session detail renders, log form submits, history list renders
- Update `src/app/plan/__tests__/` — verify session cards link to `/session/[id]`

**E2E:**
- `tests/e2e/test_full_workflow.py` — add test_07: onboarding → plan → log session → history shows 1 week

---

## File Map

| File | Action |
|------|--------|
| `backend/app/schemas/plan.py` | Modify — add `id` to `WorkoutSlot` |
| `backend/app/schemas/session_log.py` | Create — `SessionLogRequest`, `SessionLogResponse`, `SessionDetailResponse`, `WeekSummary` |
| `backend/app/db/models.py` | Modify — add `SessionLogModel` |
| `backend/app/routes/sessions.py` | Create — 4 endpoints + history |
| `backend/app/main.py` | Modify — include sessions router |
| `frontend/src/lib/api.ts` | Modify — add `getSession`, `logSession`, `getSessionLog`, `getHistory` |
| `frontend/src/app/plan/page.tsx` | Modify — link cards to session detail, log badge |
| `frontend/src/app/session/[id]/page.tsx` | Create — session detail page |
| `frontend/src/app/session/[id]/log/page.tsx` | Create — log form |
| `frontend/src/app/history/page.tsx` | Create — history list |
| `tests/backend/routes/test_sessions.py` | Create |
| `tests/e2e/test_full_workflow.py` | Modify — add test_07 |
