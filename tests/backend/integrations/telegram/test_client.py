from __future__ import annotations

import logging

import httpx
import pytest
import respx
from app.integrations.telegram.client import TelegramAPIError, TelegramBotClient


@pytest.fixture
def telegram_api():
    with respx.mock(base_url="https://api.telegram.org") as mock:
        yield mock


def test_send_message_posts_html_payload_and_returns_provider_id(telegram_api) -> None:
    route = telegram_api.post("/botbot-token/sendMessage").mock(
        return_value=httpx.Response(
            200,
            json={"ok": True, "result": {"message_id": 321}},
        )
    )

    client = TelegramBotClient("bot-token")
    try:
        provider_id = client.send_message("12345", "<b>Ready</b>")
    finally:
        client.close()

    assert provider_id == "321"
    request_payload = route.calls.last.request.content
    assert request_payload == (
        b'{"chat_id":"12345","text":"<b>Ready</b>","parse_mode":"HTML"}'
    )


def test_rate_limit_retries_after_telegram_requested_delay(telegram_api) -> None:
    route = telegram_api.post("/botbot-token/sendMessage").mock(
        side_effect=[
            httpx.Response(
                429,
                json={
                    "ok": False,
                    "error_code": 429,
                    "parameters": {"retry_after": 7},
                },
            ),
            httpx.Response(200, json={"ok": True, "result": {"message_id": 99}}),
        ]
    )
    delays: list[float] = []

    client = TelegramBotClient("bot-token", sleeper=delays.append)
    try:
        provider_id = client.send_message("12345", "Ready")
    finally:
        client.close()

    assert provider_id == "99"
    assert route.call_count == 2
    assert delays == [7.0]


def test_answer_callback_query_posts_callback_identifier(telegram_api) -> None:
    route = telegram_api.post("/botbot-token/answerCallbackQuery").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": True})
    )

    client = TelegramBotClient("bot-token")
    try:
        accepted = client.answer_callback_query("callback-7")
    finally:
        client.close()

    assert accepted is True
    assert route.calls.last.request.content == b'{"callback_query_id":"callback-7"}'


def test_set_webhook_sends_url_and_secret_token(telegram_api) -> None:
    route = telegram_api.post("/botbot-token/setWebhook").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": True})
    )

    client = TelegramBotClient("bot-token")
    try:
        accepted = client.set_webhook(
            "https://coach.example/integrations/telegram/webhook",
            "webhook-secret",
        )
    finally:
        client.close()

    assert accepted is True
    assert route.calls.last.request.content == (
        b'{"url":"https://coach.example/integrations/telegram/webhook",'
        b'"secret_token":"webhook-secret"}'
    )


def test_get_updates_sends_long_poll_offset_and_returns_updates(telegram_api) -> None:
    updates = [{"update_id": 41, "message": {"text": "hello"}}]
    route = telegram_api.post("/botbot-token/getUpdates").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": updates})
    )

    client = TelegramBotClient("bot-token")
    try:
        result = client.get_updates(offset=40, timeout=10)
    finally:
        client.close()

    assert result == updates
    assert route.calls.last.request.content == b'{"timeout":10,"offset":40}'


def test_send_chat_action_posts_typing_before_long_work(telegram_api) -> None:
    route = telegram_api.post("/botbot-token/sendChatAction").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": True})
    )

    client = TelegramBotClient("bot-token")
    try:
        accepted = client.send_chat_action("12345")
    finally:
        client.close()

    assert accepted is True
    assert route.calls.last.request.content == b'{"chat_id":"12345","action":"typing"}'


def test_send_message_includes_inline_keyboard_when_provided(telegram_api) -> None:
    route = telegram_api.post("/botbot-token/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {"message_id": 8}})
    )
    keyboard = {
        "inline_keyboard": [
            [{"text": "Approve", "callback_data": "opaque-token"}],
        ]
    }

    client = TelegramBotClient("bot-token")
    try:
        client.send_message("12345", "Choose", reply_markup=keyboard)
    finally:
        client.close()

    assert route.calls.last.request.content == (
        b'{"chat_id":"12345","text":"Choose","parse_mode":"HTML",'
        b'"reply_markup":{"inline_keyboard":[[{"text":"Approve",'
        b'"callback_data":"opaque-token"}]]}}'
    )


def test_rate_limit_envelope_retries_even_when_http_status_is_200(telegram_api) -> None:
    route = telegram_api.post("/botbot-token/sendMessage").mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "ok": False,
                    "error_code": 429,
                    "parameters": {"retry_after": 2},
                },
            ),
            httpx.Response(200, json={"ok": True, "result": {"message_id": 10}}),
        ]
    )
    delays: list[float] = []

    client = TelegramBotClient("bot-token", sleeper=delays.append)
    try:
        provider_id = client.send_message("12345", "Ready")
    finally:
        client.close()

    assert provider_id == "10"
    assert route.call_count == 2
    assert delays == [2.0]


