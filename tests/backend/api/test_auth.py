import json
import uuid

from app.core.security import hash_password
from app.db.models import AthleteModel, UserModel


def _seed_user(db, email="alice@test.com", password="password123"):
    """Create an AthleteModel + UserModel directly in the DB."""
    athlete = AthleteModel(
        id=str(uuid.uuid4()),
        name="Alice",
        age=30,
        sex="F",
        weight_kg=60.0,
        height_cm=168.0,
        primary_sport="running",
        hours_per_week=10.0,
        sports_json=json.dumps(["running"]),
        goals_json=json.dumps(["run sub-4h marathon"]),
        available_days_json=json.dumps([0, 2, 4, 6]),
        equipment_json=json.dumps([]),
    )
    db.add(athlete)
    db.flush()

    user = UserModel(
        id=str(uuid.uuid4()),
        email=email,
        hashed_password=hash_password(password),
        athlete_id=athlete.id,
    )
    db.add(user)
    db.commit()
    return athlete.id


def test_login_returns_token(client_and_db):
    client, db = client_and_db
    athlete_id = _seed_user(db)

    resp = client.post("/auth/login", json={"email": "alice@test.com", "password": "password123"})
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["athlete_id"] == athlete_id


def test_login_wrong_password_returns_401(client_and_db):
    client, db = client_and_db
    _seed_user(db)

    resp = client.post("/auth/login", json={"email": "alice@test.com", "password": "wrongpass"})
    assert resp.status_code == 401


def test_login_unknown_email_returns_401(client):
    resp = client.post("/auth/login", json={"email": "nobody@test.com", "password": "pass"})
    assert resp.status_code == 401


def test_login_returns_refresh_token(client_and_db):
    client, db = client_and_db
    _seed_user(db)

    resp = client.post("/auth/login", json={"email": "alice@test.com", "password": "password123"})
    assert resp.status_code == 200
    body = resp.json()
    assert "refresh_token" in body
    assert len(body["refresh_token"]) > 20


def test_refresh_returns_new_tokens(client_and_db):
    client, db = client_and_db
    _seed_user(db)

    # Login to get initial tokens
    resp = client.post("/auth/login", json={"email": "alice@test.com", "password": "password123"})
    original_refresh = resp.json()["refresh_token"]
    original_access = resp.json()["access_token"]

    # Refresh
    resp2 = client.post("/auth/refresh", json={"refresh_token": original_refresh})
    assert resp2.status_code == 200
    body = resp2.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["refresh_token"] != original_refresh  # rotated
    assert body["access_token"] != original_access    # new token


def test_refresh_old_token_is_invalidated(client_and_db):
    client, db = client_and_db
    _seed_user(db)

    resp = client.post("/auth/login", json={"email": "alice@test.com", "password": "password123"})
    original_refresh = resp.json()["refresh_token"]

    # Use refresh token once
    client.post("/auth/refresh", json={"refresh_token": original_refresh})

    # Try to use old refresh token again — must fail
    resp3 = client.post("/auth/refresh", json={"refresh_token": original_refresh})
    assert resp3.status_code == 401


def test_refresh_invalid_token_returns_401(client):
    resp = client.post("/auth/refresh", json={"refresh_token": "not-a-real-token"})
    assert resp.status_code == 401


def test_logout_revokes_refresh_token(client_and_db):
    client, db = client_and_db
    _seed_user(db)

    resp = client.post("/auth/login", json={"email": "alice@test.com", "password": "password123"})
    body = resp.json()
    access_token = body["access_token"]
    refresh_token = body["refresh_token"]

    # Logout
    resp2 = client.post(
        "/auth/logout",
        json={"refresh_token": refresh_token},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp2.status_code == 200

    # Refresh token should now be invalid
    resp3 = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp3.status_code == 401


def test_me_returns_current_user(client_and_db):
    client, db = client_and_db
    athlete_id = _seed_user(db, email="alice@test.com")

    resp = client.post("/auth/login", json={"email": "alice@test.com", "password": "password123"})
    token = resp.json()["access_token"]

    resp2 = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 200
    body = resp2.json()
    assert body["email"] == "alice@test.com"
    assert body["athlete_id"] == athlete_id
    assert body["is_active"] is True


def test_me_without_token_returns_401(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401
