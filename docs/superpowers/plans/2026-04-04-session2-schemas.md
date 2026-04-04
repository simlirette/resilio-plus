# Session 2 — Schémas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Créer la couche Pydantic de validation de l'AthleteState, implémenter `get_agent_view()` pour le token economy multi-agents, et générer la première migration Alembic.

**Architecture:** `models/schemas.py` contient ~15 sub-models Pydantic v2 reflétant exactement la structure JSON §2.1 du master doc. `models/views.py` implémente `get_agent_view(state, agent)` via une `AGENT_VIEW_MAP` — une fonction de projection par agent, retournant un `dict` consommable par LangGraph. La migration Alembic est générée depuis les SQLAlchemy models existants dans `models/database.py`.

**Tech Stack:** Pydantic v2 (`BaseModel`, `ConfigDict`, `Literal`), Python 3.12, pytest, Alembic + asyncpg, PostgreSQL (Docker)

---

## Contexte pour l'implémenteur

### Repo : `C:\resilio-plus`

**Fichiers existants pertinents :**
- `models/database.py` — 8 tables SQLAlchemy complètes (Athlete, AthleteState, FatigueSnapshot, LiftingSession, LiftingSet, RunActivity, WeeklyPlan, DecisionLog). Ne pas modifier.
- `tests/conftest.py` — Fixtures Simon avec constantes modules-level `SIMON_PROFILE_DATA`, `SIMON_AVAILABLE_DAYS`, `SIMON_RUNNING_PROFILE`, `SIMON_LIFTING_PROFILE`, `SIMON_NUTRITION_PROFILE`, `SIMON_ID`. Ne pas modifier.
- `alembic/env.py` + `alembic.ini` — Alembic configuré async, lit `settings.DATABASE_URL`.
- `alembic/versions/.gitkeep` — À supprimer après la migration.
- `core/config.py` — `settings.DATABASE_URL = "postgresql+asyncpg://resilio:resilio@localhost:5432/resilio_db"`
- `docker-compose.yml` — PostgreSQL sur port 5432, user/pass/db = resilio.

**Tests existants qui doivent continuer à passer :**
```bash
poetry run pytest tests/test_config.py tests/test_exercise_database.py -v
# → 12 passed
```

**Commandes de base :**
```bash
poetry run pytest tests/ -v          # lancer les tests
poetry run ruff check .              # linter
```

---

## Task 1 : `models/schemas.py` — Pydantic sub-models (TDD)

**Files:**
- Create: `tests/test_schemas.py`
- Create: `models/schemas.py`

- [ ] **Step 1 : Écrire `tests/test_schemas.py`**

