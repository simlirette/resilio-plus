from datetime import date


def test_week_status_returns_plan_data(authed_client):
    c, athlete_id = authed_client
    # authed_client already created a plan via onboarding
    resp = c.get(f"/athletes/{athlete_id}/week-status")
    assert resp.status_code == 200
    body = resp.json()
    assert "week_number" in body
    assert "planned_hours" in body
    assert "actual_hours" in body
    assert "completion_pct" in body
    assert body["week_number"] == 1


def test_week_status_without_token_returns_401(client):
    resp = client.get("/athletes/some-id/week-status")
    assert resp.status_code == 401


def test_week_status_wrong_athlete_returns_403(authed_client):
    c, _ = authed_client
    resp = c.get("/athletes/some-other-id/week-status")
    assert resp.status_code == 403


def test_weekly_review_saves_and_returns_summary(authed_client):
    c, athlete_id = authed_client
    resp = c.post(f"/athletes/{athlete_id}/review", json={
        "week_end_date": str(date.today()),
        "readiness_score": 7.5,
        "comment": "Felt good this week",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert "review_id" in body
    assert "week_number" in body
    assert "planned_hours" in body
    assert "actual_hours" in body
    assert "acwr" in body
    assert "adjustment_applied" in body
    assert "next_week_suggestion" in body
    assert body["week_number"] == 1
    assert body["adjustment_applied"] in (0.9, 1.0, 1.1)


def test_weekly_review_without_token_returns_401(client):
    resp = client.post("/athletes/some-id/review", json={"week_end_date": str(date.today())})
    assert resp.status_code == 401
