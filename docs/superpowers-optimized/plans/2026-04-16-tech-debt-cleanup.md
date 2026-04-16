# Tech Debt Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-optimized:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reach mypy --strict 0 errors + ruff 0 violations on `backend/app/` before frontend code freeze.

**Architecture:** Six sequential lots: ruff auto-fix → stubs/overrides → SQLAlchemy `Mapped[T]` migration (consolidating `models/schemas.py` into `db/models.py`) → type-arg/untyped-def fixes → decorator + graph typing → ruff manual + pre-commit.

**Tech Stack:** Python 3.13, SQLAlchemy 2.0.48, mypy 1.19.1, ruff 0.1.15, pre-commit

**Assumptions:**
- SQLAlchemy 2.0 `Mapped[T]` API is available (version confirmed: 2.0.48) — will NOT work on SA 1.4.
- All models currently use string-based `relationship("ClassName")` forward refs — migration preserves semantics.
- Pre-commit requires `pre-commit` package installed globally or in venv.
- `pytest tests/backend/` passes clean before we start (baseline 2378 tests).

---

## File Map

| File | Action | Reason |
|---|---|---|
| `backend/app/db/models.py` | Modify | Migrate 11 models to `Mapped[T]`; absorb 6 V3 models from `models/schemas.py` |
| `backend/app/models/schemas.py` | Delete (after consolidation) | All content moves to `db/models.py` |
| `backend/app/graphs/logging.py` | Modify | Add `ParamSpec`/`TypeVar` typing to `log_node` |
| `backend/app/graphs/nodes.py` | Modify | `dict[str, Any]`, union-attr guards, N806 |
| `backend/app/graphs/coaching_graph.py` | Modify | `no-untyped-def` fix, N806 |
| `backend/app/graphs/weekly_review_graph.py` | Modify | `no-untyped-def`, N806, E501 |
| `backend/app/core/security.py` | Modify | `no-any-return`, `type-arg`, `import-untyped` |
| `backend/app/core/hormonal.py` | Modify | `type-arg` (6 × `dict`) |
| `backend/app/core/analytics_logic.py` | Modify | `type-arg` + `arg-type` sort key |
| `backend/app/core/running_logic.py` | Modify | `type-arg`, operator fix |
| `backend/app/core/lifting_logic.py` | Modify | `type-arg`, N806 |
| `backend/app/core/nutrition_logic.py` | Modify | `type-arg` |
| `backend/app/core/energy_patterns.py` | Modify | `type-arg`, update import |
| `backend/app/core/strain.py` | Modify | `assignment` int/float |
| `backend/app/connectors/base.py` | Modify | Untyped defs |
| `backend/app/connectors/gpx.py` | Modify | `type-arg`, `union-attr`, N806 |
| `backend/app/connectors/fit.py` | Modify | `type-arg`, `import-untyped` ignore |
| `backend/app/connectors/apple_health.py` | Modify | `type-arg` |
| `backend/app/connectors/hevy.py` | Modify | `type-arg` |
| `backend/app/integrations/hevy/importer.py` | Modify | `type-arg` |
| `backend/app/integrations/hevy/csv_parser.py` | Modify | `type-arg` |
| `backend/app/integrations/strava/oauth_service.py` | Modify | SA Column → Mapped |
| `backend/app/integrations/nutrition/unified_service.py` | Modify | SA Column → Mapped, `type-arg` |
| `backend/app/integrations/nutrition/fcen_loader.py` | Modify | SA Column → Mapped |
| `backend/app/integrations/nutrition/usda_client.py` | Modify | `type-arg` |
| `backend/app/services/coaching_service.py` | Modify | `no-untyped-def`, `no-any-return`, N806 |
| `backend/app/services/connector_service.py` | Modify | SA Column → Mapped |
| `backend/app/services/sync_service.py` | Modify | SA Column → Mapped |
| `backend/app/services/energy_cycle_service.py` | Modify | SA Column → Mapped, update import |
| `backend/app/services/external_plan_service.py` | Modify | Update import |
| `backend/app/services/plan_import_service.py` | Modify | `type-arg`, update import |
| `backend/app/schemas/plan.py` | Modify | `attr-defined` fix |
| `backend/app/routes/auth.py` | Modify | SA Column → Mapped, `type-arg` |
| `backend/app/routes/athletes.py` | Modify | SA Column → Mapped |
| `backend/app/routes/workflow.py` | Modify | SA Column → Mapped, `type-arg`, `no-redef` |
| `backend/app/routes/sessions.py` | Modify | SA Column → Mapped |
| `backend/app/routes/connectors.py` | Modify | SA Column → Mapped, `type-arg` |
| `backend/app/routes/checkin.py` | Modify | `type-arg` |
| `backend/app/jobs/registry.py` | Modify | SA Column → Mapped, `import-untyped` |
| `backend/app/jobs/scheduler.py` | Modify | `import-untyped` |
| `backend/app/observability/pii_filter.py` | Modify | `type-arg` Pattern |
| `backend/app/observability/sentry.py` | Modify | `import-not-found` (optional dep) |
| `backend/app/main.py` | Modify | `no-untyped-def`, E402 noqa |
| `backend/app/agents/energy_coach/agent.py` | Modify | `type-arg`, remove unused-ignore |
| `pyproject.toml` | Modify | Lock mypy strict + ruff config + mypy overrides |
| `.pre-commit-config.yaml` | Create | ruff + mypy hooks |
| `docs/backend/TYPING-CONVENTIONS.md` | Create | Typing guide |

---

## Task 1: Ruff Auto-Fix

**Files:** `backend/app/**/*.py` (in-place)

- [ ] **Step 1: Run ruff --fix**

```bash
cd /c/Users/simon/resilio-plus
VENV=/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts
$VENV/python.exe -m ruff check --fix backend/app/
$VENV/python.exe -m ruff format backend/app/
```

- [ ] **Step 2: Verify count dropped**

Run: `$VENV/python.exe -m ruff check backend/app/ 2>&1 | grep "Found"`
Expected: Found ≤139 errors (197 − 58 auto-fixed)

- [ ] **Step 3: Run backend tests**

Run: `$VENV/pytest.exe tests/backend/ -x -q`
Expected: PASS, same count as baseline

- [ ] **Step 4: Commit**

```bash
git add backend/app/
git commit -m "chore(lint): ruff auto-fix — sort imports, remove unused, format"
```

---

## Task 2: Third-Party Stubs + mypy Overrides

