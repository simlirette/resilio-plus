"""
Running Coach Agent — agents/running_coach/agent.py
Orchestre RunningPrescriber (déterministe) + Anthropic LLM (coaching_notes).
S6 : remplace le stub S5.
"""
from __future__ import annotations

import json
from pathlib import Path

import anthropic

from agents.base_agent import BaseAgent
from agents.running_coach.prescriber import RunningPrescriber
from core.config import settings
from models.views import AgentType

_SYSTEM_PROMPT = (Path(__file__).parent / "running_coach_system_prompt.md").read_text()


class RunningCoachAgent(BaseAgent):
    """Running Coach — prescription VDOT + notes qualitatives via LLM."""

    agent_type = AgentType.running_coach

    def __init__(self) -> None:
        self._prescriber = RunningPrescriber()
        self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def prescribe(self, view: dict) -> dict:
        plan = self._prescriber.build_week_plan(view)
        plan["coaching_notes"] = self._get_coaching_notes(view, plan)
        return plan

    def _get_coaching_notes(self, view: dict, plan: dict) -> list[str]:
        """Appel LLM Anthropic pour les coaching notes qualitatives. Fallback = []."""
        user_content = (
            f"Génère 3-5 coaching_notes techniques CONCISES pour ce plan de course :\n"
            f"{json.dumps(plan, ensure_ascii=False, indent=2)}\n\n"
            f"Contexte athlète :\n{json.dumps(view, ensure_ascii=False, indent=2)}"
        )
        try:
            message = self._client.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=512,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
            )
            text = message.content[0].text
            lines = [
                line.strip().lstrip("-•*").strip()
                for line in text.split("\n")
                if line.strip()
            ]
            return [line for line in lines if line][:5]
        except Exception:
            return []
