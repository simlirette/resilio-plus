"""HevyClient — pagination, auth header, errors, 429 backoff (no live API)."""

from __future__ import annotations

import json

import httpx
import pytest

from resilio.core.lifting.hevy_client import (
    HevyAPIError,
    HevyAuthError,
    HevyClient,
    HevyConfigError,
    HevyRateLimitError,
)

WORKOUT = {
    "id": "w1",
    "title": "Upper",
    "routine_id": None,
    "description": "",
    "start_time": "2026-10-08T10:17:55+00:00",
    "end_time": "2026-10-08T11:00:14+00:00",
    "updated_at": "2026-10-08T11:00:19.012Z",
    "created_at": "2026-10-08T11:00:19.012Z",
    "exercises": [
        {
            "index": 0,
            "title": "Pull Up",
            "notes": None,
            "exercise_template_id": "1B2B1E7C",
            "superset_id": None,
            "sets": [
                {
                    "index": 0,
                    "type": "normal",
                    "weight_kg": None,
                    "reps": 12,
                    "distance_meters": None,
                    "duration_seconds": None,
                    "rpe": None,
                    "custom_metric": None,
                }
            ],
        }
    ],
}


def _client(handler) -> HevyClient:
    return HevyClient(api_key="k-123", transport=httpx.MockTransport(handler), sleep=lambda s: None)


def test_missing_key_raises_config_error(monkeypatch):
    monkeypatch.delenv("HEVY_API_KEY", raising=False)
    with pytest.raises(HevyConfigError):
        HevyClient.from_env()


def test_sends_api_key_header_and_pages_workouts():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.headers.get("api-key"), dict(request.url.params)))
        page = int(request.url.params["page"])
        return httpx.Response(
            200, json={"page": page, "page_count": 2, "workouts": [dict(WORKOUT, id=f"w{page}")]}
        )

    workouts = list(_client(handler).iter_workouts())
    assert [w["id"] for w in workouts] == ["w1", "w2"]
    assert all(key == "k-123" for key, _ in seen)
    assert seen[0][1]["pageSize"] == "10"


def test_iter_events_passes_since():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["since"] == "2026-10-01T00:00:00Z"
        return httpx.Response(
            200,
            json={
                "page": 1,
                "page_count": 1,
                "events": [
                    {"type": "updated", "workout": WORKOUT},
                    {"type": "deleted", "id": "gone", "deleted_at": "2026-10-02T00:00:00Z"},
                ],
            },
        )

    events = list(_client(handler).iter_workout_events("2026-10-01T00:00:00Z"))
    assert [e["type"] for e in events] == ["updated", "deleted"]


def test_empty_page_count_zero_yields_nothing():
    def handler(request):
        return httpx.Response(200, json={"page": 1, "page_count": 0, "workouts": []})

    assert list(_client(handler).iter_workouts()) == []


def test_401_raises_auth_error():
    def handler(request):
        return httpx.Response(401, json={"error": "Unauthorized"})

    with pytest.raises(HevyAuthError):
        list(_client(handler).iter_workouts())


def test_429_retries_then_succeeds():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(429, json={"error": "slow down"})
        return httpx.Response(200, json={"workout_count": 31})

    assert _client(handler).workout_count() == 31
    assert calls["n"] == 3


def test_429_exhausted_raises_rate_limit():
    def handler(request):
        return httpx.Response(429, json={"error": "slow down"})

    with pytest.raises(HevyRateLimitError):
        _client(handler).workout_count()


def test_400_raises_api_error_with_message():
    def handler(request):
        return httpx.Response(400, json={"error": "Invalid request body"})

    with pytest.raises(HevyAPIError, match="Invalid request body"):
        _client(handler).create_routine({"title": "x"})


def test_create_and_update_routine_wrap_body():
    bodies = {}

    def handler(request: httpx.Request) -> httpx.Response:
        bodies[(request.method, request.url.path)] = json.loads(request.content)
        if request.method == "POST":
            return httpx.Response(201, json={"routine": [{"id": "r1", "title": "T"}]})
        return httpx.Response(200, json={"routine": {"id": "r1", "title": "T2"}})

    c = _client(handler)
    created = c.create_routine({"title": "T", "folder_id": 7, "exercises": []})
    updated = c.update_routine("r1", {"title": "T2", "exercises": []})
    assert created["id"] == "r1" and updated["title"] == "T2"
    assert bodies[("POST", "/v1/routines")] == {
        "routine": {"title": "T", "folder_id": 7, "exercises": []}
    }
    assert bodies[("PUT", "/v1/routines/r1")] == {"routine": {"title": "T2", "exercises": []}}


def test_create_routine_folder():
    def handler(request):
        assert json.loads(request.content) == {"routine_folder": {"title": "Resilio"}}
        return httpx.Response(201, json={"id": 42, "title": "Resilio", "index": 0})

    assert _client(handler).create_routine_folder("Resilio")["id"] == 42


def test_templates_use_page_size_100():
    def handler(request):
        assert request.url.params["pageSize"] == "100"
        return httpx.Response(
            200,
            json={
                "page": 1,
                "page_count": 1,
                "exercise_templates": [
                    {
                        "id": "T1",
                        "title": "Squat (Barbell)",
                        "type": "weight_reps",
                        "primary_muscle_group": "quadriceps",
                        "secondary_muscle_groups": ["glutes"],
                        "equipment": "barbell",
                        "is_custom": False,
                    }
                ],
            },
        )

    assert [t["id"] for t in _client(handler).iter_exercise_templates()] == ["T1"]
