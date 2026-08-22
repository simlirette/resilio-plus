from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from app.db.models import AthleteModel, DeepLinkTokenModel
from app.services.deep_link_service import (
    InvalidDeepLinkError,
    UnsupportedProviderError,
    consume_link,
    issue_connector_links,
    issue_link,
    link_url,
    resolve_link,
)
from sqlalchemy.orm import Session

FIXED_NOW = datetime(2031, 3, 1, 9, 0, tzinfo=timezone.utc)


def _clock(now: datetime = FIXED_NOW):
    return lambda: now


@pytest.fixture
def athlete_id(db_session: Session) -> str:
    athlete_id = str(uuid.uuid4())
    db_session.add(
        AthleteModel(
            id=athlete_id,
            name="Link Athlete",
            age=29,
            sex="F",
            weight_kg=58.0,
            height_cm=165.0,
            primary_sport="running",
            hours_per_week=6.0,
            sports_json='["running"]',
            goals_json="[]",
            available_days_json="[]",
            equipment_json="[]",
        )
    )
    db_session.commit()
    return athlete_id


class TestIssue:
    def test_persists_provider_and_expiry(
        self, db_session: Session, athlete_id: str
    ) -> None:
        token = issue_link(
            db_session, athlete_id=athlete_id, provider="strava", clock=_clock()
        )
        row = db_session.get(DeepLinkTokenModel, token)
        assert row is not None
        assert row.provider == "strava"
        assert row.consumed_at is None

    def test_rejects_unknown_provider(
        self, db_session: Session, athlete_id: str
    ) -> None:
        with pytest.raises(UnsupportedProviderError):
            issue_link(db_session, athlete_id=athlete_id, provider="garmin")

    def test_issue_connector_links_returns_one_url_per_provider(
        self, db_session: Session, athlete_id: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PUBLIC_BASE_URL", "https://coach.example.com/")

        links = issue_connector_links(
            db_session, athlete_id=athlete_id, clock=_clock()
        )

        assert set(links) == {"strava", "hevy", "google"}
        for url in links.values():
            assert url.startswith("https://coach.example.com/integrations/link/")
        assert len(set(links.values())) == 3

    def test_link_url_uses_the_public_base(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PUBLIC_BASE_URL", "https://coach.example.com")
        assert link_url("abc") == "https://coach.example.com/integrations/link/abc"


class TestResolveAndConsume:
    def test_resolve_returns_the_link_without_burning_it(
        self, db_session: Session, athlete_id: str
    ) -> None:
        token = issue_link(
            db_session, athlete_id=athlete_id, provider="hevy", clock=_clock()
        )

        link = resolve_link(db_session, token=token, clock=_clock())

        assert link.athlete_id == athlete_id
        assert link.provider == "hevy"
        assert resolve_link(db_session, token=token, clock=_clock()).token == token

    def test_consume_is_single_use(
        self, db_session: Session, athlete_id: str
    ) -> None:
        token = issue_link(
            db_session, athlete_id=athlete_id, provider="hevy", clock=_clock()
        )

        assert consume_link(db_session, token=token, clock=_clock()).provider == "hevy"

        with pytest.raises(InvalidDeepLinkError):
            consume_link(db_session, token=token, clock=_clock())
        with pytest.raises(InvalidDeepLinkError):
            resolve_link(db_session, token=token, clock=_clock())

    def test_expired_token_is_rejected(
        self, db_session: Session, athlete_id: str
    ) -> None:
        token = issue_link(
            db_session,
            athlete_id=athlete_id,
            provider="strava",
            ttl=timedelta(minutes=5),
            clock=_clock(),
        )
        late = _clock(FIXED_NOW + timedelta(minutes=6))

        with pytest.raises(InvalidDeepLinkError):
            resolve_link(db_session, token=token, clock=late)
        with pytest.raises(InvalidDeepLinkError):
            consume_link(db_session, token=token, clock=late)

    def test_unknown_token_is_rejected(self, db_session: Session) -> None:
        with pytest.raises(InvalidDeepLinkError):
            resolve_link(db_session, token="nope", clock=_clock())
