# Hevy CSV Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `POST /integrations/hevy/import` endpoint that accepts a Hevy CSV export file and upserts workouts into `SessionLogModel`, matching plan sessions where possible.

**Architecture:** Pure parser (`csv_parser.py`) converts raw bytes → `list[HevyWorkout]` (reusing existing Pydantic schema). Importer (`importer.py`) writes to DB using the same `SessionLogModel` upsert pattern as `sync_hevy()`. Route in `routes/integrations.py` wires them together behind `get_current_athlete_id`.

**Tech Stack:** FastAPI, SQLAlchemy (SQLite in tests), Pydantic v2, Python `csv` stdlib, `itertools.groupby`, existing `HevyWorkout`/`HevyExercise`/`HevySet` schemas from `backend/app/schemas/connector.py`.

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `tests/fixtures/hevy_export_sample.csv` | Test data — 2 workouts, 5 exercises, edge cases |
| Create | `backend/app/integrations/__init__.py` | Package marker |
| Create | `backend/app/integrations/hevy/__init__.py` | Package marker |
| Create | `backend/app/integrations/hevy/csv_parser.py` | Pure: bytes → `list[HevyWorkout]` |
| Create | `tests/backend/integrations/__init__.py` | Package marker |
| Create | `tests/backend/integrations/conftest.py` | `db_session` fixture for importer tests |
| Create | `tests/backend/integrations/test_hevy_csv_parser.py` | Parser unit tests (no DB) |
| Create | `backend/app/integrations/hevy/importer.py` | `list[HevyWorkout]` → `SessionLogModel` upserts |
| Create | `tests/backend/integrations/test_hevy_csv_importer.py` | Importer unit tests |
| Create | `backend/app/routes/integrations.py` | `POST /integrations/hevy/import` |
| Modify | `backend/app/main.py` | Register integrations router |
| Create | `tests/backend/api/test_integrations.py` | API-level tests (uses `api_client` + `auth_state`) |
| Create | `docs/backend/INTEGRATIONS.md` | Integration reference doc |

---

## Existing Code to Understand

Before starting:

**Existing schemas** (`backend/app/schemas/connector.py` lines 39–56):
```python
class HevySet(BaseModel):
    reps: int | None = None
    weight_kg: float | None = None
    rpe: float | None = Field(default=None, ge=1, le=10)
    set_type: str  # "normal", "warmup", "dropset", "failure"

class HevyExercise(BaseModel):
    name: str
    sets: list[HevySet]

class HevyWorkout(BaseModel):
    id: str
    title: str
    date: date
    duration_seconds: int
    exercises: list[HevyExercise]
```

**SessionLogModel** (`backend/app/db/models.py` lines 163–184):
- `UniqueConstraint("athlete_id", "session_id")` — upsert key
- `plan_id` FK nullable → standalone imports use `None`
- `actual_data_json` — JSON string, same format as `sync_hevy()`

**Test fixtures available** (`tests/backend/conftest.py`):
- `api_client` — `TestClient` with SQLite in-memory DB
- `auth_state` — onboarded athlete, returns `{"token", "athlete_id", "headers", "plan"}`

**pytest path (Windows):**
```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe
```

---

## Task 1: CSV Fixture + Parser

**Files:**
- Create: `tests/fixtures/hevy_export_sample.csv`
- Create: `backend/app/integrations/__init__.py`
- Create: `backend/app/integrations/hevy/__init__.py`
- Create: `tests/backend/integrations/__init__.py`
- Create: `tests/backend/integrations/test_hevy_csv_parser.py`
- Create: `backend/app/integrations/hevy/csv_parser.py`

- [ ] **Step 0: Pull latest changes**

```bash
git pull --rebase origin main
```

Expected: fast-forward or no-op. Resolve any conflicts before continuing.

- [ ] **Step 1: Create test fixture CSV**

