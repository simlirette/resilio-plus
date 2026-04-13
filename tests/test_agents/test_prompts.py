"""Structural tests for agent system prompts.

Tests are purely string-based — no LLM calls, no network, no API keys needed.
"""
from __future__ import annotations

import re

import pytest


# ---------------------------------------------------------------------------
# Import guard — will fail until prompts.py exists
# ---------------------------------------------------------------------------

from backend.app.agents.prompts import (
    ENERGY_COACH_PROMPT,
    HEAD_COACH_PROMPT,
    LIFTING_COACH_PROMPT,
    NUTRITION_COACH_PROMPT,
    RECOVERY_COACH_PROMPT,
    RUNNING_COACH_PROMPT,
)

ALL_PROMPTS = {
    "head_coach": HEAD_COACH_PROMPT,
    "running": RUNNING_COACH_PROMPT,
    "lifting": LIFTING_COACH_PROMPT,
    "recovery": RECOVERY_COACH_PROMPT,
    "nutrition": NUTRITION_COACH_PROMPT,
    "energy": ENERGY_COACH_PROMPT,
}

INTERNAL_AGENTS = ["running", "lifting", "recovery", "nutrition", "energy"]

# ---------------------------------------------------------------------------
# 1. All constants exist and are non-empty strings
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", list(ALL_PROMPTS.keys()))
def test_prompt_is_non_empty_string(name: str) -> None:
    prompt = ALL_PROMPTS[name]
    assert isinstance(prompt, str), f"{name}: expected str, got {type(prompt)}"
    assert len(prompt.strip()) > 100, f"{name}: prompt is suspiciously short"


# ---------------------------------------------------------------------------
# 2. No emojis
# ---------------------------------------------------------------------------

_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001F9FF"
    "\U00002600-\U000027BF"
    "\U0000FE00-\U0000FE0F"
    "\U00002702-\U000027B0"
    "]+",
    flags=re.UNICODE,
)

@pytest.mark.parametrize("name", list(ALL_PROMPTS.keys()))
def test_no_emojis(name: str) -> None:
    match = _EMOJI_PATTERN.search(ALL_PROMPTS[name])
    assert match is None, f"{name}: emoji found: {match.group()!r}"


# ---------------------------------------------------------------------------
# 3. No forbidden motivational vocabulary
# ---------------------------------------------------------------------------

_FORBIDDEN_WORDS = [
    "bravo", "super", "félicitations", "incroyable", "tu peux",
    "courage", "amazing", "great job", "well done", "keep it up",
    "excellent", "parfait",
]

@pytest.mark.parametrize("name", list(ALL_PROMPTS.keys()))
@pytest.mark.parametrize("word", _FORBIDDEN_WORDS)
def test_no_forbidden_vocabulary(name: str, word: str) -> None:
    prompt_lower = ALL_PROMPTS[name].lower()
    assert word.lower() not in prompt_lower, (
        f"{name}: forbidden word found: {word!r}"
    )


# ---------------------------------------------------------------------------
# 4. Hard limits present per agent
# ---------------------------------------------------------------------------

_HARD_LIMITS: dict[str, list[str]] = {
    "running": ["10%", "1.5"],
    "lifting": ["MRV", "RIR"],
    "recovery": ["70%", "6h", "non-overridable"],
    "energy": ["80", "non-overridable"],
    "nutrition": ["1.6", "500"],
    "head_coach": ["veto"],
}

@pytest.mark.parametrize("name,expected_strings", list(_HARD_LIMITS.items()))
def test_hard_limits_present(name: str, expected_strings: list[str]) -> None:
    prompt = ALL_PROMPTS[name]
    for s in expected_strings:
        assert s in prompt, f"{name}: expected hard-limit string not found: {s!r}"


# ---------------------------------------------------------------------------
# 5. Format contract — internal agents have required sections
# ---------------------------------------------------------------------------

_REQUIRED_SECTIONS = ["## ASSESSMENT", "## RECOMMENDATION", "## DATA"]

@pytest.mark.parametrize("name", INTERNAL_AGENTS)
def test_internal_format_sections_present(name: str) -> None:
    prompt = ALL_PROMPTS[name]
    for section in _REQUIRED_SECTIONS:
        assert section in prompt, (
            f"{name}: required section missing: {section!r}"
        )


# ---------------------------------------------------------------------------
# 6. VETO keyword in Recovery and Energy; absent from others
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["recovery", "energy"])
def test_veto_present_in_veto_agents(name: str) -> None:
    assert "VETO" in ALL_PROMPTS[name], f"{name}: 'VETO' keyword missing"


@pytest.mark.parametrize("name", ["running", "lifting", "nutrition"])
def test_veto_absent_from_non_veto_agents(name: str) -> None:
    # Head Coach is allowed to mention veto (it reacts to it)
    assert "VETO" not in ALL_PROMPTS[name], (
        f"{name}: unexpected 'VETO' keyword found"
    )
