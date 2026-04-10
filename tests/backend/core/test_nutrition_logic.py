import pytest
from app.core.nutrition_logic import compute_nutrition_directives
from app.schemas.athlete import AthleteProfile, Sport, DayType
from app.schemas.nutrition import DayNutrition, NutritionPlan


def _athlete(weight=75.0):
    return AthleteProfile(
        name="Alex", age=30, sex="M", weight_kg=weight, height_cm=178,
        sports=[Sport.RUNNING, Sport.LIFTING], primary_sport=Sport.RUNNING,
        goals=["marathon"], available_days=[0, 2, 4, 6], hours_per_week=10.0,
    )


def test_returns_nutrition_plan():
    result = compute_nutrition_directives(_athlete())
    assert isinstance(result, NutritionPlan)


def test_all_day_types_covered():
    result = compute_nutrition_directives(_athlete())
    for day_type in [DayType.REST, DayType.STRENGTH, DayType.ENDURANCE_SHORT, DayType.ENDURANCE_LONG]:
        assert day_type in result.targets_by_day_type


def test_endurance_long_has_more_carbs_than_rest():
    result = compute_nutrition_directives(_athlete(weight=75.0))
    rest_carbs = result.targets_by_day_type[DayType.REST].macro_target.carbs_g_per_kg
    endo_carbs = result.targets_by_day_type[DayType.ENDURANCE_LONG].macro_target.carbs_g_per_kg
    assert endo_carbs > rest_carbs


def test_intra_effort_none_for_short_sessions():
    result = compute_nutrition_directives(_athlete())
    assert result.targets_by_day_type[DayType.ENDURANCE_SHORT].intra_effort_carbs_g_per_h is None


def test_intra_effort_present_for_long_sessions():
    result = compute_nutrition_directives(_athlete())
    assert result.targets_by_day_type[DayType.ENDURANCE_LONG].intra_effort_carbs_g_per_h is not None
    assert result.targets_by_day_type[DayType.ENDURANCE_LONG].intra_effort_carbs_g_per_h > 0


def test_protein_is_1_8_per_kg():
    result = compute_nutrition_directives(_athlete(weight=75.0))
    for day_type, dn in result.targets_by_day_type.items():
        assert abs(dn.macro_target.protein_g_per_kg - 1.8) < 0.01
