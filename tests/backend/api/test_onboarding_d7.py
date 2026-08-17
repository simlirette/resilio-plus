"""D7 TDD — onboarding API endpoints smoke tests."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import get_current_athlete_id, get_db


def _make_db_with_athlete(athlete_id: str = "a1") -> MagicMock:
    athlete = MagicMock()
    athlete.id = athlete_id
    athlete.journey_phase = "onboarding"
    athlete.sports_json = '["running"]'
    athlete.primary_sport = "running"
    athlete.hours_per_week = 8.0
    athlete.coaching_mode = "full"
    athlete.clinical_context_flag = None
    athlete.active_onboarding_thread_id = None
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = athlete
    return db


class TestOnboardingStartEndpoint:
    def test_start_returns_200(self):
        """POST /onboarding/start returns 200 with thread_id and block."""
        db = _make_db_with_athlete()
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_athlete_id] = lambda: "a1"

        try:
            with TestClient(app) as client:
                with patch("app.graphs.onboarding.anthropic.Anthropic") as M:
                    M.return_value.messages.create.return_value = MagicMock(
                        content=[MagicMock(text="Bienvenue!")],
                    )
                    resp = client.post(
                        "/onboarding/start",
                        json={"athlete_id": "a1"},
                    )
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 200
        data = resp.json()
        assert "thread_id" in data
        assert data["current_block"] == 1
        assert data["status"] == "in_progress"

    def test_start_forbidden_for_other_athlete(self):
        """POST /onboarding/start returns 403 if athlete_id != current user."""
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[get_current_athlete_id] = lambda: "a1"

        try:
            with TestClient(app) as client:
                resp = client.post(
                    "/onboarding/start",
                    json={"athlete_id": "other"},
                )
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 403


class TestOnboardingRespondEndpoint:
    def test_respond_returns_200(self):
        """POST /onboarding/respond returns 200 with next block."""
        from app.graphs.onboarding import _thread_states, _OnboardingThread

        # Pre-populate thread state
        thread_id = "a1:onboarding:test-d7-api"
        _thread_states[thread_id] = _OnboardingThread(
            thread_id=thread_id,
            athlete_id="a1",
            current_block=1,
            collected_data={},
            status="in_progress",
        )

        db = _make_db_with_athlete()
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_athlete_id] = lambda: "a1"

        try:
            with TestClient(app) as client:
                with patch("app.graphs.onboarding.anthropic.Anthropic") as M:
                    M.return_value.messages.create.return_value = MagicMock(
                        content=[MagicMock(text="Profil?")],
                    )
                    resp = client.post(
                        "/onboarding/respond",
                        json={"thread_id": thread_id, "user_response": "coureur"},
                    )
        finally:
            app.dependency_overrides.clear()
            _thread_states.pop(thread_id, None)

        assert resp.status_code == 200
        data = resp.json()
        assert data["current_block"] == 2

    def test_respond_unknown_thread_returns_404(self):
        """POST /onboarding/respond with unknown thread_id returns 404."""
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[get_current_athlete_id] = lambda: "a1"

        try:
            with TestClient(app) as client:
                resp = client.post(
                    "/onboarding/respond",
                    json={"thread_id": "no-such-thread", "user_response": "..."},
                )
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 404
