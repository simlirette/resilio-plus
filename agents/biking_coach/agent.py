"""
BikingCoachAgent — prescripteur de séances vélo (Coggan FTP zones).

Enchaîne BikingPrescriber (calcul déterministe) + appel LLM Anthropic
pour générer une note clinique factuelle (≤ 2 phrases).
"""
from pathlib import Path

import anthropic

from agents.base_agent import BaseAgent
from agents.biking_coach.prescriber import BikingPrescriber
from core.config import settings
from models.views import AgentType

_SYSTEM_PROMPT = (Path(__file__).parent / "biking_coach_system_prompt.md").read_text(
    encoding="utf-8"
)


class BikingCoachAgent(BaseAgent):
    """Agent Biking Coach — prescrit des séances vélo basées sur le FTP (Coggan)."""

    agent_type = AgentType.biking_coach

    def __init__(self) -> None:
        self._prescriber = BikingPrescriber()
        self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def prescribe(self, view: dict) -> dict:
        """
        Prescrit un plan vélo hebdomadaire.

        Retourne un plan structuré :
        ftp_watts, weekly_volume_km, sessions[], coaching_notes[], notes.
        """
        plan = self._prescriber.prescribe(view)
        plan["notes"] = self._get_coaching_notes(view, plan)
        return plan

    def _get_coaching_notes(self, view: dict, plan: dict) -> str:
        """
        Génère une note clinique factuelle via LLM (≤ 2 phrases, style clinique).

        Retourne "" en cas d'échec LLM.
        """
        profile = view.get("biking_profile", {})
        ftp_watts = plan.get("ftp_watts")
        weekly_volume_km = plan.get("weekly_volume_km", 0.0)
        sessions = plan.get("sessions", [])

        session_types = [s.get("session_type", "") for s in sessions]
        session_summary = ", ".join(session_types) if session_types else "aucune"

        ftp_str = f"{ftp_watts} W" if ftp_watts is not None else "non défini (RPE)"

        user_content = (
            f"FTP : {ftp_str}.\n"
            f"Volume hebdomadaire vélo : {weekly_volume_km} km.\n"
            f"Sessions planifiées ({len(sessions)}) : {session_summary}.\n"
            "Génère un constat clinique en 1-2 phrases. Factuel. Chiffré. Zéro encouragement."
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