Create `tests/fixtures/hevy_export_sample.csv`:
```csv
Date,Workout Name,Exercise Name,Set Order,Weight,Reps,Distance,Seconds,Notes,Workout Notes,RPE
2026-04-01,Push Day A,Bench Press,1,80,8,,,,,8
2026-04-01,Push Day A,Bench Press,2,82.5,6,,,,,9
2026-04-01,Push Day A,Overhead Press,1,50,10,,,,,
2026-04-03,Leg Day,Squat,1,100,5,,,,,9
2026-04-03,Leg Day,Squat,2,105,3,,,,,10
2026-04-03,Leg Day,Bodyweight Squat,1,,15,,,,,
```

Two workouts: `Push Day A` (2026-04-01, 2 exercises) and `Leg Day` (2026-04-03, 2 exercises). Edge cases: missing RPE, missing weight (bodyweight set).

- [ ] **Step 2: Create package markers**

Create `backend/app/integrations/__init__.py` — empty file.

Create `backend/app/integrations/hevy/__init__.py` — empty file.

Create `tests/backend/integrations/__init__.py` — empty file.

- [ ] **Step 3: Write failing parser tests**

Create `tests/backend/integrations/test_hevy_csv_parser.py`:
```python
from pathlib import Path
import pytest
from app.integrations.hevy.csv_parser import parse_hevy_csv

FIXTURE = (Path(__file__).parents[2] / "fixtures" / "hevy_export_sample.csv").read_bytes()


def test_parse_returns_two_workouts():
    workouts = parse_hevy_csv(FIXTURE)
    assert len(workouts) == 2


def test_first_workout_title_and_date():
    workouts = parse_hevy_csv(FIXTURE)
    assert workouts[0].title == "Push Day A"
    assert str(workouts[0].date) == "2026-04-01"


def test_first_workout_has_two_exercises():
    workouts = parse_hevy_csv(FIXTURE)
    assert len(workouts[0].exercises) == 2


def test_bench_press_sets_parsed_correctly():
    workouts = parse_hevy_csv(FIXTURE)
    bench = workouts[0].exercises[0]
    assert bench.name == "Bench Press"
    assert len(bench.sets) == 2
    assert bench.sets[0].weight_kg == 80.0
    assert bench.sets[0].reps == 8
    assert bench.sets[0].rpe == 8.0
    assert bench.sets[0].set_type == "normal"


def test_missing_rpe_is_none():
    workouts = parse_hevy_csv(FIXTURE)
    ohp = workouts[0].exercises[1]
    assert ohp.name == "Overhead Press"
    assert ohp.sets[0].rpe is None


def test_bodyweight_set_has_none_weight():
    workouts = parse_hevy_csv(FIXTURE)
    leg_day = workouts[1]
    bw = next(e for e in leg_day.exercises if e.name == "Bodyweight Squat")
    assert bw.sets[0].weight_kg is None
    assert bw.sets[0].reps == 15


def test_lbs_conversion():
    workouts = parse_hevy_csv(FIXTURE, unit="lbs")
    bench = workouts[0].exercises[0]
    assert abs(bench.sets[0].weight_kg - 80 * 0.453592) < 0.001


def test_workout_id_is_slug_of_date_and_title():
    workouts = parse_hevy_csv(FIXTURE)
    assert workouts[0].id == "2026-04-01-push-day-a"
    assert workouts[1].id == "2026-04-03-leg-day"


def test_invalid_unit_raises_value_error():
    with pytest.raises(ValueError, match="Invalid unit"):
        parse_hevy_csv(FIXTURE, unit="stone")


def test_empty_csv_raises_value_error():
    header = b"Date,Workout Name,Exercise Name,Set Order,Weight,Reps,Distance,Seconds,Notes,Workout Notes,RPE\n"
    with pytest.raises(ValueError, match="no workouts found"):
        parse_hevy_csv(header)


def test_missing_required_column_raises_value_error():
    bad = b"Date,Exercise Name\n2026-04-01,Squat\n"
    with pytest.raises(ValueError, match="Missing required columns"):
        parse_hevy_csv(bad)
```

- [ ] **Step 4: Run tests — verify they fail**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/integrations/test_hevy_csv_parser.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.integrations'`