**Files:** `pyproject.toml`, `backend/app/core/security.py`, `backend/app/connectors/fit.py`, `backend/app/jobs/registry.py`, `backend/app/jobs/scheduler.py`, `backend/app/observability/sentry.py`

- [ ] **Step 1: Add mypy overrides for untyped third-party libs**

Edit `pyproject.toml` — add after `[tool.mypy]` block:

```toml
[[tool.mypy.overrides]]
module = [
    "apscheduler",
    "apscheduler.*",
    "sentry_sdk",
    "sentry_sdk.*",
    "fitparse",
    "fitparse.*",
]
ignore_missing_imports = true
```

- [ ] **Step 2: Fix jose + passlib ignores in security.py**

In `backend/app/core/security.py`, add inline ignores on the import lines:

```python
from jose import jwt  # type: ignore[import-untyped]
from passlib.context import CryptContext  # type: ignore[import-untyped]
```

- [ ] **Step 3: Fix no-any-return in security.py**

The functions `verify_password`, `get_password_hash`, `create_access_token`, `decode_token` call untyped passlib/jose and return `Any`. Cast returns explicitly:

```python
def verify_password(plain: str, hashed: str) -> bool:
    return bool(pwd_context.verify(plain, hashed))

def get_password_hash(password: str) -> str:
    return str(pwd_context.hash(password))

def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    ...
    return str(jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM))

def decode_token(token: str) -> dict[str, Any] | None:
    try:
        payload: dict[str, Any] = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception:
        return None
```

- [ ] **Step 4: Verify mypy errors drop for stubs section**

Run: `VENV/python.exe -m mypy backend/app/core/security.py backend/app/jobs/ backend/app/observability/sentry.py --strict 2>&1 | grep "error:" | wc -l`
Expected: 0 errors for import-untyped/import-not-found in those files

- [ ] **Step 5: Run backend tests**

Run: `$VENV/pytest.exe tests/backend/ -x -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml backend/app/core/security.py backend/app/jobs/ backend/app/observability/sentry.py
git commit -m "chore(typing): add mypy overrides for apscheduler/sentry/fitparse + fix security.py no-any-return"
```

---

## Task 3: Consolidate V3 SQLAlchemy Models — Eliminate Circular Import

**Files:** `backend/app/db/models.py`, `backend/app/models/schemas.py`, `backend/app/core/energy_patterns.py`, `backend/app/services/energy_cycle_service.py`, `backend/app/services/external_plan_service.py`, `backend/app/services/plan_import_service.py`

**Context:** `models/schemas.py` contains 6 SQLAlchemy models that `db/models.py` bottom-imports to register the mapper registry (circular import). Fix: move all 6 into `db/models.py`, remove circular import, update all importers.

- [ ] **Step 1: Append V3 models to db/models.py**

Remove the bottom import block (lines 207–216) from `db/models.py`:
```python
# DELETE these lines:
from app.models.schemas import (  # noqa: E402, F401
    AllostaticEntryModel,
    EnergySnapshotModel,
    HormonalProfileModel,
    ExternalPlanModel,
    ExternalSessionModel,
    HeadCoachMessageModel,
)
```

Then append the 6 model classes directly at the end of `db/models.py` (copy verbatim from `models/schemas.py`, preserving all columns and relationships). Add `BigInteger` to the SQLAlchemy imports if not already present.

The full content to append (after the `FoodCacheModel` class):

```python
class EnergySnapshotModel(Base):
    __tablename__ = "energy_snapshots"

    id = Column(String, primary_key=True)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    allostatic_score = Column(Float, nullable=False)
    cognitive_load = Column(Float, nullable=False)
    energy_availability = Column(Float, nullable=False)
    cycle_phase = Column(String, nullable=True)
    sleep_quality = Column(Float, nullable=False)
    recommended_intensity_cap = Column(Float, nullable=False)
    veto_triggered = Column(Boolean, nullable=False, default=False)
    veto_reason = Column(Text, nullable=True)
    objective_score = Column(Float, nullable=True)
    subjective_score = Column(Float, nullable=True)
    legs_feeling = Column(String, nullable=True)
    stress_level = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))
    athlete = relationship("AthleteModel", back_populates="energy_snapshots")


class HormonalProfileModel(Base):
    __tablename__ = "hormonal_profiles"

    id = Column(String, primary_key=True)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=False, unique=True)
    enabled = Column(Boolean, nullable=False, default=False)
    cycle_length_days = Column(Integer, nullable=False, default=28)
    current_cycle_day = Column(Integer, nullable=True)
    current_phase = Column(String, nullable=True)
    last_period_start = Column(Date, nullable=True)
    tracking_source = Column(String, nullable=False, default="manual")
    notes = Column(Text, nullable=True)
    athlete = relationship("AthleteModel", back_populates="hormonal_profile")


class AllostaticEntryModel(Base):
    __tablename__ = "allostatic_entries"

    id = Column(String, primary_key=True)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=False)
    entry_date = Column(Date, nullable=False)
    allostatic_score = Column(Float, nullable=False)
    components_json = Column(Text, nullable=False, default="{}")
    intensity_cap_applied = Column(Float, nullable=False, default=1.0)
    athlete = relationship("AthleteModel", back_populates="allostatic_entries")
    __table_args__ = (UniqueConstraint("athlete_id", "entry_date"),)


class ExternalPlanModel(Base):
    __tablename__ = "external_plans"

    id = Column(String, primary_key=True)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=False)
    title = Column(String, nullable=False)
    source = Column(String, nullable=False)
    status = Column(String, nullable=False, default="active")
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))
    athlete = relationship("AthleteModel", back_populates="external_plans")
    sessions = relationship("ExternalSessionModel", back_populates="plan",
                            cascade="all, delete-orphan")


class ExternalSessionModel(Base):
    __tablename__ = "external_sessions"

    id = Column(String, primary_key=True)
    plan_id = Column(String, ForeignKey("external_plans.id"), nullable=False)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=False)
    session_date = Column(Date, nullable=False)
    sport = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    duration_min = Column(Integer, nullable=True)
    status = Column(String, nullable=False, default="planned")
    plan = relationship("ExternalPlanModel", back_populates="sessions")
    log = relationship("SessionLogModel", back_populates="external_session",
                       uselist=False, passive_deletes=True)


class HeadCoachMessageModel(Base):
    __tablename__ = "head_coach_messages"

    id = Column(String, primary_key=True)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=False)
    pattern_type = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))
    is_read = Column(Boolean, nullable=False, default=False)
    athlete = relationship("AthleteModel", back_populates="head_coach_messages")
```

