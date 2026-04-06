# agents/running_coach/agent.py
"""
Running Coach Agent — S5 stub sans appel LLM.
S6 : prescribe() sera remplacé par un appel Anthropic avec system_prompt.
"""

from agents.base_agent import BaseAgent
from models.views import AgentType


class RunningCoachAgent(BaseAgent):
    """Agent Running Coach — stub déterministe S5."""

    agent_type = AgentType.running_coach

    def prescribe(self, view: dict) -> dict:
        """
        S5 : stub déterministe sans LLM.
        Retourne une séance easy run basée sur le VDOT de l'athlète.
        """
        vdot = view.get("running_profile", {}).get("vdot", 35.0)
        return {
            "agent": "running_coach",
            "sessions": [
                {
                    "day": "tuesday",
                    "type": "easy_run",
                    "description": f"Easy run 45min @ Z1 (VDOT {vdot:.1f})",
                    "duration_min": 45,
                    "zone": "Z1",
                }
            ],
            "weekly_km_prescribed": 8.0,
            "notes": "S5 stub — prescription LLM en S6.",
        }
