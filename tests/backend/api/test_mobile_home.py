def test_mobile_home_requires_auth(client):
    resp = client.get("/mobile/home")
    assert resp.status_code == 401


def test_mobile_home_returns_stable_empty_state(authed_client):
    client, athlete_id = authed_client

    resp = client.get("/mobile/home")

    assert resp.status_code == 200
    body = resp.json()
    assert body["athlete_id"] == athlete_id
    assert body["readiness"]["value"] is None
    assert body["readiness"]["status"] == "unavailable"
    assert body["nutrition"]["calories_target"] > 0
    assert body["nutrition"]["status"] == "estimated"
    assert body["strain"]["status"] == "unavailable"
    assert "todaysSessions" in body
    assert body["dataQuality"]["readiness"] == "unavailable"


def test_mobile_home_uses_checkin_readiness(authed_client):
    client, athlete_id = authed_client
    checkin = {
        "work_intensity": "normal",
        "stress_level": "mild",
        "legs_feeling": "normal",
        "energy_global": "ok",
    }

    checkin_resp = client.post(f"/athletes/{athlete_id}/checkin", json=checkin)
    assert checkin_resp.status_code == 201

    resp = client.get("/mobile/home")

    assert resp.status_code == 200
    body = resp.json()
    assert body["readiness"]["value"] is not None
    assert body["readiness"]["status"] == "measured"
    assert body["cognitiveLoad"]["status"] == "measured"
