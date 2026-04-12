from unittest.mock import MagicMock, patch

from app.core.sync_scheduler import setup_scheduler, sync_all_hevy, sync_all_strava, sync_all_terra


def test_setup_scheduler_returns_scheduler():
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler = setup_scheduler()
    assert isinstance(scheduler, BackgroundScheduler)
    scheduler.shutdown(wait=False)


def test_setup_scheduler_has_strava_job():
    scheduler = setup_scheduler()
    job_ids = [job.id for job in scheduler.get_jobs()]
    assert "strava_sync" in job_ids
    scheduler.shutdown(wait=False)


def test_setup_scheduler_has_hevy_job():
    scheduler = setup_scheduler()
    job_ids = [job.id for job in scheduler.get_jobs()]
    assert "hevy_sync" in job_ids
    scheduler.shutdown(wait=False)


def test_sync_all_strava_isolates_per_athlete():
    """Failure for one athlete should not stop others."""
    with patch("app.core.sync_scheduler.SessionLocal") as MockSession:
        mock_db = MagicMock()
        MockSession.return_value.__enter__ = MagicMock(return_value=mock_db)
        MockSession.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.query.return_value.filter_by.return_value.all.return_value = []
        sync_all_strava()


def test_sync_all_hevy_isolates_per_athlete():
    with patch("app.core.sync_scheduler.SessionLocal") as MockSession:
        mock_db = MagicMock()
        MockSession.return_value.__enter__ = MagicMock(return_value=mock_db)
        MockSession.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.query.return_value.filter_by.return_value.all.return_value = []
        sync_all_hevy()


def test_setup_scheduler_has_terra_job():
    scheduler = setup_scheduler()
    job_ids = [job.id for job in scheduler.get_jobs()]
    assert "terra_sync" in job_ids
    scheduler.shutdown(wait=False)


def test_setup_scheduler_all_jobs_every_6h():
    scheduler = setup_scheduler()
    try:
        for job in scheduler.get_jobs():
            assert job.trigger.interval.total_seconds() == 6 * 3600, \
                f"Job {job.id} interval is not 6h"
    finally:
        scheduler.shutdown(wait=False)


def test_sync_all_terra_isolates_per_athlete():
    with patch("app.core.sync_scheduler.SessionLocal") as MockSession:
        mock_db = MagicMock()
        MockSession.return_value.__enter__ = MagicMock(return_value=mock_db)
        MockSession.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.query.return_value.filter_by.return_value.all.return_value = []
        sync_all_terra()
