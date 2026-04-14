import json
import uuid

from app.db.models import AthleteModel, ConnectorCredentialModel


# ─── fixtures ──────────────────────────────────────────────────────────────────


def _create_athlete(client):
    resp = client.post("/athletes", json={
        "name": "Alice", "age": 30, "sex": "F",
        "weight_kg": 60.0, "height_cm": 168.0,
        "sports": ["running"], "primary_sport": "running",
        "goals": ["run fast"], "available_days": [0, 2, 4],
        "hours_per_week": 10.0,
    })
    assert resp.status_code == 201
    return resp.json()["id"]


# ─── hevy ──────────────────────────────────────────────────────────────────────

def test_hevy_connect_stores_api_key(client_and_db):
    client, session = client_and_db
    athlete_id = _create_athlete(client)

    resp = client.post(
        f"/athletes/{athlete_id}/connectors/hevy",
        json={"api_key": "hevy_key_123"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["provider"] == "hevy"
    assert data["connected"] is True

    session.expire_all()
    cred = session.query(ConnectorCredentialModel).filter_by(
        athlete_id=athlete_id, provider="hevy"
    ).first()
    assert cred is not None
    assert json.loads(cred.extra_json)["api_key"] == "hevy_key_123"


def test_hevy_connect_upsert_updates_existing(client_and_db):
    client, session = client_and_db
    athlete_id = _create_athlete(client)

    client.post(f"/athletes/{athlete_id}/connectors/hevy", json={"api_key": "key_v1"})
    client.post(f"/athletes/{athlete_id}/connectors/hevy", json={"api_key": "key_v2"})

    session.expire_all()
    creds = session.query(ConnectorCredentialModel).filter_by(
        athlete_id=athlete_id, provider="hevy"
    ).all()
    assert len(creds) == 1
    assert json.loads(creds[0].extra_json)["api_key"] == "key_v2"


def test_hevy_connect_unknown_athlete_returns_404(client):
    resp = client.post(
        f"/athletes/{uuid.uuid4()}/connectors/hevy",
        json={"api_key": "key"},
    )
    assert resp.status_code == 404


# ─── list ──────────────────────────────────────────────────────────────────────

def test_list_connectors_empty(client):
    athlete_id = _create_athlete(client)
    resp = client.get(f"/athletes/{athlete_id}/connectors")
    assert resp.status_code == 200
    assert resp.json() == {"connectors": []}


def test_list_connectors_after_hevy_connect(client):
    athlete_id = _create_athlete(client)
    client.post(f"/athletes/{athlete_id}/connectors/hevy", json={"api_key": "k"})
    resp = client.get(f"/athletes/{athlete_id}/connectors")
    assert resp.status_code == 200
    connectors = resp.json()["connectors"]
    assert len(connectors) == 1
    assert connectors[0]["provider"] == "hevy"
    assert connectors[0]["connected"] is True


def test_list_connectors_does_not_expose_tokens(client):
    athlete_id = _create_athlete(client)
    client.post(f"/athletes/{athlete_id}/connectors/hevy", json={"api_key": "k"})
    resp = client.get(f"/athletes/{athlete_id}/connectors")
    raw = resp.text
    assert "api_key" not in raw
    assert "access_token" not in raw


def test_list_connectors_unknown_athlete_returns_404(client):
    resp = client.get(f"/athletes/{uuid.uuid4()}/connectors")
    assert resp.status_code == 404


# ─── delete ────────────────────────────────────────────────────────────────────

def test_delete_connector_returns_204(client):
    athlete_id = _create_athlete(client)
    client.post(f"/athletes/{athlete_id}/connectors/hevy", json={"api_key": "k"})
    resp = client.delete(f"/athletes/{athlete_id}/connectors/hevy")
    assert resp.status_code == 204


def test_delete_connector_not_found_returns_404(client):
    athlete_id = _create_athlete(client)
    resp = client.delete(f"/athletes/{athlete_id}/connectors/strava")
    assert resp.status_code == 404
