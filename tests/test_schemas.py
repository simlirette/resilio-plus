"""
TEST SCHEMAS — Validation des Pydantic models AthleteState.
Tests sans DB — pas de fixtures async, pas de PostgreSQL requis.
"""
import json
from datetime import date, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

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
    with pytest.raises(ValidationError):
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
