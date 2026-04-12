"""Unit tests for ExternalPlanService — TDD red phase."""
import uuid
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db import models as _models  # noqa: registers all ORM models
from app.db.models import AthleteModel
from app.models.schemas import ExternalPlanModel, ExternalSessionModel
from app.services.external_plan_service import ExternalPlanService


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


def _make_athlete(db, mode: str = "tracking_only") -> str:
    athlete_id = str(uuid.uuid4())
    athlete = AthleteModel(
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
        coaching_mode=mode,
    )
    db.add(athlete)
    db.commit()
    return athlete_id


# ---------------------------------------------------------------------------
# create_plan
# ---------------------------------------------------------------------------

def test_create_plan_returns_active_plan(db):
    athlete_id = _make_athlete(db)
    plan = ExternalPlanService.create_plan(
        athlete_id=athlete_id,
        title="Coach Bob's Plan",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 7, 31),
        db=db,
    )
    assert plan.id is not None
    assert plan.athlete_id == athlete_id
    assert plan.title == "Coach Bob's Plan"
    assert plan.status == "active"
    assert plan.source == "manual"
    assert plan.start_date == date(2026, 5, 1)
    assert plan.end_date == date(2026, 7, 31)


def test_create_plan_archives_previous_active_plan(db):
    athlete_id = _make_athlete(db)
    first = ExternalPlanService.create_plan(
        athlete_id=athlete_id, title="Plan A", db=db,
    )
    second = ExternalPlanService.create_plan(
        athlete_id=athlete_id, title="Plan B", db=db,
    )
    db.refresh(first)
    assert first.status == "archived"
    assert second.status == "active"


def test_create_plan_no_cross_athlete_archiving(db):
    """Creating a plan for athlete A must not archive athlete B's plan."""
    a1 = _make_athlete(db)
    a2 = _make_athlete(db)
    plan_a = ExternalPlanService.create_plan(athlete_id=a1, title="A Plan", db=db)
    ExternalPlanService.create_plan(athlete_id=a2, title="B Plan", db=db)
    db.refresh(plan_a)
    assert plan_a.status == "active"


# ---------------------------------------------------------------------------
# get_active_plan
# ---------------------------------------------------------------------------

def test_get_active_plan_returns_plan(db):
    athlete_id = _make_athlete(db)
    ExternalPlanService.create_plan(athlete_id=athlete_id, title="Active", db=db)
    plan = ExternalPlanService.get_active_plan(athlete_id=athlete_id, db=db)
    assert plan is not None
    assert plan.title == "Active"
    assert plan.status == "active"


def test_get_active_plan_returns_none_when_no_plan(db):
    athlete_id = _make_athlete(db)
    result = ExternalPlanService.get_active_plan(athlete_id=athlete_id, db=db)
    assert result is None


def test_get_active_plan_returns_none_after_archiving(db):
    athlete_id = _make_athlete(db)
    plan = ExternalPlanService.create_plan(athlete_id=athlete_id, title="X", db=db)
    plan.status = "archived"
    db.commit()
    result = ExternalPlanService.get_active_plan(athlete_id=athlete_id, db=db)
    assert result is None


# ---------------------------------------------------------------------------
# add_session
# ---------------------------------------------------------------------------

def test_add_session_creates_session(db):
    athlete_id = _make_athlete(db)
    plan = ExternalPlanService.create_plan(athlete_id=athlete_id, title="Plan", db=db)
    session = ExternalPlanService.add_session(
        plan_id=plan.id,
        athlete_id=athlete_id,
        session_date=date(2026, 5, 3),
        sport="running",
        title="Easy 5k",
        description="Slow recovery run",
        duration_min=30,
        db=db,
    )
    assert session.id is not None
    assert session.plan_id == plan.id
    assert session.athlete_id == athlete_id
    assert session.sport == "running"
    assert session.title == "Easy 5k"
    assert session.status == "planned"


def test_add_session_to_wrong_athlete_raises(db):
    a1 = _make_athlete(db)
    a2 = _make_athlete(db)
    plan = ExternalPlanService.create_plan(athlete_id=a1, title="Plan", db=db)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        ExternalPlanService.add_session(
            plan_id=plan.id,
            athlete_id=a2,
            session_date=date(2026, 5, 3),
            sport="running",
            title="Sneaky run",
            db=db,
        )
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# update_session
# ---------------------------------------------------------------------------

def test_update_session_partial(db):
    athlete_id = _make_athlete(db)
    plan = ExternalPlanService.create_plan(athlete_id=athlete_id, title="Plan", db=db)
    sess = ExternalPlanService.add_session(
        plan_id=plan.id, athlete_id=athlete_id,
        session_date=date(2026, 5, 3), sport="running", title="Run", db=db,
    )
    updated = ExternalPlanService.update_session(
        session_id=sess.id,
        athlete_id=athlete_id,
        updates={"title": "Long Run", "duration_min": 60, "status": "completed"},
        db=db,
    )
    assert updated.title == "Long Run"
    assert updated.duration_min == 60
    assert updated.status == "completed"
    assert updated.sport == "running"  # unchanged


def test_update_session_wrong_athlete_raises(db):
    a1 = _make_athlete(db)
    a2 = _make_athlete(db)
    plan = ExternalPlanService.create_plan(athlete_id=a1, title="Plan", db=db)
    sess = ExternalPlanService.add_session(
        plan_id=plan.id, athlete_id=a1,
        session_date=date(2026, 5, 3), sport="running", title="Run", db=db,
    )
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        ExternalPlanService.update_session(
            session_id=sess.id, athlete_id=a2,
            updates={"title": "Hacked"}, db=db,
        )
    assert exc.value.status_code == 404


def test_update_nonexistent_session_raises(db):
    athlete_id = _make_athlete(db)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        ExternalPlanService.update_session(
            session_id="ghost-id", athlete_id=athlete_id,
            updates={"title": "X"}, db=db,
        )
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# delete_session
# ---------------------------------------------------------------------------

def test_delete_session_removes_record(db):
    athlete_id = _make_athlete(db)
    plan = ExternalPlanService.create_plan(athlete_id=athlete_id, title="Plan", db=db)
    sess = ExternalPlanService.add_session(
        plan_id=plan.id, athlete_id=athlete_id,
        session_date=date(2026, 5, 3), sport="running", title="Run", db=db,
    )
    session_id = sess.id
    ExternalPlanService.delete_session(
        session_id=session_id, athlete_id=athlete_id, db=db,
    )
    result = db.get(ExternalSessionModel, session_id)
    assert result is None


def test_delete_session_wrong_athlete_raises(db):
    a1 = _make_athlete(db)
    a2 = _make_athlete(db)
    plan = ExternalPlanService.create_plan(athlete_id=a1, title="Plan", db=db)
    sess = ExternalPlanService.add_session(
        plan_id=plan.id, athlete_id=a1,
        session_date=date(2026, 5, 3), sport="running", title="Run", db=db,
    )
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        ExternalPlanService.delete_session(
            session_id=sess.id, athlete_id=a2, db=db,
        )
    assert exc.value.status_code == 404


def test_delete_nonexistent_session_raises(db):
    athlete_id = _make_athlete(db)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        ExternalPlanService.delete_session(
            session_id="ghost", athlete_id=athlete_id, db=db,
        )
    assert exc.value.status_code == 404
