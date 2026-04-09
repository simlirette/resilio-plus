"""
Tests unitaires — NutritionPrescriber

Couvre : TDEE Mifflin-St Jeor, macros g/kg, distribution journalière, structure de sortie.
"""

import pytest

from agents.nutrition_coach.prescriber import NutritionPrescriber

_PRESCRIBER = NutritionPrescriber()

# ─── Fixtures locales ────────────────────────────────────────────────────────

@pytest.fixture
def simon_view() -> dict:
    """Vue filtrée Nutrition Coach — athlète Simon (78.5 kg, 32 ans, H, 6.5h/semaine)."""
    return {
        "identity": {
            "first_name": "Simon",
            "age": 32,
            "sex": "M",
            "weight_kg": 78.5,
            "height_cm": 178,
        },
        "goals": {
            "primary": "run_sub_25_5k",
            "timeline_weeks": 16,
            "priority_hierarchy": ["running_5k", "hypertrophy_maintenance"],
        },
        "constraints": {"injuries_history": []},
        "nutrition_profile": {
            "tdee_estimated": 2800,
            "macros_target": {"protein_g": 160, "carbs_g": 300, "fat_g": 80},
            "supplements_current": ["creatine_5g"],
            "dietary_restrictions": [],
            "allergies": [],
        },
        "weekly_volumes": {
            "running_km": 22.0,
            "lifting_sessions": 3,
            "swimming_km": 0.0,
            "biking_km": 0.0,
            "total_training_hours": 6.5,
        },
        "current_phase": {
            "macrocycle": "base_building",
            "mesocycle_week": 3,
            "mesocycle_length": 4,
        },
    }


# ─── Tests TDEE ──────────────────────────────────────────────────────────────

def test_tdee_male_moderately_active():
    """TDEE Mifflin-St Jeor pour homme 78.5kg/178cm/32ans — 6.5h/semaine = very_active."""
    identity = {"sex": "M", "weight_kg": 78.5, "height_cm": 178, "age": 32}
    weekly = {"total_training_hours": 6.5}
    tdee = _PRESCRIBER._calculate_tdee(identity, weekly)
    # BMR = 10*78.5 + 6.25*178 - 5*32 + 5 = 785 + 1112.5 - 160 + 5 = 1742.5
    # 5-8h → moderately_active = 1.55
    # → 1742.5 * 1.55 = 2700.875
    assert 2600 < tdee < 2900


def test_tdee_female_very_active():
    """TDEE pour femme 60kg/165cm/28ans — 10h/semaine = very_active."""
    identity = {"sex": "F", "weight_kg": 60, "height_cm": 165, "age": 28}
    weekly = {"total_training_hours": 10.0}
    tdee = _PRESCRIBER._calculate_tdee(identity, weekly)
    # BMR = 10*60 + 6.25*165 - 5*28 - 161 = 600 + 1031.25 - 140 - 161 = 1330.25
    # 8-12h → very_active = 1.725
    # → 1330.25 * 1.725 ≈ 2294.7
    assert 2000 < tdee < 2600


def test_tdee_sedentary_no_training():
    """TDEE pour athlète sans entraînement cette semaine → sedentary multiplier."""
    identity = {"sex": "M", "weight_kg": 80, "height_cm": 180, "age": 30}
    weekly = {"total_training_hours": 0.0}
    tdee = _PRESCRIBER._calculate_tdee(identity, weekly)
    # BMR ≈ 1865, * 1.2 = 2238
    assert 2000 < tdee < 2500


# ─── Tests macros ──────────────────────────────────────────────────────────

def test_macros_lifting_day_weight_78kg():
    """Macros journée lifting_only pour 78.5 kg — vérifie g/kg cibles."""
    macros = _PRESCRIBER._macros_for_day("lifting_only", 78.5)
    # Cibles : carbs 4.5 g/kg, protein 2.0 g/kg, fat 0.9 g/kg
    assert abs(macros["protein_g"] - 78.5 * 2.0) < 1
    assert abs(macros["carbs_g"] - 78.5 * 4.5) < 1
    assert abs(macros["fat_g"] - 78.5 * 0.9) < 1
    assert macros["kcal"] > 0


def test_macros_long_run_day_higher_carbs():
    """Journée long_run a plus de glucides que journée repos."""
    rest = _PRESCRIBER._macros_for_day("rest", 78.5)
    long_run = _PRESCRIBER._macros_for_day("long_run", 78.5)
    assert long_run["carbs_g"] > rest["carbs_g"]


# ─── Tests distribution hebdomadaire ─────────────────────────────────────────

def test_day_schedule_standard_simon_week():
    """3 lifting + 22 km course → schedule de 7 jours (Lun-Dim) avec types corrects."""
    weekly = {
        "running_km": 22.0,
        "lifting_sessions": 3,
        "swimming_km": 0.0,
        "biking_km": 0.0,
        "total_training_hours": 6.5,
    }
    schedule = _PRESCRIBER._build_day_schedule(weekly)
    assert len(schedule) == 7
    lifting_days = [d for d in schedule if "lifting" in d or d == "double_session"]
    assert len(lifting_days) == 3
    running_days = [
        d for d in schedule
        if d in ("easy_run", "long_run", "intensity_run", "double_session")
    ]
    assert len(running_days) >= 1


def test_day_schedule_rest_only_no_training():
    """0 sessions → 7 jours de repos."""
    weekly = {
        "running_km": 0.0,
        "lifting_sessions": 0,
        "swimming_km": 0.0,
        "biking_km": 0.0,
        "total_training_hours": 0.0,
    }
    schedule = _PRESCRIBER._build_day_schedule(weekly)
    assert all(d == "rest" for d in schedule)


# ─── Tests sortie complète ────────────────────────────────────────────────────

def test_prescribe_output_structure(simon_view):
    """prescribe() retourne un dict avec toutes les clés requises."""
    result = _PRESCRIBER.prescribe(simon_view)

    assert result["agent"] == "nutrition_coach"
    assert "weekly_summary" in result
    assert "daily_plans" in result
    assert "notes" in result

    summary = result["weekly_summary"]
    assert "tdee_estimated" in summary
    assert "avg_macros_g" in summary
    assert "active_supplements" in summary

    plans = result["daily_plans"]
    assert len(plans) == 7
    for plan in plans:
        assert "day" in plan
        assert "day_type" in plan
        assert "kcal_target" in plan
        assert "macros_g" in plan
        assert "hydration_ml" in plan
        assert "timing" in plan
