"""Contract tests — POST /athletes/{id}/connectors/sync."""


def test_sync_all_requires_auth(api_client, auth_state):
    resp = api_client.post(f"/athletes/{auth_state['athlete_id']}/connectors/sync")
    assert resp.status_code == 401


def test_sync_all_returns_200(api_client, auth_state):
    resp = api_client.post(
        f"/athletes/{auth_state['athlete_id']}/connectors/sync",
        headers=auth_state["headers"],
    )
    assert resp.status_code == 200


def test_sync_all_response_schema(api_client, auth_state):
    resp = api_client.post(
        f"/athletes/{auth_state['athlete_id']}/connectors/sync",
        headers=auth_state["headers"],
    )
    body = resp.json()
    assert "synced_at" in body
    assert "results" in body
    assert "errors" in body
    assert isinstance(body["results"], dict)
    assert isinstance(body["errors"], dict)


def test_sync_all_per_provider_valid_statuses(api_client, auth_state):
    """Every provider result is ok|skipped|error."""
    resp = api_client.post(
        f"/athletes/{auth_state['athlete_id']}/connectors/sync",
        headers=auth_state["headers"],
    )
    valid = {"ok", "skipped", "error"}
    for status in resp.json()["results"].values():
        assert status in valid


def test_sync_all_unconfigured_connectors_skipped(api_client, auth_state):
    """Fresh athlete with no connectors configured → all skipped."""
    resp = api_client.post(
        f"/athletes/{auth_state['athlete_id']}/connectors/sync",
        headers=auth_state["headers"],
    )
    body = resp.json()
    # strava, hevy, terra should all be skipped (no credentials stored)
    for provider in ("strava", "hevy", "terra"):
        assert body["results"].get(provider) == "skipped"


def test_sync_all_403_for_other_athlete(api_client, auth_state):
    resp = api_client.post(
        "/athletes/00000000-0000-0000-0000-000000000000/connectors/sync",
        headers=auth_state["headers"],
    )
    assert resp.status_code == 403