def test_rate_limit_retry_is_bounded_to_three_total_attempts(telegram_api) -> None:
    response = httpx.Response(
        429,
        json={
            "ok": False,
            "error_code": 429,
            "parameters": {"retry_after": 1},
        },
    )
    route = telegram_api.post("/botbot-token/sendMessage").mock(
        side_effect=[response, response, response, response]
    )
    delays: list[float] = []

    client = TelegramBotClient("bot-token", sleeper=delays.append)
    try:
        with pytest.raises(TelegramAPIError, match="sendMessage failed"):
            client.send_message("12345", "Ready")
    finally:
        client.close()

    assert route.call_count == 3
    assert delays == [1.0, 1.0]


def test_rate_limit_delay_is_bounded(telegram_api) -> None:
    telegram_api.post("/botbot-token/sendMessage").mock(
        side_effect=[
            httpx.Response(
                429,
                json={
                    "ok": False,
                    "error_code": 429,
                    "parameters": {"retry_after": 86_400},
                },
            ),
            httpx.Response(200, json={"ok": True, "result": {"message_id": 10}}),
        ]
    )
    delays: list[float] = []
    client = TelegramBotClient("bot-token", sleeper=delays.append)
    try:
        client.send_message("12345", "Ready")
    finally:
        client.close()

    assert delays == [60.0]


def test_non_finite_rate_limit_delay_uses_safe_default(telegram_api) -> None:
    telegram_api.post("/botbot-token/sendMessage").mock(
        side_effect=[
            httpx.Response(
                429,
                content=(
                    b'{"ok":false,"error_code":429,'
                    b'"parameters":{"retry_after":Infinity}}'
                ),
                headers={"Content-Type": "application/json"},
            ),
            httpx.Response(200, json={"ok": True, "result": {"message_id": 10}}),
        ]
    )
    delays: list[float] = []
    client = TelegramBotClient("bot-token", sleeper=delays.append)
    try:
        client.send_message("12345", "Ready")
    finally:
        client.close()

    assert delays == [1.0]


def test_transport_error_is_sanitized_without_bot_token(telegram_api) -> None:
    request = httpx.Request(
        "POST",
        "https://api.telegram.org/botvery-secret-token/sendMessage",
    )
    route = telegram_api.post("/botvery-secret-token/sendMessage").mock(
        side_effect=httpx.ConnectError(
            "failed https://api.telegram.org/botvery-secret-token/sendMessage",
            request=request,
        )
    )

    client = TelegramBotClient("very-secret-token")
    try:
        with pytest.raises(TelegramAPIError) as exc_info:
            client.send_message("12345", "Ready")
    finally:
        client.close()

    assert "very-secret-token" not in str(exc_info.value)
    assert str(exc_info.value) == "Telegram sendMessage transport failed"
    assert exc_info.value.__context__ is None
    assert route.call_count == 1


def test_server_error_is_not_retried(telegram_api) -> None:
    route = telegram_api.post("/botbot-token/sendMessage").mock(
        return_value=httpx.Response(
            500,
            json={"ok": False, "error_code": 500, "description": "failure"},
        )
    )
    delays: list[float] = []
    client = TelegramBotClient("bot-token", sleeper=delays.append)
    try:
        with pytest.raises(TelegramAPIError, match="sendMessage failed"):
            client.send_message("12345", "Ready")
    finally:
        client.close()

    assert route.call_count == 1
    assert delays == []


def test_httpx_request_log_redacts_bot_token(
    caplog: pytest.LogCaptureFixture,
    telegram_api,
) -> None:
    telegram_api.post("/botvery-secret-token/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})
    )
    caplog.set_level(logging.INFO, logger="httpx")

    client = TelegramBotClient("very-secret-token")
    try:
        client.send_message("12345", "Ready")
    finally:
        client.close()

    rendered_logs = "\n".join(record.getMessage() for record in caplog.records)
    assert "very-secret-token" not in rendered_logs
    assert "/bot***/sendMessage" in rendered_logs


def test_client_applies_fifteen_second_timeout_to_bot_api_requests(telegram_api) -> None:
    observed_timeouts: list[dict[str, float | None]] = []

    def respond(request: httpx.Request) -> httpx.Response:
        observed_timeouts.append(request.extensions["timeout"])
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})

    telegram_api.post("/botbot-token/sendMessage").mock(side_effect=respond)
    client = TelegramBotClient("bot-token")
    try:
        client.send_message("12345", "Ready")
    finally:
        client.close()

    assert observed_timeouts == [
        {"connect": 15.0, "read": 15.0, "write": 15.0, "pool": 15.0}
    ]
