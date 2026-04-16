import json
import uuid

import pytest

from tests.backend.api.conftest import authed_client, client  # noqa: F401

from app.db.models import ConnectorCredentialModel


# ─── hevy ──────────────────────────────────────────────────────────────────────

def test_hevy_connect_stores_api_key(authed_client, tmp_path):
    client, athlete_id = authed_client

    resp = client.post(
        f"/athletes/{athlete_id}/connectors/hevy",
        json={"api_key": "hevy_key_123"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["provider"] == "hevy"
    assert data["connected"] is True


def test_hevy_connect_upsert_updates_existing(authed_client):
    client, athlete_id = authed_client

    client.post(f"/athletes/{athlete_id}/connectors/hevy", json={"api_key": "key_v1"})
    resp = client.post(f"/athletes/{athlete_id}/connectors/hevy", json={"api_key": "key_v2"})
    assert resp.status_code == 201


def test_hevy_connect_unknown_athlete_returns_404(authed_client):
    c, _ = authed_client
    resp = c.post(
        f"/athletes/{uuid.uuid4()}/connectors/hevy",
        json={"api_key": "key"},
    )
    assert resp.status_code in (403, 404)


def test_hevy_connect_forbidden_other_athlete(authed_client):
    """Athlete cannot connect hevy for a different athlete."""
    c, _ = authed_client
    other_id = str(uuid.uuid4())
    resp = c.post(f"/athletes/{other_id}/connectors/hevy", json={"api_key": "k"})
    assert resp.status_code == 403


# ─── list ──────────────────────────────────────────────────────────────────────

def test_list_connectors_empty(authed_client):
    client, athlete_id = authed_client
    resp = client.get(f"/athletes/{athlete_id}/connectors")
    assert resp.status_code == 200
    assert resp.json() == {"connectors": []}


def test_list_connectors_after_hevy_connect(authed_client):
    client, athlete_id = authed_client
    client.post(f"/athletes/{athlete_id}/connectors/hevy", json={"api_key": "k"})
    resp = client.get(f"/athletes/{athlete_id}/connectors")
    assert resp.status_code == 200
    connectors = resp.json()["connectors"]
    assert len(connectors) == 1
    assert connectors[0]["provider"] == "hevy"
    assert connectors[0]["connected"] is True


def test_list_connectors_does_not_expose_tokens(authed_client):
    client, athlete_id = authed_client
    client.post(f"/athletes/{athlete_id}/connectors/hevy", json={"api_key": "k"})
    resp = client.get(f"/athletes/{athlete_id}/connectors")
    raw = resp.text
    assert "api_key" not in raw
    assert "access_token" not in raw


def test_list_connectors_unknown_athlete_returns_403(authed_client):
    c, _ = authed_client
    resp = c.get(f"/athletes/{uuid.uuid4()}/connectors")
    assert resp.status_code == 403


# ─── delete ────────────────────────────────────────────────────────────────────

def test_delete_connector_returns_204(authed_client):
    client, athlete_id = authed_client
    client.post(f"/athletes/{athlete_id}/connectors/hevy", json={"api_key": "k"})
    resp = client.delete(f"/athletes/{athlete_id}/connectors/hevy")
    assert resp.status_code == 204


def test_delete_connector_not_found_returns_404(authed_client):
    client, athlete_id = authed_client
    resp = client.delete(f"/athletes/{athlete_id}/connectors/strava")
    assert resp.status_code == 404


def test_delete_connector_forbidden_other_athlete(authed_client):
    """Athlete cannot delete connectors for a different athlete."""
    c, _ = authed_client
    other_id = str(uuid.uuid4())
    resp = c.delete(f"/athletes/{other_id}/connectors/hevy")
    assert resp.status_code == 403
