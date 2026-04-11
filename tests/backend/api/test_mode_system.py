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
