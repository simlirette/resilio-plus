"""
Thin client for the Hevy public API (https://api.hevyapp.com/docs).

Requires a Hevy Pro API key in the ``HEVY_API_KEY`` environment variable.
The key is never logged or echoed. Returns raw API dicts; callers validate
them into ``resilio.schemas.lifting`` models.
"""

from __future__ import annotations

import os
import time
from typing import Any, Callable, Iterator, Optional

import httpx

BASE_URL = "https://api.hevyapp.com"
_MAX_PAGE = {
    "workouts": 10,
    "events": 10,
    "routines": 10,
    "routine_folders": 10,
    "exercise_templates": 100,
}
_RETRIES_429 = 3


class HevyError(Exception):
    """Base class for Hevy client errors."""


class HevyConfigError(HevyError):
    """No API key available."""


class HevyAuthError(HevyError):
    """Key rejected (401)."""


class HevyRateLimitError(HevyError):
    """Still rate limited after retries (429)."""


class HevyAPIError(HevyError):
    """Any other non-success response."""

    def __init__(self, status_code: int, message: str):
        super().__init__(f"Hevy API {status_code}: {message}")
        self.status_code = status_code


class HevyClient:
    def __init__(
        self,
        api_key: str,
        transport: Optional[httpx.BaseTransport] = None,
        timeout: float = 30.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not api_key:
            raise HevyConfigError("HEVY_API_KEY is empty")
        self._http = httpx.Client(
            base_url=BASE_URL,
            headers={"api-key": api_key, "accept": "application/json"},
            timeout=timeout,
            transport=transport,
        )
        self._sleep = sleep

    @classmethod
    def from_env(cls, **kwargs: Any) -> "HevyClient":
        key = os.environ.get("HEVY_API_KEY", "").strip()
        if not key:
            raise HevyConfigError(
                "HEVY_API_KEY is not set. Get it in Hevy → Settings → Developer (Hevy Pro) "
                "and set it as a user environment variable."
            )
        return cls(key, **kwargs)

    # ------------------------------------------------------------------ core

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        for attempt in range(_RETRIES_429):
            try:
                resp = self._http.request(method, path, **kwargs)
            except httpx.HTTPError as exc:
                raise HevyAPIError(0, f"network error: {exc.__class__.__name__}") from exc
            if resp.status_code == 429:
                if attempt < _RETRIES_429 - 1:
                    self._sleep(2.0 * (2**attempt))
                    continue
                raise HevyRateLimitError("Hevy API rate limit exceeded; try again in a minute")
            if resp.status_code == 401:
                raise HevyAuthError("Hevy rejected the API key (401). Check HEVY_API_KEY.")
            if resp.status_code >= 400:
                raise HevyAPIError(resp.status_code, _error_message(resp))
            return resp.json() if resp.content else None
        raise HevyRateLimitError("Hevy API rate limit exceeded")  # pragma: no cover

    def _paged(self, path: str, key: str, page_size: int, **params: Any) -> Iterator[dict]:
        page = 1
        while True:
            data = self._request(
                "GET", path, params={"page": page, "pageSize": page_size, **params}
            )
            yield from data.get(key) or []
            if page >= int(data.get("page_count") or 0):
                return
            page += 1

    # --------------------------------------------------------------- reads

    def workout_count(self) -> int:
        return int(self._request("GET", "/v1/workouts/count")["workout_count"])

    def iter_workouts(self) -> Iterator[dict]:
        return self._paged("/v1/workouts", "workouts", _MAX_PAGE["workouts"])

    def iter_workout_events(self, since_iso: str) -> Iterator[dict]:
        return self._paged("/v1/workouts/events", "events", _MAX_PAGE["events"], since=since_iso)

    def iter_exercise_templates(self) -> Iterator[dict]:
        return self._paged(
            "/v1/exercise_templates", "exercise_templates", _MAX_PAGE["exercise_templates"]
        )

    def iter_routines(self) -> Iterator[dict]:
        return self._paged("/v1/routines", "routines", _MAX_PAGE["routines"])

    def iter_routine_folders(self) -> Iterator[dict]:
        return self._paged("/v1/routine_folders", "routine_folders", _MAX_PAGE["routine_folders"])

    def get_routine(self, routine_id: str) -> dict:
        return _unwrap_routine(self._request("GET", f"/v1/routines/{routine_id}"))

    # -------------------------------------------------------------- writes

    def create_routine_folder(self, title: str) -> dict:
        data = self._request(
            "POST", "/v1/routine_folders", json={"routine_folder": {"title": title}}
        )
        return data.get("routine_folder", data) if isinstance(data, dict) else data

    def create_routine(self, routine: dict) -> dict:
        return _unwrap_routine(self._request("POST", "/v1/routines", json={"routine": routine}))

    def update_routine(self, routine_id: str, routine: dict) -> dict:
        return _unwrap_routine(
            self._request("PUT", f"/v1/routines/{routine_id}", json={"routine": routine})
        )


def _unwrap_routine(data: Any) -> dict:
    """Hevy has returned both ``{"routine": {...}}`` and ``{"routine": [{...}]}``."""
    if isinstance(data, dict) and "routine" in data:
        data = data["routine"]
    if isinstance(data, list):
        data = data[0] if data else {}
    return data or {}


def _error_message(resp: httpx.Response) -> str:
    try:
        body = resp.json()
        if isinstance(body, dict) and body.get("error"):
            return str(body["error"])
    except ValueError:
        pass
    return resp.text[:200] or resp.reason_phrase
