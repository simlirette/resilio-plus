# agents/lifting_coach/agent.py
"""
Lifting Coach Agent — S5 stub sans appel LLM.
S6/S7 : prescribe() sera remplacé par un appel Anthropic avec system_prompt.
"""

from agents.base_agent import BaseAgent
from models.views import AgentType


class LiftingCoachAgent(BaseAgent):
    """Agent Lifting Coach — stub déterministe S5."""

    agent_type = AgentType.lifting_coach

    def prescribe(self, view: dict) -> dict:
        """
        S5 : stub déterministe sans LLM.
        Retourne une séance upper body basée sur le split de l'athlète.
        """
        split = view.get("lifting_profile", {}).get("training_split", "upper_lower")
        return {
            "agent": "lifting_coach",
            "sessions": [
                {
                    "day": "monday",
                    "type": "upper_body",
                    "description": f"Upper Body — {split} split, Tier 1",
                    "exercises": ["Bench Press", "Pull-up", "OHP"],
                }
            ],
            "sessions_prescribed": 3,
            "notes": "S5 stub — prescription LLM en S7.",
        }
