"""Talk to intervals.icu.

Authentication is HTTP Basic with the literal username `API_KEY` and the
athlete's key as the password — their API's own convention, not a mistake here.

Push is idempotent by `external_id`. A re-approval of the same week must update
the entries that exist rather than add a second copy: the athlete would
otherwise end a month with four identical Tuesdays on their watch. Google
Calendar taught that lesson at cost; this repeats the fix rather than the
mistake.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://intervals.icu/api/v1"
_TIMEOUT = 20.0
#: intervals.icu authenticates with this literal username and the key as the
#: password. It is not a placeholder.
_BASIC_USER = "API_KEY"


class IntervalsConfigurationError(RuntimeError):
    """Raised when intervals.icu is used without credentials."""


@dataclass(frozen=True)
class PushReport:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "created": self.created,
            "updated": self.updated,
            "skipped": self.skipped,
            "failed": self.failed,
        }


def _credentials(api_key: str | None = None) -> str:
    key = (api_key or os.getenv("INTERVALS_ICU_API_KEY") or "").strip()
    if not key:
        raise IntervalsConfigurationError("INTERVALS_ICU_API_KEY is not set")
    return key


def _client(api_key: str) -> httpx.Client:
    return httpx.Client(
        base_url=BASE_URL,
        auth=(_BASIC_USER, api_key),
        timeout=_TIMEOUT,
    )


def _existing_by_external_id(
    client: httpx.Client,
    icu_athlete_id: str,
    oldest: str,
    newest: str,
) -> dict[str, int]:
    """Map external_id -> event id for the window being pushed."""
    response = client.get(
        f"/athlete/{icu_athlete_id}/events",
        params={"oldest": oldest, "newest": newest},
    )
    response.raise_for_status()
    events = response.json()
    if not isinstance(events, list):
        return {}
    return {
        str(event.get("external_id")): int(event["id"])
        for event in events
        if isinstance(event, dict) and event.get("external_id") and event.get("id")
    }


def push_workouts(
    icu_athlete_id: str,
    workouts: list[dict[str, Any]],
    *,
    api_key: str | None = None,
    already_skipped: int = 0,
) -> PushReport:
    """Create or update each workout. Never raises for a single failure.

    One rejected entry must not cost the athlete the rest of the week on their
    watch, so failures are counted and reported rather than propagated.
    """
    if not workouts:
        return PushReport(skipped=already_skipped)

    key = _credentials(api_key)
    dates = sorted(str(w.get("start_date_local", ""))[:10] for w in workouts)
    created = updated = failed = 0

    with _client(key) as client:
        try:
            existing = _existing_by_external_id(
                client, icu_athlete_id, dates[0], dates[-1]
            )
        except Exception:
            logger.warning("intervals_existing_lookup_failed", exc_info=True)
            existing = {}

        for workout in workouts:
            external_id = str(workout.get("external_id") or "")
            event_id = existing.get(external_id) if external_id else None
            try:
                if event_id is not None:
                    client.put(
                        f"/athlete/{icu_athlete_id}/events/{event_id}", json=workout
                    ).raise_for_status()
                    updated += 1
                else:
                    client.post(
                        f"/athlete/{icu_athlete_id}/events", json=workout
                    ).raise_for_status()
                    created += 1
            except Exception:
                logger.warning(
                    "intervals_workout_push_failed",
                    extra={"external_id": external_id},
                    exc_info=True,
                )
                failed += 1

    return PushReport(
        created=created, updated=updated, skipped=already_skipped, failed=failed
    )