- [ ] **Step 2: Replace models/schemas.py with re-export shim**

Overwrite `backend/app/models/schemas.py` with a thin re-export (backwards-compat for seed scripts and any remaining importers):

```python
"""Re-export shim — V3 SQLAlchemy models moved to app.db.models (2026-04-16).

Import from app.db.models directly. This module will be removed in a future cleanup.
"""
from app.db.models import (  # noqa: F401
    AllostaticEntryModel,
    EnergySnapshotModel,
    ExternalPlanModel,
    ExternalSessionModel,
    HeadCoachMessageModel,
    HormonalProfileModel,
)
```

- [ ] **Step 3: Update direct importers to use db.models**

Update these files to import from `app.db.models` instead of `app.models.schemas`:

`backend/app/core/energy_patterns.py` line 14:
```python
# Before:
from ..models.schemas import EnergySnapshotModel, HeadCoachMessageModel
# After:
from ..db.models import EnergySnapshotModel, HeadCoachMessageModel
```

`backend/app/services/energy_cycle_service.py` line 16:
```python
# Before:
from ..models.schemas import EnergySnapshotModel, HormonalProfileModel
# After:
from ..db.models import EnergySnapshotModel, HormonalProfileModel
```

`backend/app/services/external_plan_service.py` line 13:
```python
# Before:
from ..models.schemas import ExternalPlanModel, ExternalSessionModel
# After:
from ..db.models import ExternalPlanModel, ExternalSessionModel
```

`backend/app/services/plan_import_service.py` line 12:
```python
# Before:
from ..models.schemas import ExternalPlanModel
# After:
from ..db.models import ExternalPlanModel
```

- [ ] **Step 4: Run backend + e2e tests**

Run: `$VENV/pytest.exe tests/backend/ tests/e2e/ -x -q`
Expected: PASS — all models resolve, relationships intact

- [ ] **Step 5: Verify circular import resolved in mypy**

Run: `$VENV/python.exe -m mypy backend/app/db/models.py backend/app/models/schemas.py --strict 2>&1 | grep "import-not-found\|import-untyped\|misc"`
Expected: no `import-not-found` for those modules

- [ ] **Step 6: Commit**

```bash
git add backend/app/db/models.py backend/app/models/schemas.py \
    backend/app/core/energy_patterns.py backend/app/services/
git commit -m "refactor(db): consolidate V3 SQLAlchemy models into db/models.py — eliminate circular import"
```

---

## Task 4: SQLAlchemy Mapped[T] Migration — db/models.py

**Files:** `backend/app/db/models.py`

Migrate all 17 SQLAlchemy models (11 original + 6 V3 just added) from `Column()` style to `Mapped[T]` + `mapped_column()`. This resolves ~246 `[arg-type]` and `[assignment]` errors across all routes/services.

**Key import change at top of file:**
```python
# Before:
from sqlalchemy import BigInteger, Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

# After:
from __future__ import annotations
from typing import Optional
from sqlalchemy import BigInteger, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
```

Note: `Column` is no longer needed in the import — remove it. `from __future__ import annotations` enables string-based forward refs in type annotations.

- [ ] **Step 1: Migrate UserModel**

```python
class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True)
    hashed_password: Mapped[str] = mapped_column(String)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                  default=lambda: datetime.now(timezone.utc))

    athlete: Mapped[AthleteModel] = relationship("AthleteModel", back_populates="user")
    refresh_tokens: Mapped[list[RefreshTokenModel]] = relationship(
        "RefreshTokenModel", back_populates="user", cascade="all, delete-orphan")
    reset_tokens: Mapped[list[PasswordResetTokenModel]] = relationship(
        "PasswordResetTokenModel", back_populates="user", cascade="all, delete-orphan")
```

Run: `$VENV/pytest.exe tests/backend/ -x -q -k "auth or user"` → PASS

- [ ] **Step 2: Migrate RefreshTokenModel + PasswordResetTokenModel**

```python
class RefreshTokenModel(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                  default=lambda: datetime.now(timezone.utc))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped[UserModel] = relationship("UserModel", back_populates="refresh_tokens")


class PasswordResetTokenModel(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped[UserModel] = relationship("UserModel", back_populates="reset_tokens")
```

Run: `$VENV/pytest.exe tests/backend/ -x -q -k "auth or token"` → PASS

- [ ] **Step 3: Migrate AthleteModel**

```python
class AthleteModel(Base):
    __tablename__ = "athletes"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    age: Mapped[int] = mapped_column(Integer)
    sex: Mapped[str] = mapped_column(String)
    weight_kg: Mapped[float] = mapped_column(Float)
    height_cm: Mapped[float] = mapped_column(Float)
    primary_sport: Mapped[str] = mapped_column(String)
    target_race_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    hours_per_week: Mapped[float] = mapped_column(Float)
    sleep_hours_typical: Mapped[float] = mapped_column(Float, default=7.0)
    stress_level: Mapped[int] = mapped_column(Integer, default=5)
    job_physical: Mapped[bool] = mapped_column(Boolean, default=False)
    max_hr: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    resting_hr: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ftp_watts: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    vdot: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    css_per_100m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    coaching_mode: Mapped[str] = mapped_column(String, default="full")
    sports_json: Mapped[str] = mapped_column(Text)
    goals_json: Mapped[str] = mapped_column(Text)
    available_days_json: Mapped[str] = mapped_column(Text)
    equipment_json: Mapped[str] = mapped_column(Text, default="[]")

    user: Mapped[Optional[UserModel]] = relationship(
        "UserModel", back_populates="athlete", uselist=False, cascade="all, delete-orphan")
    plans: Mapped[list[TrainingPlanModel]] = relationship(
        "TrainingPlanModel", back_populates="athlete", cascade="all, delete-orphan")
    nutrition_plans: Mapped[list[NutritionPlanModel]] = relationship(
        "NutritionPlanModel", back_populates="athlete", cascade="all, delete-orphan")
    reviews: Mapped[list[WeeklyReviewModel]] = relationship(
        "WeeklyReviewModel", back_populates="athlete", cascade="all, delete-orphan")
    credentials: Mapped[list[ConnectorCredentialModel]] = relationship(
        "ConnectorCredentialModel", back_populates="athlete", cascade="all, delete-orphan")
    session_logs: Mapped[list[SessionLogModel]] = relationship(
        "SessionLogModel", back_populates="athlete", cascade="all, delete-orphan")
    energy_snapshots: Mapped[list[EnergySnapshotModel]] = relationship(
        "EnergySnapshotModel", back_populates="athlete", cascade="all, delete-orphan")
    hormonal_profile: Mapped[Optional[HormonalProfileModel]] = relationship(
        "HormonalProfileModel", back_populates="athlete", uselist=False,
        cascade="all, delete-orphan")
    allostatic_entries: Mapped[list[AllostaticEntryModel]] = relationship(
        "AllostaticEntryModel", back_populates="athlete", cascade="all, delete-orphan")
    external_plans: Mapped[list[ExternalPlanModel]] = relationship(
        "ExternalPlanModel", back_populates="athlete", cascade="all, delete-orphan")
    head_coach_messages: Mapped[list[HeadCoachMessageModel]] = relationship(
        "HeadCoachMessageModel", back_populates="athlete", cascade="all, delete-orphan")
```

