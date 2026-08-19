from __future__ import annotations

import pytest
from app.integrations.telegram.channel import TelegramChannel
from app.messaging.base import Button, MessagingChannel
from app.messaging.chunking import chunk_message


class RecordingTelegramClient:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str, dict[str, object] | None]] = []
        self.actions: list[tuple[str, str]] = []
        self.callbacks: list[str] = []

    def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        reply_markup: dict[str, object] | None = None,
    ) -> str:
        self.messages.append((chat_id, text, reply_markup))
        return "provider-1"

    def send_chat_action(self, chat_id: str, action: str = "typing") -> bool:
        self.actions.append((chat_id, action))
        return True

    def answer_callback_query(self, callback_query_id: str) -> bool:
        self.callbacks.append(callback_query_id)
        return True


def test_telegram_channel_implements_messaging_channel_protocol() -> None:
    assert isinstance(TelegramChannel(RecordingTelegramClient()), MessagingChannel)


def test_format_escapes_html_and_preserves_em_dash() -> None:
    channel = TelegramChannel(RecordingTelegramClient())

    formatted = channel.format("Keep < 5 km & stay easy — today")

    assert formatted == "Keep &lt; 5 km &amp; stay easy — today"


def test_format_converts_supported_markdown_subset_to_safe_html() -> None:
    channel = TelegramChannel(RecordingTelegramClient())

    formatted = channel.format(
        "**Strong <effort>**\n"
        "*Easy & calm*\n"
        "`2 < 3 & 4`\n"
        "- Run — easy\n"
        "* Lift\n"
        "Unmatched * stays"
    )

    assert formatted == (
        "<b>Strong &lt;effort&gt;</b>\n"
        "<i>Easy &amp; calm</i>\n"
        "<code>2 &lt; 3 &amp; 4</code>\n"
        "• Run — easy\n"
        "• Lift\n"
        "Unmatched * stays"
    )


def test_channel_limit_chunks_after_exact_4096_character_boundary() -> None:
    channel = TelegramChannel(RecordingTelegramClient())

    chunks = chunk_message("x" * 4097, channel.max_message_length())

    assert channel.max_message_length() == 4096
    assert [len(chunk) for chunk in chunks] == [4096, 1]


def test_send_forwards_already_formatted_html_without_double_escape() -> None:
    client = RecordingTelegramClient()
    channel = TelegramChannel(client)

    provider_id = channel.send("12345", "<b>Ready &amp; steady</b>")

    assert provider_id == "provider-1"
    assert client.messages == [("12345", "<b>Ready &amp; steady</b>", None)]


def test_send_with_buttons_builds_one_inline_keyboard_row() -> None:
    client = RecordingTelegramClient()
    channel = TelegramChannel(client)

    provider_id = channel.send_with_buttons(
        "12345",
        "Choose",
        [
            Button(label="Approve", token="approve-token"),
            Button(label="Change", token="change-token"),
        ],
    )

    assert provider_id == "provider-1"
    assert client.messages == [
        (
            "12345",
            "Choose",
            {
                "inline_keyboard": [
                    [
                        {"text": "Approve", "callback_data": "approve-token"},
                        {"text": "Change", "callback_data": "change-token"},
                    ]
                ]
            },
        )
    ]


@pytest.mark.parametrize("token", ["", "é" * 33])
def test_send_with_buttons_rejects_callback_data_outside_telegram_byte_limit(
    token: str,
) -> None:
    channel = TelegramChannel(RecordingTelegramClient())

    with pytest.raises(ValueError, match="1 to 64 UTF-8 bytes"):
        channel.send_with_buttons(
            "12345",
            "Choose",
            [Button(label="Approve", token=token)],
        )


def test_send_typing_delegates_to_telegram_chat_action() -> None:
    client = RecordingTelegramClient()
    channel = TelegramChannel(client)

    channel.send_typing("12345")

    assert client.actions == [("12345", "typing")]


def test_answer_callback_query_stops_telegram_spinner() -> None:
    client = RecordingTelegramClient()
    channel = TelegramChannel(client)

    channel.answer_callback_query("callback-7")

    assert client.callbacks == ["callback-7"]
