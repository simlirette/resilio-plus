"""Thin httpx wrapper over the Google Calendar v3 REST API.

Deliberately not the official client library: this needs five calls, and the
repo's stack rule is httpx + no new dependencies.
"""
from __future__ import annotations

import logging
import time
from collections.abc import Callable, Mapping
from typing import Any

import httpx

logger = logging.getLogger(__name__)

API_BASE = "https://www.googleapis.com/calendar/v3"
TIMEOUT_S = 15.0

MAX_RETRIES = 4
BASE_BACKOFF_S = 1.0
MAX_BACKOFF_S = 60.0

_RETRYABLE_STATUS = (403, 429, 500, 502, 503, 504)
_RETRYABLE_REASONS = frozenset(
    {"rateLimitExceeded", "userRateLimitExceeded", "backendError"}
)


class GoogleCalendarError(RuntimeError):
    """A Google Calendar call failed in a way the caller cannot retry away."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Google Calendar API error {status_code}: {detail}")


class GoogleCalendarNotFoundError(GoogleCalendarError):
    """The calendar or event no longer exists upstream."""


class GoogleCalendarClient:
    """Authenticated calls against one athlete's Google Calendar.

    ``token_provider`` returns a currently valid access token; it is called
    again after a 401 so an expired token refreshes transparently.
    """

    def __init__(
        self,
        token_provider: Callable[[], str],
        *,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._token_provider = token_provider
        self._client = client or httpx.Client(timeout=TIMEOUT_S)
        self._owns_client = client is None
        self._sleep = sleep

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "GoogleCalendarClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # ─── Calendars ───────────────────────────────────────────────────────────

    def create_calendar(self, summary: str, time_zone: str) -> dict[str, Any]:
        return self._request(
            "POST",
            f"{API_BASE}/calendars",
            json={"summary": summary, "timeZone": time_zone},
        )

    def get_calendar(self, calendar_id: str) -> dict[str, Any]:
        return self._request("GET", f"{API_BASE}/calendars/{calendar_id}")

    # ─── Events ──────────────────────────────────────────────────────────────

    def insert_event(
        self, calendar_id: str, body: Mapping[str, Any]
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"{API_BASE}/calendars/{calendar_id}/events",
            json=dict(body),
        )

    def patch_event(
        self, calendar_id: str, event_id: str, body: Mapping[str, Any]
    ) -> dict[str, Any]:
        return self._request(
            "PATCH",
            f"{API_BASE}/calendars/{calendar_id}/events/{event_id}",
            json=dict(body),
        )

    def delete_event(self, calendar_id: str, event_id: str) -> None:
        try:
            self._request("DELETE", f"{API_BASE}/calendars/{calendar_id}/events/{event_id}")
        except GoogleCalendarNotFoundError:
            # Already gone upstream — the desired end state, not an error.
            logger.info("gcal_event_already_deleted")

    def list_events(
        self, calendar_id: str, **params: Any
    ) -> dict[str, Any]:
        return self._request(
            "GET",
            f"{API_BASE}/calendars/{calendar_id}/events",
            params=params,
        )

    # ─── Transport ───────────────────────────────────────────────────────────

    def _request(
        self,
        method: str,
        url: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        attempt = 0
        refreshed = False
        while True:
            token = self._token_provider()
            response = self._client.request(
                method,
                url,
                json=json,
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
            if response.status_code < 400:
                return _decode(response)

            if response.status_code == 401 and not refreshed:
                # Token provider is expected to mint a fresh token on the retry.
                refreshed = True
                continue

            if response.status_code == 404:
                raise GoogleCalendarNotFoundError(404, _error_detail(response))

            if (
                response.status_code in _RETRYABLE_STATUS
                and _is_retryable(response)
                and attempt < MAX_RETRIES - 1
            ):
                self._sleep(min(BASE_BACKOFF_S * (2**attempt), MAX_BACKOFF_S))
                attempt += 1
                continue

            raise GoogleCalendarError(response.status_code, _error_detail(response))


def _decode(response: httpx.Response) -> dict[str, Any]:
    if not response.content:
        return {}
    try:
        payload = response.json()
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text[:200]
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str):
            return message
    return str(payload)[:200]


def _is_retryable(response: httpx.Response) -> bool:
    if response.status_code in (429, 500, 502, 503, 504):
        return True
    # A 403 is only retryable when Google says it is a rate limit.
    try:
        payload = response.json()
    except ValueError:
        return False
    error = payload.get("error") if isinstance(payload, dict) else None
    if not isinstance(error, dict):
        return False
    for item in error.get("errors", []) or []:
        if isinstance(item, dict) and item.get("reason") in _RETRYABLE_REASONS:
            return True
    return False
