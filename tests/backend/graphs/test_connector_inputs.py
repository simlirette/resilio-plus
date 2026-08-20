"""The specialists must actually see what the athlete did.

`AgentContext` has carried `strava_activities`, `hevy_workouts` and
`terra_health` since V1, and nothing ever populated them — every specialist
planned blind. These tests pin the wiring and, just as importantly, pin the
degradation: no database or a provider outage must fall back to the old
empty-list behaviour rather than sink the planning run.
"""
from __future__ import annotations

from typing import Any

import pytest
from app.graphs.nodes import _connector_inputs


class Sentinel:
    """Stands in for a provider payload; identity is all these tests need."""

    def __init__(self, label: str) -> None:
        self.label = label


def config_with(db: Any) -> dict[str, Any]:
    return {"configurable": {"db": db}}


class TestNoDatabase:
    def test_missing_configurable_is_not_fatal(self) -> None:
        assert _connector_inputs("athlete-1", {}) == {
            "strava_activities": [],
            "hevy_workouts": [],
            "terra_health": [],
        }

    def test_db_of_none_falls_back_to_empty(self) -> None:
        assert _connector_inputs("athlete-1", config_with(None))["strava_activities"] == []


class TestPopulated:
    def test_provider_data_reaches_the_context(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        run = Sentinel("run")
        lift = Sentinel("lift")
        terra = Sentinel("terra")
        monkeypatch.setattr(
            "app.services.connector_service.fetch_connector_data",
            lambda athlete_id, db: {
                "strava_activities": [run],
                "hevy_workouts": [lift],
                "terra_health": terra,
            },
        )

        result = _connector_inputs("athlete-1", config_with(object()))

        assert result["strava_activities"] == [run]
        assert result["hevy_workouts"] == [lift]
        assert result["terra_health"] == [terra]

    def test_the_athlete_id_is_passed_through(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen: dict[str, Any] = {}

        def fake(athlete_id: str, db: Any) -> dict[str, Any]:
            seen["athlete_id"] = athlete_id
            return {"strava_activities": [], "hevy_workouts": [], "terra_health": None}

        monkeypatch.setattr(
            "app.services.connector_service.fetch_connector_data", fake
        )

        _connector_inputs("athlete-42", config_with(object()))

        assert seen["athlete_id"] == "athlete-42"

    def test_a_missing_terra_snapshot_becomes_an_empty_list(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "app.services.connector_service.fetch_connector_data",
            lambda athlete_id, db: {
                "strava_activities": [],
                "hevy_workouts": [],
                "terra_health": None,
            },
        )

        assert _connector_inputs("athlete-1", config_with(object()))["terra_health"] == []

    def test_none_valued_keys_do_not_become_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "app.services.connector_service.fetch_connector_data",
            lambda athlete_id, db: {
                "strava_activities": None,
                "hevy_workouts": None,
                "terra_health": None,
            },
        )

        result = _connector_inputs("athlete-1", config_with(object()))

        assert result == {
            "strava_activities": [],
            "hevy_workouts": [],
            "terra_health": [],
        }


class TestDegradation:
    def test_a_provider_outage_degrades_instead_of_raising(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def boom(athlete_id: str, db: Any) -> dict[str, Any]:
            raise RuntimeError("strava is down")

        monkeypatch.setattr(
            "app.services.connector_service.fetch_connector_data", boom
        )

        result = _connector_inputs("athlete-1", config_with(object()))

        assert result == {
            "strava_activities": [],
            "hevy_workouts": [],
            "terra_health": [],
        }

    def test_the_outage_is_logged(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        monkeypatch.setattr(
            "app.services.connector_service.fetch_connector_data",
            lambda athlete_id, db: (_ for _ in ()).throw(RuntimeError("down")),
        )

        with caplog.at_level("WARNING"):
            _connector_inputs("athlete-1", config_with(object()))

        assert "connector_data_unavailable" in caplog.text
