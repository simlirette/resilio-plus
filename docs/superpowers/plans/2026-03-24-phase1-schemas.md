# Phase 1 — Schemas & Data Models Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the complete data layer for Resilio Plus: 5 Pydantic v2 schemas (FatigueScore, AthleteProfile, TrainingPlan, NutritionPlan, WeeklyReview) + 4 SQLAlchemy ORM tables + SQLite database setup with FK enforcement.

**Architecture:** Pydantic schemas live in `backend/resilio/schemas/` for in-memory agent/API validation. SQLAlchemy models live in `backend/resilio/db/` for persistence. The two layers are completely separate — no SQLModel coupling. Complex fields (lists, nested objects) are stored as JSON TEXT in SQLite. FatigueScore has no DB table — it is embedded as JSON inside WorkoutSlot.

**Tech Stack:** Python 3.12, Pydantic v2 (already installed), SQLAlchemy 2.x (to be added), SQLite, Poetry

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `pyproject.toml` | Modify | Add `sqlalchemy>=2.0,<3.0` dependency + `[tool.pytest.ini_options]` |
| `data/.gitkeep` | Create | Ensures `data/` directory is tracked by git; `data/resilio.db` created here at runtime |
| `backend/__init__.py` | Create | Makes `backend/` a Python namespace (required for imports) |
| `backend/resilio/__init__.py` | Create | Backend `resilio` package root |
| `backend/resilio/schemas/__init__.py` | Create | Schemas sub-package |
| `backend/resilio/schemas/fatigue.py` | Create | `FatigueScore` model |
| `backend/resilio/schemas/athlete.py` | Create | `Sport` enum, `DayType` enum, `AthleteProfile` model |
| `backend/resilio/schemas/plan.py` | Create | `WorkoutSlot` model, `TrainingPlan` model |
| `backend/resilio/schemas/nutrition.py` | Create | `MacroTarget` model, `DayNutrition` model, `NutritionPlan` model |
| `backend/resilio/schemas/review.py` | Create | `ActivityResult` model, `WeeklyReview` model |
| `backend/resilio/db/__init__.py` | Create | DB sub-package |
| `backend/resilio/db/database.py` | Create | SQLAlchemy engine, `SessionLocal`, `Base`, FK pragma event hook |
| `backend/resilio/db/models.py` | Create | 4 ORM tables: `AthleteModel`, `TrainingPlanModel`, `NutritionPlanModel`, `WeeklyReviewModel` |
| `tests/backend/__init__.py` | Create | Test sub-package |
| `tests/backend/schemas/__init__.py` | Create | Schema test sub-package |
| `tests/backend/schemas/test_fatigue.py` | Create | Tests for `FatigueScore` |
| `tests/backend/schemas/test_athlete.py` | Create | Tests for `Sport`, `DayType`, `AthleteProfile` |
| `tests/backend/schemas/test_plan.py` | Create | Tests for `WorkoutSlot`, `TrainingPlan` |
| `tests/backend/schemas/test_nutrition.py` | Create | Tests for `MacroTarget`, `DayNutrition`, `NutritionPlan` |
| `tests/backend/schemas/test_review.py` | Create | Tests for `ActivityResult`, `WeeklyReview` |
| `tests/backend/db/__init__.py` | Create | DB test sub-package |
| `tests/backend/db/test_models.py` | Create | SQLAlchemy table tests using in-memory SQLite |

---

## Task 1: Prerequisites — SQLAlchemy + Data Directory

**Files:**
- Modify: `pyproject.toml`
- Create: `data/.gitkeep`

> This task has no tests — it is pure environment setup. Verify by running commands.

- [ ] **Step 1: Add SQLAlchemy dependency**

Run from repo root (`C:\Users\simon\resilio-plus`):

```bash
poetry add "sqlalchemy>=2.0,<3.0"
```

Expected output: `poetry.lock` updated, `pyproject.toml` now contains `sqlalchemy>=2.0,<3.0` in `[project].dependencies`.

- [ ] **Step 2: Verify pyproject.toml was updated**

Run:
```bash
grep sqlalchemy pyproject.toml
```

Expected: `"sqlalchemy>=2.0,<3.0",`

- [ ] **Step 3: Create the data directory**

Run:
```bash
mkdir -p data && touch data/.gitkeep
```

Expected: `data/` directory exists at repo root, `data/.gitkeep` is an empty file.

- [ ] **Step 4: Verify existing tests still pass (baseline)**

Run:
```bash
poetry run pytest tests/unit tests/integration -q 2>&1 | tail -5
```

Expected: same number of passes as before Phase 1 (877 pass, 9 pre-existing failures or similar). If something fails here that did not fail before, stop and investigate before continuing.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml poetry.lock data/.gitkeep
git commit -m "chore: add sqlalchemy dependency and data directory"
```

---

## Task 2: Pytest Config + Package Skeleton

**Files:**
- Modify: `pyproject.toml`
- Create: `backend/__init__.py`, `backend/resilio/__init__.py`, `backend/resilio/schemas/__init__.py`, `backend/resilio/db/__init__.py`
- Create: `tests/backend/__init__.py`, `tests/backend/schemas/__init__.py`, `tests/backend/db/__init__.py`

> This task has no tests — it is scaffolding. Verify by checking imports work.

- [ ] **Step 1: Check for namespace collision risk**

Run:
```bash
grep -r "from resilio" tests/unit tests/integration 2>/dev/null | head -20
grep -r "import resilio" tests/unit tests/integration 2>/dev/null | head -20
```

Note the import patterns. They import from the top-level `resilio/` package (e.g., `from resilio.core.vdot import ...`). Adding `pythonpath = ["backend"]` will redirect `import resilio` to `backend/resilio/`. Since `backend/resilio/` does not yet exist (only `backend/README.md`), the existing tests would fail. However, since we are about to create `backend/resilio/__init__.py`, `import resilio` in existing tests would import the (empty) backend package, NOT the legacy CLI package. This is a problem.

**Resolution**: The existing tests (`tests/unit/`, `tests/integration/`) import from the installed `resilio` package (the top-level `resilio/` installed via `poetry install`). Python's import resolution with `pythonpath = ["backend"]` prepends `backend/` to `sys.path`. Since `poetry install` registers `resilio` as an installed package (editable install from the top-level `resilio/`), the installed package takes precedence over `sys.path` entries for the same package name. Verify this by running the existing tests after adding the config (Step 5 below).

- [ ] **Step 2: Add pytest config to pyproject.toml**

Open `pyproject.toml` and add this block at the end of the file (after `[tool.ruff]`):

```toml
[tool.pytest.ini_options]
pythonpath = ["backend"]
testpaths = ["tests"]
```

The full `pyproject.toml` `[tool.pytest.ini_options]` section must look exactly like the above.

- [ ] **Step 3: Create all __init__.py files**

These are all empty files. Create each one:

```
backend/__init__.py          (empty)
backend/resilio/__init__.py  (empty)
backend/resilio/schemas/__init__.py  (empty)
backend/resilio/db/__init__.py       (empty)
tests/backend/__init__.py            (empty)
tests/backend/schemas/__init__.py    (empty)
tests/backend/db/__init__.py         (empty)
```

Run in bash (from repo root):
```bash
touch backend/__init__.py
touch backend/resilio/__init__.py
touch backend/resilio/schemas/__init__.py
touch backend/resilio/db/__init__.py
touch tests/backend/__init__.py
touch tests/backend/schemas/__init__.py
touch tests/backend/db/__init__.py
```

- [ ] **Step 4: Verify existing tests still pass with new pytest config**

Run:
```bash
poetry run pytest tests/unit tests/integration -q 2>&1 | tail -5
```

Expected: same pass/fail counts as Step 4 of Task 1. If any test that was passing before is now failing, the `pythonpath` config is causing a collision — investigate before continuing.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml backend/__init__.py backend/resilio/__init__.py backend/resilio/schemas/__init__.py backend/resilio/db/__init__.py tests/backend/__init__.py tests/backend/schemas/__init__.py tests/backend/db/__init__.py
git commit -m "chore: add pytest config and backend package skeleton"
```

