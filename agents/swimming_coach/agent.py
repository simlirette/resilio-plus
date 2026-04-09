"""
SwimmingCoachAgent — prescripteur de séances natation CSS.

Enchaîne SwimmingPrescriber (calcul déterministe) + appel LLM Anthropic
pour générer une note clinique factuelle (≤ 2 phrases).
"""
from pathlib import Path

import anthropic

from agents.base_agent import BaseAgent
from agents.swimming_coach.prescriber import SwimmingPrescriber
from core.config import settings
from models.views import AgentType

_SYSTEM_PROMPT = (Path(__file__).parent / "swimming_coach_system_prompt.md").read_text(
    encoding="utf-8"
)


class SwimmingCoachAgent(BaseAgent):
    """Agent Swimming Coach — prescrit des séances natation basées sur la CSS."""

    agent_type = AgentType.swimming_coach

    def __init__(self) -> None:
        self._prescriber = SwimmingPrescriber()
        self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def prescribe(self, view: dict) -> dict:
        """
        Prescrit un plan natation hebdomadaire.

        Retourne un plan structuré :
        technique_level, css_sec_per_100m, sessions[], coaching_notes[], notes.
        """
        plan = self._prescriber.prescribe(view)
        plan["notes"] = self._get_coaching_notes(view, plan)
        return plan

    def _get_coaching_notes(self, view: dict, plan: dict) -> str:
        """
        Génère une note clinique factuelle via LLM (≤ 2 phrases, style clinique).

        Retourne "" en cas d'échec LLM.
        """
        profile = view.get("swimming_profile", {})
        technique_level = plan.get("technique_level", "beginner")
        css = plan.get("css_sec_per_100m", 150.0)
        session_count = len(plan.get("sessions", []))

        session_types = [s.get("session_type", "") for s in plan.get("sessions", [])]
        session_summary = ", ".join(session_types) if session_types else "aucune"

        user_content = (
            f"CSS : {css} s/100m.\n"
            f"Niveau technique : {technique_level}.\n"
            f"Sessions planifiées ({session_count}) : {session_summary}.\n"
            f"Volume hebdomadaire natation : {profile.get('weekly_volume_km', 0)} km.\n"
            "Génère un constat clinique en 1-2 phrases. Factuel. Chiffré. Zéro encouragement."
        )

        try:
            response = self._client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=150,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
            )
            raw = response.content[0].text.strip()
            return raw[:500]
        except Exception:
            return ""
