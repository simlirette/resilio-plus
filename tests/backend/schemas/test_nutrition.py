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
    from app.schemas.nutrition import MacroTarget
    m = MacroTarget(**make_macro())
    assert m.carbs_g_per_kg == 4.0
    assert m.protein_g_per_kg == 2.0
    assert m.fat_g_per_kg == 1.0
    assert m.calories_total == 2200


def test_macro_negative_carbs_raises():
    from app.schemas.nutrition import MacroTarget
    with pytest.raises(ValidationError):
        MacroTarget(**make_macro(carbs_g_per_kg=-1.0))


def test_macro_zero_calories_raises():
    from app.schemas.nutrition import MacroTarget
    with pytest.raises(ValidationError):
        MacroTarget(**make_macro(calories_total=0))


# --- DayNutrition ---

def test_day_nutrition_valid_no_intra():
    from app.schemas.nutrition import DayNutrition
    dn = DayNutrition(**make_day_nutrition())
    assert dn.day_type.value == "strength"
    assert dn.intra_effort_carbs_g_per_h is None
    assert dn.sodium_mg_per_h is None


def test_day_nutrition_with_intra_effort():
    from app.schemas.nutrition import DayNutrition
    dn = DayNutrition(**make_day_nutrition(
        intra_effort_carbs_g_per_h=60.0,
        sodium_mg_per_h=750.0,
    ))
    assert dn.intra_effort_carbs_g_per_h == 60.0
    assert dn.sodium_mg_per_h == 750.0


def test_day_nutrition_invalid_day_type_raises():
    from app.schemas.nutrition import DayNutrition
    with pytest.raises(ValidationError):
        DayNutrition(**make_day_nutrition(day_type="cardio"))


# --- NutritionPlan ---

def test_nutrition_plan_valid():
    from app.schemas.nutrition import NutritionPlan
    plan = NutritionPlan(**make_nutrition_plan())
    assert plan.weight_kg == 75.0
    assert len(plan.targets_by_day_type) == 2


def test_nutrition_plan_id_generated():
    from app.schemas.nutrition import NutritionPlan
    p1 = NutritionPlan(**make_nutrition_plan())
    p2 = NutritionPlan(**make_nutrition_plan())
    assert p1.id != p2.id


def test_nutrition_plan_zero_weight_raises():
    from app.schemas.nutrition import NutritionPlan
    with pytest.raises(ValidationError):
        NutritionPlan(**make_nutrition_plan(weight_kg=0.0))


def test_nutrition_plan_empty_targets_is_valid():
    from app.schemas.nutrition import NutritionPlan
    plan = NutritionPlan(
        athlete_id="00000000-0000-0000-0000-000000000001",
        weight_kg=70.0,
    )
    assert plan.targets_by_day_type == {}


def test_nutrition_plan_enum_keys_serialized_as_strings():
    from app.schemas.nutrition import NutritionPlan
    plan = NutritionPlan(**make_nutrition_plan())
    json_str = plan.model_dump_json()
    data = json.loads(json_str)
    # Pydantic v2 serializes DayType keys as their string values
    assert "rest" in data["targets_by_day_type"]
    assert "strength" in data["targets_by_day_type"]


def test_nutrition_plan_json_round_trip():
    from app.schemas.nutrition import NutritionPlan
    plan = NutritionPlan(**make_nutrition_plan())
    json_str = plan.model_dump_json()
    plan2 = NutritionPlan.model_validate_json(json_str)
    assert plan == plan2