- [ ] **Step 5: Implement the parser**

Create `backend/app/integrations/hevy/csv_parser.py`:
```python
import csv
import io
from collections import OrderedDict
from datetime import date

from ...schemas.connector import HevyExercise, HevySet, HevyWorkout

_REQUIRED_COLUMNS = {"Date", "Workout Name", "Exercise Name", "Weight", "Reps", "RPE"}


def _slugify(text: str) -> str:
    return text.lower().replace(" ", "-").replace("/", "-")


def parse_hevy_csv(content: bytes, unit: str = "kg") -> list[HevyWorkout]:
    """Parse Hevy CSV export bytes into HevyWorkout objects.

    Args:
        content: Raw CSV file bytes.
        unit: Weight unit in the file — "kg" (default) or "lbs".

    Returns:
        List of HevyWorkout, one per unique (Date, Workout Name) pair.

    Raises:
        ValueError: If unit is invalid, required columns are missing, or no data rows.
    """
    if unit not in ("kg", "lbs"):
        raise ValueError(f"Invalid unit: {unit!r}. Must be 'kg' or 'lbs'")

    text = content.decode("utf-8-sig")  # handle BOM from Windows exports
    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None:
        raise ValueError("no workouts found")

    missing = _REQUIRED_COLUMNS - set(reader.fieldnames)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    rows = list(reader)
    if not rows:
        raise ValueError("no workouts found")

    # Group by (Date, Workout Name) preserving CSV order via OrderedDict
    workout_map: OrderedDict[tuple[str, str], list[dict]] = OrderedDict()
    for row in rows:
        key = (row["Date"].strip(), row["Workout Name"].strip())
        if key not in workout_map:
            workout_map[key] = []
        workout_map[key].append(row)

    workouts: list[HevyWorkout] = []

    for (date_str, workout_name), workout_rows in workout_map.items():
        try:
            workout_date = date.fromisoformat(date_str)
        except ValueError:
            raise ValueError(f"Invalid date: {date_str!r}")

        # Group rows by exercise name, preserving first-appearance order
        exercise_map: OrderedDict[str, list[dict]] = OrderedDict()
        for row in workout_rows:
            ex_name = row["Exercise Name"].strip()
            if ex_name not in exercise_map:
                exercise_map[ex_name] = []
            exercise_map[ex_name].append(row)

        exercises: list[HevyExercise] = []
        for ex_name, ex_rows in exercise_map.items():
            sets: list[HevySet] = []
            for row in ex_rows:
                weight_raw = row["Weight"].strip()
                reps_raw = row["Reps"].strip()
                rpe_raw = row["RPE"].strip()

                weight_kg = None
                if weight_raw:
                    w = float(weight_raw)
                    weight_kg = w * 0.453592 if unit == "lbs" else w

                reps = int(reps_raw) if reps_raw else None
                rpe = float(rpe_raw) if rpe_raw else None

                sets.append(HevySet(
                    reps=reps,
                    weight_kg=weight_kg,
                    rpe=rpe,
                    set_type="normal",
                ))
            exercises.append(HevyExercise(name=ex_name, sets=sets))

        workout_id = f"{workout_date.isoformat()}-{_slugify(workout_name)}"
        workouts.append(HevyWorkout(
            id=workout_id,
            title=workout_name,
            date=workout_date,
            duration_seconds=0,
            exercises=exercises,
        ))

    return workouts
```

- [ ] **Step 6: Run tests — verify they pass**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/integrations/test_hevy_csv_parser.py -v
```

Expected: 11 PASSED

- [ ] **Step 7: Run full test suite — verify no regressions**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -x -q
```

Expected: all existing tests still pass.

- [ ] **Step 8: Commit**

```bash
git add tests/fixtures/hevy_export_sample.csv backend/app/integrations/ tests/backend/integrations/__init__.py tests/backend/integrations/test_hevy_csv_parser.py
git commit -m "feat(integrations): add Hevy CSV parser — bytes → list[HevyWorkout], unit conversion, 11 tests"
```

