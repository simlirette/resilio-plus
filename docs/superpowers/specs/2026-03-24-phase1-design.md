# Phase 1 Design Spec — Schemas & Data Models

**Date**: 2026-03-24
**Project**: Resilio Plus — Hybrid Athlete Multi-Agent Coaching Platform
**Scope**: Phase 1 — Pydantic schemas, SQLAlchemy ORM models, SQLite database setup
**Approach**: Pydantic + SQLAlchemy separate layers (Approach A)

---

## 1. Context

Phase 0 established the monorepo structure with `resilio/` (legacy CLI, read-only), `backend/` (FastAPI — placeholder), and `.bmad-core/` (agent stubs). Phase 1 creates the data layer for the backend: Pydantic schemas for in-memory validation and SQLAlchemy ORM models for persistence. No API routes are implemented in this phase.

The FatigueScore is the unified inter-agent language described in Section 6 of the blueprint. All agent outputs ultimately express themselves through FatigueScore fields.

---

## 2. Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Schema strategy | Fresh schemas (Option C) | Legacy schemas are running-specific with CLI assumptions; multi-agent platform needs clean, neutral models |
| Persistence layer | SQLite now, PostgreSQL later | SQLAlchemy abstraction makes migration trivial; SQLite is zero-config for Phase 1 |
| Pydantic + SQLAlchemy | Separate layers | Pydantic for agent/API validation; SQLAlchemy for DB persistence; no SQLModel to avoid coupling |
| FatigueScore persistence | JSON embedded in WorkoutSlot | No dedicated table needed; agents always work with Pydantic objects in memory |
| Complex fields (lists, dicts) | JSON TEXT columns | SQLite has no native array/JSON type; JSON string with agent-layer deserialization |
| Entities in scope | All 5 in Phase 1 | FatigueScore, AthleteProfile, TrainingPlan, NutritionPlan, WeeklyReview form a coherent data layer |
| Backend package name | `backend/resilio/` | Aligns with blueprint paths (`backend/resilio/agents/`, `backend/resilio/connectors/`); namespace resolved via pytest `pythonpath` config |
| SQLAlchemy version | `>=2.0,<3.0` | Required for `DeclarativeBase` from `sqlalchemy.orm`; must be added to `pyproject.toml` |
| SQLite FK enforcement | `PRAGMA foreign_keys=ON` via event hook | SQLite does not enforce FK constraints by default; event listener in `database.py` enables this |
| DATABASE_URL path | Absolute path via `pathlib` | Relative URL (`sqlite:///data/resilio.db`) is working-directory-dependent; absolute path avoids silent failures in CI |

---

## 3. Prerequisites

Before implementing, run these steps from the repo root:

```bash
# 1. Add SQLAlchemy
poetry add "sqlalchemy>=2.0,<3.0"

# 2. Create the data directory
mkdir -p data && touch data/.gitkeep

# 3. Verify existing tests still pass before touching pyproject.toml
poetry run pytest tests/unit tests/integration -q
```

Step 3 establishes a green baseline. The pytest config change in Section 4 must not break existing tests — verify this by re-running the suite after adding `[tool.pytest.ini_options]`.

---

## 4. Pytest Configuration

Add to `pyproject.toml` to resolve the Python path for backend tests without breaking existing CLI tests:

```toml
[tool.pytest.ini_options]
pythonpath = ["backend"]
testpaths = ["tests"]
```

**Why**: `backend/resilio/` and the top-level `resilio/` share the package name. With `pythonpath = ["backend"]`, `import resilio` resolves to `backend/resilio/` during test runs. The legacy CLI remains functional via `poetry run resilio` (uses the installed package from the top-level `resilio/`).

**Required verification before adding this config**: Run `grep -r "from resilio" tests/unit tests/integration` and `grep -r "import resilio" tests/unit tests/integration` to confirm that existing tests import from the top-level `resilio/` package using patterns that will continue to resolve correctly. After adding `[tool.pytest.ini_options]`, re-run `poetry run pytest tests/unit tests/integration -q` and confirm the baseline still passes. If any existing test breaks, remove the `pythonpath` addition and raise before proceeding.

**Invariant**: Both old and new tests are discovered under `tests/`. The existing `tests/conftest.py` applies to all tests — do not break it. New backend tests in `tests/backend/` must not import from the top-level `resilio/` package.

---

## 5. File Structure

```
resilio-plus/
├── backend/
│   └── resilio/
│       ├── __init__.py
│       ├── schemas/
│       │   ├── __init__.py
│       │   ├── fatigue.py          # FatigueScore
│       │   ├── athlete.py          # AthleteProfile + Sport + DayType enums
│       │   ├── plan.py             # WorkoutSlot + TrainingPlan
│       │   ├── nutrition.py        # MacroTarget + DayNutrition + NutritionPlan
│       │   └── review.py           # ActivityResult + WeeklyReview
│       └── db/
│           ├── __init__.py
│           ├── database.py         # Engine + SessionLocal + Base
│           └── models.py           # 4 SQLAlchemy ORM tables
├── data/
│   └── .gitkeep                    # DB file created here at runtime (data/resilio.db)
└── tests/
    └── backend/
        ├── __init__.py
        ├── schemas/
        │   ├── __init__.py
        │   ├── test_fatigue.py
        │   ├── test_athlete.py
        │   ├── test_plan.py
        │   ├── test_nutrition.py
        │   └── test_review.py
        └── db/
            ├── __init__.py
            └── test_models.py      # Uses in-memory SQLite (":memory:") — no file I/O
```

