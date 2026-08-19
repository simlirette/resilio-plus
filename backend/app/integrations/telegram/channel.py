from __future__ import annotations

import html
from typing import Protocol

from ...messaging.base import Button


class _TelegramMessageClient(Protocol):
    def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        reply_markup: dict[str, object] | None = None,
    ) -> str: ...

    def send_chat_action(self, chat_id: str, action: str = "typing") -> bool: ...

    def answer_callback_query(self, callback_query_id: str) -> bool: ...


class TelegramChannel:
    """Telegram implementation of the channel-neutral messaging contract."""

    name = "telegram"

    def __init__(self, client: _TelegramMessageClient) -> None:
        self._client = client

    def max_message_length(self) -> int:
        return 4096

    def send(self, external_id: str, text: str) -> str:
        return self._client.send_message(external_id, text)

    def send_typing(self, external_id: str) -> None:
        self._client.send_chat_action(external_id, "typing")

    def answer_callback_query(self, callback_query_id: str) -> None:
        self._client.answer_callback_query(callback_query_id)

    def send_with_buttons(
        self,
        external_id: str,
        text: str,
        buttons: list[Button],
    ) -> str:
        for button in buttons:
            token_bytes = len(button.token.encode("utf-8"))
            if not 1 <= token_bytes <= 64:
                raise ValueError("Telegram callback data must be 1 to 64 UTF-8 bytes")
        keyboard = [
            [
                {"text": button.label, "callback_data": button.token}
                for button in buttons
            ]
        ]
        return self._client.send_message(
            external_id,
            text,
            reply_markup={"inline_keyboard": keyboard},
        )

    def format(self, text: str) -> str:
        lines: list[str] = []
        for line in text.split("\n"):
            if line.startswith(("- ", "* ")):
                lines.append(f"• {_format_inline(line[2:])}")
            else:
                lines.append(_format_inline(line))
        return "\n".join(lines)


def _format_inline(text: str) -> str:
    output: list[str] = []
    literal_start = 0
    index = 0

    while index < len(text):
        marker: str | None = None
        tag: str | None = None
        if text[index] == "`":
            marker, tag = "`", "code"
        elif text.startswith("**", index):
            marker, tag = "**", "b"
        elif text[index] == "*":
            marker, tag = "*", "i"

        if marker is None or tag is None:
            index += 1
            continue

        closing = text.find(marker, index + len(marker))
        if closing <= index + len(marker):
            index += len(marker)
            continue

        output.append(html.escape(text[literal_start:index]))
        content = html.escape(text[index + len(marker) : closing])
        output.append(f"<{tag}>{content}</{tag}>")
        index = closing + len(marker)
        literal_start = index

    output.append(html.escape(text[literal_start:]))
    return "".join(output)
