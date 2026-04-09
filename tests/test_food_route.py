"""Tests GET /api/v1/connectors/food/search/fcen."""


def test_fcen_search_returns_200():
    from api.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    response = client.get("/api/v1/connectors/food/search/fcen?q=poulet")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert data["source"] == "fcen"


def test_fcen_search_empty_query_returns_422():
    from api.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    response = client.get("/api/v1/connectors/food/search/fcen?q=")
    assert response.status_code == 422
