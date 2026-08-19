from __future__ import annotations

import json

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
