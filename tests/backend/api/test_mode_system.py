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
