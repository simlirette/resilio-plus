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
