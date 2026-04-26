"""D1 TDD — CoordinatorService API smoke tests."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db import models as _models  # noqa: registers all ORM models
from app.db.models import AthleteModel
from app.main import app
from app.dependencies import get_current_athlete_id, get_db

ATHLETE_ID = "33333333-3333-3333-3333-333333333333"


def _make_engine():
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture()
def client_and_athlete():
    engine = _make_engine()
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)

    def override_get_db():
        with TestSession() as session:
            yield session

    with TestSession() as db:
        db.add(
            AthleteModel(
                id=ATHLETE_ID,
                name="Test",
                age=30,
                sex="M",
                weight_kg=70.0,
                height_cm=175.0,
                primary_sport="running",
                hours_per_week=8.0,
                sports_json='["running"]',
                goals_json='["fitness"]',
                available_days_json='[0,2,4]',
                equipment_json='[]',
                journey_phase="steady_state",
            )
        )
        db.commit()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_athlete_id] = lambda: ATHLETE_ID

    with TestClient(app) as c:
        yield c, ATHLETE_ID

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


class TestDispatchEndpoint:
    def test_dispatch_chat_steady_state_200(self, client_and_athlete):
        client, athlete_id = client_and_athlete
        with patch("app.routes.coordinator.coordinator_service") as mock_svc:
            mock_result = MagicMock()
            mock_result.graph_invoked = "chat_turn"
            mock_result.thread_id = f"{athlete_id}:chat_turn:test-uuid"
            mock_result.output = {"response": "Hello"}
            mock_result.pending = True
            mock_svc.dispatch.return_value = mock_result
            resp = client.post(
                "/coordinator/dispatch",
                json={"event_type": "chat", "payload": {"message": "hi"}},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["graph_invoked"] == "chat_turn"
        assert data["pending"] is True

    def test_dispatch_default_empty_payload(self, client_and_athlete):
        client, athlete_id = client_and_athlete
        with patch("app.routes.coordinator.coordinator_service") as mock_svc:
            mock_result = MagicMock()
            mock_result.graph_invoked = "chat_turn"
            mock_result.thread_id = None
            mock_result.output = None
            mock_result.pending = True
            mock_svc.dispatch.return_value = mock_result
            resp = client.post(
                "/coordinator/dispatch",
                json={"event_type": "chat"},
            )
        assert resp.status_code == 200

    def test_dispatch_requires_auth(self):
        # Fresh client with no auth override
        engine = _make_engine()
        Base.metadata.create_all(bind=engine)
        TestSession = sessionmaker(bind=engine)

        def override_get_db():
            with TestSession() as session:
                yield session

        app.dependency_overrides[get_db] = override_get_db
        # No auth override — should fail

        try:
            with TestClient(app) as c:
                resp = c.post(
                    "/coordinator/dispatch",
                    json={"event_type": "chat", "payload": {}},
                )
            assert resp.status_code in (401, 403)
        finally:
            app.dependency_overrides.clear()
            Base.metadata.drop_all(bind=engine)


class TestStateEndpoint:
    def test_get_coordinator_state_200(self, client_and_athlete):
        client, athlete_id = client_and_athlete
        resp = client.get(f"/coordinator/state/{athlete_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["journey_phase"] == "steady_state"
        assert "overlays" in data
        assert "active_threads" in data
        assert data["overlays"]["recovery_takeover_active"] is False
        assert data["overlays"]["onboarding_reentry_active"] is False

    def test_get_coordinator_state_wrong_athlete_403(self, client_and_athlete):
        client, _ = client_and_athlete
        other_id = "99999999-9999-9999-9999-999999999999"
        resp = client.get(f"/coordinator/state/{other_id}")
        assert resp.status_code == 403

    def test_get_coordinator_state_returns_active_threads(self, client_and_athlete):
        client, athlete_id = client_and_athlete
        resp = client.get(f"/coordinator/state/{athlete_id}")
        assert resp.status_code == 200
        data = resp.json()
        threads = data["active_threads"]
        assert "onboarding" in threads
        assert "recovery_takeover" in threads
        assert "followup_transition" in threads
