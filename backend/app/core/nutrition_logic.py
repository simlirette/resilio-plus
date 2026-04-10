from __future__ import annotations

import json
from pathlib import Path

from ..schemas.athlete import AthleteProfile, DayType
from ..schemas.nutrition import DayNutrition, MacroTarget, NutritionPlan

_REPO_ROOT = Path(__file__).resolve().parents[3]
_NUTRITION_DATA: dict = json.loads(
    (_REPO_ROOT / ".bmad-core" / "data" / "nutrition-targets.json").read_text()
)

# carbs_g_per_kg by day type (from nutrition-targets.json midpoints)
_CARBS_BY_DAY_TYPE: dict[DayType, float] = {
    DayType.STRENGTH:         4.5,
    DayType.ENDURANCE_SHORT:  5.5,
    DayType.ENDURANCE_LONG:   6.5,
    DayType.REST:             3.5,
    DayType.RACE:             7.0,
}

_PROTEIN_G_PER_KG = 1.8
_FAT_G_PER_KG = 1.2

# Intra-effort carbs: only for sessions > 60 min
_INTRA_EFFORT_G_PER_H: dict[DayType, float | None] = {
    DayType.STRENGTH:         None,
    DayType.ENDURANCE_SHORT:  None,
    DayType.ENDURANCE_LONG:   45.0,
    DayType.REST:             None,
    DayType.RACE:             75.0,
}


def compute_nutrition_directives(athlete: AthleteProfile) -> NutritionPlan:
    """Compute per-day-type nutrition targets for the athlete.

    Returns a NutritionPlan with targets for all DayType values.
    Calories computed from macros: carbs*4 + protein*4 + fat*9 (per kg × weight).
    """
    targets: dict[DayType, DayNutrition] = {}

    for day_type in [DayType.REST, DayType.STRENGTH, DayType.ENDURANCE_SHORT,
                     DayType.ENDURANCE_LONG, DayType.RACE]:
        carbs = _CARBS_BY_DAY_TYPE[day_type]
        protein = _PROTEIN_G_PER_KG
        fat = _FAT_G_PER_KG
        calories = int(
            (carbs * athlete.weight_kg * 4)
            + (protein * athlete.weight_kg * 4)
            + (fat * athlete.weight_kg * 9)
        )

        targets[day_type] = DayNutrition(
            day_type=day_type,
            macro_target=MacroTarget(
                carbs_g_per_kg=carbs,
                protein_g_per_kg=protein,
                fat_g_per_kg=fat,
                calories_total=calories,
            ),
            intra_effort_carbs_g_per_h=_INTRA_EFFORT_G_PER_H[day_type],
        )

    return NutritionPlan(
        athlete_id=athlete.id,
        weight_kg=athlete.weight_kg,
        targets_by_day_type=targets,
    )
