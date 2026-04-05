"""
CONFTEST.PY — Fixtures globales pour tous les tests Resilio+

Athlète de référence : "Simon"
Utilisé dans TOUS les tests unitaires et d'intégration.
Correspond à l'exemple du resilio-master-v2.md.
"""

import os

# Fournir une SECRET_KEY valide pour toute la suite de tests.
# Cela permet à Settings(_env_file=None) de passer le validator de production
# sans avoir à lire le fichier .env (qui peut ne pas exister en CI).
os.environ.setdefault("SECRET_KEY", "test-secret-key-set-by-conftest-do-not-use-in-prod")
os.environ.setdefault("STRAVA_CLIENT_ID", "215637")
os.environ.setdefault("STRAVA_CLIENT_SECRET", "test_strava_secret")
os.environ.setdefault(
    "STRAVA_REDIRECT_URI",
    "http://localhost:8000/api/v1/connectors/strava/callback",
)
os.environ.setdefault("HEVY_API_KEY", "test_hevy_key")

from datetime import date
from uuid import UUID

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from models.database import (
    Athlete,
    AthleteState,
    Base,
    FatigueSnapshot,
    MacrocyclePhase,
    ReadinessColor,
)

# ─────────────────────────────────────────────
# BASE DE DONNÉES DE TEST
# ─────────────────────────────────────────────

TEST_DATABASE_URL = "postgresql+asyncpg://resilio:resilio@localhost:5432/resilio_test"

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncSession:
    """Session de test isolée — rollback après chaque test."""
    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
        await session.rollback()


# ─────────────────────────────────────────────
# DONNÉES SIMON — ATHLÈTE DE RÉFÉRENCE
# ─────────────────────────────────────────────

SIMON_ID = UUID("00000000-0000-0000-0000-000000000001")

SIMON_PROFILE_DATA = {
    "training_history": {
        "total_years_training": 5,
        "years_running": 2,
        "years_lifting": 4,
        "years_swimming": 0.5,
        "current_weekly_volume_hours": 7,
        "longest_run_ever_km": 15,
        "current_5k_time_min": 28.5,
        "current_10k_time_min": None,
        "current_half_marathon_min": None,
        "estimated_1rm": {
            "squat": 120,
            "bench_press": 85,
            "deadlift": 140,
            "overhead_press": 55,
        },
    },
    "injuries_history": [
        {
            "type": "shin_splints",
            "year": 2024,
            "duration_weeks": 6,
            "side": "bilateral",
            "recurrent": False,
            "notes": "Augmentation trop rapide du volume de course",
        }
    ],
    "lifestyle": {
        "work_type": "desk_sedentary",
        "work_hours_per_day": 8,
        "commute_active": False,
        "sleep_avg_hours": 7.2,
        "stress_level": "moderate",
        "alcohol_per_week": 2,
        "smoking": False,
    },
    "goals": {
        "primary": "run_sub_25_5k",
        "secondary": "maintain_muscle_mass",
        "tertiary": "improve_swimming_technique",
        "timeline_weeks": 16,
        "priority_hierarchy": [
            "running_5k",
            "hypertrophy_maintenance",
            "swimming_technique",
        ],
    },
    "equipment": {
        "gym_access": True,
        "gym_equipment": ["barbell", "dumbbells", "cables", "machines", "pull_up_bar"],
        "pool_access": True,
        "pool_type": "25m_indoor",
        "outdoor_running": True,
        "treadmill": False,
        "heart_rate_monitor": True,
        "gps_watch": "garmin_forerunner_265",
        "power_meter_bike": False,
    },
}

SIMON_AVAILABLE_DAYS = {
    "monday":    {"available": True,  "max_hours": 1.5, "preferred_time": "morning"},
    "tuesday":   {"available": True,  "max_hours": 1.5, "preferred_time": "evening"},
    "wednesday": {"available": True,  "max_hours": 1.0, "preferred_time": "morning"},
    "thursday":  {"available": True,  "max_hours": 1.5, "preferred_time": "evening"},
    "friday":    {"available": False, "max_hours": 0,   "preferred_time": None},
    "saturday":  {"available": True,  "max_hours": 2.5, "preferred_time": "morning"},
    "sunday":    {"available": True,  "max_hours": 2.0, "preferred_time": "morning"},
}