Run: `$VENV/pytest.exe tests/backend/ -x -q -k "athlete"` → PASS

- [ ] **Step 4: Migrate TrainingPlanModel + NutritionPlanModel + WeeklyReviewModel**

```python
class TrainingPlanModel(Base):
    __tablename__ = "training_plans"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    phase: Mapped[str] = mapped_column(String)
    total_weekly_hours: Mapped[float] = mapped_column(Float)
    acwr: Mapped[float] = mapped_column(Float)
    weekly_slots_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                  default=lambda: datetime.now(timezone.utc))

    athlete: Mapped[AthleteModel] = relationship("AthleteModel", back_populates="plans")
    reviews: Mapped[list[WeeklyReviewModel]] = relationship(
        "WeeklyReviewModel", back_populates="plan")


class NutritionPlanModel(Base):
    __tablename__ = "nutrition_plans"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"))
    weight_kg: Mapped[float] = mapped_column(Float)
    targets_json: Mapped[str] = mapped_column(Text)

    athlete: Mapped[AthleteModel] = relationship("AthleteModel", back_populates="nutrition_plans")


class WeeklyReviewModel(Base):
    __tablename__ = "weekly_reviews"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"))
    plan_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("training_plans.id"),
                                                    nullable=True)
    week_start: Mapped[date] = mapped_column(Date)
    week_number: Mapped[int] = mapped_column(Integer, default=1)
    planned_hours: Mapped[float] = mapped_column(Float, default=0.0)
    actual_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    acwr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    adjustment_applied: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    readiness_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hrv_rmssd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sleep_hours_avg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    athlete_comment: Mapped[str] = mapped_column(Text, default="")
    results_json: Mapped[str] = mapped_column(Text, default="{}")

    athlete: Mapped[AthleteModel] = relationship("AthleteModel", back_populates="reviews")
    plan: Mapped[Optional[TrainingPlanModel]] = relationship(
        "TrainingPlanModel", back_populates="reviews")
```

Run: `$VENV/pytest.exe tests/backend/ -x -q -k "plan or review"` → PASS

- [ ] **Step 5: Migrate ConnectorCredentialModel + StravaActivityModel**

```python
class ConnectorCredentialModel(Base):
    __tablename__ = "connector_credentials"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"))
    provider: Mapped[str] = mapped_column(String)
    access_token_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refresh_token_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    extra_json: Mapped[str] = mapped_column(Text, default="{}")

    athlete: Mapped[AthleteModel] = relationship("AthleteModel", back_populates="credentials")
    __table_args__ = (UniqueConstraint("athlete_id", "provider"),)


class StravaActivityModel(Base):
    __tablename__ = "strava_activities"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id", ondelete="CASCADE"))
    strava_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    sport_type: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_s: Mapped[int] = mapped_column(Integer)
    distance_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    elevation_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_hr: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_hr: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    avg_watts: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    perceived_exertion: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    raw_json: Mapped[str] = mapped_column(Text, default="{}")
```

Run: `$VENV/pytest.exe tests/backend/ -x -q -k "strava or connector"` → PASS

- [ ] **Step 6: Migrate SessionLogModel + FoodCacheModel**

```python
class SessionLogModel(Base):
    __tablename__ = "session_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"))
    plan_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("training_plans.id"),
                                                    nullable=True)
    session_id: Mapped[str] = mapped_column(String, index=True)
    actual_duration_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    skipped: Mapped[bool] = mapped_column(Boolean, default=False)
    rpe: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    actual_data_json: Mapped[str] = mapped_column(Text, default="{}")
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                 default=lambda: datetime.now(timezone.utc))
    external_session_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("external_sessions.id", ondelete="SET NULL"), nullable=True)

    athlete: Mapped[AthleteModel] = relationship("AthleteModel", back_populates="session_logs")
    plan: Mapped[Optional[TrainingPlanModel]] = relationship("TrainingPlanModel")
    external_session: Mapped[Optional[ExternalSessionModel]] = relationship(
        "ExternalSessionModel", back_populates="log")

    __table_args__ = (UniqueConstraint("athlete_id", "session_id"),)


class FoodCacheModel(Base):
    __tablename__ = "food_cache"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    source: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    name_en: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    name_fr: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    calories_per_100g: Mapped[float] = mapped_column(Float)
    protein_g: Mapped[float] = mapped_column(Float)
    carbs_g: Mapped[float] = mapped_column(Float)
    fat_g: Mapped[float] = mapped_column(Float)
    fiber_g: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sodium_mg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sugar_g: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cached_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
```

- [ ] **Step 7: Migrate V3 models (EnergySnapshotModel through HeadCoachMessageModel)**

Same pattern. For EnergySnapshotModel:
```python
class EnergySnapshotModel(Base):
    __tablename__ = "energy_snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    allostatic_score: Mapped[float] = mapped_column(Float)
    cognitive_load: Mapped[float] = mapped_column(Float)
    energy_availability: Mapped[float] = mapped_column(Float)
    cycle_phase: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sleep_quality: Mapped[float] = mapped_column(Float)
    recommended_intensity_cap: Mapped[float] = mapped_column(Float)
    veto_triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    veto_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    objective_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    subjective_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    legs_feeling: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    stress_level: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                  default=lambda: datetime.now(timezone.utc))
    athlete: Mapped[AthleteModel] = relationship("AthleteModel", back_populates="energy_snapshots")
```

