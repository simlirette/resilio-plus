"""An OAuth deep link burns when the athlete finishes, not when it is opened.

`open_link` consumed the token before issuing the redirect, so anything that
merely *fetched* the URL destroyed it. Hit for real on 2026-08-20: a `curl`
that followed the redirect to check the link worked consumed the Strava token
without connecting anything, and a fresh link had to be issued. Telegram's
link preview, a browser prefetch, a security scanner or an antivirus proxy
would all do the same, and the athlete would be left tapping a dead link with
no idea why.

Single-use is still the rule -- it just now attaches to completing the
connection rather than to opening the page. The form providers already worked
this way: their token burns on the POST that carries the key.
"""
from __future__ import annotations

from datetime import timedelta

import pytest
from app.db.models import AthleteModel
from app.services.deep_link_service import (
    InvalidDeepLinkError,
    consume_pending,
    issue_link,
    resolve_link,
)

ATHLETE = "88888888-8888-8888-8888-888888888888"


@pytest.fixture
def db_session():
    from app.db import models  # noqa: F401 -- registers ORM models with Base
    from app.db.database import Base
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import Session as SASession

    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def _fk(conn, _):
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(engine)
    with SASession(engine) as s:
        yield s
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def athlete(db_session) -> AthleteModel:
    row = AthleteModel(
        id=ATHLETE,
        name="Simon",
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
    db_session.add(row)
    db_session.commit()
    return row


class TestConsumePending:
    def test_it_burns_the_live_token_for_that_provider(self, db_session) -> None:
        token = issue_link(db_session, athlete_id=ATHLETE, provider="strava")

        assert consume_pending(db_session, athlete_id=ATHLETE, provider="strava")

        with pytest.raises(InvalidDeepLinkError):
            resolve_link(db_session, token=token)

    def test_it_leaves_other_providers_alone(self, db_session) -> None:
        google = issue_link(db_session, athlete_id=ATHLETE, provider="google")
        issue_link(db_session, athlete_id=ATHLETE, provider="strava")

        consume_pending(db_session, athlete_id=ATHLETE, provider="strava")

        assert resolve_link(db_session, token=google).provider == "google"

    def test_it_burns_the_newest_when_several_were_issued(self, db_session) -> None:
        """Re-sending /connect issues a new link; the one just used is the last."""
        old = issue_link(db_session, athlete_id=ATHLETE, provider="strava")
        new = issue_link(db_session, athlete_id=ATHLETE, provider="strava")

        consume_pending(db_session, athlete_id=ATHLETE, provider="strava")

        with pytest.raises(InvalidDeepLinkError):
            resolve_link(db_session, token=new)
        assert resolve_link(db_session, token=old).token == old

    def test_nothing_pending_is_not_an_error(self, db_session) -> None:
        """An athlete may connect through the API without a deep link at all."""
        assert not consume_pending(db_session, athlete_id=ATHLETE, provider="strava")

    def test_an_expired_token_is_not_reported_as_consumed(self, db_session) -> None:
        issue_link(
            db_session,
            athlete_id=ATHLETE,
            provider="strava",
            ttl=timedelta(seconds=-1),
        )

        assert not consume_pending(db_session, athlete_id=ATHLETE, provider="strava")


class TestOpeningDoesNotBurn:
    def test_resolving_leaves_the_token_usable(self, db_session) -> None:
        """`resolve_link` is the read the redirect path performs."""
        token = issue_link(db_session, athlete_id=ATHLETE, provider="strava")

        resolve_link(db_session, token=token)
        resolve_link(db_session, token=token)

        assert resolve_link(db_session, token=token).athlete_id == ATHLETE


class TestTheRouteNoLongerBurnsOnOpen:
    """Pins the route itself: the regression is one `consume_link` call away."""

    def test_open_link_does_not_consume_for_oauth_providers(self) -> None:
        import ast
        import inspect

        from app.routes import link as link_routes

        source = inspect.getsource(link_routes.open_link)
        tree = ast.parse(source.lstrip())

        called = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }

        assert "consume_link" not in called, (
            "open_link burns the token before the athlete has connected anything"
        )
