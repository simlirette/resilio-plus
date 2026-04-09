"""
RecoveryCoachAgent — portier biométrique de Resilio+.

Enchaîne RecoveryPrescriber (calcul déterministe) + appel LLM Anthropic
pour générer une note factuelle biométrique (≤ 2 phrases).
"""
from pathlib import Path

import anthropic

from agents.base_agent import BaseAgent
from agents.recovery_coach.prescriber import RecoveryPrescriber
from core.config import settings
from models.views import AgentType

_SYSTEM_PROMPT = (Path(__file__).parent / "recovery_coach_system_prompt.md").read_text(
    encoding="utf-8"
)


class RecoveryCoachAgent(BaseAgent):
    """Agent Recovery Coach — calcule le Readiness Score et génère un constat biométrique."""

    agent_type = AgentType.recovery_coach

    def __init__(self) -> None:
        self._prescriber = RecoveryPrescriber()
        self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def prescribe(self, view: dict) -> dict:
        """
        Évalue la capacité physiologique de l'athlète.

        Retourne un verdict structuré (pas de sessions[]) :
        readiness_score, color, factors, modification_params, overtraining_alert, notes.
        """
        verdict = self._prescriber.evaluate(view)
        verdict["notes"] = self._get_coaching_notes(view, verdict)
        return verdict

    def _get_coaching_notes(self, view: dict, verdict: dict) -> str:
        """
        Génère un constat biométrique factuel via LLM (≤ 2 phrases, style clinique).

        Retourne "" en cas d'échec LLM.
        """
        fatigue = view.get("fatigue", {})
        factors = verdict["factors"]

        user_content = (
            f"Readiness Score : {verdict['readiness_score']}/100 → {verdict['color'].upper()}.\n"
            f"HRV RMSSD : {fatigue.get('hrv_rmssd_today')} ms "
            f"(baseline {fatigue.get('hrv_rmssd_baseline')} ms) → score {factors['hrv_score']}/100.\n"
            f"Sommeil : {fatigue.get('sleep_hours_last_night')}h, "
            f"qualité {fatigue.get('sleep_quality_subjective')}/10 → score {factors['sleep_score']}/100.\n"
            f"ACWR global : {fatigue.get('acwr')} → score {factors['acwr_score']}/100.\n"
            f"FC repos : {fatigue.get('hr_rest_today')} bpm → score {factors['hr_rest_score']}/100.\n"
            f"Fatigue subjective : {fatigue.get('fatigue_subjective')}/10 → score {factors['subjective_score']}/100.\n"
            f"Surentraînement détecté : {verdict['overtraining_alert']}.\n"
            "Génère un constat biométrique en 1-2 phrases. Factuel. Chiffré. Zéro encouragement."
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