HormonalProfileModel:
```python
class HormonalProfileModel(Base):
    __tablename__ = "hormonal_profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    cycle_length_days: Mapped[int] = mapped_column(Integer, default=28)
    current_cycle_day: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    current_phase: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_period_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    tracking_source: Mapped[str] = mapped_column(String, default="manual")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    athlete: Mapped[AthleteModel] = relationship("AthleteModel", back_populates="hormonal_profile")
```

AllostaticEntryModel:
```python
class AllostaticEntryModel(Base):
    __tablename__ = "allostatic_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"))
    entry_date: Mapped[date] = mapped_column(Date)
    allostatic_score: Mapped[float] = mapped_column(Float)
    components_json: Mapped[str] = mapped_column(Text, default="{}")
    intensity_cap_applied: Mapped[float] = mapped_column(Float, default=1.0)
    athlete: Mapped[AthleteModel] = relationship("AthleteModel", back_populates="allostatic_entries")
    __table_args__ = (UniqueConstraint("athlete_id", "entry_date"),)
```

ExternalPlanModel:
```python
class ExternalPlanModel(Base):
    __tablename__ = "external_plans"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"))
    title: Mapped[str] = mapped_column(String)
    source: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="active")
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                  default=lambda: datetime.now(timezone.utc))
    athlete: Mapped[AthleteModel] = relationship("AthleteModel", back_populates="external_plans")
    sessions: Mapped[list[ExternalSessionModel]] = relationship(
        "ExternalSessionModel", back_populates="plan", cascade="all, delete-orphan")
```

ExternalSessionModel:
```python
class ExternalSessionModel(Base):
    __tablename__ = "external_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    plan_id: Mapped[str] = mapped_column(String, ForeignKey("external_plans.id"))
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"))
    session_date: Mapped[date] = mapped_column(Date)
    sport: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String, default="planned")
    plan: Mapped[ExternalPlanModel] = relationship("ExternalPlanModel", back_populates="sessions")
    log: Mapped[Optional[SessionLogModel]] = relationship(
        "SessionLogModel", back_populates="external_session", uselist=False, passive_deletes=True)
```

HeadCoachMessageModel:
```python
class HeadCoachMessageModel(Base):
    __tablename__ = "head_coach_messages"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"))
    pattern_type: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                  default=lambda: datetime.now(timezone.utc))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    athlete: Mapped[AthleteModel] = relationship("AthleteModel", back_populates="head_coach_messages")
```

- [ ] **Step 8: Run full backend tests**

Run: `$VENV/pytest.exe tests/backend/ tests/e2e/ -x -q`
Expected: PASS — all 17 models migrated, relationships resolve via string forward refs

- [ ] **Step 9: Verify mypy Column errors gone**

Run: `$VENV/python.exe -m mypy backend/app/db/models.py --strict 2>&1 | grep "error:" | wc -l`
Expected: 0 errors

- [ ] **Step 10: Commit**

```bash
git add backend/app/db/models.py backend/app/models/schemas.py
git commit -m "refactor(db): migrate all SQLAlchemy models to Mapped[T] + mapped_column() — SA 2.0 typing"
```

---

## Task 5: Fix type-arg, no-untyped-def, no-any-return — Core + Connectors

**Files:** `backend/app/core/hormonal.py`, `backend/app/core/analytics_logic.py`, `backend/app/core/running_logic.py`, `backend/app/core/lifting_logic.py`, `backend/app/core/nutrition_logic.py`, `backend/app/core/energy_patterns.py`, `backend/app/core/strain.py`, `backend/app/connectors/gpx.py`, `backend/app/connectors/fit.py`, `backend/app/connectors/apple_health.py`, `backend/app/connectors/hevy.py`, `backend/app/connectors/base.py`, `backend/app/integrations/hevy/importer.py`, `backend/app/integrations/hevy/csv_parser.py`, `backend/app/integrations/nutrition/usda_client.py`, `backend/app/observability/pii_filter.py`, `backend/app/agents/energy_coach/agent.py`

**Pattern for all `type-arg` fixes:**
- `dict` → `dict[str, Any]` (add `from typing import Any` at top if missing)
- `list` → `list[SpecificType]`
- `Pattern` → `Pattern[str]`
- `StateGraph` → `StateGraph[dict[str, Any]]`

- [ ] **Step 1: Fix core/hormonal.py (6 × dict type-arg)**

Read the file, add `from typing import Any` at the top, replace all bare `dict` with `dict[str, Any]` in function signatures and return types.

Run: `$VENV/python.exe -m mypy backend/app/core/hormonal.py --strict 2>&1 | grep "error:" | wc -l`
Expected: 0

- [ ] **Step 2: Fix core/analytics_logic.py (5 × type-arg + 2 × arg-type sort key)**

Add `from typing import Any`. Replace bare `dict` with `dict[str, Any]`.

For the sort key errors at lines 148-149 (key returns `object` instead of comparable):
```python
# Before (approximate):
items.sort(key=lambda x: x.get("some_field"))
# After:
items.sort(key=lambda x: x.get("some_field") or 0)
# or with explicit cast:
items.sort(key=lambda x: float(x.get("some_field", 0)))
```

Read the actual lines before fixing to ensure correct cast.

Run: `$VENV/python.exe -m mypy backend/app/core/analytics_logic.py --strict 2>&1 | grep "error:" | wc -l`
Expected: 0

- [ ] **Step 3: Fix core/running_logic.py (6 × type-arg + operator None/int)**

Add `from typing import Any`. Replace bare `dict`. For line 131 (`None / int` operator):
```python
# Read the line, then guard:
if value is None:
    return default_value
return value / divisor
```

Run: `$VENV/python.exe -m mypy backend/app/core/running_logic.py --strict 2>&1 | grep "error:" | wc -l`
Expected: 0

- [ ] **Step 4: Fix core/lifting_logic.py, core/nutrition_logic.py, core/energy_patterns.py, core/strain.py**

`lifting_logic.py`: `dict[str, Any]`, N806 variables `_TIER_NOTE`/`_Z` must be renamed to `_tier_note`/`_z` (lowercase).

`nutrition_logic.py`: `dict[str, Any]`.

`energy_patterns.py`: `list[...]` generics.

`strain.py` line 244: `Mapped[float]` column now returns `float` — the assignment `int_var = float_val` is a type mismatch. Fix: cast explicitly `int_var = int(float_val)` or change the variable type annotation.

Run: `$VENV/python.exe -m mypy backend/app/core/ --strict 2>&1 | grep "error:" | wc -l`
Expected: 0

