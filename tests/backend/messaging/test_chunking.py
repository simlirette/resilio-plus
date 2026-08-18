from dataclasses import FrozenInstanceError

import pytest
from app.messaging import Button, MessagingChannel, chunk_message


class ExampleChannel:
    name = "example"

    def send(self, external_id: str, text: str) -> str:
        return f"{external_id}:{text}"

    def send_with_buttons(
        self,
        external_id: str,
        text: str,
        buttons: list[Button],
    ) -> str:
        return f"{external_id}:{text}:{len(buttons)}"

    def max_message_length(self) -> int:
        return 1_000

    def format(self, text: str) -> str:
        return text


class IncompleteChannel:
    name = "incomplete"

    def send(self, external_id: str, text: str) -> str:
        return f"{external_id}:{text}"


def test_button_is_immutable_and_keeps_token_opaque() -> None:
    button = Button(label="Open workout", token="opaque:workout/42?day=easy")

    assert button.label == "Open workout"
    assert button.token == "opaque:workout/42?day=easy"
    with pytest.raises(FrozenInstanceError):
        button.token = "replacement"  # type: ignore[misc]


def test_messaging_channel_is_runtime_checkable() -> None:
    assert isinstance(ExampleChannel(), MessagingChannel)


def test_incomplete_channel_does_not_conform_at_runtime() -> None:
    assert not isinstance(IncompleteChannel(), MessagingChannel)


@pytest.mark.parametrize("max_length", [0, -1])
def test_chunk_message_rejects_non_positive_limit(max_length: int) -> None:
    with pytest.raises(ValueError, match="max_length must be positive"):
        chunk_message("content", max_length)


def test_chunk_message_returns_no_chunks_for_empty_text() -> None:
    assert chunk_message("", 10) == []


def test_chunk_message_keeps_text_exactly_at_boundary_unchanged() -> None:
    text = "x" * 20

    assert chunk_message(text, 20) == [text]


def test_chunk_message_prefers_paragraph_boundary() -> None:
    text = "Alpha paragraph.\n\nBeta paragraph."

    assert chunk_message(text, 20) == ["Alpha paragraph.\n\n", "Beta paragraph."]


def test_chunk_message_falls_back_to_sentence_boundary() -> None:
    text = "First sentence. Second sentence."

    assert chunk_message(text, 20) == ["First sentence. ", "Second sentence."]


def test_chunk_message_hard_cuts_when_no_natural_boundary_exists() -> None:
    text = "abcdefghijklmnopqrstuvwxyz"

    assert chunk_message(text, 10) == ["abcdefghij", "klmnopqrst", "uvwxyz"]


def test_chunk_message_never_splits_fenced_code_block() -> None:
    code_block = "```python\nvalue = 'abcdefghijklmnopqrstuvwxyz'\n```\n"
    text = f"Before.\n{code_block}After."

    chunks = chunk_message(text, 20)

    assert "".join(chunks) == text
    assert code_block in chunks
    assert len(code_block) > 20


def test_fence_with_trailing_content_does_not_close_code_block() -> None:
    code_block = "```python\nalpha\n```not-a-close\nomega\n```\n"

    chunks = chunk_message(code_block, 18)

    assert chunks == [code_block]


def test_unclosed_fence_remains_atomic_to_end_of_text() -> None:
    code_block = "```python\n" + ("value\n" * 8)
    text = f"Before.\n{code_block}"

    chunks = chunk_message(text, 18)

    assert "".join(chunks) == text
    assert code_block in chunks


def test_four_backtick_fence_requires_equal_or_longer_closer() -> None:
    code_block = "````python\nalpha\n```\nomega\n````\n"

    chunks = chunk_message(code_block, 18)

    assert chunks == [code_block]


def test_chunk_message_never_splits_single_bullet_line() -> None:
    bullet = f"- {'a' * 40}\n"
    text = f"Warm-up.\n{bullet}Cool-down."

    chunks = chunk_message(text, 15)

    assert "".join(chunks) == text
    assert bullet in chunks
    assert len(bullet) > 15


def test_chunk_message_never_splits_ordered_list_line() -> None:
    bullet = f"1. {'b' * 40}\n"
    text = f"Before.\n{bullet}After."

    chunks = chunk_message(text, 15)

    assert "".join(chunks) == text
    assert bullet in chunks


def test_chunk_message_greedily_packs_short_protected_units() -> None:
    text = "Intro.\n- One\n- Two\n- Three\nOutro."

    assert chunk_message(text, 20) == [
        "Intro.\n- One\n- Two\n",
        "- Three\nOutro.",
    ]


def test_chunk_message_safely_chunks_long_plan() -> None:
    plan_fragment = "Run easy today. Recover fully tomorrow.\n\n"
    text = (plan_fragment * 400)[:12_000]

    chunks = chunk_message(text, 500)

    assert len(text) == 12_000
    assert len(chunks) > 1
    assert "".join(chunks) == text
    assert all(len(chunk) <= 500 for chunk in chunks)