SIMON_RUNNING_PROFILE = {
    "vdot": 38.2,
    "training_paces": {
        "easy_min_per_km": "6:24",
        "easy_max_per_km": "7:06",
        "marathon_pace_per_km": "5:42",
        "threshold_pace_per_km": "5:18",
        "interval_pace_per_km": "4:48",
        "repetition_pace_per_km": "4:24",
        "long_run_pace_per_km": "6:36",
    },
    "weekly_km_current": 22,
    "weekly_km_target": 35,
    "max_long_run_km": 12,
    "cadence_avg": 168,
    "preferred_terrain": "road",
}

SIMON_LIFTING_PROFILE = {
    "training_split": "upper_lower",
    "sessions_per_week": 3,
    "current_volume_per_muscle": {
        "quadriceps": 8, "hamstrings": 6, "chest": 10,
        "back": 12, "shoulders": 8, "biceps": 6,
        "triceps": 6, "calves": 4,
    },
    "volume_landmarks": {
        "quadriceps": {"mev": 6, "mav": 10, "mrv_hybrid": 12},
        "hamstrings":  {"mev": 4, "mav": 8,  "mrv_hybrid": 10},
        "chest":       {"mev": 6, "mav": 14, "mrv_hybrid": 18},
        "back":        {"mev": 6, "mav": 14, "mrv_hybrid": 20},
        "shoulders":   {"mev": 6, "mav": 12, "mrv_hybrid": 16},
        "biceps":      {"mev": 4, "mav": 10, "mrv_hybrid": 14},
        "triceps":     {"mev": 4, "mav": 8,  "mrv_hybrid": 12},
        "calves":      {"mev": 4, "mav": 8,  "mrv_hybrid": 6},
    },
    "progression_model": "double_progression",
    "rir_target_range": [1, 3],
}

SIMON_NUTRITION_PROFILE = {
    "tdee_estimated": 2800,
    "macros_target": {
        "protein_g": 160,
        "carbs_g": 300,
        "fat_g": 80,
    },
    "supplements_current": ["creatine_5g"],
    "dietary_restrictions": [],
    "allergies": [],
}


# ─────────────────────────────────────────────
# FIXTURES SIMON
# ─────────────────────────────────────────────

@pytest.fixture
def simon_dict() -> dict:
    """Dictionnaire brut Simon — pour les tests sans DB."""
    return {
        "id": str(SIMON_ID),
        "first_name": "Simon",
        "age": 32,
        "sex": "M",
        "weight_kg": 78.5,
        "height_cm": 178,
        "body_fat_percent": 16.5,
        "resting_hr": 58,
        "max_hr_measured": 188,
        "profile_data": SIMON_PROFILE_DATA,
        "available_days": SIMON_AVAILABLE_DAYS,
        "running_profile": SIMON_RUNNING_PROFILE,
        "lifting_profile": SIMON_LIFTING_PROFILE,
        "nutrition_profile": SIMON_NUTRITION_PROFILE,
    }


@pytest_asyncio.fixture
async def simon_athlete(db_session: AsyncSession) -> Athlete:
    """Athlète Simon persisté en base de test."""
    athlete = Athlete(
        id=SIMON_ID,
        first_name="Simon",
        age=32,
        sex="M",
        weight_kg=78.5,
        height_cm=178,
        body_fat_percent=16.5,
        resting_hr=58,
        max_hr_measured=188,
        profile_data=SIMON_PROFILE_DATA,
        available_days=SIMON_AVAILABLE_DAYS,
    )
    db_session.add(athlete)
    await db_session.flush()
    return athlete


@pytest_asyncio.fixture
async def simon_state(db_session: AsyncSession, simon_athlete: Athlete) -> AthleteState:
    """AthleteState de Simon en phase base building, semaine 3."""
    state = AthleteState(
        athlete_id=SIMON_ID,
        macrocycle_phase=MacrocyclePhase.base_building,
        mesocycle_week=3,
        target_event_date=date(2026, 7, 15),
        running_profile=SIMON_RUNNING_PROFILE,
        lifting_profile=SIMON_LIFTING_PROFILE,
        swimming_profile={
            "reference_times": {},
            "technique_level": "beginner",
            "weekly_volume_km": 0,
        },
        biking_profile={"ftp_watts": None, "weekly_volume_km": 0},
        nutrition_profile=SIMON_NUTRITION_PROFILE,
        weekly_km_running=22.0,
        weekly_sessions_lifting=3,
        weekly_km_biking=0.0,
        weekly_km_swimming=0.0,
        total_training_hours=6.5,
        completion_rate_4weeks=0.88,
        nutrition_adherence_7days=0.75,
    )
    db_session.add(state)
    await db_session.flush()
    return state