- [ ] **Step 5: Fix connectors (gpx, fit, apple_health, hevy, base)**

`gpx.py`:
- N806: rename `R` constant → move it outside function (it's Earth radius = 6371.0, a module-level constant)
- `union-attr` line 53: guard `if value is None: continue` or `str(value)`
- `arg-type` line 47: `float(value) if value is not None else 0.0`

`fit.py`: `# type: ignore[import-untyped]  # fitparse has no stubs` already handled by mypy override in Task 2. Fix `dict` type-args.

`apple_health.py`, `connectors/hevy.py`: `dict[str, Any]`.

`connectors/base.py`: Add missing return type annotations to all public methods.

Run: `$VENV/python.exe -m mypy backend/app/connectors/ --strict 2>&1 | grep "error:" | wc -l`
Expected: 0

- [ ] **Step 6: Fix integrations (hevy, usda_client, pii_filter, energy_coach)**

`integrations/hevy/importer.py`, `integrations/hevy/csv_parser.py`: `dict[str, Any]`.

`integrations/nutrition/usda_client.py`: `dict[str, Any]`.

`observability/pii_filter.py`: `Pattern` → `Pattern[str]` (add `from re import Pattern`).

`agents/energy_coach/agent.py` line 159: `dict[str, Any]`. Line 264: remove `# type: ignore` that's now unused.

Run: `$VENV/python.exe -m mypy backend/app/integrations/ backend/app/observability/pii_filter.py backend/app/agents/energy_coach/ --strict 2>&1 | grep "error:" | wc -l`
Expected: 0

- [ ] **Step 7: Run backend tests**

Run: `$VENV/pytest.exe tests/backend/ -x -q`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add backend/app/core/ backend/app/connectors/ backend/app/integrations/ \
    backend/app/observability/pii_filter.py backend/app/agents/energy_coach/
git commit -m "fix(typing): add generic type params + fix connectors untyped defs + strain/analytics guards"
```

---

## Task 6: Fix Routes — Column→Mapped Cascade + Remaining arg-type

**Files:** `backend/app/routes/workflow.py`, `backend/app/routes/sessions.py`, `backend/app/routes/auth.py`, `backend/app/routes/athletes.py`, `backend/app/routes/connectors.py`, `backend/app/routes/checkin.py`, `backend/app/schemas/plan.py`, `backend/app/services/coaching_service.py`, `backend/app/services/connector_service.py`, `backend/app/services/sync_service.py`, `backend/app/jobs/registry.py`, `backend/app/integrations/strava/oauth_service.py`, `backend/app/integrations/nutrition/unified_service.py`, `backend/app/integrations/nutrition/fcen_loader.py`

**Context:** After the `Mapped[T]` migration in Task 4, `model.column_name` now returns the Python type directly (e.g., `str` not `Column[str]`). Most `[arg-type]` and `[assignment]` errors in routes/services should auto-resolve. Run mypy first to see what remains.

- [ ] **Step 1: Run mypy to check remaining route errors**

Run: `$VENV/python.exe -m mypy backend/app/routes/ backend/app/services/ backend/app/jobs/registry.py backend/app/integrations/strava/ backend/app/integrations/nutrition/ --strict 2>&1 | grep "error:" | head -40`

Catalogue remaining errors before fixing.

- [ ] **Step 2: Fix workflow.py**

The `WorkflowStatus` `phase` arg: `Literal['onboarding', 'no_plan', 'active', 'weekly_review_due']` — assign to typed variable before passing:
```python
plan_phase: Literal["onboarding", "no_plan", "active", "weekly_review_due"] = "active"
```
For `no-redef` at line 197 (`phase` already defined): rename second use to `plan_phase`.

For `dict` type-args: `dict[str, Any]`.

For json.loads after Mapped: `plan.weekly_slots_json` is now `str` — `json.loads(plan.weekly_slots_json)` works directly. Remove any `str()` casts if previously added.

- [ ] **Step 3: Fix routes/auth.py**

`dict[str, Any]` for bare dicts. SA Column errors should be gone post-Mapped migration.

- [ ] **Step 4: Fix routes/athletes.py + routes/connectors.py + routes/sessions.py + routes/checkin.py**

SA Column errors gone. Fix remaining `dict[str, Any]`.

- [ ] **Step 5: Fix schemas/plan.py (attr-defined)**

Lines 46-54 — object has no attribute `weekly_slots_json` etc. The function parameter is typed as `object` instead of `TrainingPlanModel`. Fix the function signature:
```python
from app.db.models import TrainingPlanModel

def plan_to_dict(plan: TrainingPlanModel) -> dict[str, Any]:
    ...
```

- [ ] **Step 6: Fix services/coaching_service.py**

Add return type annotations to the 4 untyped functions. N806: rename `TrainingPlanModel`/`WeeklyReviewModel` local vars to `training_plan_model`/`weekly_review_model` (they're used as local variable names shadowing the class — rename the import aliases).

For `no-any-return` at lines 126-127: the LangGraph checkpointer returns `Any` — cast:
```python
result: dict[str, Any] | None = dict(raw_result) if raw_result else None
return result
```

- [ ] **Step 7: Fix services/connector_service.py + sync_service.py + jobs/registry.py**

SA Column errors gone post-Mapped. For `jobs/registry.py` lines 63-64: `athlete.id` and `athlete.email` are now `str` — no cast needed.

- [ ] **Step 8: Fix integrations/strava/oauth_service.py + nutrition/unified_service.py + fcen_loader.py**

SA Column assignment errors gone post-Mapped. Verify with targeted mypy run.

- [ ] **Step 9: Fix graphs/weekly_review_graph.py**

`no-untyped-def` line 347: add return type annotation. `StateGraph` type-arg: `StateGraph[dict[str, Any]]`. N806: rename `SessionLogModel`/`TrainingPlanModel`/`WeeklyReviewModel` local vars.

- [ ] **Step 10: Fix main.py lifespan**

`no-untyped-def` for `lifespan`: add return type `AsyncIterator[None]`:
```python
from collections.abc import AsyncIterator

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    ...
```

- [ ] **Step 11: Run backend + e2e tests**

Run: `$VENV/pytest.exe tests/backend/ tests/e2e/ -x -q`
Expected: PASS

- [ ] **Step 12: Commit**

```bash
git add backend/app/routes/ backend/app/services/ backend/app/schemas/ \
    backend/app/jobs/registry.py backend/app/integrations/ backend/app/graphs/ backend/app/main.py
git commit -m "fix(typing): fix routes/services typing cascade — Column→Mapped resolution + untyped-def"
```

---

## Task 7: log_node Decorator Typing + graphs/nodes.py + union-attr Guards

**Files:** `backend/app/graphs/logging.py`, `backend/app/graphs/nodes.py`, `backend/app/graphs/coaching_graph.py`

- [ ] **Step 1: Type log_node with ParamSpec**

Rewrite `backend/app/graphs/logging.py`:

```python
"""Structured JSON logging decorator for LangGraph node functions."""
from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

logger = logging.getLogger("resilio.graph")

P = ParamSpec("P")
R = TypeVar("R", bound=dict[str, Any])


def log_node(func: Callable[P, R]) -> Callable[P, R]:
    """Decorator that logs entry/exit for a LangGraph node function."""
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        state: dict[str, Any] = args[0] if args else {}  # type: ignore[assignment]
        node = func.__name__
        athlete = state.get("athlete_id", "?")
        logger.info(json.dumps({"event": "node_enter", "node": node, "athlete_id": athlete}))
        t0 = time.perf_counter()
        result = func(*args, **kwargs)
        ms = round((time.perf_counter() - t0) * 1000)
        changed = list(result.keys()) if isinstance(result, dict) else []
        logger.info(json.dumps({
            "event": "node_exit", "node": node, "athlete_id": athlete,
            "duration_ms": ms, "keys_changed": changed,
        }))
        return result
    return wrapper  # type: ignore[return-value]  # ParamSpec wrapper typing limitation
```

- [ ] **Step 2: Fix graphs/nodes.py (19 × dict type-arg + 3 × union-attr + dict-item)**

For all bare `dict` return types → `dict[str, Any]`.

For union-attr at lines 381, 383, 391 (accessing `.get()` on `dict[str, Any] | None`):
```python
# Before:
value = some_dict.get("key")
# After:
if some_dict is None:
    return {}  # or raise, depending on context
value = some_dict.get("key")
```

For dict-item at line 402 (unpacking `dict[str, Any] | None`):
```python
# Before:
{**some_dict, "extra": 1}
# After:
{**(some_dict or {}), "extra": 1}
```

N806 line 288: `_EnergyCycleService` (imported inside function) → rename to `energy_cycle_service_cls`. Line 371: `TrainingPlanModel` local → `training_plan_model_cls`.

- [ ] **Step 3: Fix graphs/coaching_graph.py**

`no-untyped-def` at line 52: read the function, add proper signature. After log_node is typed, `no-untyped-call` errors for lines 63-73 should resolve.

- [ ] **Step 4: Run mypy on graphs only**

Run: `$VENV/python.exe -m mypy backend/app/graphs/ --strict 2>&1 | grep "error:" | wc -l`
Expected: 0

- [ ] **Step 5: Run backend tests**

Run: `$VENV/pytest.exe tests/backend/ tests/runtime/ -x -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/graphs/
git commit -m "fix(typing): type log_node with ParamSpec + fix nodes.py dict generics + union-attr guards"
```

---

## Task 8: Full mypy --strict Verification

- [ ] **Step 1: Run full mypy**

Run: `$VENV/python.exe -m mypy backend/app/ --strict 2>&1 | grep "^Found"`
Expected: `Found 0 errors in XX files`

If errors remain, fix them now — do not proceed to Task 9 until count = 0.

- [ ] **Step 2: Triage any remaining errors**

For each remaining error, apply the minimal fix:
- `[misc]` on SQLAlchemy `Base` subclass: `# type: ignore[misc]  # SQLAlchemy declarative Base — resolved at runtime`
- `[no-untyped-call]` from LangGraph internals: add `# type: ignore[no-untyped-call]  # LangGraph internal, no stubs`
- Any other: fix properly before adding ignore

- [ ] **Step 3: Run full test suite**

Run: `$VENV/pytest.exe tests/ -x -q`
Expected: ≥2378 passing, 0 new failures

- [ ] **Step 4: Commit any remaining fixes**

```bash
git add backend/app/
git commit -m "fix(typing): resolve remaining mypy --strict errors — 0 errors target reached"
```

---

## Task 9: Ruff Manual Fixes (E501, E402, N806)

**Files:** Multiple — see ruff output

- [ ] **Step 1: Fix N806 — uppercase vars in functions**

Files: `agents/biking_coach.py`, `agents/lifting_coach.py`, `agents/running_coach.py`, `agents/swimming_coach.py`, `connectors/gpx.py`, `core/lifting_logic.py`, `core/running_logic.py`, `graphs/nodes.py`, `graphs/weekly_review_graph.py`, `services/coaching_service.py`

Pattern: `_INTENSITY` → `_intensity`, `_LIFT_INTENSITY` → `_lift_intensity`, `R` → `r` (in gpx function), `_TIER_NOTE` → `_tier_note`, `_Z` → `_z`, `_EnergyCycleService` → `energy_cycle_service_cls`, `TrainingPlanModel`/etc. local imports → rename to `_model_cls` suffix.

- [ ] **Step 2: Fix E402 — imports not at top**

`main.py` lines 5-18: The first two lines (configure_logging + init_sentry) MUST precede other imports (documented in comment). Mark as structural noqa:
```python
# Observability MUST be configured before anything else imports logging
from .observability.logging_config import configure_logging as _configure_logging  # noqa: E402
_configure_logging()
from .observability.sentry import init_sentry as _init_sentry  # noqa: E402
_init_sentry()

import os  # noqa: E402
...
```

Alternatively, restructure: put the `_configure_logging()` + `_init_sentry()` calls in a module-level `__init__` function that runs immediately, and move actual imports to top. Simpler: keep `# noqa: E402` on the structural lines with an explanatory comment.

`observability/metrics.py` lines 111-113: Check why imports are mid-file — likely a circular import avoidance. Add `# noqa: E402  # Deferred import: avoids circular dependency`.

`observability/pii_filter.py` line 56`: Same pattern — add `# noqa: E402`.

`routes/admin.py` line 92`: Same — add `# noqa: E402`.

- [ ] **Step 3: Fix E501 — line too long**

Run: `$VENV/python.exe -m ruff check backend/app/ 2>&1 | grep "E501"`

For each violation:
- Long strings in `agents/prompts.py`: use implicit concatenation `"part1" "part2"` or `textwrap.dedent`
- Long function signatures: break onto multiple lines with trailing comma
- Long comments: wrap at 99 chars
- Long import lines: use parentheses

- [ ] **Step 4: Verify ruff clean**

Run: `$VENV/python.exe -m ruff check backend/app/ 2>&1 | grep "Found"`
Expected: `Found 0 errors.`

Run: `$VENV/python.exe -m ruff format --check backend/app/ 2>&1`
Expected: clean

- [ ] **Step 5: Run backend tests**

Run: `$VENV/pytest.exe tests/backend/ -x -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/
git commit -m "chore(lint): fix E501 E402 N806 — ruff 0 errors"
```

---

## Task 10: Update pyproject.toml + Pre-Commit Hook

**Files:** `pyproject.toml`, `.pre-commit-config.yaml`

- [ ] **Step 1: Update pyproject.toml tool configs**

Ensure `[tool.mypy]` is:
```toml
[tool.mypy]
python_version = "3.13"
strict = true
warn_return_any = true
warn_unused_configs = true

[[tool.mypy.overrides]]
module = [
    "apscheduler",
    "apscheduler.*",
    "sentry_sdk",
    "sentry_sdk.*",
    "fitparse",
    "fitparse.*",
]
ignore_missing_imports = true
```

Ensure `[tool.ruff]` is:
```toml
[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]
```

Note: rename `select` from top-level `[tool.ruff]` to `[tool.ruff.lint]` (ruff 0.1.x format).

- [ ] **Step 2: Install pre-commit**

Run: `$VENV/pip.exe install pre-commit`

Verify: `$VENV/pre-commit.exe --version`

- [ ] **Step 3: Create .pre-commit-config.yaml**

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.15
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.0
    hooks:
      - id: mypy
        args: [--strict, --config-file=pyproject.toml]
        additional_dependencies:
          - pydantic>=2.0
          - sqlalchemy>=2.0
          - types-passlib
          - fastapi
```

- [ ] **Step 4: Install pre-commit hooks**

Run: `$VENV/pre-commit.exe install`
Expected: `pre-commit installed at .git/hooks/pre-commit`

- [ ] **Step 5: Run pre-commit on all files**

Run: `$VENV/pre-commit.exe run --all-files 2>&1 | tail -20`
Expected: all hooks pass

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .pre-commit-config.yaml
git commit -m "chore(ci): lock mypy --strict + ruff in pyproject.toml + add pre-commit hooks"
```

---

## Task 11: TYPING-CONVENTIONS.md

**Files:** `docs/backend/TYPING-CONVENTIONS.md`

- [ ] **Step 1: Write conventions doc**

```markdown
# Typing Conventions — Resilio Plus Backend

**Date:** 2026-04-16 | **mypy version:** 1.19.1 | **Python:** 3.13

## 1. SQLAlchemy Models

Use SA 2.0 `Mapped[T]` + `mapped_column()` exclusively. Never use the legacy `Column()` style.

```python
# ✅ Correct
class Athlete(Base):
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                  default=lambda: datetime.now(timezone.utc))
    plans: Mapped[list[TrainingPlanModel]] = relationship("TrainingPlanModel")

