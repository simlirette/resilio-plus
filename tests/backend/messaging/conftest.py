from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session


@pytest.fixture
def sqlite_engine() -> Iterator[Engine]:
    """Create an isolated SQLite database with foreign keys enforced."""
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    from app.db import models  # noqa: F401 -- register every model before create_all
    from app.db.database import Base

    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(sqlite_engine: Engine) -> Iterator[Session]:
    with Session(sqlite_engine) as session:
        yield session


@pytest.fixture
def athlete_id(db_session: Session) -> str:
    from app.db.models import AthleteModel

    athlete_id = "athlete-messaging-test"
    db_session.add(
        AthleteModel(
            id=athlete_id,
            name="Messaging Test Athlete",
            age=32,
            sex="F",
            weight_kg=62.0,
            height_cm=170.0,
            primary_sport="running",
            hours_per_week=8.0,
            sports_json='["running"]',
            goals_json='["half-marathon"]',
            available_days_json="[1, 3, 5]",
            equipment_json="[]",
        )
    )
    db_session.commit()
    return athlete_id
