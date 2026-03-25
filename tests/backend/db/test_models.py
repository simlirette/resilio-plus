import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker


def make_test_engine():
    """Create a fresh in-memory SQLite engine with FK enforcement for testing."""
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def set_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def test_base_is_importable():
    from app.db.database import Base
    assert Base is not None


def test_database_url_is_absolute():
    from app.db.database import DATABASE_URL
    # Must start with sqlite:/// followed by an absolute path (not relative)
    assert DATABASE_URL.startswith("sqlite:///")
    path_part = DATABASE_URL[len("sqlite:///"):]
    # Absolute paths start with / (Unix) or a drive letter (Windows)
    assert path_part.startswith("/") or (len(path_part) > 1 and path_part[1] == ":")


def test_session_local_is_importable():
    from app.db.database import SessionLocal
    assert SessionLocal is not None


def test_in_memory_engine_fk_enforcement():
    """SQLite FK constraints are OFF by default — verify our pragma enables them."""
    engine = make_test_engine()
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA foreign_keys"))
        value = result.scalar()
    assert value == 1, "PRAGMA foreign_keys must be ON"