# ❌ Never
class Athlete(Base):
    id = Column(String, primary_key=True)
```

Use string-based forward refs in `relationship("ClassName")` — never import a model class for typing relationships (causes circular imports).

Add `from __future__ import annotations` at the top of `db/models.py` to enable PEP 563 deferred evaluation.

## 2. Pydantic Models

Use Pydantic V2 `model_config = ConfigDict(...)` exclusively. Never use `class Config:`.

```python
from pydantic import BaseModel, ConfigDict

class MySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    value: float
```

## 3. Dict and List Generics

Never use bare `dict` or `list` — always parameterize:

```python
from typing import Any
# ✅ 
def parse(data: dict[str, Any]) -> list[str]: ...
# ❌ 
def parse(data: dict) -> list: ...
```

## 4. Third-Party Libs Without Stubs

Add to `[[tool.mypy.overrides]]` in `pyproject.toml`, not inline `# type: ignore` per-call:
```toml
[[tool.mypy.overrides]]
module = ["apscheduler.*", "sentry_sdk.*", "fitparse.*"]
ignore_missing_imports = true
```

For `jose` and `passlib` (no stub package): `# type: ignore[import-untyped]` on the import line only.

## 5. type: ignore Usage Rules

- **Never** use bare `# type: ignore` — always `# type: ignore[specific-code]`
- **Always** add a justifying comment: `# SQLAlchemy declarative Base` / `# LangGraph internal` / etc.
- Permitted cases:
  - `[import-untyped]` on specific import lines for known stub-less libs
  - `[misc]` on SQLAlchemy `Base` subclass declarations
  - `[return-value]` on ParamSpec decorator wrappers (Python typing limitation)