```python
"""
TEST SCHEMAS — Validation des Pydantic models AthleteState.
Tests sans DB — pas de fixtures async, pas de PostgreSQL requis.
"""
import json
from datetime import date, datetime
from uuid import UUID

import pytest

from models.schemas import (
    ACWRBySport,
    AthleteProfile,
    AthleteStateSchema,
    BikingProfile,
    Compliance,
    CurrentPhase,
    DayAvailability,
    Equipment,
    FatigueState,
    Goals,
    Injury,
    Lifestyle,
    LiftingProfile,
    MacrosTarget,
    NutritionProfile,
    RunningProfile,
    SwimmingProfile,
    TrainingHistory,
    TrainingPaces,
    VolumeLandmarks,
    WeeklyVolumes,
)

SIMON_ID = UUID("00000000-0000-0000-0000-000000000001")


def _make_simon_state() -> AthleteStateSchema:
    """Construit l'AthleteStateSchema complet de Simon pour les tests."""
    return AthleteStateSchema(
        athlete_id=SIMON_ID,
        updated_at=datetime(2026, 4, 4, 10, 0, 0),
        profile=AthleteProfile(
            first_name="Simon",
            age=32,
            sex="M",
            weight_kg=78.5,
            height_cm=178,
            body_fat_percent=16.5,
            resting_hr=58,
            max_hr_measured=188,
            training_history=TrainingHistory(
                total_years_training=5,
                years_running=2,
                years_lifting=4,
                years_swimming=0.5,
                current_weekly_volume_hours=7,
                longest_run_ever_km=15,
                current_5k_time_min=28.5,
                estimated_1rm={
                    "squat": 120,
                    "bench_press": 85,
                    "deadlift": 140,
                    "overhead_press": 55,
                },
            ),
            injuries_history=[
                Injury(
                    type="shin_splints",
                    year=2024,
                    duration_weeks=6,
                    side="bilateral",
                    recurrent=False,
                    notes="Augmentation trop rapide du volume de course",
                )
            ],
            lifestyle=Lifestyle(
                work_type="desk_sedentary",
                work_hours_per_day=8,
                commute_active=False,
                sleep_avg_hours=7.2,
                stress_level="moderate",
                alcohol_per_week=2,
                smoking=False,
            ),
            goals=Goals(
                primary="run_sub_25_5k",
                secondary="maintain_muscle_mass",
                tertiary="improve_swimming_technique",
                timeline_weeks=16,
                priority_hierarchy=[
                    "running_5k",
                    "hypertrophy_maintenance",
                    "swimming_technique",
                ],
            ),
            equipment=Equipment(
                gym_access=True,
                gym_equipment=["barbell", "dumbbells", "cables", "machines", "pull_up_bar"],
                pool_access=True,
                pool_type="25m_indoor",
                outdoor_running=True,
                heart_rate_monitor=True,
                gps_watch="garmin_forerunner_265",
            ),
            active_sports=["running", "lifting"],
            available_days={
                "monday": DayAvailability(available=True, max_hours=1.5, preferred_time="morning"),
                "tuesday": DayAvailability(available=True, max_hours=1.5, preferred_time="evening"),
                "wednesday": DayAvailability(available=True, max_hours=1.0, preferred_time="morning"),
                "thursday": DayAvailability(available=True, max_hours=1.5, preferred_time="evening"),
                "friday": DayAvailability(available=False, max_hours=0, preferred_time=None),
                "saturday": DayAvailability(available=True, max_hours=2.5, preferred_time="morning"),
                "sunday": DayAvailability(available=True, max_hours=2.0, preferred_time="morning"),
            },
        ),
        current_phase=CurrentPhase(
            macrocycle="base_building",
            mesocycle_week=3,
            mesocycle_length=4,
            target_event="local_5k_race",
            target_event_date=date(2026, 7, 15),
        ),
        running_profile=RunningProfile(
            vdot=38.2,
            training_paces=TrainingPaces(
                easy_min_per_km="6:24",
                easy_max_per_km="7:06",
                marathon_pace_per_km="5:42",
                threshold_pace_per_km="5:18",
                interval_pace_per_km="4:48",
                repetition_pace_per_km="4:24",
                long_run_pace_per_km="6:36",
            ),
            weekly_km_current=22,
            weekly_km_target=35,
            max_long_run_km=12,
            cadence_avg=168,
            preferred_terrain="road",
        ),
        lifting_profile=LiftingProfile(
            training_split="upper_lower",
            sessions_per_week=3,
            current_volume_per_muscle={
                "quadriceps": 8,
                "hamstrings": 6,
                "chest": 10,
                "back": 12,
                "shoulders": 8,
                "biceps": 6,
                "triceps": 6,
                "calves": 4,
            },
            volume_landmarks={
                "quadriceps": VolumeLandmarks(mev=6, mav=10, mrv_hybrid=12),
                "hamstrings": VolumeLandmarks(mev=4, mav=8, mrv_hybrid=10),
                "chest": VolumeLandmarks(mev=6, mav=14, mrv_hybrid=18),
                "back": VolumeLandmarks(mev=6, mav=14, mrv_hybrid=20),
                "shoulders": VolumeLandmarks(mev=6, mav=12, mrv_hybrid=16),
                "biceps": VolumeLandmarks(mev=4, mav=10, mrv_hybrid=14),
                "triceps": VolumeLandmarks(mev=4, mav=8, mrv_hybrid=12),
                "calves": VolumeLandmarks(mev=4, mav=8, mrv_hybrid=6),
            },
            progression_model="double_progression",
            rir_target_range=[1, 3],
        ),
        nutrition_profile=NutritionProfile(
            tdee_estimated=2800,
            macros_target=MacrosTarget(protein_g=160, carbs_g=300, fat_g=80),
            supplements_current=["creatine_5g"],
        ),
        fatigue=FatigueState(
            acwr=1.05,
            acwr_trend="stable",
            acwr_by_sport=ACWRBySport(running=1.08, lifting=1.02),
            weekly_fatigue_score=320,
            fatigue_by_muscle={
                "quadriceps": 65,
                "hamstrings": 50,
                "chest": 30,
                "back": 35,
                "shoulders": 25,
                "calves": 40,
            },
            cns_load_7day_avg=45,
            recovery_score_today=72,
            hrv_rmssd_today=58,
            hrv_rmssd_baseline=62,
            sleep_hours_last_night=7.1,
            sleep_quality_subjective=7,
            fatigue_subjective=3,
        ),
        compliance=Compliance(
            last_4_weeks_completion_rate=0.88,
            nutrition_adherence_7day=0.75,
        ),
        weekly_volumes=WeeklyVolumes(
            running_km=22,
            lifting_sessions=3,
            total_training_hours=6.5,
        ),
    )


def test_simon_state_constructs():
    state = _make_simon_state()
    assert state.profile.first_name == "Simon"
    assert state.profile.sex == "M"
    assert state.profile.age == 32
    assert state.running_profile.vdot == 38.2
    assert state.lifting_profile.sessions_per_week == 3
    assert state.athlete_id == SIMON_ID


def test_optional_sport_profiles_default_empty():
    state = _make_simon_state()
    assert state.biking_profile.ftp_watts is None
    assert state.biking_profile.weekly_volume_km == 0.0
    assert state.swimming_profile.weekly_volume_km == 0.0
    assert state.swimming_profile.reference_times == {}


def test_sex_literal_rejects_invalid_value():
    with pytest.raises(Exception):
        AthleteProfile(
            first_name="Test",
            age=30,
            sex="X",  # invalid — doit lever une exception
            weight_kg=70,
            height_cm=175,
            training_history=TrainingHistory(
                total_years_training=1,
                years_running=1,
                years_lifting=1,
                years_swimming=0,
                current_weekly_volume_hours=3,
            ),
            lifestyle=Lifestyle(
                work_type="desk_sedentary",
                work_hours_per_day=8,
                commute_active=False,
                sleep_avg_hours=7,
                stress_level="low",
            ),
            goals=Goals(primary="test", timeline_weeks=4),
            equipment=Equipment(gym_access=False),
        )


def test_jsonb_roundtrip():
    """Simule le cycle JSONB : model_dump → JSON string → model_validate."""
    state = _make_simon_state()
    dumped = json.dumps(state.model_dump(mode="json"))
    restored = AthleteStateSchema.model_validate(json.loads(dumped))
    assert restored.athlete_id == state.athlete_id
    assert restored.profile.first_name == state.profile.first_name
    assert restored.running_profile.vdot == state.running_profile.vdot
    assert restored.lifting_profile.volume_landmarks["quadriceps"].mev == 6
    assert restored.fatigue.acwr_by_sport.running == 1.08


def test_volume_landmarks_coercion_from_raw_dict():
    """volume_landmarks peut être peuplé depuis des dicts bruts (comme depuis JSONB PostgreSQL)."""
    profile = LiftingProfile(
        training_split="upper_lower",
        sessions_per_week=3,
        volume_landmarks={
            "chest": {"mev": 6, "mav": 14, "mrv_hybrid": 18}
        },
    )
    assert profile.volume_landmarks["chest"].mev == 6
    assert profile.volume_landmarks["chest"].mrv_hybrid == 18


def test_available_days_coercion_from_raw_dict():
    """available_days peut être peuplé depuis des dicts bruts (comme depuis JSONB PostgreSQL)."""
    state = AthleteStateSchema.model_validate({
        "athlete_id": str(SIMON_ID),
        "updated_at": "2026-04-04T10:00:00",
        "profile": {
            "first_name": "Simon",
            "age": 32,
            "sex": "M",
            "weight_kg": 78.5,
            "height_cm": 178,
            "training_history": {
                "total_years_training": 5,
                "years_running": 2,
                "years_lifting": 4,
                "years_swimming": 0.5,
                "current_weekly_volume_hours": 7,
            },
            "lifestyle": {
                "work_type": "desk_sedentary",
                "work_hours_per_day": 8,
                "commute_active": False,
                "sleep_avg_hours": 7.2,
                "stress_level": "moderate",
            },
            "goals": {"primary": "run_sub_25_5k", "timeline_weeks": 16},
            "equipment": {"gym_access": True},
            "available_days": {
                "monday": {"available": True, "max_hours": 1.5, "preferred_time": "morning"},
                "friday": {"available": False, "max_hours": 0, "preferred_time": None},
            },
        },
        "current_phase": {"macrocycle": "base_building", "mesocycle_week": 3},
        "running_profile": {
            "vdot": 38.2,
            "training_paces": {
                "easy_min_per_km": "6:24",
                "easy_max_per_km": "7:06",
                "threshold_pace_per_km": "5:18",
                "interval_pace_per_km": "4:48",
                "repetition_pace_per_km": "4:24",
                "long_run_pace_per_km": "6:36",
            },
            "weekly_km_current": 22,
            "weekly_km_target": 35,
            "max_long_run_km": 12,
        },
        "lifting_profile": {
            "training_split": "upper_lower",
            "sessions_per_week": 3,
        },
        "nutrition_profile": {
            "tdee_estimated": 2800,
            "macros_target": {"protein_g": 160, "carbs_g": 300, "fat_g": 80},
        },
    })
    assert state.profile.available_days["monday"].available is True
    assert state.profile.available_days["monday"].max_hours == 1.5
    assert state.profile.available_days["friday"].available is False
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
poetry run pytest tests/test_schemas.py -v
```

