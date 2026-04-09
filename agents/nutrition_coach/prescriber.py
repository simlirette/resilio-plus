"""
NutritionPrescriber — calcul déterministe des macros et timing nutritionnel.

Sources :
- data/nutrition_targets.json — macros g/kg par type de journée
- Mifflin-St Jeor BMR + multiplicateurs d'activité
"""

import json
from pathlib import Path

_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "nutrition_targets.json"
_TARGETS = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
_DAY_TYPES = _TARGETS["day_types"]
_HYDRATION = _TARGETS["hydration_targets"]

_ACTIVITY_MULTIPLIERS = {
    "sedentary":         1.2,    # < 3h/semaine
    "lightly_active":    1.375,  # 3-5h/semaine
    "moderately_active": 1.55,   # 5-8h/semaine
    "very_active":       1.725,  # 8-12h/semaine
    "extremely_active":  1.9,    # > 12h/semaine
}

_DAYS = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
]


class NutritionPrescriber:
    """
    Génère le plan nutritionnel journalier (7 jours) à partir de la vue nutrition.

    Entrée : vue filtrée par _nutrition_view() — identity, nutrition_profile,
             weekly_volumes, current_phase.
    Sortie : { agent, weekly_summary, daily_plans, notes }.
    """

    def prescribe(self, view: dict) -> dict:
        identity = view.get("identity", {})
        nutrition_profile = view.get("nutrition_profile", {})
        weekly_volumes = view.get("weekly_volumes", {})

        weight_kg = float(identity.get("weight_kg", 70))
        tdee = self._calculate_tdee(identity, weekly_volumes)
        day_schedule = self._build_day_schedule(weekly_volumes)

        daily_plans = []
        for i, day_type in enumerate(day_schedule):
            macros = self._macros_for_day(day_type, weight_kg)
            daily_plans.append({
                "day": _DAYS[i],
                "day_type": day_type,
                "kcal_target": macros["kcal"],
                "macros_g": {
                    "protein_g": macros["protein_g"],
                    "carbs_g": macros["carbs_g"],
                    "fat_g": macros["fat_g"],
                },
                "fiber_g_target": macros["fiber_g"],
                "hydration_ml": self._hydration_ml(day_type, weight_kg),
                "timing": self._timing(day_type, weight_kg),
            })

        avg_macros = {
            "protein_g": round(
                sum(d["macros_g"]["protein_g"] for d in daily_plans) / 7, 1
            ),
            "carbs_g": round(
                sum(d["macros_g"]["carbs_g"] for d in daily_plans) / 7, 1
            ),
            "fat_g": round(
                sum(d["macros_g"]["fat_g"] for d in daily_plans) / 7, 1
            ),
        }

        return {
            "agent": "nutrition_coach",
            "weekly_summary": {
                "tdee_estimated": round(tdee),
                "avg_macros_g": avg_macros,
                "active_supplements": nutrition_profile.get("supplements_current", []),
                "dietary_restrictions": nutrition_profile.get("dietary_restrictions", []),
            },
            "daily_plans": daily_plans,
            "notes": "",
        }

    # ── TDEE ──────────────────────────────────────────────────────────────────

    def _calculate_tdee(self, identity: dict, weekly_volumes: dict) -> float:
        """Mifflin-St Jeor BMR × multiplicateur d'activité."""
        weight = float(identity.get("weight_kg", 70))
        height = float(identity.get("height_cm", 175))
        age = int(identity.get("age", 30))
        sex = identity.get("sex", "M")

        if sex == "M":
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
        else:
            bmr = 10 * weight + 6.25 * height - 5 * age - 161

        hours = float(weekly_volumes.get("total_training_hours", 0))
        if hours < 3:
            level = "sedentary"
        elif hours < 5:
            level = "lightly_active"
        elif hours < 8:
            level = "moderately_active"
        elif hours < 12:
            level = "very_active"
        else:
            level = "extremely_active"

        return bmr * _ACTIVITY_MULTIPLIERS[level]

    # ── Distribution hebdomadaire ─────────────────────────────────────────────

    def _build_day_schedule(self, weekly_volumes: dict) -> list[str]:
        """
        Distribue les types de journée sur 7 jours (Lun→Dim).

        Règles :
        - Lifting : Lun (0), Mer (2), Ven (4) → Lun, Mer si 2 → Lun si 1
        - Course longue : Sam (5) si running_km ≥ 60 ou total_hours ≥ 7
        - Course intense : Jeu (3) si total_hours ≥ 5 et running_km ≥ 20
        - Courses faciles : créneaux libres restants
        - Double : si lifting + course se cumulent sur le même jour
        - Repos : jours non assignés
        """
        lifting = int(weekly_volumes.get("lifting_sessions", 0))
        running_km = float(weekly_volumes.get("running_km", 0))
        total_hours = float(weekly_volumes.get("total_training_hours", 0))

        running_sessions = (
            min(int(running_km / 8) + (1 if (running_km % 8) > 3 else 0), 5)
            if running_km > 0
            else 0
        )
        is_long_run = running_km >= 60 or total_hours >= 7
        is_intensity = total_hours >= 5 and running_km >= 20

        schedule = ["rest"] * 7  # index 0=Lun … 6=Dim

        # Lifting : Lun, Mer, Ven, Mar, Jeu (priorité)
        lifting_slots = [0, 2, 4, 1, 3]
        for i in range(min(lifting, 5)):
            schedule[lifting_slots[i]] = "lifting_only"

        runs_remaining = running_sessions

        # Course longue → Sam (5)
        if is_long_run and runs_remaining > 0:
            if schedule[5] == "rest":
                schedule[5] = "long_run"
            elif schedule[5] == "lifting_only":
                schedule[5] = "double_session"
            runs_remaining -= 1

        # Course intense → Jeu (3)
        if is_intensity and runs_remaining > 0:
            if schedule[3] == "rest":
                schedule[3] = "intensity_run"
            elif schedule[3] == "lifting_only":
                schedule[3] = "double_session"
            runs_remaining -= 1

        # Courses faciles → créneaux libres (Mar, Jeu, Sam, Dim)
        for slot in [1, 3, 5, 6]:
            if runs_remaining <= 0:
                break
            if schedule[slot] == "rest":
                schedule[slot] = "easy_run"
                runs_remaining -= 1
            elif schedule[slot] == "lifting_only":
                schedule[slot] = "double_session"
                runs_remaining -= 1

        return schedule

    # ── Macros ────────────────────────────────────────────────────────────────

    def _macros_for_day(self, day_type: str, weight_kg: float) -> dict:
        """Calcule les macros en grammes absolus pour un type de journée."""
        target = _DAY_TYPES.get(day_type, _DAY_TYPES["rest"])

        protein_g = round(target["protein_g_per_kg"]["target"] * weight_kg, 1)
        carbs_g = round(target["carbs_g_per_kg"]["target"] * weight_kg, 1)
        fat_g = round(target["fat_g_per_kg"]["target"] * weight_kg, 1)
        kcal = round(protein_g * 4 + carbs_g * 4 + fat_g * 9)

        fiber_range = target.get("fiber_g", {"min": 25, "max": 35})
        fiber_g = round((fiber_range["min"] + fiber_range.get("max", fiber_range["min"] + 10)) / 2)

        return {
            "protein_g": protein_g,
            "carbs_g": carbs_g,
            "fat_g": fat_g,
            "kcal": kcal,
            "fiber_g": fiber_g,
        }

    # ── Hydratation ──────────────────────────────────────────────────────────

    def _hydration_ml(self, day_type: str, weight_kg: float) -> int:
        """Hydratation journalière en ml — baseline + bonus effort."""
        baseline_range = _HYDRATION["baseline_ml_per_kg_per_day"]
        base_ml_per_kg = (baseline_range["min"] + baseline_range["max"]) / 2  # 37.5
        base_ml = round(base_ml_per_kg * weight_kg)

        if day_type in ("long_run", "double_session", "pre_competition"):
            return base_ml + 800
        if day_type in ("intensity_run", "lifting_only", "easy_run"):
            return base_ml + 400
        return base_ml

    # ── Timing nutritionnel ────────────────────────────────────────────────

    def _timing(self, day_type: str, weight_kg: float) -> dict:
        """Construit les fenêtres de timing nutritionnel pour un type de journée."""
        target = _DAY_TYPES.get(day_type, _DAY_TYPES["rest"])
        result: dict = {
            "priority": target.get("timing_priority", "aucun"),
            "meal_focus": target.get("meal_focus", ""),
        }

        if "pre_workout" in target:
            pw = target["pre_workout"]
            result["pre_workout"] = {
                "timing_hours_before": pw.get("timing_hours_before", 2),
                "carbs_g": round(pw.get("carbs_g_per_kg", 1.0) * weight_kg, 1),
                "protein_g": pw.get("protein_g", 25),
                "example": pw.get("example", ""),
            }

        if "post_workout" in target:
            pw = target["post_workout"]
            result["post_workout"] = {
                "timing_minutes_after": pw.get("timing_minutes_after", 45),
                "carbs_g": round(pw.get("carbs_g_per_kg", 1.0) * weight_kg, 1),
                "protein_g": pw.get("protein_g", 30),
                "example": pw.get("example", ""),
            }

        if "intra_workout" in target:
            iw = target["intra_workout"]
            result["intra_workout"] = {
                "required": iw.get("required", False),
                "carbs_g_per_hour": iw.get("carbs_g_per_hour", 0),
                "hydration_ml_per_hour": iw.get("hydration_ml_per_hour", 400),
            }

        return result
