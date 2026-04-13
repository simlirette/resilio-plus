from tests.backend.api.conftest import athlete_payload


def test_list_athletes_empty(authed_client):
    c, _ = authed_client
    resp = c.get("/athletes/")
    assert resp.status_code == 200
    # authed_client creates one athlete via onboarding, so list has 1 entry
    assert isinstance(resp.json(), list)


def test_create_athlete_returns_201(client):
    resp = client.post("/athletes/", json=athlete_payload())
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Alice"
    assert body["primary_sport"] == "running"
    assert "id" in body


def test_list_athletes_after_create(authed_client):
    c, _ = authed_client
    c.post("/athletes/", json=athlete_payload())
    resp = c.get("/athletes/")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_get_athlete_returns_200(authed_client):
    c, athlete_id = authed_client
    resp = c.get(f"/athletes/{athlete_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == athlete_id


def test_update_athlete_returns_200(authed_client):
    c, athlete_id = authed_client
    resp = c.put(f"/athletes/{athlete_id}", json={"name": "Bob", "age": 25})
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Bob"
    assert body["age"] == 25


def test_delete_athlete_returns_204(authed_client):
    c, athlete_id = authed_client
    resp = c.delete(f"/athletes/{athlete_id}")
    assert resp.status_code == 204


def test_create_athlete_missing_required_field_returns_422(client):
    payload = athlete_payload()
    del payload["name"]
    resp = client.post("/athletes/", json=payload)
    assert resp.status_code == 422


def test_list_athletes_without_token_returns_401(client):
    resp = client.get("/athletes/")
    assert resp.status_code == 401


def test_get_athlete_without_token_returns_401(client):
    create_resp = client.post("/athletes/", json=athlete_payload())
    athlete_id = create_resp.json()["id"]
    resp = client.get(f"/athletes/{athlete_id}")
    assert resp.status_code == 401


def test_get_athlete_with_wrong_token_returns_403(authed_client):
    c, _ = authed_client
    resp = c.get("/athletes/some-other-athlete-id")
    assert resp.status_code == 403