---

## 6. Pydantic Schemas

All schemas use **Pydantic v2** (`from pydantic import BaseModel, Field`). UUIDs default to `uuid4`. All fields validated at construction.

### 6.1 Shared Enums (athlete.py)

```python
from enum import Enum

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
```

### 6.2 FatigueScore (fatigue.py)

Inter-agent communication primitive. All values 0–100 except `recovery_hours`.

```python
from pydantic import BaseModel, Field

class FatigueScore(BaseModel):
    local_muscular: float = Field(..., ge=0, le=100)   # Muscle group fatigue
    cns_load: float = Field(..., ge=0, le=100)          # Central nervous system load
    metabolic_cost: float = Field(..., ge=0, le=100)    # Energy system demand
    recovery_hours: float = Field(..., ge=0)             # Hours to full recovery
    affected_muscles: list[str] = Field(default_factory=list)  # e.g. ["quads", "glutes"]
```

### 6.3 AthleteProfile (athlete.py)

Full onboarding data. Fitness markers are all optional (not known at sign-up).

```python
from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from datetime import date
from typing import Literal

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
    ftp_watts: int | None = None          # Cycling FTP
    vdot: float | None = None             # Running VDOT (Daniels)
    css_per_100m: float | None = None     # Swimming CSS (seconds per 100m)
    # Lifestyle
    sleep_hours_typical: float = Field(default=7.0)
    stress_level: int = Field(default=5, ge=1, le=10)
    job_physical: bool = False
```

### 6.4 WorkoutSlot + TrainingPlan (plan.py)

`weekly_slots` keyed by `"YYYY-WW"` (ISO week string). ACWR is the Acute:Chronic Workload Ratio (safe zone 0.8–1.3).

**JSON serialization note**: `weekly_slots_json` stores a `dict[str, list[WorkoutSlot]]` where each `WorkoutSlot` contains a nested `FatigueScore`. Pydantic v2 fully handles nested model serialization via `model.model_dump_json()`. The repository layer (Phase 4) must reconstruct the full structure using `TrainingPlan.model_validate_json(row.weekly_slots_json)` — Pydantic reconstructs nested models automatically from JSON.

```python
from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from datetime import date
from typing import Literal
from .fatigue import FatigueScore
from .athlete import Sport

class WorkoutSlot(BaseModel):
    date: date
    sport: Sport
    workout_type: str      # e.g. "easy_run", "tempo", "strength_upper"
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

### 6.5 MacroTarget + DayNutrition + NutritionPlan (nutrition.py)

Macros periodized per `DayType`. Carbs range: 4–5 g/kg (strength) → 6–7 g/kg (endurance). Intra-effort and sodium only needed on training days.

**JSON serialization note**: `targets_by_day_type` uses `DayType` enum as dict key. Pydantic v2 serializes this as `{"rest": {...}, "strength": {...}, ...}` (string values of the enum). The `targets_json` TEXT column stores this string-keyed JSON. The repository layer (Phase 4) must deserialize using `{DayType(k): DayNutrition(**v) for k, v in json.loads(targets_json).items()}`.

```python
from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from .athlete import DayType

class MacroTarget(BaseModel):
    carbs_g_per_kg: float = Field(..., ge=0)
    protein_g_per_kg: float = Field(..., ge=0)
    fat_g_per_kg: float = Field(..., ge=0)
    calories_total: int = Field(..., gt=0)

class DayNutrition(BaseModel):
    day_type: DayType
    macro_target: MacroTarget
    intra_effort_carbs_g_per_h: float | None = None   # 30–90 g/h depending on intensity
    sodium_mg_per_h: float | None = None               # ~500–1000 mg/h for long efforts

