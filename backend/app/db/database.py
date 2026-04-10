import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# DATABASE_URL env var is set in Docker (points to postgres).
# Falls back to SQLite for local dev and all tests.
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    _REPO_ROOT = Path(__file__).resolve().parents[3]
    _DB_PATH = _REPO_ROOT / "data" / "resilio.db"
    DATABASE_URL = f"sqlite:///{_DB_PATH}"

_is_sqlite = DATABASE_URL.startswith("sqlite")

_engine_kwargs: dict = {}
if _is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **_engine_kwargs)

if _is_sqlite:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass
