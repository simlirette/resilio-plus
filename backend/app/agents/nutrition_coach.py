from __future__ import annotations

from ..agents.base import AgentContext, AgentRecommendation, BaseAgent
from ..core.nutrition_logic import compute_nutrition_directives
from ..schemas.fatigue import FatigueScore


class NutritionCoach(BaseAgent):
    """Specialist agent for nutrition: carb periodization by day type.

    Does not generate physical sessions. Produces nutrition directives
    as structured notes. weekly_load = 0, readiness_modifier = 1.0.
    """

    @property
    def name(self) -> str:
        return "nutrition"

    def analyze(self, context: AgentContext) -> AgentRecommendation:
        plan = compute_nutrition_directives(context.athlete)

        lines = []
        for day_type, dn in plan.targets_by_day_type.items():
            mt = dn.macro_target
            line = (
                f"{day_type.value}: carbs={mt.carbs_g_per_kg}g/kg "
                f"protein={mt.protein_g_per_kg}g/kg "
                f"kcal≈{mt.calories_total}"
            )
            if dn.intra_effort_carbs_g_per_h:
                line += f" | intra: {dn.intra_effort_carbs_g_per_h}g/h"
            lines.append(line)

        return AgentRecommendation(
            agent_name=self.name,
            fatigue_score=FatigueScore(
                local_muscular=0.0, cns_load=0.0, metabolic_cost=0.0,
                recovery_hours=0.0, affected_muscles=[],
            ),
            weekly_load=0.0,
            suggested_sessions=[],
            readiness_modifier=1.0,
            notes="\n".join(lines),
        )
