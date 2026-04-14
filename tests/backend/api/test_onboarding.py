from datetime import date


def _onboarding_payload(**overrides):
    base = {
        "name": "Alice",
        "age": 30,
        "sex": "F",
        "weight_kg": 60.0,
        "height_cm": 168.0,
        "sports": ["running", "lifting"],
        "primary_sport": "running",
        "goals": ["run sub-4h marathon"],
        "available_days": [0, 2, 4, 6],
        "hours_per_week": 10.0,
        "email": "alice@test.com",
        "password": "password123",
        "plan_start_date": str(date.today()),
    }
    return {**base, **overrides}


def test_onboarding_creates_athlete_plan_and_token(client):
    resp = client.post("/athletes/onboarding", json=_onboarding_payload())
    assert resp.status_code == 201
    body = resp.json()
    assert "athlete" in body
    assert "plan" in body
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert "refresh_token" in body
    assert len(body["refresh_token"]) > 20
    assert body["athlete"]["name"] == "Alice"


def test_onboarding_duplicate_email_returns_409(client):
    client.post("/athletes/onboarding", json=_onboarding_payload())
    resp = client.post("/athletes/onboarding", json=_onboarding_payload())
    assert resp.status_code == 409


def test_onboarding_password_too_short_returns_422(client):
    payload = _onboarding_payload(password="short")
    resp = client.post("/athletes/onboarding", json=payload)
    assert resp.status_code == 422


def test_onboarding_token_is_valid_for_login(client):
    resp = client.post("/athletes/onboarding", json=_onboarding_payload())
    body = resp.json()
    athlete_id = body["athlete"]["id"]

    login_resp = client.post("/auth/login", json={"email": "alice@test.com", "password": "password123"})
    assert login_resp.status_code == 200
    assert login_resp.json()["athlete_id"] == athlete_id