## 6. FastAPI Route Handlers

Use `Annotated` for dependency injection:
```python
from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import Session

DbSession = Annotated[Session, Depends(get_db)]

@router.get("/athletes")
def list_athletes(db: DbSession) -> list[AthleteResponse]:
    ...
```

## 7. Enforcement

```bash
# Check
python -m mypy backend/app/ --strict
python -m ruff check backend/app/
python -m ruff format --check backend/app/

# Fix
python -m ruff check --fix backend/app/
python -m ruff format backend/app/
```

Pre-commit hook runs these automatically on every `git commit`.
```

- [ ] **Step 2: Commit**

```bash
git add docs/backend/TYPING-CONVENTIONS.md
git commit -m "docs(typing): add TYPING-CONVENTIONS.md — Mapped[T], Pydantic V2, type: ignore rules"
```

---

## Task 12: Final Verification

- [ ] **Step 1: Full mypy --strict**

Run: `$VENV/python.exe -m mypy backend/app/ --strict 2>&1 | grep "^Found"`
Expected: `Found 0 errors in XX files (checked 131 source files)`

- [ ] **Step 2: Full ruff**

Run: `$VENV/python.exe -m ruff check backend/app/ && $VENV/python.exe -m ruff format --check backend/app/`
Expected: no output (clean)

- [ ] **Step 3: Full test suite**

Run: `$VENV/pytest.exe tests/ -q 2>&1 | tail -5`
Expected: ≥2378 passed, 0 new failures

- [ ] **Step 4: Pre-commit dry-run**

Run: `$VENV/pre-commit.exe run --all-files 2>&1 | grep -E "Passed|Failed|Error"`
Expected: all `Passed`

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "chore(debt): tech debt sprint complete — mypy --strict 0 errors, ruff clean, pre-commit active"
```
