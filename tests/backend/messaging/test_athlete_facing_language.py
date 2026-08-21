"""Everything the athlete reads is in French.

The coach prompts are French and answer in French, but the transport around
them was written in English: the approval buttons said "Approve / Change /
Skip this week", `/help` listed its commands in English, and a failed calendar
push apologised in English. Half a conversation in each language.

The interesting part is not the translation, it is the guard. A new message
added in English months from now is exactly the kind of thing nobody notices
in review, so this scans the athlete-facing constants for English function
words rather than pinning each string.

Scope is deliberately the transport layer. Log messages, exception text and
docstrings stay English -- they are read by whoever maintains this, not by the
athlete.
"""
from __future__ import annotations

import ast
import pathlib
import re

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]

# Modules whose string constants reach the athlete verbatim.
ATHLETE_FACING = [
    "backend/app/messaging/approval_service.py",
    "backend/app/messaging/commands.py",
    "backend/app/messaging/plan_renderer.py",
]

# Function words that do not occur in French. Content words are avoided on
# purpose: "sessions", "plan", "format" and "calendar" are all fine in French.
ENGLISH_MARKERS = {
    "the", "your", "you", "is", "was", "are", "will", "with", "and", "not",
    "this", "that", "there", "here", "what", "when", "which", "from", "have",
    "has", "for", "yet", "any", "some", "already", "nothing", "whenever",
    "could", "would", "should", "about", "into", "again", "than", "them",
    "they", "week", "day", "days", "understand", "connect", "connected",
}

MIN_WORDS = 3


def _string_constants(path: pathlib.Path) -> list[tuple[int, str]]:
    """Every string literal that is not documentation.

    A bare string used as a statement is a docstring -- module, class, function,
    or the attribute-docstring form that follows a dataclass field. None of
    those reach the athlete, and they stay English.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))

    documentation: set[int] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            documentation.add(id(node.value))

    return [
        (node.lineno, node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in documentation
    ]


_CODE_SPAN = re.compile(r"`[^`]*`")


def _english_words(text: str) -> set[str]:
    """English function words in `text`, ignoring inline-code spans.

    Command names are literals, not prose: `/connect` must not read as the
    English verb, while a bare "not connected" in a status line still must.
    """
    prose = _CODE_SPAN.sub(" ", text)
    words = {
        "".join(ch for ch in token if ch.isalpha()).lower()
        for token in prose.split()
    }
    return words & ENGLISH_MARKERS


def _candidates(path: pathlib.Path) -> list[tuple[int, str]]:
    """Sentence-like literals -- the ones a person would actually read."""
    return [
        (line, value)
        for line, value in _string_constants(path)
        if len([w for w in value.split() if any(c.isalpha() for c in w)]) >= MIN_WORDS
    ]


@pytest.mark.parametrize("module", ATHLETE_FACING)
def test_no_athlete_facing_string_is_english(module: str) -> None:
    path = REPO_ROOT / module
    assert path.is_file(), f"{module} moved; update this test"

    offenders = [
        f"  line {line}: {sorted(hits)} -> {value[:70]!r}"
        for line, value in _candidates(path)
        if (hits := _english_words(value))
    ]

    assert not offenders, "English text reaches the athlete in {}:\n{}".format(
        module, "\n".join(offenders)
    )


class TestTheGuardActuallyCatchesThings:
    """A scanner that cannot fail is worse than none."""

    def test_an_english_sentence_is_detected(self) -> None:
        assert _english_words("Plan approved and written to your calendar")

    def test_a_french_sentence_is_clean(self) -> None:
        assert not _english_words(
            "Semaine approuvée et écrite dans ton agenda Resilio Training."
        )

    def test_shared_words_do_not_false_positive(self) -> None:
        """French keeps 'plan', 'format', 'sessions', 'calendar' as 'agenda'."""
        assert not _english_words("Plan de la semaine : 4 sessions, format long.")

    def test_a_command_name_is_not_read_as_prose(self) -> None:
        assert not _english_words("- `/connect` — liens pour connecter Strava")

    def test_english_outside_a_code_span_is_still_caught(self) -> None:
        assert _english_words("- `/status` — what is connected")


class TestTheButtonsSpecifically:
    """The three most-seen strings in the product."""

    def test_the_approval_buttons_are_french(self) -> None:
        from app.messaging.approval_service import (
            APPROVE_LABEL,
            REJECT_LABEL,
            REVISE_LABEL,
        )

        for label in (APPROVE_LABEL, REVISE_LABEL, REJECT_LABEL):
            assert not _english_words(label), f"{label!r} is English"

    def test_the_revision_prompt_is_french(self) -> None:
        from app.messaging.approval_service import _REVISION_PROMPT

        assert not _english_words(_REVISION_PROMPT)
