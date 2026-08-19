from __future__ import annotations

import json

import pytest
import sentry_sdk
from app.observability.sentry import _sentry_pii_scrubber, init_sentry


def test_sentry_transaction_scrubber_removes_bot_token_from_httpx_span() -> None:
    token = "very-secret-bot-token"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    event = {
        "transaction": f"POST {url}",
        "request": {"url": url},
        "spans": [
            {
                "description": f"POST {url}",
                "data": {"http.request.url": url},
            }
        ],
    }

    scrubbed = _sentry_pii_scrubber(event, hint={})

    rendered = json.dumps(scrubbed)
    assert token not in rendered
    assert "https://api.telegram.org/bot***/sendMessage" in rendered


def test_sentry_registers_scrubber_for_transaction_events(monkeypatch) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setenv("SENTRY_DSN", "https://public@example.ingest.sentry.io/1")
    monkeypatch.setattr(sentry_sdk, "init", lambda **kwargs: captured.update(kwargs))

    init_sentry()

    assert captured["before_send_transaction"] is _sentry_pii_scrubber
    assert captured["include_local_variables"] is False


@pytest.mark.parametrize(
    "header_name",
    [
        "secret_token",
        "Secret_Token",
        "x-telegram-bot-api-secret-token",
        "X-Telegram-Bot-Api-Secret-Token",
    ],
)
def test_sentry_scrubber_redacts_telegram_webhook_secret_header(
    header_name: str,
) -> None:
    secret = "webhook-auth-secret"
    event = {"request": {"headers": {header_name: secret}}}

    scrubbed = _sentry_pii_scrubber(event, hint={})

    assert scrubbed["request"]["headers"][header_name] == "***"
    assert secret not in json.dumps(scrubbed)


@pytest.mark.parametrize(
    ("payload", "sensitive_values"),
    [
        (
            {
                "update_id": 41,
                "message": {
                    "chat": {"id": 123456, "type": "private"},
                    "text": "athlete health concern",
                },
            },
            ["123456", "athlete health concern"],
        ),
        (
            {
                "update_id": 42,
                "callback_query": {
                    "id": "callback-identifier",
                    "data": "opaque-approval-token",
                },
            },
            ["callback-identifier", "opaque-approval-token"],
        ),
    ],
)
def test_sentry_scrubber_drops_telegram_webhook_request_body(
    payload: dict[str, object],
    sensitive_values: list[str],
) -> None:
    secret = "webhook-auth-secret"
    event = {
        "request": {
            "url": "https://coach.example/integrations/telegram/webhook?source=bot",
            "method": "POST",
            "headers": {
                "Content-Type": "application/json",
                "X-Telegram-Bot-Api-Secret-Token": secret,
            },
            "data": payload,
        }
    }

    scrubbed = _sentry_pii_scrubber(event, hint={})

    assert "data" not in scrubbed["request"]
    rendered = json.dumps(scrubbed)
    assert secret not in rendered
    assert all(value not in rendered for value in sensitive_values)
