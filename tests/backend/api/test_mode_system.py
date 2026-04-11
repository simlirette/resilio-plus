"""Tests for the mode system: coaching_mode field, ExternalPlan models."""
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db import models as _models  # noqa: registers all ORM classes


def _engine():
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def test_athlete_model_has_coaching_mode_column():
    engine = _engine()
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("athletes")}
    assert "coaching_mode" in columns, "athletes table missing coaching_mode column"


def test_training_plan_model_has_status_column():
    engine = _engine()
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("training_plans")}
    assert "status" in columns, "training_plans table missing status column"


def test_external_plans_table_exists():
    engine = _engine()
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    assert "external_plans" in inspector.get_table_names()


def test_external_sessions_table_exists():
    engine = _engine()
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    assert "external_sessions" in inspector.get_table_names()


def test_athlete_coaching_mode_defaults_to_full():
    """Verify coaching_mode defaults to 'full' when not specified."""
    from app.db.models import AthleteModel
    import uuid

    engine = _engine()
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    athlete = AthleteModel(
        id=str(uuid.uuid4()),
        name="Test Athlete",
        age=30,
        sex="M",
        weight_kg=70.0,
        height_cm=175.0,
        primary_sport="running",
        hours_per_week=8.0,
        sports_json='["running"]',
        goals_json='["fitness"]',
        available_days_json='["monday", "wednesday", "friday"]',
        equipment_json='[]',
    )
    session.add(athlete)
    session.commit()
    session.refresh(athlete)

    assert athlete.coaching_mode == "full"
    session.close()


def test_training_plan_status_defaults_to_active():
    """Verify status defaults to 'active' when not specified."""
    from app.db.models import AthleteModel, TrainingPlanModel
    import uuid
    from datetime import date

    engine = _engine()
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    athlete_id = str(uuid.uuid4())
    athlete = AthleteModel(
        id=athlete_id,
        name="Plan Athlete",
        age=25,
        sex="F",
        weight_kg=60.0,
        height_cm=165.0,
        primary_sport="cycling",
        hours_per_week=6.0,
        sports_json='["cycling"]',
        goals_json='["endurance"]',
        available_days_json='["tuesday", "thursday"]',
        equipment_json='[]',
    )
    session.add(athlete)

    plan = TrainingPlanModel(
        id=str(uuid.uuid4()),
        athlete_id=athlete_id,
        start_date=date.today(),
        end_date=date.today(),
        phase="base",
        total_weekly_hours=6.0,
        acwr=1.0,
        weekly_slots_json='[]',
    )
    session.add(plan)
    session.commit()
    session.refresh(plan)

    assert plan.status == "active"
    session.close()


def test_external_plan_cascade_deletes_sessions():
    """Verify deleting an ExternalPlan cascades to its ExternalSessions."""
    from app.models.schemas import ExternalPlanModel, ExternalSessionModel
    from app.db.models import AthleteModel
    import uuid
    from datetime import date

    engine = _engine()
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    athlete_id = str(uuid.uuid4())
    athlete = AthleteModel(
        id=athlete_id,
        name="Cascade Athlete",
        age=28,
        sex="M",
        weight_kg=75.0,
        height_cm=180.0,
        primary_sport="running",
        hours_per_week=5.0,
        sports_json='["running"]',
        goals_json='[]',
        available_days_json='["monday"]',
        equipment_json='[]',
    )
    session.add(athlete)

    plan_id = str(uuid.uuid4())
    plan = ExternalPlanModel(
        id=plan_id,
        athlete_id=athlete_id,
        title="Test Plan",
        source="manual",
    )
    session.add(plan)

    ext_session = ExternalSessionModel(
        id=str(uuid.uuid4()),
        plan_id=plan_id,
        athlete_id=athlete_id,
        session_date=date.today(),
        sport="running",
        title="Easy Run",
    )
    session.add(ext_session)
    session.commit()

    session.delete(plan)
    session.commit()

    count = session.query(ExternalSessionModel).filter_by(plan_id=plan_id).count()
    assert count == 0, "ExternalSessions should be cascade-deleted with their plan"
    session.close()


# Schema tests for coaching_mode
from app.schemas.athlete import AthleteCreate, AthleteProfile, AthleteUpdate


def test_athlete_create_has_coaching_mode_default():
    payload = {
        "name": "Bob",
        "age": 28,
        "sex": "M",
        "weight_kg": 75.0,
        "height_cm": 180.0,
        "sports": ["running"],
        "primary_sport": "running",
        "goals": ["run 10k"],
        "available_days": [1, 3, 5],
        "hours_per_week": 6.0,
    }
    athlete = AthleteCreate(**payload)
    assert athlete.coaching_mode == "full"


def test_athlete_create_accepts_tracking_only():
    payload = {
        "name": "Carol",
        "age": 35,
        "sex": "F",
        "weight_kg": 58.0,
        "height_cm": 165.0,
        "sports": ["running"],
        "primary_sport": "running",
        "goals": ["finish marathon"],
        "available_days": [0, 2, 5],
        "hours_per_week": 8.0,
        "coaching_mode": "tracking_only",
    }
    athlete = AthleteCreate(**payload)
    assert athlete.coaching_mode == "tracking_only"


