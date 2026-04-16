import uuid
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db import models as _models  # noqa: F401
from app.jobs import models as _job_models  # noqa: F401
from app.jobs.models import JobRunModel
from app.jobs.sync_jobs import sync_strava_for_athlete, sync_hevy_for_athlete, sync_terra_for_athlete


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)
    with Session() as session:
        yield session
    Base.metadata.drop_all(engine)


@patch("app.jobs.sync_jobs.strava_sync")
@patch("app.jobs.sync_jobs.SessionLocal")
def test_sync_strava_for_athlete_logs_run(mock_session_cls, mock_sync):
    mock_db = MagicMock()
    mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_db)
    mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)
    mock_sync.return_value = MagicMock(synced=2, skipped=0)

    sync_strava_for_athlete(athlete_id="abc-123")

    mock_sync.assert_called_once_with("abc-123", mock_db)


@patch("app.jobs.sync_jobs.SyncService.sync_hevy")
@patch("app.jobs.sync_jobs.SessionLocal")
def test_sync_hevy_for_athlete_logs_run(mock_session_cls, mock_sync):
    mock_db = MagicMock()
    mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_db)
    mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)
    mock_sync.return_value = {"synced": 1, "skipped": 0}

    sync_hevy_for_athlete(athlete_id="abc-123")

    mock_sync.assert_called_once_with("abc-123", mock_db)


@patch("app.jobs.sync_jobs.SyncService.sync_terra")
@patch("app.jobs.sync_jobs.SessionLocal")
def test_sync_terra_for_athlete_logs_run(mock_session_cls, mock_sync):
    mock_db = MagicMock()
    mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_db)
    mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)
    mock_sync.return_value = {"synced": 1, "hrv_rmssd": 55.0}

    sync_terra_for_athlete(athlete_id="abc-123")

    mock_sync.assert_called_once_with("abc-123", mock_db)
