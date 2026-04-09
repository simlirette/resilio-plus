"""
Lifting Coach Agent — agents/lifting_coach/agent.py
Orchestre LiftingPrescriber (déterministe) + Anthropic LLM (coaching_notes).
S7 : remplace le stub S5.
"""
from __future__ import annotations

import json
from pathlib import Path

import anthropic

from agents.base_agent import BaseAgent
from agents.lifting_coach.prescriber import LiftingPrescriber
from core.config import settings
from models.views import AgentType

_SYSTEM_PROMPT = (Path(__file__).parent / "system_prompt.md.txt").read_text()


class LiftingCoachAgent(BaseAgent):
    """Lifting Coach — prescription DUP + notes qualitatives via LLM."""

    agent_type = AgentType.lifting_coach

    def __init__(self) -> None:
        self._prescriber = LiftingPrescriber()
        self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def prescribe(self, view: dict) -> dict:
        plan = self._prescriber.build_week_plan(view)
        plan["coaching_notes"] = self._get_coaching_notes(view, plan)
        return plan

    def _get_coaching_notes(self, view: dict, plan: dict) -> list[str]:
        """Appel LLM Anthropic pour notes qualitatives. Fallback = [] si exception."""
        user_content = (
            f"Génère 3-5 coaching_notes techniques CONCISES pour ce plan de musculation :\n"
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
