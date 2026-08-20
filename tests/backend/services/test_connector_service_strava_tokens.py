"""The planner Strava fetch must decrypt tokens before using them.

V3-R (2026-04-14) moved Strava tokens to Fernet-encrypted columns
(`access_token_enc`). `connector_service._model_to_credential` was never
updated: it copies the ciphertext straight into `ConnectorCredential.
access_token`, so the connector sends a Fernet blob as a bearer token and
Strava answers 401. `fetch_connector_data` swallows that into a warning and
returns an empty list.

The blast radius is the whole planning path -- every agent receives
`strava_activities=[]`, so VDOT falls back to the 35.0 beginner floor and the
cardio half of the strain index never loads. ACWR kept working and hid it,
because `daily_training_loads` reads the `strava_activities` table instead.

Caught live on 2026-08-20 against a real account with 27 synced activities.

`_persist_token_update` had the mirror-image bug: it wrote the refreshed
*plaintext* token back into the `_enc` column, which would then fail to
decrypt on the V3-R read path.
"""
from __future__ import annotations

import json
from datetime import date
from unittest.mock import patch

import pytest
from app.db.models import AthleteModel, ConnectorCredentialModel
from app.schemas.connector import StravaActivity

PLAINTEXT_ACCESS = "plain-access-token"
PLAINTEXT_REFRESH = "plain-refresh-token"
ATHLETE = "11111111-1111-1111-1111-111111111111"


@pytest.fixture(autouse=True)
def _athlete(db_session):
    """connector_credentials.athlete_id is a real FK."""
    db_session.add(
        AthleteModel(
            id=ATHLETE,
            name="Test",
            age=24,
            sex="M",
            weight_kg=77.0,
            height_cm=183.0,
            hours_per_week=8.0,
            primary_sport="running",
            sports_json='["running"]',
            goals_json="[]",
            available_days_json="[]",
            equipment_json="[]",
        )
    )
    db_session.commit()


@pytest.fixture()
def _key(monkeypatch: pytest.MonkeyPatch) -> str:
    from cryptography.fernet import Fernet

    key = Fernet.generate_key().decode()
    monkeypatch.setenv("STRAVA_ENCRYPTION_KEY", key)
    monkeypatch.setenv("STRAVA_CLIENT_ID", "cid")
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "csecret")
    return key


@pytest.fixture()
def strava_row(db_session, _key: str) -> ConnectorCredentialModel:
    from app.integrations.strava.oauth_service import encrypt_token

    row = ConnectorCredentialModel(
        id="22222222-2222-2222-2222-222222222222",
        athlete_id=ATHLETE,
        provider="strava",
        access_token_enc=encrypt_token(PLAINTEXT_ACCESS, _key),
        refresh_token_enc=encrypt_token(PLAINTEXT_REFRESH, _key),
        expires_at=99_999_999_999,  # far future: no refresh
        extra_json="{}",
    )
    db_session.add(row)
    db_session.commit()
    return row


def _activity() -> StravaActivity:
    return StravaActivity(
        id="strava_1",
        name="Morning Run",
        sport_type="Run",
        date=date(2026, 8, 19),
        duration_seconds=1980,
        distance_meters=4010.0,
    )


class _Fake:
    """Minimal connector stand-in; subclasses decide what fetch returns."""

    seen: dict = {}

    def __init__(self, cred, **kwargs):
        type(self).seen["access_token"] = cred.access_token
        type(self).seen["extra"] = cred.extra
        self.credential = cred

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class TestTokensAreDecrypted:
    def test_the_connector_never_receives_the_ciphertext(
        self, db_session, strava_row
    ) -> None:
        from app.services.connector_service import fetch_connector_data

        class FakeConnector(_Fake):
            seen: dict = {}

            def fetch_activities(self, since=None, until=None):
                return [_activity()]

        with patch("app.services.connector_service.StravaConnector", FakeConnector):
            result = fetch_connector_data(ATHLETE, db_session)

        assert FakeConnector.seen["access_token"] != strava_row.access_token_enc, (
            "the Fernet ciphertext was sent as a bearer token"
        )
        assert FakeConnector.seen["access_token"] == PLAINTEXT_ACCESS
        assert len(result["strava_activities"]) == 1

    def test_activities_actually_reach_the_caller(self, db_session, strava_row) -> None:
        from app.services.connector_service import fetch_connector_data

        class FakeConnector(_Fake):
            seen: dict = {}

            def fetch_activities(self, since=None, until=None):
                return [_activity()]

        with patch("app.services.connector_service.StravaConnector", FakeConnector):
            result = fetch_connector_data(ATHLETE, db_session)

        assert [a.name for a in result["strava_activities"]] == ["Morning Run"]


class TestRefreshedTokensStayEncrypted:
    def test_a_refresh_does_not_write_plaintext_into_the_enc_column(
        self, db_session, strava_row, _key: str
    ) -> None:
        """A plaintext token in an `_enc` column breaks every later read."""
        from app.integrations.strava.oauth_service import decrypt_token
        from app.services.connector_service import fetch_connector_data

        rotated = "rotated-access-token"

        class RotatingConnector(_Fake):
            seen: dict = {}

            def fetch_activities(self, since=None, until=None):
                self.credential.access_token = rotated
                return []

        with patch("app.services.connector_service.StravaConnector", RotatingConnector):
            fetch_connector_data(ATHLETE, db_session)

        db_session.refresh(strava_row)
        stored = strava_row.access_token_enc
        assert stored != rotated, "plaintext token written into the _enc column"
        assert decrypt_token(stored, _key) in (PLAINTEXT_ACCESS, rotated)


class TestDegradation:
    def test_no_credential_yields_an_empty_list_not_an_error(self, db_session) -> None:
        from app.services.connector_service import fetch_connector_data

        result = fetch_connector_data(ATHLETE, db_session)

        assert result["strava_activities"] == []

    def test_an_undecryptable_token_degrades(self, db_session, _key: str) -> None:
        """A key rotation must not take the planning run down with it."""
        from app.services.connector_service import fetch_connector_data

        db_session.add(
            ConnectorCredentialModel(
                id="33333333-3333-3333-3333-333333333333",
                athlete_id=ATHLETE,
                provider="strava",
                access_token_enc="not-a-fernet-token",
                refresh_token_enc="not-a-fernet-token",
                expires_at=99_999_999_999,
                extra_json="{}",
            )
        )
        db_session.commit()

        result = fetch_connector_data(ATHLETE, db_session)

        assert result["strava_activities"] == []


class TestHevyUnaffected:
    def test_hevy_still_reads_its_api_key_from_extra_json(self, db_session) -> None:
        from app.services.connector_service import fetch_connector_data

        db_session.add(
            ConnectorCredentialModel(
                id="44444444-4444-4444-4444-444444444444",
                athlete_id=ATHLETE,
                provider="hevy",
                extra_json=json.dumps({"api_key": "hevy-key"}),
            )
        )
        db_session.commit()

        class FakeHevy(_Fake):
            seen: dict = {}

            def fetch_workouts(self, since=None, until=None):
                return []

        with patch("app.services.connector_service.HevyConnector", FakeHevy):
            fetch_connector_data(ATHLETE, db_session)

        assert FakeHevy.seen["extra"] == {"api_key": "hevy-key"}
