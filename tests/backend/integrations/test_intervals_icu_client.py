"""Pushing a week to intervals.icu is idempotent and never all-or-nothing.

Two failures this must not have, both silent when they happen:

  - A re-approval that creates a second copy of every session. The athlete ends
    a month with four identical Tuesdays on their watch and no idea why. Google
    Calendar shipped that bug once; this repeats the fix, not the mistake.
  - One rejected entry costing the whole week. The athlete gets nothing on
    their wrist because a single slot was malformed.
"""
from __future__ import annotations

import httpx
import pytest
import respx

from app.integrations.intervals_icu.client import (
    BASE_URL,
    IntervalsConfigurationError,
    push_workouts,
)

ICU_ID = "i12345"
KEY = "test-key"


def _workout(slot_id: str, day: str = "2026-08-24") -> dict:
    return {
        "start_date_local": f"{day}T00:00:00",
        "category": "WORKOUT",
        "type": "Run",
        "name": "tempo z2",
        "description": "45 min",
        "moving_time": 2700,
        "external_id": f"resilio-{slot_id}",
    }


def _events(*pairs: tuple[str, int]) -> list[dict]:
    return [
        {"id": event_id, "external_id": f"resilio-{slot_id}"}
        for slot_id, event_id in pairs
    ]


class TestFirstPush:
    @respx.mock(base_url=BASE_URL)
    def test_new_workouts_are_created(self, respx_mock) -> None:
        respx_mock.get(f"/athlete/{ICU_ID}/events").mock(
            return_value=httpx.Response(200, json=[])
        )
        create = respx_mock.post(f"/athlete/{ICU_ID}/events").mock(
            return_value=httpx.Response(200, json={"id": 1})
        )

        report = push_workouts(ICU_ID, [_workout("a"), _workout("b")], api_key=KEY)

        assert report.created == 2
        assert report.updated == 0
        assert create.call_count == 2


class TestRePush:
    @respx.mock(base_url=BASE_URL)
    def test_an_existing_workout_is_updated_not_duplicated(self, respx_mock) -> None:
        respx_mock.get(f"/athlete/{ICU_ID}/events").mock(
            return_value=httpx.Response(200, json=_events(("a", 77)))
        )
        update = respx_mock.put(f"/athlete/{ICU_ID}/events/77").mock(
            return_value=httpx.Response(200, json={"id": 77})
        )
        create = respx_mock.post(f"/athlete/{ICU_ID}/events").mock(
            return_value=httpx.Response(200, json={"id": 2})
        )

        report = push_workouts(ICU_ID, [_workout("a"), _workout("b")], api_key=KEY)

        assert report.updated == 1
        assert report.created == 1
        assert update.call_count == 1
        assert create.call_count == 1

    @respx.mock(base_url=BASE_URL)
    def test_an_unreadable_lookup_falls_back_to_creating(self, respx_mock) -> None:
        """Better a possible duplicate than a watch with nothing on it."""
        respx_mock.get(f"/athlete/{ICU_ID}/events").mock(
            return_value=httpx.Response(500)
        )
        respx_mock.post(f"/athlete/{ICU_ID}/events").mock(
            return_value=httpx.Response(200, json={"id": 1})
        )

        report = push_workouts(ICU_ID, [_workout("a")], api_key=KEY)

        assert report.created == 1


class TestPartialFailure:
    @respx.mock(base_url=BASE_URL)
    def test_one_rejected_workout_does_not_sink_the_others(self, respx_mock) -> None:
        respx_mock.get(f"/athlete/{ICU_ID}/events").mock(
            return_value=httpx.Response(200, json=[])
        )
        respx_mock.post(f"/athlete/{ICU_ID}/events").mock(
            side_effect=[
                httpx.Response(400, json={"error": "bad"}),
                httpx.Response(200, json={"id": 2}),
            ]
        )

        report = push_workouts(ICU_ID, [_workout("a"), _workout("b")], api_key=KEY)

        assert report.failed == 1
        assert report.created == 1


class TestNothingToDo:
    def test_an_empty_week_needs_no_credentials(self) -> None:
        """A lifting-only week must not error on a missing key."""
        report = push_workouts(ICU_ID, [], already_skipped=3)

        assert report.as_dict() == {
            "created": 0,
            "updated": 0,
            "skipped": 3,
            "failed": 0,
        }

    def test_a_missing_key_is_named_not_guessed(self, monkeypatch) -> None:
        monkeypatch.delenv("INTERVALS_ICU_API_KEY", raising=False)

        with pytest.raises(IntervalsConfigurationError):
            push_workouts(ICU_ID, [_workout("a")])
