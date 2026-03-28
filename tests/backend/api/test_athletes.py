from tests.backend.api.conftest import athlete_payload


def test_list_athletes_empty(client):
    resp = client.get("/athletes/")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_athlete_returns_201(client):
    resp = client.post("/athletes/", json=athlete_payload())
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Alice"
    assert body["primary_sport"] == "running"
    assert "id" in body


def test_list_athletes_after_create(client):
    client.post("/athletes/", json=athlete_payload())
    resp = client.get("/athletes/")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_get_athlete_returns_200(client):
    create_resp = client.post("/athletes/", json=athlete_payload())
    athlete_id = create_resp.json()["id"]
    resp = client.get(f"/athletes/{athlete_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == athlete_id


def test_get_athlete_not_found_returns_404(client):
    resp = client.get("/athletes/does-not-exist")
    assert resp.status_code == 404


def test_update_athlete_returns_200(client):
    create_resp = client.post("/athletes/", json=athlete_payload())
    athlete_id = create_resp.json()["id"]
    resp = client.put(f"/athletes/{athlete_id}", json={"name": "Bob", "age": 25})
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Bob"
    assert body["age"] == 25
    assert body["sex"] == "F"  # unchanged


def test_delete_athlete_returns_204(client):
    create_resp = client.post("/athletes/", json=athlete_payload())
    athlete_id = create_resp.json()["id"]
    resp = client.delete(f"/athletes/{athlete_id}")
    assert resp.status_code == 204
    assert client.get(f"/athletes/{athlete_id}").status_code == 404


def test_create_athlete_missing_required_field_returns_422(client):
    payload = athlete_payload()
    del payload["name"]
    resp = client.post("/athletes/", json=payload)
    assert resp.status_code == 422