---

## Task 3: FatigueScore Schema

**Files:**
- Create: `backend/resilio/schemas/fatigue.py`
- Test: `tests/backend/schemas/test_fatigue.py`

`FatigueScore` is the inter-agent communication primitive. 5 fields: 3 floats clamped to 0–100, 1 float ≥ 0, 1 list of strings.

- [ ] **Step 1: Write the failing test**

Create `tests/backend/schemas/test_fatigue.py`:

```python
import pytest
from pydantic import ValidationError


def make_valid_fatigue(**overrides):
    defaults = {
        "local_muscular": 40.0,
        "cns_load": 55.0,
        "metabolic_cost": 30.0,
        "recovery_hours": 24.0,
        "affected_muscles": ["quads", "glutes"],
    }
    defaults.update(overrides)
    return defaults


def test_valid_construction():
    from resilio.schemas.fatigue import FatigueScore
    fs = FatigueScore(**make_valid_fatigue())
    assert fs.local_muscular == 40.0
    assert fs.cns_load == 55.0
    assert fs.metabolic_cost == 30.0
    assert fs.recovery_hours == 24.0
    assert fs.affected_muscles == ["quads", "glutes"]


def test_affected_muscles_defaults_to_empty_list():
    from resilio.schemas.fatigue import FatigueScore
    data = make_valid_fatigue()
    del data["affected_muscles"]
    fs = FatigueScore(**data)
    assert fs.affected_muscles == []


def test_local_muscular_above_100_raises():
    from resilio.schemas.fatigue import FatigueScore
    with pytest.raises(ValidationError):
        FatigueScore(**make_valid_fatigue(local_muscular=101.0))


def test_local_muscular_below_0_raises():
    from resilio.schemas.fatigue import FatigueScore
    with pytest.raises(ValidationError):
        FatigueScore(**make_valid_fatigue(local_muscular=-1.0))


def test_cns_load_above_100_raises():
    from resilio.schemas.fatigue import FatigueScore
    with pytest.raises(ValidationError):
        FatigueScore(**make_valid_fatigue(cns_load=150.0))


def test_metabolic_cost_above_100_raises():
    from resilio.schemas.fatigue import FatigueScore
    with pytest.raises(ValidationError):
        FatigueScore(**make_valid_fatigue(metabolic_cost=100.1))


def test_recovery_hours_negative_raises():
    from resilio.schemas.fatigue import FatigueScore
    with pytest.raises(ValidationError):
        FatigueScore(**make_valid_fatigue(recovery_hours=-0.1))


def test_recovery_hours_zero_is_valid():
    from resilio.schemas.fatigue import FatigueScore
    fs = FatigueScore(**make_valid_fatigue(recovery_hours=0.0))
    assert fs.recovery_hours == 0.0


def test_json_round_trip():
    from resilio.schemas.fatigue import FatigueScore
    fs = FatigueScore(**make_valid_fatigue())
    json_str = fs.model_dump_json()
    fs2 = FatigueScore.model_validate_json(json_str)
    assert fs == fs2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/backend/schemas/test_fatigue.py -v 2>&1 | head -20
```

Expected: `ImportError` or `ModuleNotFoundError` — `resilio.schemas.fatigue` does not exist yet.

- [ ] **Step 3: Write the implementation**

Create `backend/resilio/schemas/fatigue.py`:

```python
from pydantic import BaseModel, Field


class FatigueScore(BaseModel):
    local_muscular: float = Field(..., ge=0, le=100)
    cns_load: float = Field(..., ge=0, le=100)
    metabolic_cost: float = Field(..., ge=0, le=100)
    recovery_hours: float = Field(..., ge=0)
    affected_muscles: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
poetry run pytest tests/backend/schemas/test_fatigue.py -v
```

Expected: 9 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/resilio/schemas/fatigue.py tests/backend/schemas/test_fatigue.py
git commit -m "feat: add FatigueScore schema with validation"
```

---

## Task 4: Sport & DayType Enums + AthleteProfile Schema

**Files:**
- Create: `backend/resilio/schemas/athlete.py`
- Test: `tests/backend/schemas/test_athlete.py`

`Sport` and `DayType` are `str` enums (values are lowercase strings, used as dict keys). `AthleteProfile` has 20 fields; fitness markers are all optional.

- [ ] **Step 1: Write the failing test**

Create `tests/backend/schemas/test_athlete.py`:

```python
import pytest
from datetime import date
from pydantic import ValidationError


