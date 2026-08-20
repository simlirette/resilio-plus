"""The routing prompt must actually load.

`_PROMPT_PATH` used `parents[4]`, which from
`backend/app/services/classify_intent_service.py` resolves to the directory
*above* the repository. The file never existed there, so the loader silently
fell back to a 277-character inline stub while `docs/prompts/classify-intent.md`
— 82 KB, 1299 lines of routing rules — sat unused.

Every downstream symptom traces back here: the model invented decisions outside
the enum, emitted a ```json fence instead of the contract tags, and escalated
"jambes mortes" to an acute neuromuscular emergency. It was working from four
lines of instruction.

The silent fallback is the dangerous part, so this pins the path itself rather
than just the behaviour.
"""
from __future__ import annotations

from pathlib import Path

from app.services import classify_intent_service as svc

REPO_ROOT = Path(__file__).resolve().parents[3]
PROMPT_FILE = REPO_ROOT / "docs" / "prompts" / "classify-intent.md"


def test_the_prompt_file_is_where_we_think_it_is() -> None:
    assert PROMPT_FILE.is_file(), f"{PROMPT_FILE} is missing"


def test_the_configured_path_points_at_it() -> None:
    assert svc._PROMPT_PATH.resolve() == PROMPT_FILE.resolve(), (
        "the loader resolves outside the repository, so it silently uses the stub"
    )


def test_the_real_prompt_is_loaded_not_the_stub() -> None:
    assert len(svc._SYSTEM_PROMPT) > 10_000, (
        f"only {len(svc._SYSTEM_PROMPT)} chars loaded - that is the inline "
        "fallback, not the routing rules"
    )


def test_the_loaded_prompt_teaches_the_decision_enum() -> None:
    for decision in (
        "HEAD_COACH_DIRECT",
        "SPECIALIST_TECHNICAL",
        "CLINICAL_ESCALATION_IMMEDIATE",
        "OUT_OF_SCOPE",
        "CLARIFICATION_NEEDED",
    ):
        assert decision in svc._SYSTEM_PROMPT, f"{decision} not taught to the model"


def test_the_loaded_prompt_specifies_the_output_contract() -> None:
    assert "contract_payload" in svc._SYSTEM_PROMPT


def test_the_stub_is_still_there_for_a_trimmed_image() -> None:
    """A Docker image without docs/ must still start, just less well."""
    original = svc._PROMPT_PATH
    try:
        svc._PROMPT_PATH = Path("/definitely/not/here.md")
        fallback = svc._load_system_prompt()
    finally:
        svc._PROMPT_PATH = original

    assert "classify_intent" in fallback
    assert len(fallback) < 1000