@pytest_asyncio.fixture
async def simon_fatigue_normal(
    db_session: AsyncSession, simon_athlete: Athlete
) -> FatigueSnapshot:
    """Fatigue Simon — état normal (readiness VERT)."""
    snapshot = FatigueSnapshot(
        athlete_id=SIMON_ID,
        snapshot_date=date.today(),
        hrv_rmssd=58,
        hr_rest=58,
        sleep_hours=7.2,
        sleep_quality_subjective=7,
        acwr_global=1.05,
        acwr_running=1.08,
        acwr_lifting=1.02,
        acwr_biking=None,
        weekly_fatigue_score=320,
        cns_load_7day_avg=45,
        fatigue_by_muscle={
            "quadriceps": 65, "hamstrings": 50, "chest": 30,
            "back": 35, "shoulders": 25, "calves": 40,
        },
        recovery_score=72,
        readiness_color=ReadinessColor.green,
        fatigue_subjective=3,
    )
    db_session.add(snapshot)
    await db_session.flush()
    return snapshot


@pytest_asyncio.fixture
async def simon_fatigue_red(
    db_session: AsyncSession, simon_athlete: Athlete
) -> FatigueSnapshot:
    """Fatigue Simon — état critique (readiness ROUGE) pour tests edge cases."""
    snapshot = FatigueSnapshot(
        athlete_id=SIMON_ID,
        snapshot_date=date.today(),
        hrv_rmssd=38,           # -39% vs baseline 62
        hr_rest=67,             # +9 bpm vs baseline 58
        sleep_hours=5.1,
        sleep_quality_subjective=4,
        acwr_global=1.61,       # Zone rouge
        acwr_running=1.68,
        acwr_lifting=1.45,
        acwr_biking=None,
        weekly_fatigue_score=520,
        cns_load_7day_avg=72,
        fatigue_by_muscle={
            "quadriceps": 88, "hamstrings": 75, "chest": 40,
            "back": 50, "shoulders": 35, "calves": 80,
        },
        recovery_score=38,
        readiness_color=ReadinessColor.red,
        fatigue_subjective=8,
    )
    db_session.add(snapshot)
    await db_session.flush()
    return snapshot


# ─────────────────────────────────────────────
# FIXTURES UTILITAIRES
# ─────────────────────────────────────────────

@pytest.fixture
def simon_agent_view_running(simon_dict: dict) -> dict:
    """Vue filtrée Running Coach — sans DB."""
    return {
        "identity": {
            "first_name": simon_dict["first_name"],
            "age": simon_dict["age"],
            "sex": simon_dict["sex"],
            "weight_kg": simon_dict["weight_kg"],
        },
        "goals": simon_dict["profile_data"]["goals"],
        "constraints": {
            "injuries_history": simon_dict["profile_data"]["injuries_history"],
        },
        "equipment": simon_dict["profile_data"]["equipment"],
        "available_days": simon_dict["available_days"],
        "running_profile": simon_dict["running_profile"],
        "fatigue": {
            "acwr_by_sport_running": 1.08,
            "hrv_rmssd_today": 58,
            "recovery_score_today": 72,
        },
        "current_phase": {
            "macrocycle": "base_building",
            "mesocycle_week": 3,
            "target_event_date": "2026-07-15",
        },
    }


@pytest.fixture
def simon_agent_view_lifting(simon_dict: dict) -> dict:
    """Vue filtrée Lifting Coach — sans DB."""
    return {
        "identity": {
            "first_name": simon_dict["first_name"],
            "age": simon_dict["age"],
            "sex": simon_dict["sex"],
            "weight_kg": simon_dict["weight_kg"],
        },
        "goals": simon_dict["profile_data"]["goals"],
        "constraints": {
            "injuries_history": simon_dict["profile_data"]["injuries_history"],
        },
        "equipment": simon_dict["profile_data"]["equipment"],
        "available_days": simon_dict["available_days"],
        "lifting_profile": simon_dict["lifting_profile"],
        "fatigue": {
            "acwr_by_sport_lifting": 1.02,
            "fatigue_by_muscle": {
                "quadriceps": 65, "hamstrings": 50, "chest": 30,
                "back": 35, "shoulders": 25, "calves": 40,
            },
            "cns_load_7day_avg": 45,
            "recovery_score_today": 72,
        },
        "current_phase": {
            "macrocycle": "base_building",
            "mesocycle_week": 3,
        },
    }
