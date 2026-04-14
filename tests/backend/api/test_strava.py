# tests/backend/api/test_strava.py
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet

from app.schemas.strava import SyncSummary

TEST_KEY = Fernet.generate_key().decode()


@pytest.fixture(autouse=True)
def strava_env(monkeypatch):
    monkeypatch.setenv("STRAVA_CLIENT_ID", "test_id")
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "test_secret")
    monkeypatch.setenv("STRAVA_REDIRECT_URI", "http://localhost/callback")
    monkeypatch.setenv("STRAVA_ENCRYPTION_KEY", TEST_KEY)


# ── POST /integrations/strava/connect ────────────────────────────────────────

def test_connect_returns_auth_url(api_client, auth_state):
    resp = api_client.post(
        "/integrations/strava/connect",
        headers=auth_state["headers"],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "auth_url" in data
    assert "strava.com" in data["auth_url"]
    assert "state=" in data["auth_url"]


def test_connect_unauthenticated_returns_401(api_client):
    resp = api_client.post("/integrations/strava/connect")
    assert resp.status_code == 401


# ── GET /integrations/strava/callback ────────────────────────────────────────

def test_callback_invalid_state_returns_400(api_client):
    resp = api_client.get("/integrations/strava/callback?code=abc&state=bad_state")
    assert resp.status_code == 400


# ── POST /integrations/strava/sync ───────────────────────────────────────────

def test_sync_returns_summary(api_client, auth_state):
    with patch("app.routes.strava.strava_sync") as mock_sync:
        mock_sync.return_value = SyncSummary(
            synced=3, skipped=0, sport_breakdown={"running": 2, "biking": 1}
        )
        resp = api_client.post(
            "/integrations/strava/sync",
            headers=auth_state["headers"],
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["synced"] == 3
    assert body["skipped"] == 0
    assert body["sport_breakdown"]["running"] == 2


def test_sync_unauthenticated_returns_401(api_client):
    resp = api_client.post("/integrations/strava/sync")
    assert resp.status_code == 401


def test_sync_not_connected_returns_404(api_client, auth_state):
    with patch("app.routes.strava.strava_sync") as mock_sync:
        mock_sync.side_effect = ValueError("Strava not connected")
        resp = api_client.post(
            "/integrations/strava/sync",
            headers=auth_state["headers"],
        )
    assert resp.status_code == 404
