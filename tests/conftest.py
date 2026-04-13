"""
Pytest configuration and shared fixtures.
"""

import sys
import pytest
from pathlib import Path


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create a temporary data directory for testing."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Create subdirectories
    (data_dir / "config").mkdir()
    (data_dir / "athlete").mkdir()
    (data_dir / "activities").mkdir()
    (data_dir / "metrics" / "daily").mkdir(parents=True)
    (data_dir / "plans").mkdir()

    return data_dir


@pytest.fixture
def sample_profile():
    """Sample athlete profile for testing."""
    return {
        "_schema": {"format_version": "1.0.0", "schema_type": "profile"},
        "name": "Test Athlete",
        "created_at": "2026-01-12",
        "running_priority": "secondary",
        "primary_sport": "bouldering",
        "conflict_policy": "ask_each_time",
        "constraints": {
            "unavailable_run_days": ["monday", "wednesday", "thursday", "friday", "sunday"],
            "min_run_days_per_week": 2,
            "max_run_days_per_week": 3,
        },
        "goal": {
            "type": "half_marathon",
            "target_date": "2026-04-15",
        },
    }


# ---------------------------------------------------------------------------
# DB integration fixtures (opt-in — only active when db_session is requested)
# ---------------------------------------------------------------------------

import os as _os

_TEST_DB_URL = _os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://resilio:resilio@localhost:5433/resilio_test",
)


@pytest.fixture(scope="session")
def _db_engine_session():
    """Create test DB engine once per session. Skip if DB not available."""
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(_TEST_DB_URL)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception:
        return None


@pytest.fixture(scope="session")
def db_engine(_db_engine_session):
    """Session-scoped engine with migrations applied. Skip if DB unavailable."""
    if _db_engine_session is None:
        pytest.skip("Test PostgreSQL not available")
    from alembic.config import Config
    from alembic import command as alembic_cmd
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", _TEST_DB_URL)
    alembic_cmd.upgrade(cfg, "head")
    yield _db_engine_session
    from sqlalchemy import text
    with _db_engine_session.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.commit()
    _db_engine_session.dispose()


@pytest.fixture(scope="session")
def _seed_db(db_engine):
    """Seed test fixture once per session."""
    from sqlalchemy.orm import Session
    from scripts.seed_data.test_fixture import insert_test_fixture
    with Session(db_engine) as session:
        insert_test_fixture(session)
        session.commit()


@pytest.fixture
def db_session(db_engine, _seed_db):
    """Per-test transactional session. Rolls back after each test."""
    from sqlalchemy.orm import Session
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    transaction.rollback()
    connection.close()
