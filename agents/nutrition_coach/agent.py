"""
NutritionCoachAgent — prescripteur nutritionnel de Resilio+.

Enchaîne NutritionPrescriber (calcul déterministe) + appel LLM Anthropic
pour générer une note clinique (≤ 3 phrases) sur les priorités nutritionnelles
de la semaine.
"""

from pathlib import Path

import anthropic

from agents.base_agent import BaseAgent
from agents.nutrition_coach.prescriber import NutritionPrescriber
from core.config import settings
from models.views import AgentType

_SYSTEM_PROMPT = (
    Path(__file__).parent / "nutrition_coach_system_prompt.md"
).read_text(encoding="utf-8")


class NutritionCoachAgent(BaseAgent):
    """Agent Nutrition Coach — prescrit les macros/timing journaliers + note LLM."""

    agent_type = AgentType.nutrition_coach

    def __init__(self) -> None:
        self._prescriber = NutritionPrescriber()
        self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def prescribe(self, view: dict) -> dict:
        """
        Génère le plan nutritionnel hebdomadaire.

        Returns:
            {
              "agent": "nutrition_coach",
              "weekly_summary": { tdee_estimated, avg_macros_g, active_supplements,
                                  dietary_restrictions },
              "daily_plans": [ 7 × { day, day_type, kcal_target, macros_g,
                                     fiber_g_target, hydration_ml, timing } ],
              "notes": str (note clinique LLM, vide si indisponible),
            }
        """
        plan = self._prescriber.prescribe(view)
        plan["notes"] = self._get_coaching_notes(view, plan)
        return plan

    def _get_coaching_notes(self, view: dict, plan: dict) -> str:
        """
        Génère une note clinique (≤ 3 phrases) sur les priorités de la semaine.

        Retourne "" en cas d'échec LLM.
        """
        summary = plan.get("weekly_summary", {})
        identity = view.get("identity", {})
        weekly = view.get("weekly_volumes", {})

        user_content = (
            f"Athlète : {identity.get('first_name', 'N/A')}, "
            f"{identity.get('weight_kg', 0)} kg.\n"
            f"TDEE estimé : {summary.get('tdee_estimated', 0)} kcal/jour.\n"
            f"Macros moyennes : "
            f"{summary.get('avg_macros_g', {}).get('protein_g', 0)}g P / "
            f"{summary.get('avg_macros_g', {}).get('carbs_g', 0)}g G / "
            f"{summary.get('avg_macros_g', {}).get('fat_g', 0)}g L.\n"
            f"Volume semaine : {weekly.get('total_training_hours', 0)}h "
            f"({weekly.get('running_km', 0)} km course, "
            f"{weekly.get('lifting_sessions', 0)} séances lifting).\n"
            f"Suppléments actuels : {summary.get('active_supplements', [])}.\n"
            "Génère une note clinique de 2-3 phrases. "
            "Priorités nutritionnelles clés pour cette semaine. "
            "Factuel. Chiffré. Zéro encouragement."
        )

        try:
            response = self._client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=200,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
            )
            raw = response.content[0].text.strip()
            return raw[:600]
        except Exception:
            return ""
