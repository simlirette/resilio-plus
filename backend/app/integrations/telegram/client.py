from __future__ import annotations

import logging
import math
import re
import time
from collections.abc import Callable
from threading import Event
from typing import Any, cast

import httpx

_API_ROOT = "https://api.telegram.org"
_MAX_ATTEMPTS = 3
_MAX_RETRY_AFTER_SECONDS = 60.0


class _TelegramTokenLogFilter(logging.Filter):
    _token_path = re.compile(r"/bot[^/\s]+")

    def filter(self, record: logging.LogRecord) -> bool:
        rendered = record.getMessage()
        redacted = self._token_path.sub("/bot***", rendered)
        if redacted != rendered:
            record.msg = redacted
            record.args = ()
        return True


logging.getLogger("httpx").addFilter(_TelegramTokenLogFilter())


class TelegramAPIError(RuntimeError):
    """Raised when Telegram rejects a Bot API operation."""


class _TelegramRequestCancelledError(RuntimeError):
    """Internal signal used to stop a polling request between retries."""


class TelegramBotClient:
    """Small synchronous wrapper around the Telegram Bot API."""

    def __init__(
        self,
        token: str,
        *,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if not token.strip():
            raise ValueError("Telegram bot token must not be empty")
        self._token = token
        self._client = httpx.Client(timeout=15.0)
        self._sleeper = sleeper

    def close(self) -> None:
        self._client.close()

    def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        reply_markup: dict[str, object] | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        result = self._request("sendMessage", payload)
        if not isinstance(result, dict):
            raise TelegramAPIError("Telegram sendMessage returned an invalid result")
        message_id = result.get("message_id")
        if isinstance(message_id, bool) or not isinstance(message_id, (int, str)):
            raise TelegramAPIError("Telegram sendMessage omitted message_id")
        return str(message_id)

    def answer_callback_query(self, callback_query_id: str) -> bool:
        result = self._request(
            "answerCallbackQuery",
            {"callback_query_id": callback_query_id},
        )
        if not isinstance(result, bool):
            raise TelegramAPIError("Telegram answerCallbackQuery returned an invalid result")
        return result

    def set_webhook(self, url: str, secret_token: str) -> bool:
        result = self._request(
            "setWebhook",
            {"url": url, "secret_token": secret_token},
        )
        if not isinstance(result, bool):
            raise TelegramAPIError("Telegram setWebhook returned an invalid result")
        return result

    def get_updates(
        self,
        *,
        offset: int | None = None,
        timeout: int = 10,
        stop_event: Event | None = None,
    ) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"timeout": timeout}
        if offset is not None:
            payload["offset"] = offset
        try:
            result = self._request(
                "getUpdates",
                payload,
                stop_event=stop_event,
            )
        except _TelegramRequestCancelledError:
            return []
        if not isinstance(result, list) or not all(isinstance(item, dict) for item in result):
            raise TelegramAPIError("Telegram getUpdates returned an invalid result")
        return [cast(dict[str, Any], dict(item)) for item in result]

    def send_chat_action(self, chat_id: str, action: str = "typing") -> bool:
        result = self._request(
            "sendChatAction",
            {"chat_id": chat_id, "action": action},
        )
        if not isinstance(result, bool):
            raise TelegramAPIError("Telegram sendChatAction returned an invalid result")
        return result

    def _request(
        self,
        method: str,
        payload: dict[str, Any],
        *,
        stop_event: Event | None = None,
    ) -> object:
        for attempt in range(_MAX_ATTEMPTS):
            if stop_event is not None and stop_event.is_set():
                raise _TelegramRequestCancelledError
            response: httpx.Response | None
            try:
                response = self._client.post(
                    f"{_API_ROOT}/bot{self._token}/{method}",
                    json=payload,
                )
            except httpx.RequestError:
                response = None
            if response is None:
                # Raise after leaving the handler so the secret-bearing
                # RequestError is not retained as exception context.
                raise TelegramAPIError(f"Telegram {method} transport failed")
            try:
                body = response.json()
            except ValueError:
                raise TelegramAPIError(f"Telegram {method} returned invalid JSON") from None
            envelope_rate_limited = (
                isinstance(body, dict) and body.get("error_code") == 429
            )
            if (
                response.status_code == 429 or envelope_rate_limited
            ) and attempt < _MAX_ATTEMPTS - 1:
                delay = _retry_after(body, response)
                if stop_event is not None:
                    if stop_event.wait(delay):
                        raise _TelegramRequestCancelledError
                else:
                    self._sleeper(delay)
                continue
            if response.is_error or not isinstance(body, dict) or body.get("ok") is not True:
                raise TelegramAPIError(f"Telegram {method} failed")
            return body.get("result")
        raise AssertionError("unreachable")


def _retry_after(body: object, response: httpx.Response) -> float:
    if isinstance(body, dict):
        parameters = body.get("parameters")
        if isinstance(parameters, dict):
            value = parameters.get("retry_after")
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                try:
                    delay = float(value)
                except (OverflowError, ValueError):
                    pass
                else:
                    if math.isfinite(delay) and delay >= 0:
                        return min(delay, _MAX_RETRY_AFTER_SECONDS)
    header = response.headers.get("Retry-After")
    if header is not None:
        try:
            delay = float(header)
            if math.isfinite(delay):
                return min(max(0.0, delay), _MAX_RETRY_AFTER_SECONDS)
        except (OverflowError, ValueError):
            pass
    return 1.0