def make_valid_athlete(**overrides):
    defaults = {
        "name": "Alice",
        "age": 30,
        "sex": "F",
        "weight_kg": 60.0,
        "height_cm": 168.0,
        "sports": ["running", "lifting"],
        "primary_sport": "running",
        "goals": ["run a marathon sub-4h"],
        "available_days": [0, 2, 4, 6],
        "hours_per_week": 10.0,
    }
    defaults.update(overrides)
    return defaults


# --- Sport enum ---

def test_sport_valid_values():
    from resilio.schemas.athlete import Sport
    assert Sport("running") == Sport.RUNNING
    assert Sport("lifting") == Sport.LIFTING
    assert Sport("swimming") == Sport.SWIMMING
    assert Sport("biking") == Sport.BIKING


def test_sport_invalid_value_raises():
    from resilio.schemas.athlete import Sport
    with pytest.raises(ValueError):
        Sport("cycling")


# --- DayType enum ---

def test_daytype_valid_values():
    from resilio.schemas.athlete import DayType
    assert DayType("rest") == DayType.REST
    assert DayType("strength") == DayType.STRENGTH
    assert DayType("endurance_short") == DayType.ENDURANCE_SHORT
    assert DayType("endurance_long") == DayType.ENDURANCE_LONG
    assert DayType("race") == DayType.RACE


def test_daytype_invalid_value_raises():
    from resilio.schemas.athlete import DayType
    with pytest.raises(ValueError):
        DayType("cardio")


# --- AthleteProfile ---

def test_athlete_valid_minimal():
    from resilio.schemas.athlete import AthleteProfile
    athlete = AthleteProfile(**make_valid_athlete())
    assert athlete.name == "Alice"
    assert athlete.age == 30
    assert athlete.sex == "F"
    assert athlete.weight_kg == 60.0
    assert athlete.vdot is None
    assert athlete.ftp_watts is None
    assert athlete.sleep_hours_typical == 7.0
    assert athlete.stress_level == 5
    assert athlete.job_physical is False
    assert athlete.equipment == []
    assert athlete.target_race_date is None


def test_athlete_id_generated_automatically():
    from resilio.schemas.athlete import AthleteProfile
    a1 = AthleteProfile(**make_valid_athlete())
    a2 = AthleteProfile(**make_valid_athlete())
    assert a1.id != a2.id


def test_athlete_age_too_young_raises():
    from resilio.schemas.athlete import AthleteProfile
    with pytest.raises(ValidationError):
        AthleteProfile(**make_valid_athlete(age=13))


def test_athlete_age_too_old_raises():
    from resilio.schemas.athlete import AthleteProfile
    with pytest.raises(ValidationError):
        AthleteProfile(**make_valid_athlete(age=101))


def test_athlete_negative_weight_raises():
    from resilio.schemas.athlete import AthleteProfile
    with pytest.raises(ValidationError):
        AthleteProfile(**make_valid_athlete(weight_kg=-1.0))


def test_athlete_zero_weight_raises():
    from resilio.schemas.athlete import AthleteProfile
    with pytest.raises(ValidationError):
        AthleteProfile(**make_valid_athlete(weight_kg=0.0))


def test_athlete_stress_level_out_of_range_raises():
    from resilio.schemas.athlete import AthleteProfile
    with pytest.raises(ValidationError):
        AthleteProfile(**make_valid_athlete(stress_level=11))
    with pytest.raises(ValidationError):
        AthleteProfile(**make_valid_athlete(stress_level=0))


def test_athlete_sex_invalid_raises():
    from resilio.schemas.athlete import AthleteProfile
    with pytest.raises(ValidationError):
        AthleteProfile(**make_valid_athlete(sex="X"))


def test_athlete_with_fitness_markers():
    from resilio.schemas.athlete import AthleteProfile
    athlete = AthleteProfile(**make_valid_athlete(
        vdot=52.3,
        ftp_watts=280,
        css_per_100m=95.0,
        max_hr=185,
        resting_hr=48,
    ))
    assert athlete.vdot == 52.3
    assert athlete.ftp_watts == 280
    assert athlete.css_per_100m == 95.0


def test_athlete_with_target_race_date():
    from resilio.schemas.athlete import AthleteProfile
    athlete = AthleteProfile(**make_valid_athlete(
        target_race_date=date(2026, 10, 18)
    ))
    assert athlete.target_race_date == date(2026, 10, 18)


def test_athlete_sport_enum_parsed_from_string():
    from resilio.schemas.athlete import AthleteProfile, Sport
    athlete = AthleteProfile(**make_valid_athlete(primary_sport="swimming"))
    assert athlete.primary_sport == Sport.SWIMMING


def test_athlete_json_round_trip():
    from resilio.schemas.athlete import AthleteProfile
    athlete = AthleteProfile(**make_valid_athlete())
    json_str = athlete.model_dump_json()
    athlete2 = AthleteProfile.model_validate_json(json_str)
    assert athlete == athlete2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/backend/schemas/test_athlete.py -v 2>&1 | head -20
```

Expected: `ImportError` — `resilio.schemas.athlete` does not exist yet.

- [ ] **Step 3: Write the implementation**

Create `backend/resilio/schemas/athlete.py`:

```python
from enum import Enum
from datetime import date
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Sport(str, Enum):
    RUNNING = "running"
    LIFTING = "lifting"
    SWIMMING = "swimming"
    BIKING = "biking"


class DayType(str, Enum):
    REST = "rest"
    STRENGTH = "strength"
    ENDURANCE_SHORT = "endurance_short"
    ENDURANCE_LONG = "endurance_long"
    RACE = "race"


