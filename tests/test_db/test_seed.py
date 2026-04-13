"""Integration tests for seed scripts — require live PostgreSQL on port 5433.

Run with: pytest tests/test_db/ -v -m db_integration
Skip if TEST_DATABASE_URL is not available: tests auto-skip.
"""
from __future__ import annotations

import os

import pytest


_TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://resilio:resilio@localhost:5433/resilio_test",
)

pytestmark = pytest.mark.db_integration


@pytest.fixture(scope="module")
def test_engine():
    """Create test DB engine and apply migrations once for this module."""
    pytest.importorskip("psycopg2", reason="psycopg2 not available")
    from sqlalchemy import create_engine
    from alembic.config import Config
    from alembic import command as alembic_cmd

    engine = create_engine(_TEST_DB_URL)
    try:
        with engine.connect():
            pass
    except Exception:
        pytest.skip("Test PostgreSQL not available on port 5433")

    # Apply migrations
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", _TEST_DB_URL)
    alembic_cmd.upgrade(cfg, "head")

    yield engine

    # Teardown: wipe schema
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.commit()
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    """Per-test transactional session with savepoint rollback."""
    from sqlalchemy.orm import Session

    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    yield session

    session.close()
    transaction.rollback()
    connection.close()


def test_test_fixture_inserts_expected_rows(db_session):
    from scripts.seed_data.test_fixture import insert_test_fixture, TEST_ATHLETE_ID
    from app.db.models import AthleteModel, UserModel, TrainingPlanModel, SessionLogModel
    from app.models.schemas import EnergySnapshotModel, AllostaticEntryModel

    insert_test_fixture(db_session)
    db_session.flush()

    assert db_session.get(AthleteModel, TEST_ATHLETE_ID) is not None
    assert db_session.query(UserModel).filter_by(athlete_id=TEST_ATHLETE_ID).count() == 1
    assert db_session.query(TrainingPlanModel).filter_by(athlete_id=TEST_ATHLETE_ID).count() == 1
    assert db_session.query(SessionLogModel).filter_by(athlete_id=TEST_ATHLETE_ID).count() == 3
    assert db_session.query(EnergySnapshotModel).filter_by(athlete_id=TEST_ATHLETE_ID).count() == 1
    assert db_session.query(AllostaticEntryModel).filter_by(athlete_id=TEST_ATHLETE_ID).count() == 1


def test_test_fixture_is_idempotent(db_session):
    from scripts.seed_data.test_fixture import insert_test_fixture, TEST_ATHLETE_ID
    from app.db.models import AthleteModel

    insert_test_fixture(db_session)
    insert_test_fixture(db_session)  # second call — must not raise or duplicate
    db_session.flush()

    count = db_session.query(AthleteModel).filter_by(id=TEST_ATHLETE_ID).count()
    assert count == 1


def test_alice_inserts_expected_rows(db_session):
    from scripts.seed_data.alice import insert_alice, ALICE_ID
    from app.db.models import (
        AthleteModel, UserModel, TrainingPlanModel,
        SessionLogModel, WeeklyReviewModel, NutritionPlanModel,
    )
    from app.models.schemas import (
        AllostaticEntryModel, EnergySnapshotModel,
        HormonalProfileModel, HeadCoachMessageModel,
    )

    insert_alice(db_session)
    db_session.flush()

    assert db_session.get(AthleteModel, ALICE_ID) is not None
    assert db_session.query(UserModel).filter_by(athlete_id=ALICE_ID).count() == 1
    assert db_session.query(TrainingPlanModel).filter_by(athlete_id=ALICE_ID).count() == 1
    assert db_session.query(NutritionPlanModel).filter_by(athlete_id=ALICE_ID).count() == 1
    assert db_session.query(SessionLogModel).filter_by(athlete_id=ALICE_ID).count() == 35
    assert db_session.query(AllostaticEntryModel).filter_by(athlete_id=ALICE_ID).count() == 28
    assert db_session.query(EnergySnapshotModel).filter_by(athlete_id=ALICE_ID).count() == 14
    assert db_session.query(WeeklyReviewModel).filter_by(athlete_id=ALICE_ID).count() == 2
    assert db_session.query(HormonalProfileModel).filter_by(athlete_id=ALICE_ID).count() == 1
    assert db_session.query(HeadCoachMessageModel).filter_by(athlete_id=ALICE_ID).count() == 1


def test_alice_is_idempotent(db_session):
    from scripts.seed_data.alice import insert_alice, ALICE_ID
    from app.db.models import AthleteModel

    insert_alice(db_session)
    insert_alice(db_session)
    db_session.flush()
    assert db_session.query(AthleteModel).filter_by(id=ALICE_ID).count() == 1


def test_marc_inserts_expected_rows(db_session):
    from scripts.seed_data.marc import insert_marc, MARC_ID
    from app.db.models import (
        AthleteModel, UserModel, TrainingPlanModel,
        SessionLogModel, WeeklyReviewModel, ConnectorCredentialModel,
    )
    from app.models.schemas import AllostaticEntryModel, EnergySnapshotModel

    insert_marc(db_session)
    db_session.flush()

    assert db_session.get(AthleteModel, MARC_ID) is not None
    assert db_session.query(UserModel).filter_by(athlete_id=MARC_ID).count() == 1
    assert db_session.query(ConnectorCredentialModel).filter_by(athlete_id=MARC_ID).count() == 1
    assert db_session.query(TrainingPlanModel).filter_by(athlete_id=MARC_ID).count() == 1
    assert db_session.query(SessionLogModel).filter_by(athlete_id=MARC_ID).count() == 41
    assert db_session.query(AllostaticEntryModel).filter_by(athlete_id=MARC_ID).count() == 28
    assert db_session.query(EnergySnapshotModel).filter_by(athlete_id=MARC_ID).count() == 14
    assert db_session.query(WeeklyReviewModel).filter_by(athlete_id=MARC_ID).count() == 2


def test_marc_is_idempotent(db_session):
    from scripts.seed_data.marc import insert_marc, MARC_ID
    from app.db.models import AthleteModel

    insert_marc(db_session)
    insert_marc(db_session)
    db_session.flush()
    assert db_session.query(AthleteModel).filter_by(id=MARC_ID).count() == 1


def test_seed_dev_inserts_both_athletes(db_session):
    """seed_dev inserts Alice and Marc without errors."""
    from scripts.seed_data.alice import insert_alice, ALICE_ID
    from scripts.seed_data.marc import insert_marc, MARC_ID
    from app.db.models import AthleteModel

    insert_alice(db_session)
    insert_marc(db_session)
    db_session.flush()

    assert db_session.query(AthleteModel).filter_by(id=ALICE_ID).count() == 1
    assert db_session.query(AthleteModel).filter_by(id=MARC_ID).count() == 1


def test_db_reset_guard_requires_confirm(monkeypatch):
    """reset() exits with code 1 if --confirm not in argv."""
    import sys
    monkeypatch.setattr(sys, "argv", ["db-reset"])
    with pytest.raises(SystemExit) as exc_info:
        from scripts.db_commands import reset
        reset()
    assert exc_info.value.code == 1