---

## Task 2: Importer

**Files:**
- Create: `tests/backend/integrations/conftest.py`
- Create: `tests/backend/integrations/test_hevy_csv_importer.py`
- Create: `backend/app/integrations/hevy/importer.py`

- [ ] **Step 1: Create importer test conftest**

Create `tests/backend/integrations/conftest.py`:
```python
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db import models  # noqa: F401 — registers ORM models with Base


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def set_pragma(conn, _):
        conn.cursor().execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)
    with Session() as session:
        yield session
    Base.metadata.drop_all(engine)
```

- [ ] **Step 2: Write failing importer tests**

Create `tests/backend/integrations/test_hevy_csv_importer.py`:
```python
import json
import uuid
from datetime import date

import pytest

from app.db.models import AthleteModel, SessionLogModel
from app.integrations.hevy.importer import import_hevy_workouts
from app.schemas.connector import HevyExercise, HevySet, HevyWorkout


def _make_athlete(db_session) -> AthleteModel:
    athlete = AthleteModel(
        id=str(uuid.uuid4()),
        name="Test Athlete",
        age=30,
        sex="M",
        weight_kg=75.0,
        height_cm=180.0,
        primary_sport="lifting",
        hours_per_week=5.0,
        sports_json='["lifting"]',
        goals_json='["strength"]',
        available_days_json='[0, 2, 4]',
        equipment_json='[]',
    )
    db_session.add(athlete)
    db_session.commit()
    return athlete


def _make_workout(title: str = "Push Day A", workout_date: date = date(2026, 4, 1)) -> HevyWorkout:
    slug = title.lower().replace(" ", "-")
    return HevyWorkout(
        id=f"{workout_date.isoformat()}-{slug}",
        title=title,
        date=workout_date,
        duration_seconds=0,
        exercises=[
            HevyExercise(
                name="Squat",
                sets=[
                    HevySet(reps=5, weight_kg=100.0, rpe=8.0, set_type="normal"),
                    HevySet(reps=5, weight_kg=100.0, rpe=9.0, set_type="normal"),
                ],
            )
        ],
    )


def test_import_creates_standalone_when_no_plan(db_session):
    athlete = _make_athlete(db_session)
    result = import_hevy_workouts(athlete.id, [_make_workout()], db_session)

    assert result["total_workouts"] == 1
    assert result["standalone"] == 1
    assert result["matched"] == 0
    assert result["skipped"] == 0

    log = db_session.query(SessionLogModel).filter_by(athlete_id=athlete.id).first()
    assert log is not None
    assert log.session_id.startswith("hevy-standalone-")
    assert log.plan_id is None


def test_import_upsert_does_not_create_duplicate(db_session):
    athlete = _make_athlete(db_session)
    workout = _make_workout()
    import_hevy_workouts(athlete.id, [workout], db_session)
    import_hevy_workouts(athlete.id, [workout], db_session)  # second import

    count = db_session.query(SessionLogModel).filter_by(athlete_id=athlete.id).count()
    assert count == 1


def test_import_actual_data_json_structure(db_session):
    athlete = _make_athlete(db_session)
    import_hevy_workouts(athlete.id, [_make_workout()], db_session)

    log = db_session.query(SessionLogModel).filter_by(athlete_id=athlete.id).first()
    data = json.loads(log.actual_data_json)

    assert data["source"] == "hevy_csv"
    assert "hevy_workout_id" in data
    assert len(data["exercises"]) == 1
    assert data["exercises"][0]["name"] == "Squat"
    assert len(data["exercises"][0]["sets"]) == 2
    assert data["exercises"][0]["sets"][0]["weight_kg"] == 100.0


def test_import_multiple_workouts_creates_separate_logs(db_session):
    athlete = _make_athlete(db_session)
    workouts = [
        _make_workout("Push Day A", date(2026, 4, 1)),
        _make_workout("Leg Day", date(2026, 4, 3)),
    ]
    result = import_hevy_workouts(athlete.id, workouts, db_session)

    assert result["total_workouts"] == 2
    count = db_session.query(SessionLogModel).filter_by(athlete_id=athlete.id).count()
    assert count == 2


def test_import_response_includes_workout_details(db_session):
    athlete = _make_athlete(db_session)
    result = import_hevy_workouts(athlete.id, [_make_workout()], db_session)

    assert len(result["workouts"]) == 1
    w = result["workouts"][0]
    assert w["date"] == "2026-04-01"
    assert w["workout_name"] == "Push Day A"
    assert w["sets_imported"] == 2
    assert "session_id" in w
    assert isinstance(w["matched"], bool)


def test_import_sets_imported_count(db_session):
    athlete = _make_athlete(db_session)
    workout = HevyWorkout(
        id="2026-04-01-push-day-a",
        title="Push Day A",
        date=date(2026, 4, 1),
        duration_seconds=0,
        exercises=[
            HevyExercise(
                name="Bench Press",
                sets=[
                    HevySet(reps=8, weight_kg=80.0, set_type="normal"),
                    HevySet(reps=6, weight_kg=82.5, set_type="normal"),
                ],
            ),
            HevyExercise(
                name="Overhead Press",
                sets=[HevySet(reps=10, weight_kg=50.0, set_type="normal")],
            ),
        ],
    )
    result = import_hevy_workouts(athlete.id, [workout], db_session)
    assert result["workouts"][0]["sets_imported"] == 3
```

