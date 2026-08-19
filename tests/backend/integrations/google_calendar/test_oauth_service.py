from __future__ import annotations

import time
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx
from app.db.models import AthleteModel, GoogleCalendarCredentialModel
from app.integrations.google_calendar.oauth_service import (
    SCOPE,
    GoogleCalendarConfigurationError,
    GoogleCalendarNotConnectedError,
    InvalidOAuthStateError,
    callback,
    connect,
    decrypt_token,
    encrypt_token,
    get_access_token,
    is_connected,
    token_provider,
)
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

ATHLETE_ID = "athlete-google"
TOKEN_PATH = "/token"


@pytest.fixture
def key(monkeypatch: pytest.MonkeyPatch) -> str:
    generated = Fernet.generate_key().decode()
    monkeypatch.setenv("GOOGLE_ENCRYPTION_KEY", generated)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv(
        "GOOGLE_REDIRECT_URI", "https://coach.example.com/integrations/link/callback/google"
    )
    return generated


@pytest.fixture
def athlete(db_session: Session) -> str:
    db_session.add(
        AthleteModel(
            id=ATHLETE_ID,
            name="Google Athlete",
            age=30,
            sex="M",
            weight_kg=70.0,
            height_cm=175.0,
            primary_sport="running",
            hours_per_week=5.0,
            sports_json='["running"]',
            goals_json="[]",
            available_days_json="[]",
            equipment_json="[]",
        )
    )
    db_session.commit()
    return ATHLETE_ID


class TestConnect:
    def test_builds_a_consent_url_and_stores_the_state(
        self, db_session: Session, athlete: str, key: str
    ) -> None:
        result = connect(athlete, db_session)

        parsed = urlparse(result["auth_url"])
        params = parse_qs(parsed.query)
        assert parsed.netloc == "accounts.google.com"
        assert params["scope"] == [SCOPE]
        assert params["access_type"] == ["offline"]
        assert params["prompt"] == ["consent"]
        assert params["redirect_uri"] == [
            "https://coach.example.com/integrations/link/callback/google"
        ]

        row = db_session.get(GoogleCalendarCredentialModel, athlete)
        assert row is not None
        assert row.state == params["state"][0]

    def test_requires_configuration(
        self, db_session: Session, athlete: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GOOGLE_ENCRYPTION_KEY", raising=False)
        with pytest.raises(GoogleCalendarConfigurationError):
            connect(athlete, db_session)


class TestCallback:
    @respx.mock(base_url="https://oauth2.googleapis.com")
    def test_stores_encrypted_tokens_and_clears_the_state(
        self,
        respx_mock: respx.Router,
        db_session: Session,
        athlete: str,
        key: str,
    ) -> None:
        connect(athlete, db_session)
        row = db_session.get(GoogleCalendarCredentialModel, athlete)
        assert row is not None
        state = row.state
        assert state is not None

        respx_mock.post(TOKEN_PATH).mock(
            return_value=httpx.Response(
                200,
                json={
                    "access_token": "access-1",
                    "refresh_token": "refresh-1",
                    "expires_in": 3600,
                    "scope": SCOPE,
                },
            )
        )

        result = callback(code="code-1", state=state, db=db_session)

        assert result == {"connected": True, "athlete_id": athlete}
        db_session.expire_all()
        row = db_session.get(GoogleCalendarCredentialModel, athlete)
        assert row is not None
        assert row.state is None
        assert row.refresh_token_enc != "refresh-1"
        assert decrypt_token(row.refresh_token_enc or "", key) == "refresh-1"
        assert decrypt_token(row.access_token_enc or "", key) == "access-1"
        assert row.connected_at is not None
        assert is_connected(athlete, db_session)

    def test_unknown_state_is_rejected(
        self, db_session: Session, athlete: str, key: str
    ) -> None:
        with pytest.raises(InvalidOAuthStateError):
            callback(code="code-1", state="not-a-state", db=db_session)


class TestAccessToken:
    def _seed(self, db_session: Session, key: str, *, expires_at: int) -> None:
        db_session.add(
            GoogleCalendarCredentialModel(
                athlete_id=ATHLETE_ID,
                refresh_token_enc=encrypt_token("refresh-1", key),
                access_token_enc=encrypt_token("access-cached", key),
                expires_at=expires_at,
            )
        )
        db_session.commit()

    def test_cached_token_is_reused_while_fresh(
        self, db_session: Session, athlete: str, key: str
    ) -> None:
        self._seed(db_session, key, expires_at=int(time.time()) + 3600)

        assert get_access_token(athlete, db_session) == "access-cached"

    @respx.mock(base_url="https://oauth2.googleapis.com")
    def test_expiring_token_is_refreshed(
        self,
        respx_mock: respx.Router,
        db_session: Session,
        athlete: str,
        key: str,
    ) -> None:
        self._seed(db_session, key, expires_at=int(time.time()) + 30)
        respx_mock.post(TOKEN_PATH).mock(
            return_value=httpx.Response(
                200, json={"access_token": "access-fresh", "expires_in": 3600}
            )
        )

        assert get_access_token(athlete, db_session) == "access-fresh"
        db_session.expire_all()
        row = db_session.get(GoogleCalendarCredentialModel, athlete)
        assert row is not None
        assert decrypt_token(row.access_token_enc or "", key) == "access-fresh"

    @respx.mock(base_url="https://oauth2.googleapis.com")
    def test_rotated_refresh_token_is_stored(
        self,
        respx_mock: respx.Router,
        db_session: Session,
        athlete: str,
        key: str,
    ) -> None:
        self._seed(db_session, key, expires_at=0)
        respx_mock.post(TOKEN_PATH).mock(
            return_value=httpx.Response(
                200,
                json={
                    "access_token": "access-fresh",
                    "refresh_token": "refresh-2",
                    "expires_in": 3600,
                },
            )
        )

        get_access_token(athlete, db_session)

        db_session.expire_all()
        row = db_session.get(GoogleCalendarCredentialModel, athlete)
        assert row is not None
        assert decrypt_token(row.refresh_token_enc or "", key) == "refresh-2"

    def test_unconnected_athlete_raises(
        self, db_session: Session, athlete: str, key: str
    ) -> None:
        with pytest.raises(GoogleCalendarNotConnectedError):
            get_access_token(athlete, db_session)
        assert not is_connected(athlete, db_session)

    @respx.mock(base_url="https://oauth2.googleapis.com")
    def test_token_provider_forces_a_refresh_on_the_retry(
        self,
        respx_mock: respx.Router,
        db_session: Session,
        athlete: str,
        key: str,
    ) -> None:
        self._seed(db_session, key, expires_at=int(time.time()) + 3600)
        respx_mock.post(TOKEN_PATH).mock(
            return_value=httpx.Response(
                200, json={"access_token": "access-forced", "expires_in": 3600}
            )
        )

        provide = token_provider(athlete, db_session)

        assert provide() == "access-cached"
        assert provide() == "access-forced"