class NutritionPlan(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    athlete_id: UUID
    weight_kg: float = Field(..., gt=0)
    targets_by_day_type: dict[DayType, DayNutrition] = Field(default_factory=dict)
```

### 6.6 ActivityResult + WeeklyReview (review.py)

Tracks planned vs. actual execution. `readiness_score`, `hrv_rmssd`, and `sleep_hours_avg` come from Apple Health / Terra connector (Phase 2).

**JSON serialization note**: `results` defaults to an empty list `[]`. Serialized as `"[]"` (not `NULL`), which is consistent with `results_json nullable=False`. An empty week is a valid state (no activities logged yet).

```python
from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from datetime import date
from .athlete import Sport

class ActivityResult(BaseModel):
    date: date
    sport: Sport
    planned_duration_min: int = Field(..., gt=0)
    actual_duration_min: int | None = None    # None = not completed
    rpe_actual: int | None = Field(None, ge=1, le=10)
    notes: str = ""

class WeeklyReview(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    athlete_id: UUID
    plan_id: UUID
    week_start: date
    results: list[ActivityResult] = Field(default_factory=list)
    # Recovery metrics (Phase 2 connectors — optional until then)
    readiness_score: float | None = None      # 0–100 composite from HRV + sleep
    hrv_rmssd: float | None = None            # ms
    sleep_hours_avg: float | None = None
    athlete_comment: str = ""
```

---

## 7. SQLAlchemy ORM Models

**Database**: SQLite at `<repo_root>/data/resilio.db` (created at runtime). Switching to PostgreSQL later requires only changing `DATABASE_URL`.

**Requires**: `sqlalchemy>=2.0,<3.0` (see Prerequisites section).

### 7.1 database.py

Uses an **absolute path** derived from `__file__` to avoid working-directory-dependent behavior. Enables SQLite FK enforcement via an `@event.listens_for` hook (SQLite ignores FK constraints by default without `PRAGMA foreign_keys=ON`).

```python
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Absolute path: <repo_root>/data/resilio.db
_REPO_ROOT = Path(__file__).resolve().parents[3]  # backend/resilio/db/ -> repo root
_DB_PATH = _REPO_ROOT / "data" / "resilio.db"
DATABASE_URL = f"sqlite:///{_DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass
```

**Test override**: `test_models.py` must create its own in-memory engine (`create_engine("sqlite:///:memory:")`) and apply the same FK pragma. Do not use the module-level `engine` in tests.

### 7.2 models.py — 4 Tables

Complex fields (lists, nested objects) stored as **JSON TEXT**. Agents work with Pydantic objects in memory; serialization/deserialization happens at the repository layer (Phase 4). See JSON serialization notes in Pydantic schema sections for deserialization patterns.

```python
from sqlalchemy import Column, String, Float, Integer, Boolean, Text, Date, ForeignKey, event
from sqlalchemy.orm import relationship
from .database import Base

class AthleteModel(Base):
    __tablename__ = "athletes"
    id = Column(String, primary_key=True)           # UUID as string
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
    sports_json = Column(Text, nullable=False)         # JSON list of Sport strings, e.g. '["running","lifting"]'
    goals_json = Column(Text, nullable=False)          # JSON list of strings
    available_days_json = Column(Text, nullable=False) # JSON list of ints, e.g. '[0,1,2]'
    equipment_json = Column(Text, nullable=False)      # JSON list of strings
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
    weekly_slots_json = Column(Text, nullable=False)   # JSON dict[week_str, list[WorkoutSlot]]
    athlete = relationship("AthleteModel", back_populates="plans")
    reviews = relationship("WeeklyReviewModel", back_populates="plan")


class NutritionPlanModel(Base):
    __tablename__ = "nutrition_plans"
    id = Column(String, primary_key=True)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=False)
    weight_kg = Column(Float, nullable=False)
    targets_json = Column(Text, nullable=False)        # JSON dict[DayType.value, DayNutrition dict]
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
    results_json = Column(Text, nullable=False)        # JSON list[ActivityResult]; '[]' for empty week
    athlete = relationship("AthleteModel", back_populates="reviews")
    plan = relationship("TrainingPlanModel", back_populates="reviews")
```

---

## 8. Testing Strategy

Each schema file gets a dedicated test file. Tests follow TDD (RED → GREEN → REFACTOR). DB tests use **in-memory SQLite** (`"sqlite:///:memory:"`) — no file I/O, no dependency on `data/` directory.

### Schema tests (per schema):
- **Valid construction**: all required fields → object created
- **Field validation**: invalid values raise `ValidationError` (e.g., `local_muscular=150`, `age=-1`)
- **Optional fields default correctly**: `None` where expected
- **Enum acceptance**: valid string values parsed, invalid strings rejected
- **JSON round-trip**: `model.model_dump_json()` → `Model.model_validate_json(...)` → same data

### DB tests (test_models.py):
- **In-memory engine setup**: each test function creates a fresh `create_engine("sqlite:///:memory:")` with `PRAGMA foreign_keys=ON` applied; `Base.metadata.create_all()` before test, `drop_all()` after
- **Table creation**: all 4 tables present after `create_all`
- **CRUD round-trip**: create `AthleteModel` row → commit → query → assert scalar values match
- **FK constraint**: `TrainingPlanModel` with non-existent `athlete_id` raises `IntegrityError` (enforced by `PRAGMA foreign_keys=ON`)
- **JSON TEXT fields**: verify stored value is a string, parse back to original structure

---

## 9. Out of Scope for Phase 1

- API routes (FastAPI endpoints) — Phase 4
- Repository layer (ORM ↔ Pydantic mappers) — Phase 4
- Connector schemas (Strava, Hevy, FatSecret) — Phase 2
- Migration tooling (Alembic) — Phase 4
- Any agent logic — Phase 3
