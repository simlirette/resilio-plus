# tests/backend/integrations/strava/test_sync_service.py
import time
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest
import respx
from cryptography.fernet import Fernet
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db import models  # noqa: F401
from app.db.models import AthleteModel, ConnectorCredentialModel, StravaActivityModel
from app.integrations.strava.oauth_service import encrypt_token
from app.integrations.strava.sync_service import sync

TEST_KEY = Fernet.generate_key().decode()
_ATHLETE_ID = str(uuid.uuid4())

STRAVA_ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"


def _make_raw_activity(strava_id: int = 1, sport_type: str = "Run") -> dict:
    return {
        "id": strava_id,
        "name": "Morning Run",
        "sport_type": sport_type,
        "type": sport_type,
        "start_date_local": "2026-04-10T07:00:00Z",
        "elapsed_time": 3600,
        "distance": 10000.0,
        "total_elevation_gain": 100.0,
        "average_heartrate": 145.0,
        "max_heartrate": 175.0,
        "average_watts": None,
        "perceived_exertion": None,
    }


@pytest.fixture()
def db_session(monkeypatch):
    monkeypatch.setenv("STRAVA_CLIENT_ID", "test_id")
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "test_secret")
    monkeypatch.setenv("STRAVA_REDIRECT_URI", "http://localhost/callback")
    monkeypatch.setenv("STRAVA_ENCRYPTION_KEY", TEST_KEY)

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)
    with Session() as session:
        session.add(AthleteModel(
            id=_ATHLETE_ID, name="Alice", age=30, sex="F",
            weight_kg=60.0, height_cm=168.0,
            sports_json='["running"]', primary_sport="running",
            goals_json='["run fast"]', available_days_json="[0]",
            hours_per_week=10.0, equipment_json="[]",
        ))
        session.commit()
        yield session
    Base.metadata.drop_all(engine)


def _seed_strava_cred(db_session, expires_at: int | None = None) -> None:
    if expires_at is None:
        expires_at = int(time.time()) + 3600
    db_session.add(ConnectorCredentialModel(
        id=str(uuid.uuid4()),
        athlete_id=_ATHLETE_ID,
        provider="strava",
        access_token_enc=encrypt_token("access_tok", TEST_KEY),
        refresh_token_enc=encrypt_token("refresh_tok", TEST_KEY),
        expires_at=expires_at,
        last_sync_at=None,
        extra_json="{}",
    ))
    db_session.commit()


@respx.mock
def test_sync_null_last_sync_at_fetches_90_days(db_session):
    _seed_strava_cred(db_session)
    respx.get(STRAVA_ACTIVITIES_URL).mock(return_value=httpx.Response(200, json=[]))

    result = sync(_ATHLETE_ID, db_session)
    assert result.synced == 0
    assert result.skipped == 0

    request = respx.calls.last.request
    params = dict(request.url.params.multi_items())
    after_ts = int(params["after"])
    expected = int((datetime.now(timezone.utc) - timedelta(days=90)).timestamp())
    assert abs(after_ts - expected) < 10


@respx.mock
def test_sync_incremental_uses_last_sync_at(db_session):
    _seed_strava_cred(db_session)

    last_sync = datetime(2026, 4, 1, tzinfo=timezone.utc)
    cred = db_session.query(ConnectorCredentialModel).filter_by(
        athlete_id=_ATHLETE_ID, provider="strava"
    ).first()
    cred.last_sync_at = last_sync
    db_session.commit()

    respx.get(STRAVA_ACTIVITIES_URL).mock(return_value=httpx.Response(200, json=[]))
    sync(_ATHLETE_ID, db_session)

    request = respx.calls.last.request
    params = dict(request.url.params.multi_items())
    assert int(params["after"]) == int(last_sync.timestamp())


@respx.mock
def test_sync_upserts_activities(db_session):
    _seed_strava_cred(db_session)
    respx.get(STRAVA_ACTIVITIES_URL).mock(
        return_value=httpx.Response(200, json=[
            _make_raw_activity(1, "Run"),
            _make_raw_activity(2, "Ride"),
        ])
    )

    result = sync(_ATHLETE_ID, db_session)
    assert result.synced == 2
    assert result.skipped == 0
    assert result.sport_breakdown["running"] == 1
    assert result.sport_breakdown["biking"] == 1

    rows = db_session.query(StravaActivityModel).filter_by(athlete_id=_ATHLETE_ID).all()
    assert len(rows) == 2


@respx.mock
def test_sync_idempotent(db_session):
    _seed_strava_cred(db_session)
    activity_json = [_make_raw_activity(1, "Run")]
    respx.get(STRAVA_ACTIVITIES_URL).mock(
        return_value=httpx.Response(200, json=activity_json)
    )

    sync(_ATHLETE_ID, db_session)
    sync(_ATHLETE_ID, db_session)

    rows = db_session.query(StravaActivityModel).filter_by(athlete_id=_ATHLETE_ID).all()
    assert len(rows) == 1


@respx.mock
def test_sync_updates_last_sync_at(db_session):
    _seed_strava_cred(db_session)
    respx.get(STRAVA_ACTIVITIES_URL).mock(return_value=httpx.Response(200, json=[]))

    before = datetime.now(timezone.utc)
    sync(_ATHLETE_ID, db_session)

    db_session.expire_all()
    cred = db_session.query(ConnectorCredentialModel).filter_by(
        athlete_id=_ATHLETE_ID, provider="strava"
    ).first()
    assert cred.last_sync_at is not None
    last_sync = cred.last_sync_at
    if last_sync.tzinfo is None:
        last_sync = last_sync.replace(tzinfo=timezone.utc)
    assert last_sync >= before


@respx.mock
def test_sync_skips_unknown_sport_type(db_session):
    _seed_strava_cred(db_session)
    respx.get(STRAVA_ACTIVITIES_URL).mock(
        return_value=httpx.Response(200, json=[_make_raw_activity(1, "Yoga")])
    )

    result = sync(_ATHLETE_ID, db_session)
    assert result.skipped == 1
    assert result.synced == 0


def test_sync_raises_if_not_connected(db_session):
    with pytest.raises(ValueError, match="Strava not connected"):
        sync(_ATHLETE_ID, db_session)
