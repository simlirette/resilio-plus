import os
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_current_athlete_id


def _override_athlete(athlete_id: str):
    def _dep() -> str:
        return athlete_id
    return _dep


def test_admin_metrics_requires_auth():
    # No override, no auth header
    client = TestClient(app)
    response = client.get("/admin/metrics")
    # Either 401 (missing token) or 403 (wrong athlete) is acceptable
    assert response.status_code in (401, 403)


def test_admin_metrics_forbidden_for_non_admin():
    app.dependency_overrides[get_current_athlete_id] = _override_athlete("not-admin-uuid")
    try:
        with patch.dict(os.environ, {"ADMIN_ATHLETE_ID": "admin-uuid-1"}):
            client = TestClient(app)
            response = client.get("/admin/metrics")
            assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_athlete_id, None)


def test_admin_metrics_ok_for_admin():
    app.dependency_overrides[get_current_athlete_id] = _override_athlete("admin-uuid-1")
    try:
        with patch.dict(os.environ, {"ADMIN_ATHLETE_ID": "admin-uuid-1"}):
            client = TestClient(app)
            response = client.get("/admin/metrics")
            assert response.status_code == 200
            body = response.json()
            assert "started_at" in body
            assert "uptime_s" in body
            assert "http" in body
            assert "agents" in body
            assert "jobs" in body
    finally:
        app.dependency_overrides.pop(get_current_athlete_id, None)


def test_admin_metrics_response_increments_http_counter():
    app.dependency_overrides[get_current_athlete_id] = _override_athlete("admin-uuid-1")
    try:
        with patch.dict(os.environ, {"ADMIN_ATHLETE_ID": "admin-uuid-1"}):
            client = TestClient(app)
            r1 = client.get("/admin/metrics")
            body1 = r1.json()
            r2 = client.get("/admin/metrics")
            body2 = r2.json()
            key = "GET /admin/metrics:200"
            assert body2["http"]["requests_total"][key] >= body1["http"]["requests_total"].get(key, 0) + 1
    finally:
        app.dependency_overrides.pop(get_current_athlete_id, None)
