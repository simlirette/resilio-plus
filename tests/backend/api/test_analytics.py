import pytest
from tests.backend.api.conftest import authed_client, client  # noqa: F401


def test_load_analytics_empty(authed_client):
    c, athlete_id = authed_client
    resp = c.get(f"/athletes/{athlete_id}/analytics/load")
    assert resp.status_code == 200
    data = resp.json()
    assert "acwr" in data
    assert "training_load" in data
    assert data["acwr"] == []
    assert data["training_load"] == []


def test_sport_breakdown_empty(authed_client):
    c, athlete_id = authed_client
    resp = c.get(f"/athletes/{athlete_id}/analytics/sport-breakdown")
    assert resp.status_code == 200
    data = resp.json()
    assert data == {}


def test_performance_analytics_empty(authed_client):
    c, athlete_id = authed_client
    resp = c.get(f"/athletes/{athlete_id}/analytics/performance")
    assert resp.status_code == 200
    data = resp.json()
    assert "vdot" in data
    assert "e1rm" in data
    assert data["vdot"] == []
    assert data["e1rm"] == []


def test_load_analytics_forbidden(authed_client):
    c, _ = authed_client
    resp = c.get("/athletes/99999/analytics/load")
    assert resp.status_code == 403


def test_analytics_unauthenticated(client):
    resp = client.get("/athletes/1/analytics/load")
    assert resp.status_code == 401
