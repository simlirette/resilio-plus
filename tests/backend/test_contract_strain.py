"""Contract tests — GET /athletes/{id}/strain."""


def test_strain_requires_auth(api_client, auth_state):
    resp = api_client.get(f"/athletes/{auth_state['athlete_id']}/strain")
    assert resp.status_code == 401


def test_strain_returns_200_with_schema(api_client, auth_state):
    resp = api_client.get(
        f"/athletes/{auth_state['athlete_id']}/strain",
        headers=auth_state["headers"],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "computed_at" in body
    assert "scores" in body
    assert "peak_group" in body
    assert "peak_score" in body


def test_strain_scores_all_ten_muscle_groups(api_client, auth_state):
    resp = api_client.get(
        f"/athletes/{auth_state['athlete_id']}/strain",
        headers=auth_state["headers"],
    )
    body = resp.json()
    expected = {
        "quads", "posterior_chain", "glutes", "calves", "chest",
        "upper_pull", "shoulders", "triceps", "biceps", "core",
    }
    assert set(body["scores"].keys()) == expected
    for score in body["scores"].values():
        assert 0.0 <= score <= 100.0


def test_strain_peak_matches_max_score(api_client, auth_state):
    resp = api_client.get(
        f"/athletes/{auth_state['athlete_id']}/strain",
        headers=auth_state["headers"],
    )
    body = resp.json()
    assert body["scores"][body["peak_group"]] == body["peak_score"]


def test_strain_403_for_other_athlete(api_client, auth_state):
    resp = api_client.get(
        "/athletes/00000000-0000-0000-0000-000000000000/strain",
        headers=auth_state["headers"],
    )
    assert resp.status_code == 403
