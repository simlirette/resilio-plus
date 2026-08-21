from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from app.db import models as _models  # noqa: F401 — registers ORM models
from app.db.database import Base
from app.db.models import AthleteModel, ConnectorCredentialModel, DeepLinkTokenModel
from app.dependencies import get_db
from app.main import app
from app.services.deep_link_service import issue_link
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

ATHLETE_ID = "44444444-4444-4444-4444-444444444444"


@pytest.fixture(autouse=True)
def no_messaging_channel(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)


@pytest.fixture
def client_and_db(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[TestClient, Session]]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)

    def override_get_db() -> Iterator[Session]:
        with TestSession() as session:
            yield session

    with TestSession() as db:
        db.add(
            AthleteModel(
                id=ATHLETE_ID,
                name="Link Route Athlete",
                age=31,
                sex="M",
                weight_kg=74.0,
                height_cm=180.0,
                primary_sport="running",
                hours_per_week=6.0,
                sports_json='["running"]',
                goals_json="[]",
                available_days_json="[]",
                equipment_json="[]",
            )
        )
        db.commit()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client, TestSession() as db:
        yield client, db
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def _issue(db: Session, provider: str) -> str:
    return issue_link(db, athlete_id=ATHLETE_ID, provider=provider)


class TestOpenLink:
    def test_hevy_link_renders_a_key_form(
        self, client_and_db: tuple[TestClient, Session]
    ) -> None:
        client, db = client_and_db
        token = _issue(db, "hevy")

        response = client.get(f"/integrations/link/{token}")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert token in response.text
        assert "api_key" in response.text

    def test_strava_link_redirects_to_the_provider(
        self, client_and_db: tuple[TestClient, Session], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client, db = client_and_db
        token = _issue(db, "strava")
        monkeypatch.setattr(
            "app.routes.link.strava_oauth_connect",
            lambda athlete_id, db: {"auth_url": "https://strava.example/oauth"},
        )

        response = client.get(f"/integrations/link/{token}", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["location"] == "https://strava.example/oauth"

    def test_opening_a_strava_link_does_not_burn_it(
        self, client_and_db: tuple[TestClient, Session], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Changed 2026-08-20. This used to assert the second open returned 410.

        Consuming at the redirect meant anything that merely *fetched* the URL
        destroyed it -- a link preview, a browser prefetch, a scanner. It
        happened for real: a curl checking the link worked burned the Strava
        token without connecting anything.

        Single-use still holds; it now attaches to completing the connection.
        See test_deep_link_burns_on_completion.py.
        """
        client, db = client_and_db
        token = _issue(db, "strava")
        monkeypatch.setattr(
            "app.routes.link.strava_oauth_connect",
            lambda athlete_id, db: {"auth_url": "https://strava.example/oauth"},
        )

        client.get(f"/integrations/link/{token}", follow_redirects=False)
        second = client.get(f"/integrations/link/{token}", follow_redirects=False)

        assert second.status_code == 302

    def test_a_strava_link_dies_once_the_connection_completes(
        self, client_and_db: tuple[TestClient, Session], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.services.deep_link_service import consume_pending

        client, db = client_and_db
        token = _issue(db, "strava")
        monkeypatch.setattr(
            "app.routes.link.strava_oauth_connect",
            lambda athlete_id, db: {"auth_url": "https://strava.example/oauth"},
        )

        client.get(f"/integrations/link/{token}", follow_redirects=False)
        consume_pending(db, athlete_id=ATHLETE_ID, provider="strava")

        assert (
            client.get(
                f"/integrations/link/{token}", follow_redirects=False
            ).status_code
            == 410
        )

    def test_terra_link_redirects_when_a_widget_is_configured(
        self, client_and_db: tuple[TestClient, Session], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client, db = client_and_db
        token = _issue(db, "terra")
        monkeypatch.setenv("TERRA_WIDGET_URL", "https://widget.tryterra.co/abc")

        response = client.get(f"/integrations/link/{token}", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["location"] == "https://widget.tryterra.co/abc"

    def test_terra_link_falls_back_to_a_form(
        self, client_and_db: tuple[TestClient, Session], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client, db = client_and_db
        token = _issue(db, "terra")
        monkeypatch.delenv("TERRA_WIDGET_URL", raising=False)

        response = client.get(f"/integrations/link/{token}")

        assert response.status_code == 200
        assert "terra_user_id" in response.text

    def test_unknown_token_is_gone(
        self, client_and_db: tuple[TestClient, Session]
    ) -> None:
        client, _ = client_and_db
        assert client.get("/integrations/link/nope").status_code == 410


class TestSubmitLink:
    def test_pasted_hevy_key_is_stored_and_token_burned(
        self, client_and_db: tuple[TestClient, Session]
    ) -> None:
        client, db = client_and_db
        token = _issue(db, "hevy")

        response = client.post(
            f"/integrations/link/{token}", data={"api_key": "hevy-secret"}
        )

        assert response.status_code == 200
        assert "go back to Telegram" in response.text

        db.expire_all()
        cred = (
            db.query(ConnectorCredentialModel)
            .filter_by(athlete_id=ATHLETE_ID, provider="hevy")
            .one()
        )
        assert json.loads(cred.extra_json)["api_key"] == "hevy-secret"
        row = db.get(DeepLinkTokenModel, token)
        assert row is not None and row.consumed_at is not None

    def test_replayed_submission_is_gone(
        self, client_and_db: tuple[TestClient, Session]
    ) -> None:
        client, db = client_and_db
        token = _issue(db, "hevy")

        client.post(f"/integrations/link/{token}", data={"api_key": "one"})
        second = client.post(f"/integrations/link/{token}", data={"api_key": "two"})

        assert second.status_code == 410
        db.expire_all()
        cred = (
            db.query(ConnectorCredentialModel)
            .filter_by(athlete_id=ATHLETE_ID, provider="hevy")
            .one()
        )
        assert json.loads(cred.extra_json)["api_key"] == "one"

    def test_blank_key_re_renders_the_form_without_burning_the_token(
        self, client_and_db: tuple[TestClient, Session]
    ) -> None:
        client, db = client_and_db
        token = _issue(db, "hevy")

        response = client.post(f"/integrations/link/{token}", data={"api_key": "   "})

        assert response.status_code == 200
        assert "api_key" in response.text
        db.expire_all()
        row = db.get(DeepLinkTokenModel, token)
        assert row is not None and row.consumed_at is None

    def test_strava_token_cannot_be_used_as_a_key_form(
        self, client_and_db: tuple[TestClient, Session]
    ) -> None:
        client, db = client_and_db
        token = _issue(db, "strava")

        response = client.post(
            f"/integrations/link/{token}", data={"api_key": "nope"}
        )

        assert response.status_code == 410


class TestStravaCallback:
    def test_finishes_the_exchange_and_sends_them_back(
        self, client_and_db: tuple[TestClient, Session], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client, _ = client_and_db
        seen: dict[str, Any] = {}

        def fake_callback(code: str, state: str, db: Session) -> dict[str, Any]:
            seen["code"] = code
            seen["state"] = state
            return {"connected": True, "athlete_id": ATHLETE_ID}

        monkeypatch.setattr("app.routes.link.strava_oauth_callback", fake_callback)

        response = client.get(
            "/integrations/link/callback/strava",
            params={"code": "abc", "state": "xyz"},
        )

        assert response.status_code == 200
        assert "go back to Telegram" in response.text
        assert seen == {"code": "abc", "state": "xyz"}

    def test_bad_state_is_reported_as_a_dead_link(
        self, client_and_db: tuple[TestClient, Session], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client, _ = client_and_db

        def fake_callback(code: str, state: str, db: Session) -> dict[str, Any]:
            raise ValueError("bad state")

        monkeypatch.setattr("app.routes.link.strava_oauth_callback", fake_callback)

        response = client.get(
            "/integrations/link/callback/strava",
            params={"code": "abc", "state": "bad"},
        )

        assert response.status_code == 410

    def test_callback_path_is_not_swallowed_by_the_token_route(
        self, client_and_db: tuple[TestClient, Session], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client, _ = client_and_db
        monkeypatch.setattr(
            "app.routes.link.strava_oauth_callback",
            lambda code, state, db: {"connected": True, "athlete_id": ATHLETE_ID},
        )

        response = client.get(
            "/integrations/link/callback/strava",
            params={"code": "abc", "state": "xyz"},
        )

        assert response.status_code == 200
        assert "no longer valid" not in response.text


def test_unique_tokens_per_issue(client_and_db: tuple[TestClient, Session]) -> None:
    _, db = client_and_db
    tokens = {_issue(db, "hevy") for _ in range(5)}
    assert len(tokens) == 5
    assert all(isinstance(uuid.uuid5(uuid.NAMESPACE_URL, t).hex, str) for t in tokens)
