"""Contract: coaching skills and CLAUDE.md keep the lifting workflow wired (both skill trees)."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TREES = (".claude/skills", ".agents/skills")


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


@pytest.mark.parametrize("tree", TREES)
@pytest.mark.parametrize("skill,needles", [
    ("weekly-plan-generate/SKILL.md", ["resilio lift suggest-loads", "references/lifting_weekly.md"]),
    ("weekly-plan-apply/SKILL.md", ["resilio lift push --week"]),
    ("macro-plan-create/SKILL.md", ["resilio lift blocks set", "references/lifting_macro.md"]),
    ("weekly-analysis/SKILL.md", ["resilio lift adherence", "resilio lift volume"]),
    ("first-session/SKILL.md", ["resilio lift profile set", "resilio lift sync"]),
])
def test_skills_reference_lifting_commands(tree, skill, needles):
    text = _read(f"{tree}/{skill}")
    for needle in needles:
        assert needle in text, f"{tree}/{skill} lost '{needle}'"


@pytest.mark.parametrize("tree", TREES)
def test_lifting_references_exist(tree):
    assert "strength_sessions" in _read(f"{tree}/weekly-plan-generate/references/lifting_weekly.md")
    assert "lifting_blocks" in _read(f"{tree}/macro-plan-create/references/lifting_macro.md")


@pytest.mark.parametrize("doc", ["CLAUDE.md", "AGENTS.md"])
def test_root_docs_have_lifting_rules(doc):
    text = _read(doc)
    assert "## Lifting (Hevy)" in text
    assert "resilio lift push --week N" in text
    assert "never invent a load" in text.lower() or "never invent a load" in text


def test_methodology_doc_exists():
    assert "double progression" in _read("docs/coaching/lifting_methodology.md").lower()