- [ ] **Step 3: Run tests — verify they fail**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/integrations/test_hevy_csv_importer.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.integrations.hevy.importer'`

- [ ] **Step 4: Implement the importer**

Create `backend/app/integrations/hevy/importer.py`:
```python
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import desc
from sqlalchemy.orm import Session

from ...db.models import SessionLogModel, TrainingPlanModel
from ...schemas.connector import HevyWorkout


def _get_latest_plan(athlete_id: str, db: Session) -> TrainingPlanModel | None:
    return (
        db.query(TrainingPlanModel)
        .filter(TrainingPlanModel.athlete_id == athlete_id)
        .order_by(desc(TrainingPlanModel.created_at))
        .first()
    )


def _slugify(text: str) -> str:
    return text.lower().replace(" ", "-").replace("/", "-")


def import_hevy_workouts(
    athlete_id: str,
    workouts: list[HevyWorkout],
    db: Session,
) -> dict:
    """Upsert HevyWorkout list into SessionLogModel.

    Matches each workout to a training plan lifting slot by date if available.
    Falls back to a standalone session_id when no plan slot is found.

    Returns a summary dict with per-workout results and totals.
    """
    plan = _get_latest_plan(athlete_id, db)
    plan_slots: list[dict] = json.loads(plan.weekly_slots_json) if plan else []

    results: list[dict] = []
    matched_count = 0
    standalone_count = 0

    for workout in workouts:
        date_key = workout.date.isoformat()
        slug = _slugify(workout.title)

        plan_session_id: str | None = next(
            (s["id"] for s in plan_slots if s["date"] == date_key and s["sport"] == "lifting"),
            None,
        )

        if plan_session_id:
            session_id = plan_session_id
            plan_id: str | None = plan.id  # type: ignore[union-attr]
            matched = True
            matched_count += 1
        else:
            session_id = f"hevy-standalone-{date_key}-{slug}"
            plan_id = None
            matched = False
            standalone_count += 1

        sets_imported = sum(len(ex.sets) for ex in workout.exercises)

        actual_data = {
            "source": "hevy_csv",
            "hevy_workout_id": workout.id,
            "exercises": [
                {
                    "name": ex.name,
                    "sets": [
                        {
                            "reps": s.reps,
                            "weight_kg": s.weight_kg,
                            "rpe": s.rpe,
                            "set_type": s.set_type,
                        }
                        for s in ex.sets
                    ],
                }
                for ex in workout.exercises
            ],
        }

        existing = (
            db.query(SessionLogModel)
            .filter_by(athlete_id=athlete_id, session_id=session_id)
            .first()
        )

        if existing:
            existing.actual_data_json = json.dumps(actual_data)
            existing.logged_at = datetime.now(timezone.utc)
        else:
            db.add(SessionLogModel(
                id=str(uuid.uuid4()),
                athlete_id=athlete_id,
                plan_id=plan_id,
                session_id=session_id,
                actual_duration_min=None,
                skipped=False,
                actual_data_json=json.dumps(actual_data),
                logged_at=datetime.now(timezone.utc),
            ))

        results.append({
            "date": date_key,
            "workout_name": workout.title,
            "session_id": session_id,
            "matched": matched,
            "sets_imported": sets_imported,
        })

    db.commit()

    return {
        "total_workouts": len(workouts),
        "matched": matched_count,
        "standalone": standalone_count,
        "skipped": 0,
        "workouts": results,
    }
```