class AthleteProfile(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    age: int = Field(..., ge=14, le=100)
    sex: Literal["M", "F", "other"]
    weight_kg: float = Field(..., gt=0)
    height_cm: float = Field(..., gt=0)
    sports: list[Sport]
    primary_sport: Sport
    goals: list[str]
    target_race_date: date | None = None
    available_days: list[int] = Field(..., description="0=Mon … 6=Sun")
    hours_per_week: float = Field(..., gt=0)
    equipment: list[str] = Field(default_factory=list)
    # Fitness markers (optional — filled progressively)
    max_hr: int | None = None
    resting_hr: int | None = None
    ftp_watts: int | None = None
    vdot: float | None = None
    css_per_100m: float | None = None
    # Lifestyle
    sleep_hours_typical: float = Field(default=7.0)
    stress_level: int = Field(default=5, ge=1, le=10)
    job_physical: bool = False
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
poetry run pytest tests/backend/schemas/test_athlete.py -v
```

Expected: 14 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/resilio/schemas/athlete.py tests/backend/schemas/test_athlete.py
git commit -m "feat: add Sport/DayType enums and AthleteProfile schema"
```

---

## Task 5: WorkoutSlot + TrainingPlan Schema

**Files:**
- Create: `backend/resilio/schemas/plan.py`
- Test: `tests/backend/schemas/test_plan.py`

`WorkoutSlot` embeds a `FatigueScore`. `TrainingPlan` has `weekly_slots` as `dict[str, list[WorkoutSlot]]` keyed by `"YYYY-WW"`. ACWR must be ≥ 0.

- [ ] **Step 1: Write the failing test**

Create `tests/backend/schemas/test_plan.py`:

```python
import pytest
from datetime import date
from pydantic import ValidationError


def make_fatigue(**overrides):
    defaults = {
        "local_muscular": 40.0,
        "cns_load": 30.0,
        "metabolic_cost": 35.0,
        "recovery_hours": 12.0,
    }
    defaults.update(overrides)
    return defaults


def make_slot(**overrides):
    defaults = {
        "date": date(2026, 4, 7),
        "sport": "running",
        "workout_type": "easy_run",
        "duration_min": 60,
        "fatigue_score": make_fatigue(),
    }
    defaults.update(overrides)
    return defaults


def make_plan(**overrides):
    defaults = {
        "athlete_id": "00000000-0000-0000-0000-000000000001",
        "start_date": date(2026, 4, 7),
        "end_date": date(2026, 5, 4),
        "phase": "base",
        "total_weekly_hours": 8.0,
        "acwr": 1.0,
    }
    defaults.update(overrides)
    return defaults


# --- WorkoutSlot ---

def test_workout_slot_valid():
    from resilio.schemas.plan import WorkoutSlot
    slot = WorkoutSlot(**make_slot())
    assert slot.sport.value == "running"
    assert slot.workout_type == "easy_run"
    assert slot.duration_min == 60
    assert slot.notes == ""
    assert slot.fatigue_score.local_muscular == 40.0


def test_workout_slot_duration_zero_raises():
    from resilio.schemas.plan import WorkoutSlot
    with pytest.raises(ValidationError):
        WorkoutSlot(**make_slot(duration_min=0))


def test_workout_slot_negative_duration_raises():
    from resilio.schemas.plan import WorkoutSlot
    with pytest.raises(ValidationError):
        WorkoutSlot(**make_slot(duration_min=-10))


def test_workout_slot_invalid_sport_raises():
    from resilio.schemas.plan import WorkoutSlot
    with pytest.raises(ValidationError):
        WorkoutSlot(**make_slot(sport="yoga"))


def test_workout_slot_notes_defaults_to_empty():
    from resilio.schemas.plan import WorkoutSlot
    slot = WorkoutSlot(**make_slot())
    assert slot.notes == ""


def test_workout_slot_with_notes():
    from resilio.schemas.plan import WorkoutSlot
    slot = WorkoutSlot(**make_slot(notes="Feel good, pushed the pace."))
    assert slot.notes == "Feel good, pushed the pace."


# --- TrainingPlan ---

def test_training_plan_valid_empty_slots():
    from resilio.schemas.plan import TrainingPlan
    plan = TrainingPlan(**make_plan())
    assert plan.phase == "base"
    assert plan.weekly_slots == {}
    assert plan.acwr == 1.0


def test_training_plan_id_generated():
    from resilio.schemas.plan import TrainingPlan
    p1 = TrainingPlan(**make_plan())
    p2 = TrainingPlan(**make_plan())
    assert p1.id != p2.id


def test_training_plan_invalid_phase_raises():
    from resilio.schemas.plan import TrainingPlan
    with pytest.raises(ValidationError):
        TrainingPlan(**make_plan(phase="maintenance"))


def test_training_plan_negative_acwr_raises():
    from resilio.schemas.plan import TrainingPlan
    with pytest.raises(ValidationError):
        TrainingPlan(**make_plan(acwr=-0.1))


def test_training_plan_with_weekly_slots():
    from resilio.schemas.plan import TrainingPlan
    plan = TrainingPlan(**make_plan(
        weekly_slots={"2026-W15": [make_slot()]}
    ))
    assert len(plan.weekly_slots["2026-W15"]) == 1
    assert plan.weekly_slots["2026-W15"][0].workout_type == "easy_run"


def test_training_plan_json_round_trip_with_slots():
    from resilio.schemas.plan import TrainingPlan
    plan = TrainingPlan(**make_plan(
        weekly_slots={"2026-W15": [make_slot()]}
    ))
    json_str = plan.model_dump_json()
    plan2 = TrainingPlan.model_validate_json(json_str)
    assert plan == plan2
    # Verify nested FatigueScore round-trips correctly
    assert plan2.weekly_slots["2026-W15"][0].fatigue_score.local_muscular == 40.0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/backend/schemas/test_plan.py -v 2>&1 | head -20
```

Expected: `ImportError` — `resilio.schemas.plan` does not exist yet.

- [ ] **Step 3: Write the implementation**

Create `backend/resilio/schemas/plan.py`:

```python
from datetime import date
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .athlete import Sport
from .fatigue import FatigueScore


class WorkoutSlot(BaseModel):
    date: date
    sport: Sport
    workout_type: str
    duration_min: int = Field(..., gt=0)
    fatigue_score: FatigueScore
    notes: str = ""


class TrainingPlan(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    athlete_id: UUID
    start_date: date
    end_date: date
    phase: Literal["base", "build", "peak", "taper", "recovery"]
    weekly_slots: dict[str, list[WorkoutSlot]] = Field(default_factory=dict)
    total_weekly_hours: float = Field(..., ge=0)
    acwr: float = Field(..., ge=0, description="Acute:Chronic Workload Ratio — safe zone 0.8–1.3")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
poetry run pytest tests/backend/schemas/test_plan.py -v
```

Expected: 12 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/resilio/schemas/plan.py tests/backend/schemas/test_plan.py
git commit -m "feat: add WorkoutSlot and TrainingPlan schemas"
```

---

## Task 6: NutritionPlan Schema

**Files:**
- Create: `backend/resilio/schemas/nutrition.py`
- Test: `tests/backend/schemas/test_nutrition.py`

`NutritionPlan` maps `DayType` enum to `DayNutrition` objects. Pydantic v2 serializes enum keys as their string values (`"rest"`, `"strength"`, etc.).

- [ ] **Step 1: Write the failing test**

Create `tests/backend/schemas/test_nutrition.py`:

```python
import json
import pytest
from pydantic import ValidationError


def make_macro(**overrides):
    defaults = {
        "carbs_g_per_kg": 4.0,
        "protein_g_per_kg": 2.0,
        "fat_g_per_kg": 1.0,
        "calories_total": 2200,
    }
    defaults.update(overrides)
    return defaults


def make_day_nutrition(**overrides):
    defaults = {
        "day_type": "strength",
        "macro_target": make_macro(),
    }
    defaults.update(overrides)
    return defaults


def make_nutrition_plan(**overrides):
    defaults = {
        "athlete_id": "00000000-0000-0000-0000-000000000001",
        "weight_kg": 75.0,
        "targets_by_day_type": {
            "rest": {**make_day_nutrition(day_type="rest"), "macro_target": make_macro(carbs_g_per_kg=3.0, calories_total=1800)},
            "strength": make_day_nutrition(),
        }
    }
    defaults.update(overrides)
    return defaults


# --- MacroTarget ---

def test_macro_valid():
    from resilio.schemas.nutrition import MacroTarget
    m = MacroTarget(**make_macro())
    assert m.carbs_g_per_kg == 4.0
    assert m.protein_g_per_kg == 2.0
    assert m.fat_g_per_kg == 1.0
    assert m.calories_total == 2200


def test_macro_negative_carbs_raises():
    from resilio.schemas.nutrition import MacroTarget
    with pytest.raises(ValidationError):
        MacroTarget(**make_macro(carbs_g_per_kg=-1.0))


def test_macro_zero_calories_raises():
    from resilio.schemas.nutrition import MacroTarget
    with pytest.raises(ValidationError):
        MacroTarget(**make_macro(calories_total=0))


# --- DayNutrition ---

def test_day_nutrition_valid_no_intra():
    from resilio.schemas.nutrition import DayNutrition
    dn = DayNutrition(**make_day_nutrition())
    assert dn.day_type.value == "strength"
    assert dn.intra_effort_carbs_g_per_h is None
    assert dn.sodium_mg_per_h is None


def test_day_nutrition_with_intra_effort():
    from resilio.schemas.nutrition import DayNutrition
    dn = DayNutrition(**make_day_nutrition(
        intra_effort_carbs_g_per_h=60.0,
        sodium_mg_per_h=750.0,
    ))
    assert dn.intra_effort_carbs_g_per_h == 60.0
    assert dn.sodium_mg_per_h == 750.0


def test_day_nutrition_invalid_day_type_raises():
    from resilio.schemas.nutrition import DayNutrition
    with pytest.raises(ValidationError):
        DayNutrition(**make_day_nutrition(day_type="cardio"))


# --- NutritionPlan ---

def test_nutrition_plan_valid():
    from resilio.schemas.nutrition import NutritionPlan
    plan = NutritionPlan(**make_nutrition_plan())
    assert plan.weight_kg == 75.0
    assert len(plan.targets_by_day_type) == 2


def test_nutrition_plan_id_generated():
    from resilio.schemas.nutrition import NutritionPlan
    p1 = NutritionPlan(**make_nutrition_plan())
    p2 = NutritionPlan(**make_nutrition_plan())
    assert p1.id != p2.id


def test_nutrition_plan_zero_weight_raises():
    from resilio.schemas.nutrition import NutritionPlan
    with pytest.raises(ValidationError):
        NutritionPlan(**make_nutrition_plan(weight_kg=0.0))


def test_nutrition_plan_empty_targets_is_valid():
    from resilio.schemas.nutrition import NutritionPlan
    plan = NutritionPlan(
        athlete_id="00000000-0000-0000-0000-000000000001",
        weight_kg=70.0,
    )
    assert plan.targets_by_day_type == {}


def test_nutrition_plan_enum_keys_serialized_as_strings():
    from resilio.schemas.nutrition import NutritionPlan
    plan = NutritionPlan(**make_nutrition_plan())
    json_str = plan.model_dump_json()
    data = json.loads(json_str)
    # Pydantic v2 serializes DayType keys as their string values
    assert "rest" in data["targets_by_day_type"]
    assert "strength" in data["targets_by_day_type"]


def test_nutrition_plan_json_round_trip():
    from resilio.schemas.nutrition import NutritionPlan
    plan = NutritionPlan(**make_nutrition_plan())
    json_str = plan.model_dump_json()
    plan2 = NutritionPlan.model_validate_json(json_str)
    assert plan == plan2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/backend/schemas/test_nutrition.py -v 2>&1 | head -20
```

Expected: `ImportError` — `resilio.schemas.nutrition` does not exist yet.

- [ ] **Step 3: Write the implementation**

Create `backend/resilio/schemas/nutrition.py`:

```python
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .athlete import DayType


class MacroTarget(BaseModel):
    carbs_g_per_kg: float = Field(..., ge=0)
    protein_g_per_kg: float = Field(..., ge=0)
    fat_g_per_kg: float = Field(..., ge=0)
    calories_total: int = Field(..., gt=0)


class DayNutrition(BaseModel):
    day_type: DayType
    macro_target: MacroTarget
    intra_effort_carbs_g_per_h: float | None = None
    sodium_mg_per_h: float | None = None


class NutritionPlan(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    athlete_id: UUID
    weight_kg: float = Field(..., gt=0)
    targets_by_day_type: dict[DayType, DayNutrition] = Field(default_factory=dict)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
poetry run pytest tests/backend/schemas/test_nutrition.py -v
```

Expected: 12 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/resilio/schemas/nutrition.py tests/backend/schemas/test_nutrition.py
git commit -m "feat: add MacroTarget, DayNutrition, NutritionPlan schemas"
```

---

## Task 7: WeeklyReview Schema

**Files:**
- Create: `backend/resilio/schemas/review.py`
- Test: `tests/backend/schemas/test_review.py`

`WeeklyReview` tracks planned vs. actual weekly activity. `results` defaults to `[]` and is serialized as `"[]"` (not `NULL`) — consistent with `results_json nullable=False` in the DB layer.

- [ ] **Step 1: Write the failing test**

Create `tests/backend/schemas/test_review.py`:

```python
import pytest
from datetime import date
from pydantic import ValidationError


def make_activity(**overrides):
    defaults = {
        "date": date(2026, 4, 7),
        "sport": "running",
        "planned_duration_min": 60,
    }
    defaults.update(overrides)
    return defaults


def make_review(**overrides):
    defaults = {
        "athlete_id": "00000000-0000-0000-0000-000000000001",
        "plan_id": "00000000-0000-0000-0000-000000000002",
        "week_start": date(2026, 4, 7),
    }
    defaults.update(overrides)
    return defaults


# --- ActivityResult ---

def test_activity_result_valid_minimal():
    from resilio.schemas.review import ActivityResult
    a = ActivityResult(**make_activity())
    assert a.actual_duration_min is None
    assert a.rpe_actual is None
    assert a.notes == ""


def test_activity_result_with_actual():
    from resilio.schemas.review import ActivityResult
    a = ActivityResult(**make_activity(actual_duration_min=55, rpe_actual=7))
    assert a.actual_duration_min == 55
    assert a.rpe_actual == 7


def test_activity_result_zero_planned_duration_raises():
    from resilio.schemas.review import ActivityResult
    with pytest.raises(ValidationError):
        ActivityResult(**make_activity(planned_duration_min=0))


def test_activity_result_rpe_below_1_raises():
    from resilio.schemas.review import ActivityResult
    with pytest.raises(ValidationError):
        ActivityResult(**make_activity(rpe_actual=0))


def test_activity_result_rpe_above_10_raises():
    from resilio.schemas.review import ActivityResult
    with pytest.raises(ValidationError):
        ActivityResult(**make_activity(rpe_actual=11))


def test_activity_result_invalid_sport_raises():
    from resilio.schemas.review import ActivityResult
    with pytest.raises(ValidationError):
        ActivityResult(**make_activity(sport="yoga"))


# --- WeeklyReview ---

def test_weekly_review_valid_empty_results():
    from resilio.schemas.review import WeeklyReview
    review = WeeklyReview(**make_review())
    assert review.results == []
    assert review.readiness_score is None
    assert review.hrv_rmssd is None
    assert review.sleep_hours_avg is None
    assert review.athlete_comment == ""


def test_weekly_review_id_generated():
    from resilio.schemas.review import WeeklyReview
    r1 = WeeklyReview(**make_review())
    r2 = WeeklyReview(**make_review())
    assert r1.id != r2.id


def test_weekly_review_with_results():
    from resilio.schemas.review import WeeklyReview
    review = WeeklyReview(**make_review(
        results=[make_activity(), make_activity(sport="lifting")]
    ))
    assert len(review.results) == 2
    assert review.results[0].sport.value == "running"
    assert review.results[1].sport.value == "lifting"


def test_weekly_review_with_recovery_metrics():
    from resilio.schemas.review import WeeklyReview
    review = WeeklyReview(**make_review(
        readiness_score=78.5,
        hrv_rmssd=42.3,
        sleep_hours_avg=7.5,
    ))
    assert review.readiness_score == 78.5
    assert review.hrv_rmssd == 42.3
    assert review.sleep_hours_avg == 7.5


def test_weekly_review_empty_results_json_not_null():
    from resilio.schemas.review import WeeklyReview
    import json
    review = WeeklyReview(**make_review())
    json_str = review.model_dump_json()
    data = json.loads(json_str)
    # results serializes as [] not null
    assert data["results"] == []


def test_weekly_review_json_round_trip():
    from resilio.schemas.review import WeeklyReview
    review = WeeklyReview(**make_review(
        results=[make_activity(actual_duration_min=58, rpe_actual=6)],
        readiness_score=80.0,
    ))
    json_str = review.model_dump_json()
    review2 = WeeklyReview.model_validate_json(json_str)
    assert review == review2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/backend/schemas/test_review.py -v 2>&1 | head -20
```

Expected: `ImportError` — `resilio.schemas.review` does not exist yet.

- [ ] **Step 3: Write the implementation**

Create `backend/resilio/schemas/review.py`:

```python
from datetime import date
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .athlete import Sport


class ActivityResult(BaseModel):
    date: date
    sport: Sport
    planned_duration_min: int = Field(..., gt=0)
    actual_duration_min: int | None = None
    rpe_actual: int | None = Field(None, ge=1, le=10)
    notes: str = ""


class WeeklyReview(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    athlete_id: UUID
    plan_id: UUID
    week_start: date
    results: list[ActivityResult] = Field(default_factory=list)
    readiness_score: float | None = None
    hrv_rmssd: float | None = None
    sleep_hours_avg: float | None = None
    athlete_comment: str = ""
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
poetry run pytest tests/backend/schemas/test_review.py -v
```

Expected: 12 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/resilio/schemas/review.py tests/backend/schemas/test_review.py
git commit -m "feat: add ActivityResult and WeeklyReview schemas"
```

---

## Task 8: Database Engine Setup

**Files:**
- Create: `backend/resilio/db/database.py`
- Test: `tests/backend/db/test_models.py` (partial — just engine/base tests first)

The database module creates the SQLAlchemy engine with an absolute path and enables FK enforcement via a connect event hook. Tests use in-memory SQLite (`"sqlite:///:memory:"`), never the file-based engine.

- [ ] **Step 1: Write the failing test (engine + base)**

Create `tests/backend/db/test_models.py` with the following content (we will add more tests in Task 9):

```python
import pytest
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import sessionmaker


def make_test_engine():
    """Create a fresh in-memory SQLite engine with FK enforcement for testing."""
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def set_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def test_base_is_importable():
    from resilio.db.database import Base
    assert Base is not None


def test_database_url_is_absolute():
    from resilio.db.database import DATABASE_URL
    # Must start with sqlite:/// followed by an absolute path (not relative)
    assert DATABASE_URL.startswith("sqlite:///")
    path_part = DATABASE_URL[len("sqlite:///"):]
    # Absolute paths start with / (Unix) or a drive letter (Windows)
    assert path_part.startswith("/") or (len(path_part) > 1 and path_part[1] == ":")


def test_session_local_is_importable():
    from resilio.db.database import SessionLocal
    assert SessionLocal is not None


def test_in_memory_engine_fk_enforcement():
    """SQLite FK constraints are OFF by default — verify our pragma enables them."""
    engine = make_test_engine()
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA foreign_keys"))
        value = result.scalar()
    assert value == 1, "PRAGMA foreign_keys must be ON"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/backend/db/test_models.py -v 2>&1 | head -20
```

Expected: `ImportError` — `resilio.db.database` does not exist yet.

- [ ] **Step 3: Write the implementation**

Create `backend/resilio/db/database.py`:

```python
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# backend/resilio/db/database.py → parents[3] = repo root
_REPO_ROOT = Path(__file__).resolve().parents[3]
_DB_PATH = _REPO_ROOT / "data" / "resilio.db"
DATABASE_URL = f"sqlite:///{_DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
poetry run pytest tests/backend/db/test_models.py -v
```

Expected: 4 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/resilio/db/database.py tests/backend/db/test_models.py
git commit -m "feat: add database engine with absolute path and FK pragma"
```

---

## Task 9: SQLAlchemy ORM Models

**Files:**
- Create: `backend/resilio/db/models.py`
- Modify: `tests/backend/db/test_models.py` (add model tests)

4 ORM tables. Complex fields stored as JSON TEXT. FK relationships enforced by `PRAGMA foreign_keys=ON`. All tests use `make_test_engine()` with in-memory SQLite.

- [ ] **Step 1: Write the failing tests**

Add `import json` and `from datetime import date` to the **existing import block at the top** of `tests/backend/db/test_models.py` (after `from sqlalchemy.orm import sessionmaker`), then append the following functions to the bottom of the file:

```python
# (These imports go at the TOP of the file, not here)
# import json
# from datetime import date



def setup_db(engine):
    """Create all tables. Call at start of each DB test."""
    from resilio.db.database import Base
    from resilio.db import models  # noqa: F401 — registers ORM models with Base
    Base.metadata.create_all(engine)
    return sessionmaker(engine)


def teardown_db(engine):
    """Drop all tables. Call at end of each DB test."""
    from resilio.db.database import Base
    Base.metadata.drop_all(engine)


def make_athlete_row():
    import uuid
    return {
        "id": str(uuid.uuid4()),
        "name": "Alice",
        "age": 30,
        "sex": "F",
        "weight_kg": 60.0,
        "height_cm": 168.0,
        "primary_sport": "running",
        "hours_per_week": 10.0,
        "sports_json": '["running","lifting"]',
        "goals_json": '["run a marathon sub-4h"]',
        "available_days_json": '[0,2,4,6]',
        "equipment_json": '[]',
    }


def test_all_four_tables_created():
    engine = make_test_engine()
    setup_db(engine)
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    assert "athletes" in table_names
    assert "training_plans" in table_names
    assert "nutrition_plans" in table_names
    assert "weekly_reviews" in table_names
    teardown_db(engine)


def test_athlete_crud_round_trip():
    from resilio.db.models import AthleteModel
    engine = make_test_engine()
    Session = setup_db(engine)
    row = make_athlete_row()
    with Session() as session:
        athlete = AthleteModel(**row)
        session.add(athlete)
        session.commit()
        fetched = session.get(AthleteModel, row["id"])
        assert fetched.name == "Alice"
        assert fetched.age == 30
        assert fetched.sex == "F"
        assert fetched.sports_json == '["running","lifting"]'
    teardown_db(engine)


def test_athlete_json_fields_stored_as_strings():
    from resilio.db.models import AthleteModel
    engine = make_test_engine()
    Session = setup_db(engine)
    row = make_athlete_row()
    with Session() as session:
        session.add(AthleteModel(**row))
        session.commit()
        fetched = session.get(AthleteModel, row["id"])
        # JSON fields must be strings (not already parsed)
        assert isinstance(fetched.sports_json, str)
        # And parseable back to list
        assert json.loads(fetched.sports_json) == ["running", "lifting"]
        assert json.loads(fetched.goals_json) == ["run a marathon sub-4h"]
        assert json.loads(fetched.available_days_json) == [0, 2, 4, 6]
        assert json.loads(fetched.equipment_json) == []
    teardown_db(engine)


def test_training_plan_fk_constraint_enforced():
    from resilio.db.models import TrainingPlanModel
    from sqlalchemy.exc import IntegrityError
    import uuid
    engine = make_test_engine()
    Session = setup_db(engine)
    with Session() as session:
        plan = TrainingPlanModel(
            id=str(uuid.uuid4()),
            athlete_id="does-not-exist",  # FK violation
            start_date=date(2026, 4, 7),
            end_date=date(2026, 5, 4),
            phase="base",
            total_weekly_hours=8.0,
            acwr=1.0,
            weekly_slots_json="{}",
        )
        session.add(plan)
        with pytest.raises(IntegrityError):
            session.commit()
    teardown_db(engine)


def test_weekly_review_fk_to_both_athlete_and_plan():
    from resilio.db.models import AthleteModel, TrainingPlanModel, WeeklyReviewModel
    import uuid
    engine = make_test_engine()
    Session = setup_db(engine)
    athlete_id = str(uuid.uuid4())
    plan_id = str(uuid.uuid4())
    review_id = str(uuid.uuid4())
    with Session() as session:
        session.add(AthleteModel(**{**make_athlete_row(), "id": athlete_id}))
        session.add(TrainingPlanModel(
            id=plan_id,
            athlete_id=athlete_id,
            start_date=date(2026, 4, 7),
            end_date=date(2026, 5, 4),
            phase="base",
            total_weekly_hours=8.0,
            acwr=1.0,
            weekly_slots_json="{}",
        ))
        session.add(WeeklyReviewModel(
            id=review_id,
            athlete_id=athlete_id,
            plan_id=plan_id,
            week_start=date(2026, 4, 7),
            results_json="[]",
        ))
        session.commit()
        review = session.get(WeeklyReviewModel, review_id)
        assert review.athlete_id == athlete_id
        assert review.plan_id == plan_id
        assert review.results_json == "[]"
    teardown_db(engine)


def test_nutrition_plan_targets_json_round_trip():
    from resilio.db.models import AthleteModel, NutritionPlanModel
    import uuid
    engine = make_test_engine()
    Session = setup_db(engine)
    athlete_id = str(uuid.uuid4())
    plan_id = str(uuid.uuid4())
    targets = {"rest": {"day_type": "rest", "macro_target": {"carbs_g_per_kg": 3.0, "protein_g_per_kg": 2.0, "fat_g_per_kg": 1.0, "calories_total": 1800}, "intra_effort_carbs_g_per_h": None, "sodium_mg_per_h": None}}
    with Session() as session:
        session.add(AthleteModel(**{**make_athlete_row(), "id": athlete_id}))
        session.add(NutritionPlanModel(
            id=plan_id,
            athlete_id=athlete_id,
            weight_kg=75.0,
            targets_json=json.dumps(targets),
        ))
        session.commit()
        fetched = session.get(NutritionPlanModel, plan_id)
        assert isinstance(fetched.targets_json, str)
        parsed = json.loads(fetched.targets_json)
        assert "rest" in parsed
        assert parsed["rest"]["macro_target"]["carbs_g_per_kg"] == 3.0
    teardown_db(engine)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/backend/db/test_models.py -v 2>&1 | head -30
```

Expected: `ImportError` or collection errors — `resilio.db.models` does not exist yet.

- [ ] **Step 3: Write the implementation**

Create `backend/resilio/db/models.py`:

```python
from sqlalchemy import Boolean, Column, Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


class AthleteModel(Base):
    __tablename__ = "athletes"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    sex = Column(String, nullable=False)
    weight_kg = Column(Float, nullable=False)
    height_cm = Column(Float, nullable=False)
    primary_sport = Column(String, nullable=False)
    target_race_date = Column(Date, nullable=True)
    hours_per_week = Column(Float, nullable=False)
    sleep_hours_typical = Column(Float, default=7.0)
    stress_level = Column(Integer, default=5)
    job_physical = Column(Boolean, default=False)
    max_hr = Column(Integer, nullable=True)
    resting_hr = Column(Integer, nullable=True)
    ftp_watts = Column(Integer, nullable=True)
    vdot = Column(Float, nullable=True)
    css_per_100m = Column(Float, nullable=True)
    # JSON-serialized list fields
    sports_json = Column(Text, nullable=False)
    goals_json = Column(Text, nullable=False)
    available_days_json = Column(Text, nullable=False)
    equipment_json = Column(Text, nullable=False)
    # Relationships
    plans = relationship("TrainingPlanModel", back_populates="athlete")
    nutrition_plans = relationship("NutritionPlanModel", back_populates="athlete")
    reviews = relationship("WeeklyReviewModel", back_populates="athlete")


class TrainingPlanModel(Base):
    __tablename__ = "training_plans"

    id = Column(String, primary_key=True)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    phase = Column(String, nullable=False)
    total_weekly_hours = Column(Float, nullable=False)
    acwr = Column(Float, nullable=False)
    weekly_slots_json = Column(Text, nullable=False)
    # Relationships
    athlete = relationship("AthleteModel", back_populates="plans")
    reviews = relationship("WeeklyReviewModel", back_populates="plan")


class NutritionPlanModel(Base):
    __tablename__ = "nutrition_plans"

    id = Column(String, primary_key=True)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=False)
    weight_kg = Column(Float, nullable=False)
    targets_json = Column(Text, nullable=False)
    # Relationships
    athlete = relationship("AthleteModel", back_populates="nutrition_plans")


class WeeklyReviewModel(Base):
    __tablename__ = "weekly_reviews"

    id = Column(String, primary_key=True)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=False)
    plan_id = Column(String, ForeignKey("training_plans.id"), nullable=False)
    week_start = Column(Date, nullable=False)
    readiness_score = Column(Float, nullable=True)
    hrv_rmssd = Column(Float, nullable=True)
    sleep_hours_avg = Column(Float, nullable=True)
    athlete_comment = Column(Text, default="")
    results_json = Column(Text, nullable=False)
    # Relationships
    athlete = relationship("AthleteModel", back_populates="reviews")
    plan = relationship("TrainingPlanModel", back_populates="reviews")
```

- [ ] **Step 4: Run all DB tests**

```bash
poetry run pytest tests/backend/db/test_models.py -v
```

Expected: all tests PASSED (4 from Task 8 + 6 new tests = 10 total).

- [ ] **Step 5: Commit**

```bash
git add backend/resilio/db/models.py tests/backend/db/test_models.py
git commit -m "feat: add SQLAlchemy ORM models (4 tables) with FK enforcement"
```

---

## Task 10: Final Verification

**Files:** None — verification only.

> Confirm that all new backend tests pass and all existing CLI tests are still green.

- [ ] **Step 1: Run all backend tests**

```bash
poetry run pytest tests/backend/ -v
```

Expected: all schema and DB tests pass. Count: 69 tests (9 fatigue + 14 athlete + 12 plan + 12 nutrition + 12 review + 10 db). If any fail, fix before continuing.

- [ ] **Step 2: Run existing CLI tests**

```bash
poetry run pytest tests/unit tests/integration -q 2>&1 | tail -5
```

Expected: same pass/fail counts as Task 1 Step 4 baseline. If new failures appear that did not exist before, the `pythonpath` config is causing a collision — investigate.

- [ ] **Step 3: Verify CLI still works**

```bash
poetry run resilio --help
```

Expected: Typer CLI help text displayed. If this fails, the package configuration is broken.

- [ ] **Step 4: Run full test suite**

```bash
poetry run pytest -q 2>&1 | tail -10
```

Expected: all new backend tests pass + existing tests unchanged.

- [ ] **Step 5: Final commit**

```bash
git add -A
git status  # verify nothing unexpected is staged
git commit -m "feat: complete Phase 1 — Pydantic schemas and SQLAlchemy ORM models"
```

---

## Summary

| Task | Deliverable | Tests |
|---|---|---|
| 1 | SQLAlchemy added, `data/` created | Baseline verified |
| 2 | Package skeleton + pytest config | Existing tests unbroken |
| 3 | `FatigueScore` schema | 9 tests |
| 4 | `Sport`, `DayType`, `AthleteProfile` | 14 tests |
| 5 | `WorkoutSlot`, `TrainingPlan` | 12 tests |
| 6 | `MacroTarget`, `DayNutrition`, `NutritionPlan` | 12 tests |
| 7 | `ActivityResult`, `WeeklyReview` | 12 tests |
| 8 | `database.py` (engine + FK pragma) | 4 tests |
| 9 | `models.py` (4 ORM tables) | 6 new + 4 from Task 8 |
| 10 | Full verification | All suites green |
