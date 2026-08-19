from __future__ import annotations

import httpx
import pytest
import respx
from app.integrations.google_calendar.client import (
    API_BASE,
    GoogleCalendarClient,
    GoogleCalendarError,
    GoogleCalendarNotFoundError,
)

CAL = "cal-1"
EVENTS_URL = f"{API_BASE}/calendars/{CAL}/events"


def build(tokens: list[str] | None = None) -> tuple[GoogleCalendarClient, list[float]]:
    issued = list(tokens or ["token-1", "token-2", "token-3", "token-4"])
    slept: list[float] = []

    def provider() -> str:
        return issued.pop(0) if issued else "token-last"

    client = GoogleCalendarClient(provider, sleep=slept.append)
    return client, slept


@respx.mock(base_url="https://www.googleapis.com")
def test_insert_event_returns_the_created_event(respx_mock: respx.Router) -> None:
    route = respx_mock.post(f"/calendar/v3/calendars/{CAL}/events").mock(
        return_value=httpx.Response(200, json={"id": "evt-1"})
    )
    client, _ = build()

    assert client.insert_event(CAL, {"summary": "x"}) == {"id": "evt-1"}
    assert route.calls[0].request.headers["authorization"] == "Bearer token-1"


@respx.mock(base_url="https://www.googleapis.com")
def test_rate_limited_request_is_retried_with_backoff(
    respx_mock: respx.Router,
) -> None:
    respx_mock.post(f"/calendar/v3/calendars/{CAL}/events").mock(
        side_effect=[
            httpx.Response(429, json={"error": {"message": "slow down"}}),
            httpx.Response(200, json={"id": "evt-1"}),
        ]
    )
    client, slept = build()

    assert client.insert_event(CAL, {"summary": "x"}) == {"id": "evt-1"}
    assert slept == [1.0]


@respx.mock(base_url="https://www.googleapis.com")
def test_403_rate_limit_exceeded_is_retried(respx_mock: respx.Router) -> None:
    respx_mock.post(f"/calendar/v3/calendars/{CAL}/events").mock(
        side_effect=[
            httpx.Response(
                403,
                json={
                    "error": {
                        "message": "Rate Limit Exceeded",
                        "errors": [{"reason": "rateLimitExceeded"}],
                    }
                },
            ),
            httpx.Response(200, json={"id": "evt-1"}),
        ]
    )
    client, slept = build()

    assert client.insert_event(CAL, {"summary": "x"})["id"] == "evt-1"
    assert slept == [1.0]


@respx.mock(base_url="https://www.googleapis.com")
def test_403_permission_denied_fails_immediately(respx_mock: respx.Router) -> None:
    respx_mock.post(f"/calendar/v3/calendars/{CAL}/events").mock(
        return_value=httpx.Response(
            403,
            json={
                "error": {
                    "message": "Insufficient permission",
                    "errors": [{"reason": "insufficientPermissions"}],
                }
            },
        )
    )
    client, slept = build()

    with pytest.raises(GoogleCalendarError) as exc:
        client.insert_event(CAL, {"summary": "x"})

    assert exc.value.status_code == 403
    assert slept == []


@respx.mock(base_url="https://www.googleapis.com")
def test_401_refreshes_the_token_and_retries_once(respx_mock: respx.Router) -> None:
    route = respx_mock.post(f"/calendar/v3/calendars/{CAL}/events").mock(
        side_effect=[
            httpx.Response(401, json={"error": {"message": "expired"}}),
            httpx.Response(200, json={"id": "evt-1"}),
        ]
    )
    client, _ = build(["stale", "fresh"])

    assert client.insert_event(CAL, {"summary": "x"})["id"] == "evt-1"
    assert route.calls[0].request.headers["authorization"] == "Bearer stale"
    assert route.calls[1].request.headers["authorization"] == "Bearer fresh"


@respx.mock(base_url="https://www.googleapis.com")
def test_repeated_401_is_surfaced(respx_mock: respx.Router) -> None:
    respx_mock.post(f"/calendar/v3/calendars/{CAL}/events").mock(
        return_value=httpx.Response(401, json={"error": {"message": "expired"}})
    )
    client, _ = build()

    with pytest.raises(GoogleCalendarError) as exc:
        client.insert_event(CAL, {"summary": "x"})

    assert exc.value.status_code == 401


@respx.mock(base_url="https://www.googleapis.com")
def test_delete_tolerates_an_event_already_gone(respx_mock: respx.Router) -> None:
    respx_mock.delete(f"/calendar/v3/calendars/{CAL}/events/evt-1").mock(
        return_value=httpx.Response(404, json={"error": {"message": "Not Found"}})
    )
    client, _ = build()

    client.delete_event(CAL, "evt-1")  # must not raise


@respx.mock(base_url="https://www.googleapis.com")
def test_patch_on_a_missing_event_raises_not_found(respx_mock: respx.Router) -> None:
    respx_mock.patch(f"/calendar/v3/calendars/{CAL}/events/evt-1").mock(
        return_value=httpx.Response(404, json={"error": {"message": "Not Found"}})
    )
    client, _ = build()

    with pytest.raises(GoogleCalendarNotFoundError):
        client.patch_event(CAL, "evt-1", {"summary": "x"})


@respx.mock(base_url="https://www.googleapis.com")
def test_persistent_server_errors_give_up_after_the_retry_budget(
    respx_mock: respx.Router,
) -> None:
    respx_mock.post(f"/calendar/v3/calendars/{CAL}/events").mock(
        return_value=httpx.Response(503, json={"error": {"message": "unavailable"}})
    )
    client, slept = build()

    with pytest.raises(GoogleCalendarError):
        client.insert_event(CAL, {"summary": "x"})

    assert slept == [1.0, 2.0, 4.0]


@respx.mock(base_url="https://www.googleapis.com")
def test_create_calendar_sends_summary_and_timezone(
    respx_mock: respx.Router,
) -> None:
    route = respx_mock.post("/calendar/v3/calendars").mock(
        return_value=httpx.Response(200, json={"id": "cal-new"})
    )
    client, _ = build()

    assert client.create_calendar("Resilio Training", "America/Montreal") == {
        "id": "cal-new"
    }
    assert route.calls[0].request.read() == (
        b'{"summary":"Resilio Training","timeZone":"America/Montreal"}'
    )


@respx.mock(base_url="https://www.googleapis.com")
def test_empty_body_decodes_to_an_empty_dict(respx_mock: respx.Router) -> None:
    respx_mock.delete(f"/calendar/v3/calendars/{CAL}/events/evt-1").mock(
        return_value=httpx.Response(204)
    )
    client, _ = build()

    client.delete_event(CAL, "evt-1")
