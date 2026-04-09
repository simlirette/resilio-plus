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
