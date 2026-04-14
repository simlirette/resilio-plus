# Hevy CSV Import Design — Resilio+

**Date:** 2026-04-14  
**Status:** Approved  
**Scope:** Hevy CSV export → parse → map to SessionLogModel via `POST /integrations/hevy/import`

---

## Context

Resilio+ already syncs Hevy data via REST API (`sync_hevy()`). This feature adds a complementary CSV import path for athletes who want to bulk-import historical workout data from a Hevy export file without re-authorizing the API connector.

Existing infrastructure reused:
- `HevyWorkout` / `HevyExercise` / `HevySet` schemas (`schemas/connector.py`)
- `SessionLogModel` with `actual_data_json` (same structure as API sync)
- `_get_latest_plan()` plan matching logic (`routes/connectors.py`)
- `get_current_athlete_id` FastAPI dependency

---

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Module location | `backend/app/integrations/hevy/` | Clean separation from OAuth connectors; testable in isolation |
| Unit detection | `?unit=kg\|lbs` query param (default: kg) | Hevy CSV has no unit column; explicit is unambiguous |
| Duplicate handling | Upsert | Re-import corrected data just works; no friction |
| Plan matching | Match if found, standalone if not | No data lost; historical imports don't need a plan slot |
| Response | Per-workout summary + totals | Full visibility without overwhelming the caller |

---

## File Structure

```
backend/app/integrations/
  __init__.py
  hevy/
    __init__.py
    csv_parser.py      — parse raw bytes → list[HevyWorkout]
    importer.py        — list[HevyWorkout] → SessionLogModel upserts + summary

backend/app/routes/integrations.py   — POST /integrations/hevy/import

tests/backend/integrations/
  test_hevy_csv_parser.py
  test_hevy_csv_importer.py
tests/fixtures/hevy_export_sample.csv

docs/backend/INTEGRATIONS.md
```

---

## CSV Format

Standard Hevy export columns (in order):
```
Date, Workout Name, Exercise Name, Set Order, Weight, Reps,
Distance, Seconds, Notes, Workout Notes, RPE
```

- `Date` — ISO 8601 date string (`2026-04-01`)
- `Weight` — numeric, unit determined by `?unit` param; empty = bodyweight (`None`)
- `Reps` — integer; empty = `None`
- `RPE` — float 1–10; empty = `None`

Grouping:
- Rows with same `(Date, Workout Name)` → one `HevyWorkout`
- Within a workout, rows with same `Exercise Name` → one `HevyExercise`
- Each row → one `HevySet`

---

## CSV Parser (`csv_parser.py`)

Pure function — no DB, no HTTP.

```python
def parse_hevy_csv(content: bytes, unit: str = "kg") -> list[HevyWorkout]:
    ...
```

- Input: raw file bytes + unit (`"kg"` or `"lbs"`)
- Output: `list[HevyWorkout]` (existing Pydantic schema)
- Raises `ValueError` on: malformed CSV, missing required columns, no data rows, invalid date
- Weight conversion: if `unit == "lbs"`, multiply by `0.453592` before storing
- `HevyWorkout.performed_at` = parsed date at midnight UTC

---

## Importer (`importer.py`)

```python
def import_hevy_workouts(
    athlete_id: str,
    workouts: list[HevyWorkout],
    db: Session,
) -> ImportSummary:
    ...
```

Per workout:
1. Look up latest active plan via `_get_latest_plan(athlete_id, db)`
2. Search plan slots for `date == workout.date AND sport == "lifting"`
3. **Match** → `session_id` from plan slot
4. **No match** → `session_id = f"hevy-standalone-{date}-{workout_name_slug}"`
5. Upsert `SessionLogModel` on `(athlete_id, session_id)` unique constraint

`actual_data_json` structure:
```json
{
  "source": "hevy_csv",
  "hevy_workout_id": "2026-04-01-push-day-a",
  "exercises": [
    {
      "name": "Squat",
      "sets": [
        {"reps": 5, "weight_kg": 100.0, "rpe": 8.0, "set_type": "normal"}
      ]
    }
  ]
}
```

`actual_duration_min` → `None` (CSV has no duration).

---

## Endpoint

```
POST /integrations/hevy/import?unit=kg
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
Body: file=<hevy_export.csv>
```

- Protected by `get_current_athlete_id` (no `athlete_id` in URL — user imports own data)
- `unit` query param: `"kg"` (default) or `"lbs"`
- Router registered on main app as `/integrations`

### Response `200 OK`

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

### Error responses

| Status | Condition |
|---|---|
| `422` | Malformed CSV, missing columns, no data rows, invalid `unit` value |
| `404` | Athlete not found (guard only — valid JWT implies valid athlete) |

---

## Testing Plan

### `test_hevy_csv_parser.py`

- Nominal: valid 3-workout CSV → 3 `HevyWorkout` objects, correct grouping
- Unit conversion: `lbs` CSV → weights stored in kg
- Bodyweight sets: empty Weight → `None`
- Malformed CSV: missing required column → `ValueError`
- Empty CSV (header only): → `ValueError("no workouts found")`
- Multi-exercise workout: correct `HevyExercise` grouping

### `test_hevy_csv_importer.py`

- Match found: workout date+lifting slot in plan → `session_id` from plan
- No match: no plan slot → standalone `session_id` generated
- Upsert: re-import same workout → overwrites, no duplicate row
- No plan: athlete has no plan → all standalone
- Multiple workouts: mixed matched/standalone in one import

### `test_integrations.py` (API-level)

- `POST /integrations/hevy/import` nominal → 200 with correct counts
- Unknown unit param → 422
- Empty file → 422
- Unauthenticated → 401

---

## `actual_data_json` Compatibility

The `source: "hevy_csv"` field distinguishes CSV imports from API syncs (`source: "hevy"`). All other fields are identical — the coaching agents and review logic treat them the same.

---

## V2 Roadmap (not in scope)

- Auto-detect unit from a user profile preference
- Duration estimation from `Seconds` column (aggregate per workout)
- FatSecret CSV import (same pattern)
- Garmin FIT bulk import
