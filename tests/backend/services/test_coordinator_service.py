"""D1 TDD — CoordinatorService routing matrix, thread lifecycle, journey_phase transitions."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db import models as _models  # noqa: registers all ORM models
from app.db.models import AthleteModel
from app.services.coordinator_service import CoordinatorService


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _make_athlete(
    db,
    journey_phase: str = "signup",
    recovery_takeover_active: bool = False,
    onboarding_reentry_active: bool = False,
) -> str:
    athlete_id = str(uuid.uuid4())
    db.add(
        AthleteModel(
            id=athlete_id,
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
            journey_phase=journey_phase,
            recovery_takeover_active=recovery_takeover_active,
            onboarding_reentry_active=onboarding_reentry_active,
        )
    )
    db.commit()
    return athlete_id


# ─── Routing matrix ────────────────────────────────────────────────────────────

class TestRoutingMatrix:
    def test_chat_signup_returns_no_graph(self, db):
        svc = CoordinatorService()
        athlete_id = _make_athlete(db, journey_phase="signup")
        result = svc.dispatch(athlete_id, "chat", {"message": "hi"}, db)
        assert result.graph_invoked is None

    def test_chat_scope_selection_returns_no_graph(self, db):
        svc = CoordinatorService()
        athlete_id = _make_athlete(db, journey_phase="scope_selection")
        result = svc.dispatch(athlete_id, "chat", {"message": "hi"}, db)
        assert result.graph_invoked is None

    def test_chat_onboarding_routes_to_onboarding(self, db):
        svc = CoordinatorService()
        athlete_id = _make_athlete(db, journey_phase="onboarding")
        result = svc.dispatch(athlete_id, "chat", {"message": "hi"}, db)
        assert result.graph_invoked == "onboarding"

    def test_chat_baseline_pending_routes_to_plan_generation(self, db):
        svc = CoordinatorService()
        athlete_id = _make_athlete(db, journey_phase="baseline_pending_confirmation")
        result = svc.dispatch(athlete_id, "chat", {"message": "hi"}, db)
        assert result.graph_invoked == "plan_generation"

    def test_chat_baseline_active_routes_to_chat_turn(self, db):
        svc = CoordinatorService()
        athlete_id = _make_athlete(db, journey_phase="baseline_active")
        result = svc.dispatch(athlete_id, "chat", {"message": "hi"}, db)
        assert result.graph_invoked == "chat_turn"

    def test_chat_followup_transition_routes_to_followup(self, db):
        svc = CoordinatorService()
        athlete_id = _make_athlete(db, journey_phase="followup_transition")
        result = svc.dispatch(athlete_id, "chat", {"message": "hi"}, db)
        assert result.graph_invoked == "followup_transition"

    def test_chat_steady_state_routes_to_chat_turn(self, db):
        svc = CoordinatorService()
        athlete_id = _make_athlete(db, journey_phase="steady_state")
        result = svc.dispatch(athlete_id, "chat", {"message": "hi"}, db)
        assert result.graph_invoked == "chat_turn"

    def test_recovery_takeover_overlay_overrides_any_phase(self, db):
        svc = CoordinatorService()
        for phase in ["onboarding", "baseline_active", "steady_state"]:
            athlete_id = _make_athlete(
                db, journey_phase=phase, recovery_takeover_active=True
            )
            result = svc.dispatch(athlete_id, "chat", {"message": "hi"}, db)
            assert result.graph_invoked == "recovery_takeover", (
                f"recovery_takeover overlay must override phase={phase!r}"
            )

    def test_onboarding_reentry_overlay_overrides_steady_state(self, db):
        svc = CoordinatorService()
        athlete_id = _make_athlete(
            db, journey_phase="steady_state", onboarding_reentry_active=True
        )
        result = svc.dispatch(athlete_id, "chat", {"message": "hi"}, db)
        assert result.graph_invoked == "onboarding"

    def test_system_silent_returns_no_graph(self, db):
        svc = CoordinatorService()
        athlete_id = _make_athlete(db, journey_phase="steady_state")
        result = svc.dispatch(athlete_id, "system_silent", {}, db)
        assert result.graph_invoked is None

    def test_system_proactive_baseline_active_routes_chat_turn(self, db):
        svc = CoordinatorService()
        athlete_id = _make_athlete(db, journey_phase="baseline_active")
        result = svc.dispatch(athlete_id, "system_proactive", {"seed_message": "..."}, db)
        assert result.graph_invoked == "chat_turn"

    def test_system_proactive_steady_state_routes_chat_turn(self, db):
        svc = CoordinatorService()
        athlete_id = _make_athlete(db, journey_phase="steady_state")
        result = svc.dispatch(athlete_id, "system_proactive", {"seed_message": "..."}, db)
        assert result.graph_invoked == "chat_turn"

    def test_system_injury_activates_overlay_and_routes_recovery(self, db):
        svc = CoordinatorService()
        athlete_id = _make_athlete(db, journey_phase="steady_state")
        result = svc.dispatch(athlete_id, "system_injury", {}, db)
        assert result.graph_invoked == "recovery_takeover"
        athlete = db.query(AthleteModel).filter_by(id=athlete_id).first()
        assert athlete.recovery_takeover_active is True


# ─── Thread lifecycle ───────────────────────────────────────────────────────────

class TestThreadLifecycle:
    def test_onboarding_creates_new_thread_id(self, db):
        svc = CoordinatorService()
        athlete_id = _make_athlete(db, journey_phase="onboarding")
        result = svc.dispatch(athlete_id, "chat", {"message": "hi"}, db)
        assert result.thread_id is not None
        assert result.thread_id.startswith(f"{athlete_id}:onboarding:")

    def test_onboarding_resumes_existing_thread_id(self, db):
        svc = CoordinatorService()
        athlete_id = _make_athlete(db, journey_phase="onboarding")
        r1 = svc.dispatch(athlete_id, "chat", {"message": "hi"}, db)
        r2 = svc.dispatch(athlete_id, "chat", {"message": "next"}, db)
        assert r1.thread_id == r2.thread_id

    def test_recovery_takeover_resumes_stored_thread(self, db):
        svc = CoordinatorService()
        athlete_id = _make_athlete(
            db, journey_phase="steady_state", recovery_takeover_active=True
        )
        existing = f"{athlete_id}:recovery_takeover:existing-uuid"
        athlete = db.query(AthleteModel).filter_by(id=athlete_id).first()
        athlete.active_recovery_thread_id = existing
        db.commit()
        result = svc.dispatch(athlete_id, "chat", {"message": "hi"}, db)
        assert result.thread_id == existing

    def test_followup_transition_stores_thread_on_athlete(self, db):
        svc = CoordinatorService()
        athlete_id = _make_athlete(db, journey_phase="followup_transition")
        result = svc.dispatch(athlete_id, "chat", {"message": "hi"}, db)
        assert result.thread_id is not None
        athlete = db.query(AthleteModel).filter_by(id=athlete_id).first()
        assert athlete.active_followup_thread_id == result.thread_id

    def test_chat_turn_thread_not_persisted_on_athlete(self, db):
        svc = CoordinatorService()
        athlete_id = _make_athlete(db, journey_phase="steady_state")
        svc.dispatch(athlete_id, "chat", {"message": "hi"}, db)
        athlete = db.query(AthleteModel).filter_by(id=athlete_id).first()
        # Short-lived: none of the persistent thread fields should be set
        assert athlete.active_onboarding_thread_id is None
        assert athlete.active_recovery_thread_id is None
        assert athlete.active_followup_thread_id is None


# ─── Journey phase transitions ─────────────────────────────────────────────────

class TestJourneyPhaseTransitions:
    def test_advance_signup_to_scope_selection(self, db):
        svc = CoordinatorService()
        athlete_id = _make_athlete(db, journey_phase="signup")
        svc.advance_journey_phase(athlete_id, "scope_selection", db)
        athlete = db.query(AthleteModel).filter_by(id=athlete_id).first()
        assert athlete.journey_phase == "scope_selection"

    def test_advance_scope_to_onboarding(self, db):
        svc = CoordinatorService()
        athlete_id = _make_athlete(db, journey_phase="scope_selection")
        svc.advance_journey_phase(athlete_id, "onboarding", db)
        athlete = db.query(AthleteModel).filter_by(id=athlete_id).first()
        assert athlete.journey_phase == "onboarding"

    def test_invalid_transition_raises(self, db):
        svc = CoordinatorService()
        athlete_id = _make_athlete(db, journey_phase="signup")
        with pytest.raises(ValueError, match="Invalid journey_phase transition"):
            svc.advance_journey_phase(athlete_id, "steady_state", db)

    def test_all_valid_transitions(self, db):
        valid = [
            ("signup", "scope_selection"),
            ("scope_selection", "onboarding"),
            ("onboarding", "baseline_pending_confirmation"),
            ("baseline_pending_confirmation", "baseline_active"),
            ("baseline_active", "followup_transition"),
            ("baseline_active", "baseline_active"),
            ("followup_transition", "steady_state"),
            ("followup_transition", "baseline_active"),
            ("steady_state", "baseline_pending_confirmation"),
            ("steady_state", "steady_state"),
        ]
        svc = CoordinatorService()
        for from_phase, to_phase in valid:
            athlete_id = _make_athlete(db, journey_phase=from_phase)
            svc.advance_journey_phase(athlete_id, to_phase, db)
            athlete = db.query(AthleteModel).filter_by(id=athlete_id).first()
            assert athlete.journey_phase == to_phase, (
                f"transition {from_phase!r} → {to_phase!r} failed"
            )

    def test_invalid_backward_transition_raises(self, db):
        svc = CoordinatorService()
        athlete_id = _make_athlete(db, journey_phase="steady_state")
        with pytest.raises(ValueError, match="Invalid journey_phase transition"):
            svc.advance_journey_phase(athlete_id, "signup", db)

    def test_athlete_not_found_raises(self, db):
        svc = CoordinatorService()
        with pytest.raises(ValueError, match="not found"):
            svc.advance_journey_phase("nonexistent-id", "scope_selection", db)