def test_athlete_create_rejects_invalid_mode():
    from pydantic import ValidationError
    import pytest
    payload = {
        "name": "Dan",
        "age": 40,
        "sex": "M",
        "weight_kg": 80.0,
        "height_cm": 175.0,
        "sports": ["lifting"],
        "primary_sport": "lifting",
        "goals": ["bench 100kg"],
        "available_days": [1, 4],
        "hours_per_week": 5.0,
        "coaching_mode": "invalid_mode",
    }
    with pytest.raises(ValidationError):
        AthleteCreate(**payload)


# ModeGuard dependency tests
import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException

from app.dependencies.mode_guard import require_full_mode, require_tracking_mode
from app.db.models import AthleteModel


def _make_athlete(coaching_mode: str, athlete_id: str = "abc") -> AthleteModel:
    a = MagicMock(spec=AthleteModel)
    a.id = athlete_id
    a.coaching_mode = coaching_mode
    return a


def test_require_full_mode_passes_for_full():
    athlete = _make_athlete("full", "abc")
    db = MagicMock()
    db.get.return_value = athlete
    result = require_full_mode(athlete_id="abc", current_id="abc", db=db)
    assert result is athlete


def test_require_full_mode_raises_for_tracking_only():
    athlete = _make_athlete("tracking_only", "abc")
    db = MagicMock()
    db.get.return_value = athlete
    with pytest.raises(HTTPException) as exc_info:
        require_full_mode(athlete_id="abc", current_id="abc", db=db)
    assert exc_info.value.status_code == 403


def test_require_full_mode_raises_for_wrong_owner():
    athlete = _make_athlete("full", "abc")
    db = MagicMock()
    db.get.return_value = athlete
    with pytest.raises(HTTPException) as exc_info:
        require_full_mode(athlete_id="abc", current_id="xyz", db=db)
    assert exc_info.value.status_code == 403


def test_require_tracking_mode_passes_for_tracking_only():
    athlete = _make_athlete("tracking_only", "abc")
    db = MagicMock()
    db.get.return_value = athlete
    result = require_tracking_mode(athlete_id="abc", current_id="abc", db=db)
    assert result is athlete


def test_require_tracking_mode_raises_for_full():
    athlete = _make_athlete("full", "abc")
    db = MagicMock()
    db.get.return_value = athlete
    with pytest.raises(HTTPException) as exc_info:
        require_tracking_mode(athlete_id="abc", current_id="abc", db=db)
    assert exc_info.value.status_code == 403


def test_patch_mode_switches_to_tracking_only(authed_client):
    client, athlete_id = authed_client
    resp = client.patch(
        f"/athletes/{athlete_id}/mode",
        json={"coaching_mode": "tracking_only"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["coaching_mode"] == "tracking_only"


def test_patch_mode_switches_back_to_full(authed_client):
    client, athlete_id = authed_client
    # Switch to tracking_only first
    client.patch(f"/athletes/{athlete_id}/mode", json={"coaching_mode": "tracking_only"})
    # Switch back to full
    resp = client.patch(f"/athletes/{athlete_id}/mode", json={"coaching_mode": "full"})
    assert resp.status_code == 200
    assert resp.json()["coaching_mode"] == "full"


def test_patch_mode_rejects_invalid_value(authed_client):
    client, athlete_id = authed_client
    resp = client.patch(
        f"/athletes/{athlete_id}/mode",
        json={"coaching_mode": "coaching_only"},
    )
    assert resp.status_code == 422


def test_patch_mode_archives_active_plan_when_switching_to_tracking(authed_client):
    """Switching to tracking_only archives the active training plan."""
    client, athlete_id = authed_client
    resp = client.patch(
        f"/athletes/{athlete_id}/mode",
        json={"coaching_mode": "tracking_only"},
    )
    assert resp.status_code == 200
    # Verify plan is now archived via the plans endpoint
    plans_resp = client.get(f"/athletes/{athlete_id}/plans")
    assert plans_resp.status_code == 200
    plans = plans_resp.json()
    if plans:  # onboarding creates a plan
        assert all(p.get("status", "active") == "archived" for p in plans), \
            "All plans should be archived after switching to tracking_only"


def test_patch_mode_requires_auth(client):
    resp = client.patch("/athletes/some-id/mode", json={"coaching_mode": "full"})
    assert resp.status_code == 401


def test_onboarding_with_tracking_only_mode(client):
    """An athlete can register with tracking_only mode."""
    payload = {
        "name": "Eve",
        "age": 25,
        "sex": "F",
        "weight_kg": 55.0,
        "height_cm": 162.0,
        "sports": ["running"],
        "primary_sport": "running",
        "goals": ["stay active"],
        "available_days": [1, 3, 5],
        "hours_per_week": 5.0,
        "email": "eve@test.com",
        "password": "password123",
        "plan_start_date": "2026-05-01",
        "coaching_mode": "tracking_only",
    }
    resp = client.post("/athletes/onboarding", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["athlete"]["coaching_mode"] == "tracking_only"


def test_onboarding_defaults_to_full_mode(client):
    """Onboarding without coaching_mode defaults to full."""
    payload = {
        "name": "Frank",
        "age": 32,
        "sex": "M",
        "weight_kg": 78.0,
        "height_cm": 178.0,
        "sports": ["running", "lifting"],
        "primary_sport": "running",
        "goals": ["sub-25 5k"],
        "available_days": [0, 2, 4, 6],
        "hours_per_week": 8.0,
        "email": "frank@test.com",
        "password": "password123",
        "plan_start_date": "2026-05-01",
    }
    resp = client.post("/athletes/onboarding", json=payload)
    assert resp.status_code == 201
    assert resp.json()["athlete"]["coaching_mode"] == "full"