Expected: `ImportError: cannot import name 'AthleteStateSchema' from 'models.schemas'` (le fichier n'existe pas)

- [ ] **Step 3 : Créer `models/schemas.py`**

```python
"""
SCHEMAS PYDANTIC — Resilio+
Couche de validation au-dessus des SQLAlchemy models.
Utilisé pour valider les données JSONB et filtrer l'AthleteState par agent via get_agent_view().
"""
from __future__ import annotations

import uuid
from datetime import datetime, date
from typing import Literal

from pydantic import BaseModel, ConfigDict


class TrainingHistory(BaseModel):
    total_years_training: float
    years_running: float
    years_lifting: float
    years_swimming: float
    current_weekly_volume_hours: float
    longest_run_ever_km: float | None = None
    current_5k_time_min: float | None = None
    current_10k_time_min: float | None = None
    current_half_marathon_min: float | None = None
    estimated_1rm: dict[str, float] = {}


class Injury(BaseModel):
    type: str
    year: int
    duration_weeks: int
    side: str | None = None
    recurrent: bool = False
    notes: str | None = None


class Lifestyle(BaseModel):
    work_type: str
    work_hours_per_day: float
    commute_active: bool
    sleep_avg_hours: float
    stress_level: str
    alcohol_per_week: int = 0
    smoking: bool = False


class Goals(BaseModel):
    primary: str
    secondary: str | None = None
    tertiary: str | None = None
    timeline_weeks: int
    priority_hierarchy: list[str] = []


class Equipment(BaseModel):
    gym_access: bool
    gym_equipment: list[str] = []
    pool_access: bool = False
    pool_type: str | None = None
    outdoor_running: bool = True
    treadmill: bool = False
    heart_rate_monitor: bool = False
    gps_watch: str | None = None
    power_meter_bike: bool = False


class DayAvailability(BaseModel):
    available: bool
    max_hours: float
    preferred_time: str | None = None


class AthleteProfile(BaseModel):
    first_name: str
    age: int
    sex: Literal["M", "F"]
    weight_kg: float
    height_cm: float
    body_fat_percent: float | None = None
    resting_hr: int | None = None
    max_hr_measured: int | None = None
    max_hr_formula: int | None = None
    training_history: TrainingHistory
    injuries_history: list[Injury] = []
    lifestyle: Lifestyle
    goals: Goals
    equipment: Equipment
    active_sports: list[str] = []
    available_days: dict[str, DayAvailability] = {}


class CurrentPhase(BaseModel):
    macrocycle: str
    mesocycle_week: int
    mesocycle_length: int = 4
    next_deload: str | None = None
    target_event: str | None = None
    target_event_date: date | None = None


class TrainingPaces(BaseModel):
    easy_min_per_km: str
    easy_max_per_km: str
    marathon_pace_per_km: str | None = None
    threshold_pace_per_km: str
    interval_pace_per_km: str
    repetition_pace_per_km: str
    long_run_pace_per_km: str


class RunningProfile(BaseModel):
    vdot: float
    training_paces: TrainingPaces
    weekly_km_current: float
    weekly_km_target: float
    max_long_run_km: float
    cadence_avg: int | None = None
    preferred_terrain: str = "road"


class VolumeLandmarks(BaseModel):
    mev: int
    mav: int
    mrv_hybrid: int


class LiftingProfile(BaseModel):
    training_split: str
    sessions_per_week: int
    current_volume_per_muscle: dict[str, int] = {}
    volume_landmarks: dict[str, VolumeLandmarks] = {}
    progression_model: str = "double_progression"
    rir_target_range: list[int] = [1, 3]


class SwimmingProfile(BaseModel):
    reference_times: dict[str, float] = {}
    technique_level: str = "beginner"
    weekly_volume_km: float = 0.0


class BikingProfile(BaseModel):
    ftp_watts: float | None = None
    weekly_volume_km: float = 0.0


class MacrosTarget(BaseModel):
    protein_g: float
    carbs_g: float
    fat_g: float


class NutritionProfile(BaseModel):
    tdee_estimated: float
    macros_target: MacrosTarget
    supplements_current: list[str] = []
    dietary_restrictions: list[str] = []
    allergies: list[str] = []


class ACWRBySport(BaseModel):
    running: float | None = None
    lifting: float | None = None
    biking: float | None = None
    swimming: float | None = None


class FatigueState(BaseModel):
    acwr: float | None = None
    acwr_trend: str | None = None
    acwr_by_sport: ACWRBySport = ACWRBySport()
    weekly_fatigue_score: float | None = None
    fatigue_by_muscle: dict[str, float] = {}
    cns_load_7day_avg: float | None = None
    recovery_score_today: float | None = None
    hrv_rmssd_today: float | None = None
    hrv_rmssd_baseline: float | None = None
    sleep_hours_last_night: float | None = None
    sleep_quality_subjective: int | None = None
    fatigue_subjective: int | None = None


class Compliance(BaseModel):
    last_4_weeks_completion_rate: float | None = None
    missed_sessions_this_week: list[str] = []
    nutrition_adherence_7day: float | None = None


class WeeklyVolumes(BaseModel):
    running_km: float = 0.0
    lifting_sessions: int = 0
    swimming_km: float = 0.0
    biking_km: float = 0.0
    total_training_hours: float = 0.0


class AthleteStateSchema(BaseModel):
    model_config = ConfigDict(strict=False)

    athlete_id: uuid.UUID
    updated_at: datetime
    profile: AthleteProfile
    current_phase: CurrentPhase
    running_profile: RunningProfile
    lifting_profile: LiftingProfile
    swimming_profile: SwimmingProfile = SwimmingProfile()
    biking_profile: BikingProfile = BikingProfile()
    nutrition_profile: NutritionProfile
    fatigue: FatigueState = FatigueState()
    compliance: Compliance = Compliance()
    weekly_volumes: WeeklyVolumes = WeeklyVolumes()
```

- [ ] **Step 4 : Vérifier que les tests passent**

```bash
poetry run pytest tests/test_schemas.py -v
```

Expected:
```
tests/test_schemas.py::test_simon_state_constructs PASSED
tests/test_schemas.py::test_optional_sport_profiles_default_empty PASSED
tests/test_schemas.py::test_sex_literal_rejects_invalid_value PASSED
tests/test_schemas.py::test_jsonb_roundtrip PASSED
tests/test_schemas.py::test_volume_landmarks_coercion_from_raw_dict PASSED
tests/test_schemas.py::test_available_days_coercion_from_raw_dict PASSED
6 passed
```

- [ ] **Step 5 : Vérifier que les tests S1 passent toujours**

```bash
poetry run pytest tests/ -v
```

Expected: 18 passed (12 S1 + 6 nouveaux)

- [ ] **Step 6 : Commit**

```bash
git add models/schemas.py tests/test_schemas.py
git commit -m "feat: add AthleteState Pydantic schemas with JSONB coercion (TDD)"
```

---

## Task 2 : `models/views.py` — `get_agent_view()` (TDD)

**Files:**
- Create: `tests/test_views.py`
- Create: `models/views.py`

- [ ] **Step 1 : Écrire `tests/test_views.py`**

```python
"""
TEST VIEWS — Validation du filtrage AthleteState par agent.
Tests sans DB — pas de fixtures async requis.
"""
from datetime import datetime
from uuid import UUID

from models.schemas import (
    ACWRBySport,
    AthleteProfile,
    AthleteStateSchema,
    BikingProfile,
    Compliance,
    CurrentPhase,
    DayAvailability,
    Equipment,
    FatigueState,
    Goals,
    Injury,
    LiftingProfile,
    Lifestyle,
    MacrosTarget,
    NutritionProfile,
    RunningProfile,
    SwimmingProfile,
    TrainingHistory,
    TrainingPaces,
    WeeklyVolumes,
)
from models.views import AgentType, get_agent_view

SIMON_ID = UUID("00000000-0000-0000-0000-000000000001")


def _make_state() -> AthleteStateSchema:
    """State Simon minimal pour les tests de vues."""
    return AthleteStateSchema(
        athlete_id=SIMON_ID,
        updated_at=datetime(2026, 4, 4, 10, 0, 0),
        profile=AthleteProfile(
            first_name="Simon",
            age=32,
            sex="M",
            weight_kg=78.5,
            height_cm=178,
            training_history=TrainingHistory(
                total_years_training=5,
                years_running=2,
                years_lifting=4,
                years_swimming=0.5,
                current_weekly_volume_hours=7,
            ),
            injuries_history=[
                Injury(type="shin_splints", year=2024, duration_weeks=6, recurrent=False)
            ],
            lifestyle=Lifestyle(
                work_type="desk_sedentary",
                work_hours_per_day=8,
                commute_active=False,
                sleep_avg_hours=7.2,
                stress_level="moderate",
            ),
            goals=Goals(primary="run_sub_25_5k", timeline_weeks=16),
            equipment=Equipment(gym_access=True),
            active_sports=["running", "lifting"],
            available_days={
                "monday": DayAvailability(available=True, max_hours=1.5, preferred_time="morning"),
            },
        ),
        current_phase=CurrentPhase(macrocycle="base_building", mesocycle_week=3),
        running_profile=RunningProfile(
            vdot=38.2,
            training_paces=TrainingPaces(
                easy_min_per_km="6:24",
                easy_max_per_km="7:06",
                threshold_pace_per_km="5:18",
                interval_pace_per_km="4:48",
                repetition_pace_per_km="4:24",
                long_run_pace_per_km="6:36",
            ),
            weekly_km_current=22,
            weekly_km_target=35,
            max_long_run_km=12,
        ),
        lifting_profile=LiftingProfile(training_split="upper_lower", sessions_per_week=3),
        nutrition_profile=NutritionProfile(
            tdee_estimated=2800,
            macros_target=MacrosTarget(protein_g=160, carbs_g=300, fat_g=80),
        ),
        fatigue=FatigueState(
            acwr=1.05,
            acwr_by_sport=ACWRBySport(running=1.08, lifting=1.02),
            fatigue_by_muscle={"quadriceps": 65, "hamstrings": 50},
            cns_load_7day_avg=45,
            recovery_score_today=72,
            hrv_rmssd_today=58,
        ),
        compliance=Compliance(last_4_weeks_completion_rate=0.88),
        weekly_volumes=WeeklyVolumes(running_km=22, lifting_sessions=3, total_training_hours=6.5),
    )


def test_running_coach_receives_running_profile():
    view = get_agent_view(_make_state(), AgentType.running_coach)
    assert "running_profile" in view
    assert view["running_profile"]["vdot"] == 38.2


def test_running_coach_does_not_receive_lifting_profile():
    view = get_agent_view(_make_state(), AgentType.running_coach)
    assert "lifting_profile" not in view


def test_running_coach_receives_correct_fatigue_subset():
    view = get_agent_view(_make_state(), AgentType.running_coach)
    assert "fatigue" in view
    fatigue = view["fatigue"]
    assert "acwr_by_sport_running" in fatigue
    assert fatigue["acwr_by_sport_running"] == 1.08
    assert "hrv_rmssd_today" in fatigue
    assert "recovery_score_today" in fatigue
    assert "fatigue_by_muscle" not in fatigue  # pas pour le Running Coach


def test_lifting_coach_receives_fatigue_by_muscle_and_cns():
    view = get_agent_view(_make_state(), AgentType.lifting_coach)
    assert "fatigue" in view
    fatigue = view["fatigue"]
    assert "fatigue_by_muscle" in fatigue
    assert "cns_load_7day_avg" in fatigue
    assert fatigue["cns_load_7day_avg"] == 45


def test_lifting_coach_does_not_receive_running_profile():
    view = get_agent_view(_make_state(), AgentType.lifting_coach)
    assert "running_profile" not in view


def test_nutrition_coach_receives_weekly_volumes_and_nutrition_profile():
    view = get_agent_view(_make_state(), AgentType.nutrition_coach)
    assert "weekly_volumes" in view
    assert "nutrition_profile" in view
    assert view["nutrition_profile"]["tdee_estimated"] == 2800


def test_nutrition_coach_does_not_receive_running_or_lifting_profile():
    view = get_agent_view(_make_state(), AgentType.nutrition_coach)
    assert "running_profile" not in view
    assert "lifting_profile" not in view


def test_recovery_coach_receives_full_fatigue():
    view = get_agent_view(_make_state(), AgentType.recovery_coach)
    assert "fatigue" in view
    fatigue = view["fatigue"]
    assert "acwr" in fatigue
    assert "fatigue_by_muscle" in fatigue
    assert "cns_load_7day_avg" in fatigue
    assert "hrv_rmssd_today" in fatigue
    assert "recovery_score_today" in fatigue


def test_recovery_coach_receives_compliance_and_weekly_volumes():
    view = get_agent_view(_make_state(), AgentType.recovery_coach)
    assert "compliance" in view
    assert "weekly_volumes" in view


def test_head_coach_receives_all_top_level_sections():
    view = get_agent_view(_make_state(), AgentType.head_coach)
    assert "running_profile" in view
    assert "lifting_profile" in view
    assert "fatigue" in view
    assert "nutrition_profile" in view
    assert "profile" in view
    assert "compliance" in view
    assert "weekly_volumes" in view


def test_no_specialist_agent_receives_training_history():
    """Aucun agent spécialiste ne reçoit training_history (trop verbeux)."""
    state = _make_state()
    specialist_agents = [
        AgentType.running_coach,
        AgentType.lifting_coach,
        AgentType.swimming_coach,
        AgentType.biking_coach,
        AgentType.nutrition_coach,
        AgentType.recovery_coach,
    ]
    for agent in specialist_agents:
        view = get_agent_view(state, agent)
        # Les agents reçoivent "identity" (subset de profile), pas le profil complet
        if "profile" in view:
            assert "training_history" not in view["profile"], f"{agent} leaked training_history"
        if "identity" in view:
            assert "training_history" not in view["identity"], f"{agent} leaked training_history"
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
poetry run pytest tests/test_views.py -v
```

Expected: `ImportError: cannot import name 'AgentType' from 'models.views'` (le fichier n'existe pas)

- [ ] **Step 3 : Créer `models/views.py`**

```python
"""
AGENT VIEWS — Resilio+
Filtrage de l'AthleteState par agent (token economy §2.3 du master doc).
Chaque agent reçoit uniquement les champs pertinents à son domaine.
"""
from enum import Enum
from typing import Callable

from models.schemas import AthleteStateSchema


class AgentType(str, Enum):
    head_coach = "head_coach"
    running_coach = "running_coach"
    lifting_coach = "lifting_coach"
    swimming_coach = "swimming_coach"
    biking_coach = "biking_coach"
    nutrition_coach = "nutrition_coach"
    recovery_coach = "recovery_coach"


def _head_coach_view(state: AthleteStateSchema) -> dict:
    return state.model_dump(mode="python")


def _running_view(state: AthleteStateSchema) -> dict:
    return {
        "identity": state.profile.model_dump(
            include={"first_name", "age", "sex", "weight_kg"}
        ),
        "goals": state.profile.goals.model_dump(),
        "constraints": {
            "injuries_history": [i.model_dump() for i in state.profile.injuries_history]
        },
        "equipment": state.profile.equipment.model_dump(),
        "available_days": {
            k: v.model_dump() for k, v in state.profile.available_days.items()
        },
        "running_profile": state.running_profile.model_dump(),
        "fatigue": {
            "acwr_by_sport_running": state.fatigue.acwr_by_sport.running,
            "hrv_rmssd_today": state.fatigue.hrv_rmssd_today,
            "recovery_score_today": state.fatigue.recovery_score_today,
        },
        "current_phase": state.current_phase.model_dump(),
    }


def _lifting_view(state: AthleteStateSchema) -> dict:
    return {
        "identity": state.profile.model_dump(
            include={"first_name", "age", "sex", "weight_kg"}
        ),
        "goals": state.profile.goals.model_dump(),
        "constraints": {
            "injuries_history": [i.model_dump() for i in state.profile.injuries_history]
        },
        "equipment": state.profile.equipment.model_dump(),
        "available_days": {
            k: v.model_dump() for k, v in state.profile.available_days.items()
        },
        "lifting_profile": state.lifting_profile.model_dump(),
        "fatigue": {
            "acwr_by_sport_lifting": state.fatigue.acwr_by_sport.lifting,
            "fatigue_by_muscle": state.fatigue.fatigue_by_muscle,
            "cns_load_7day_avg": state.fatigue.cns_load_7day_avg,
            "recovery_score_today": state.fatigue.recovery_score_today,
        },
        "current_phase": state.current_phase.model_dump(),
    }


def _swimming_view(state: AthleteStateSchema) -> dict:
    return {
        "identity": state.profile.model_dump(
            include={"first_name", "age", "sex", "weight_kg"}
        ),
        "goals": state.profile.goals.model_dump(),
        "constraints": {
            "injuries_history": [i.model_dump() for i in state.profile.injuries_history]
        },
        "equipment": state.profile.equipment.model_dump(),
        "swimming_profile": state.swimming_profile.model_dump(),
        "fatigue": {
            "hrv_rmssd_today": state.fatigue.hrv_rmssd_today,
            "recovery_score_today": state.fatigue.recovery_score_today,
        },
        "current_phase": state.current_phase.model_dump(),
    }


def _biking_view(state: AthleteStateSchema) -> dict:
    return {
        "identity": state.profile.model_dump(
            include={"first_name", "age", "sex", "weight_kg"}
        ),
        "goals": state.profile.goals.model_dump(),
        "constraints": {
            "injuries_history": [i.model_dump() for i in state.profile.injuries_history]
        },
        "equipment": state.profile.equipment.model_dump(),
        "biking_profile": state.biking_profile.model_dump(),
        "fatigue": {
            "acwr_by_sport_biking": state.fatigue.acwr_by_sport.biking,
            "hrv_rmssd_today": state.fatigue.hrv_rmssd_today,
            "recovery_score_today": state.fatigue.recovery_score_today,
        },
        "current_phase": state.current_phase.model_dump(),
    }


def _nutrition_view(state: AthleteStateSchema) -> dict:
    return {
        "identity": state.profile.model_dump(
            include={"first_name", "age", "sex", "weight_kg"}
        ),
        "goals": state.profile.goals.model_dump(),
        "constraints": {
            "injuries_history": [i.model_dump() for i in state.profile.injuries_history]
        },
        "nutrition_profile": state.nutrition_profile.model_dump(),
        "weekly_volumes": state.weekly_volumes.model_dump(),
        "current_phase": state.current_phase.model_dump(),
    }


def _recovery_view(state: AthleteStateSchema) -> dict:
    return {
        "identity": state.profile.model_dump(
            include={"first_name", "age", "sex", "weight_kg"}
        ),
        "constraints": {
            "injuries_history": [i.model_dump() for i in state.profile.injuries_history]
        },
        "fatigue": state.fatigue.model_dump(),
        "weekly_volumes": state.weekly_volumes.model_dump(),
        "compliance": state.compliance.model_dump(),
        "current_phase": state.current_phase.model_dump(),
    }


AGENT_VIEW_MAP: dict[AgentType, Callable[[AthleteStateSchema], dict]] = {
    AgentType.head_coach: _head_coach_view,
    AgentType.running_coach: _running_view,
    AgentType.lifting_coach: _lifting_view,
    AgentType.swimming_coach: _swimming_view,
    AgentType.biking_coach: _biking_view,
    AgentType.nutrition_coach: _nutrition_view,
    AgentType.recovery_coach: _recovery_view,
}


def get_agent_view(state: AthleteStateSchema, agent: AgentType) -> dict:
    """Filtre l'AthleteState selon les permissions de l'agent (master doc §2.3)."""
    return AGENT_VIEW_MAP[agent](state)
```

- [ ] **Step 4 : Vérifier que les tests passent**

```bash
poetry run pytest tests/test_views.py -v
```

Expected:
```
tests/test_views.py::test_running_coach_receives_running_profile PASSED
tests/test_views.py::test_running_coach_does_not_receive_lifting_profile PASSED
tests/test_views.py::test_running_coach_receives_correct_fatigue_subset PASSED
tests/test_views.py::test_lifting_coach_receives_fatigue_by_muscle_and_cns PASSED
tests/test_views.py::test_lifting_coach_does_not_receive_running_profile PASSED
tests/test_views.py::test_nutrition_coach_receives_weekly_volumes_and_nutrition_profile PASSED
tests/test_views.py::test_nutrition_coach_does_not_receive_running_or_lifting_profile PASSED
tests/test_views.py::test_recovery_coach_receives_full_fatigue PASSED
tests/test_views.py::test_recovery_coach_receives_compliance_and_weekly_volumes PASSED
tests/test_views.py::test_head_coach_receives_all_top_level_sections PASSED
tests/test_views.py::test_no_specialist_agent_receives_training_history PASSED
11 passed
```

- [ ] **Step 5 : Vérifier la suite complète**

```bash
poetry run pytest tests/ -v
```

Expected: 29 passed (12 S1 + 6 schemas + 11 views)

- [ ] **Step 6 : Commit**

```bash
git add models/views.py tests/test_views.py
git commit -m "feat: add get_agent_view() with 7-agent AGENT_VIEW_MAP (TDD)"
```

---

## Task 3 : Migration Alembic initiale

**Files:**
- Create: `alembic/versions/<hash>_initial_schema.py` (générée automatiquement)
- Delete: `alembic/versions/.gitkeep`

**Pré-requis :** Docker Desktop doit être lancé.

- [ ] **Step 1 : Démarrer PostgreSQL**

```bash
docker compose up db -d
```

Expected:
```
[+] Running 1/1
 ✔ Container resilio-plus-db-1  Started
```

- [ ] **Step 2 : Vérifier que la DB est healthy**

```bash
docker compose ps
```

Expected: `resilio-plus-db-1` avec status `healthy` ou `running`.

- [ ] **Step 3 : Générer la migration**

```bash
poetry run alembic revision --autogenerate -m "initial schema"
```

Expected:
```
INFO  [alembic.runtime.migration] Context impl PostgreSQLImpl.
INFO  [alembic.autogenerate.compare] Detected added table 'athletes'
INFO  [alembic.autogenerate.compare] Detected added table 'athlete_states'
INFO  [alembic.autogenerate.compare] Detected added table 'fatigue_snapshots'
INFO  [alembic.autogenerate.compare] Detected added table 'lifting_sessions'
INFO  [alembic.autogenerate.compare] Detected added table 'lifting_sets'
INFO  [alembic.autogenerate.compare] Detected added table 'run_activities'
INFO  [alembic.autogenerate.compare] Detected added table 'weekly_plans'
INFO  [alembic.autogenerate.compare] Detected added table 'decision_logs'
  Generating alembic/versions/<hash>_initial_schema.py ... done
```

Si l'output n'affiche pas les 8 tables, vérifier que `alembic/env.py` importe bien `from models.database import Base`.

- [ ] **Step 4 : Appliquer la migration**

```bash
poetry run alembic upgrade head
```

Expected:
```
INFO  [alembic.runtime.migration] Running upgrade  -> <hash>, initial schema
```

- [ ] **Step 5 : Vérifier l'état**

```bash
poetry run alembic current
```

Expected: `<hash> (head)` — le hash de la migration générée à l'étape 3.

- [ ] **Step 6 : Supprimer `.gitkeep` et committer**

```bash
git rm alembic/versions/.gitkeep
git add alembic/versions/
git commit -m "feat: generate initial Alembic migration (8 tables)"
```

---

## Vérification finale post-S2

```bash
# Tous les tests (sans DB requise)
poetry run pytest tests/test_config.py tests/test_exercise_database.py tests/test_schemas.py tests/test_views.py -v
# Expected: 29 passed

# Linter
poetry run ruff check .
# Expected: All checks passed.

# Migration (nécessite PostgreSQL)
poetry run alembic current
# Expected: <hash> (head)
```

---

## Self-review du plan

**Spec coverage :**
- ✅ `models/schemas.py` — 15 sub-models + `AthleteStateSchema` avec `ConfigDict(strict=False)`
- ✅ `models/views.py` — `AgentType` enum + `AGENT_VIEW_MAP` + `get_agent_view()`
- ✅ Migration Alembic initiale — 8 tables générées depuis `models/database.py`
- ✅ `tests/test_schemas.py` — 6 tests dont JSONB roundtrip et coercion depuis dicts bruts
- ✅ `tests/test_views.py` — 11 tests dont vérification des exclusions par agent

**Placeholders :** Aucun — tout le code est explicité step by step.

**Type consistency :**
- `VolumeLandmarks` défini en Task 1, utilisé dans `LiftingProfile` dans la même task — cohérent.
- `AgentType` défini dans `models/views.py` Task 2, importé dans `tests/test_views.py` — cohérent.
- `get_agent_view(state: AthleteStateSchema, agent: AgentType) -> dict` — signature identique dans l'implémentation et les tests.