- [ ] **Step 5: Run tests — verify they pass**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/integrations/test_hevy_csv_importer.py -v
```

Expected: 6 PASSED

- [ ] **Step 6: Run full test suite — verify no regressions**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -x -q
```

Expected: all existing tests still pass.

- [ ] **Step 7: Commit**

```bash
git add backend/app/integrations/hevy/importer.py tests/backend/integrations/conftest.py tests/backend/integrations/test_hevy_csv_importer.py
git commit -m "feat(integrations): add Hevy CSV importer — HevyWorkout → SessionLogModel upserts, 6 tests"
```

---

## Task 3: Route + Router Registration + API Tests

**Files:**
- Create: `backend/app/routes/integrations.py`
- Modify: `backend/app/main.py`
- Create: `tests/backend/api/test_integrations.py`

- [ ] **Step 1: Write failing API tests**

Create `tests/backend/api/test_integrations.py`:
```python
import io
from pathlib import Path

FIXTURE = (Path(__file__).parents[2] / "fixtures" / "hevy_export_sample.csv").read_bytes()


def test_hevy_csv_import_returns_200(api_client, auth_state):
    resp = api_client.post(
        "/integrations/hevy/import",
        files={"file": ("hevy_export.csv", io.BytesIO(FIXTURE), "text/csv")},
        headers=auth_state["headers"],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_workouts"] == 2
    assert body["matched"] + body["standalone"] == 2
    assert len(body["workouts"]) == 2


def test_hevy_csv_import_response_shape(api_client, auth_state):
    resp = api_client.post(
        "/integrations/hevy/import",
        files={"file": ("hevy_export.csv", io.BytesIO(FIXTURE), "text/csv")},
        headers=auth_state["headers"],
    )
    body = resp.json()
    assert "total_workouts" in body
    assert "matched" in body
    assert "standalone" in body
    assert "skipped" in body
    assert "workouts" in body
    w = body["workouts"][0]
    assert "date" in w
    assert "workout_name" in w
    assert "session_id" in w
    assert "matched" in w
    assert "sets_imported" in w


def test_hevy_csv_import_upsert_no_duplicate(api_client, auth_state):
    """Re-importing same file must not duplicate rows — idempotent."""
    for _ in range(2):
        resp = api_client.post(
            "/integrations/hevy/import",
            files={"file": ("hevy_export.csv", io.BytesIO(FIXTURE), "text/csv")},
            headers=auth_state["headers"],
        )
        assert resp.status_code == 200
    # Second import returns same total_workouts, not doubled
    assert resp.json()["total_workouts"] == 2


def test_hevy_csv_import_lbs_unit(api_client, auth_state):
    resp = api_client.post(
        "/integrations/hevy/import?unit=lbs",
        files={"file": ("hevy_export.csv", io.BytesIO(FIXTURE), "text/csv")},
        headers=auth_state["headers"],
    )
    assert resp.status_code == 200


def test_hevy_csv_import_empty_file_returns_422(api_client, auth_state):
    header = b"Date,Workout Name,Exercise Name,Set Order,Weight,Reps,Distance,Seconds,Notes,Workout Notes,RPE\n"
    resp = api_client.post(
        "/integrations/hevy/import",
        files={"file": ("empty.csv", io.BytesIO(header), "text/csv")},
        headers=auth_state["headers"],
    )
    assert resp.status_code == 422


def test_hevy_csv_import_unauthenticated_returns_401(api_client):
    resp = api_client.post(
        "/integrations/hevy/import",
        files={"file": ("hevy_export.csv", io.BytesIO(FIXTURE), "text/csv")},
    )
    assert resp.status_code == 401
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/api/test_integrations.py -v
```

Expected: all fail with 404 (route not registered yet).

- [ ] **Step 3: Create the route**

Create `backend/app/routes/integrations.py`:
```python
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session

from ..db.models import AthleteModel
from ..dependencies import get_db, get_current_athlete_id
from ..integrations.hevy.csv_parser import parse_hevy_csv
from ..integrations.hevy.importer import import_hevy_workouts

router = APIRouter(prefix="/integrations", tags=["integrations"])

DB = Annotated[Session, Depends(get_db)]


@router.post("/hevy/import")
def hevy_csv_import(
    db: DB,
    athlete_id: Annotated[str, Depends(get_current_athlete_id)],
    file: UploadFile = File(...),
    unit: Literal["kg", "lbs"] = Query(default="kg"),
) -> dict:
    """Import Hevy CSV export → parse → upsert to SessionLogModel.

    Matches workouts to active training plan lifting slots by date.
    Falls back to standalone session logs when no plan slot exists.
    """
    if db.get(AthleteModel, athlete_id) is None:
        raise HTTPException(status_code=404, detail="Athlete not found")

    content = file.file.read()
    try:
        workouts = parse_hevy_csv(content, unit=unit)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return import_hevy_workouts(athlete_id, workouts, db)
```

- [ ] **Step 4: Register the router in main.py**

In `backend/app/main.py`, add after the existing router imports (around line 23):
```python
from .routes.integrations import router as integrations_router
```

And add after `app.include_router(strain_router)` (end of the file):
```python
app.include_router(integrations_router)
```

The final main.py import block should look like:
```python
from .routes.auth import router as auth_router
from .routes.onboarding import router as onboarding_router
from .routes.athletes import router as athletes_router
from .routes.connectors import router as connectors_router
from .routes.plans import router as plans_router
from .routes.reviews import router as reviews_router
from .routes.nutrition import router as nutrition_router
from .routes.recovery import router as recovery_router
from .routes.sessions import router as sessions_router
from .routes.analytics import router as analytics_router
from .routes.food import router as food_router
from .routes.workflow import router as workflow_router
from .routes.mode import router as mode_router
from .routes.checkin import router as checkin_router
from .routes.external_plan import router as external_plan_router
from .routes.strain import router as strain_router
from .routes.integrations import router as integrations_router
```

And at the bottom of the router registrations:
```python
app.include_router(integrations_router)
```

- [ ] **Step 5: Run API tests — verify they pass**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/api/test_integrations.py -v
```

Expected: 6 PASSED

- [ ] **Step 6: Run full test suite — verify no regressions**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -x -q
```

Expected: all existing tests still pass.

- [ ] **Step 7: Commit**

```bash
git add backend/app/routes/integrations.py backend/app/main.py tests/backend/api/test_integrations.py
git commit -m "feat(integrations): add POST /integrations/hevy/import endpoint, register router, 6 API tests"
```

---

## Task 4: INTEGRATIONS.md

**Files:**
- Create: `docs/backend/INTEGRATIONS.md`

- [ ] **Step 1: Write INTEGRATIONS.md**

Create `docs/backend/INTEGRATIONS.md`:
```markdown
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
- `RPE` — numeric 1–10 or empty
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
```

- [ ] **Step 2: Commit**

```bash
git add docs/backend/INTEGRATIONS.md
git commit -m "docs(integrations): add INTEGRATIONS.md — Hevy CSV import reference, format, curl examples"
```

- [ ] **Step 3: Run full test suite one final time**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -q
```

Expected: all tests pass (previously passing count + 23 new tests).
