"""A database that is not up yet must not cost the athlete their weekly plan.

Observed 2026-08-21 on a live restart::

    Could not restore per-athlete jobs on startup (DB unavailable):
    connection to server at "localhost" (::1), port 5432 failed

The app then logged "Background scheduler started with 3 jobs" and reported
`/health: ok`. The three are the global crons. Every per-athlete job — the
provider syncs and, above all, the weekly cycle — was silently gone until
somebody happened to restart the process a second time.

That is the whole of goal step 5: the athlete receives next week without asking
for it. It failing quietly, behind a healthy-looking process, is worse than it
failing loudly. Postgres coming up a few seconds after the API is ordinary; the
scheduler has to survive it.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def scheduler() -> MagicMock:
    sched = MagicMock()
    sched.get_jobs.return_value = []
    return sched


class TestWhenTheDatabaseIsUp:
    def test_it_restores_immediately_and_schedules_no_retry(self, scheduler) -> None:
        from app.jobs.scheduler import restore_athlete_jobs

        with patch("app.jobs.scheduler.SessionLocal"), patch(
            "app.jobs.scheduler.restore_all_jobs"
        ) as restore_all, patch("app.jobs.scheduler.restore_weekly_cycles") as restore_weekly:
            restored = restore_athlete_jobs(scheduler)

        assert restored is True
        restore_all.assert_called_once()
        restore_weekly.assert_called_once()
        scheduler.add_job.assert_not_called()


class TestWhenTheDatabaseIsDown:
    def test_it_reports_failure_instead_of_pretending(self, scheduler) -> None:
        from app.jobs.scheduler import restore_athlete_jobs

        with patch("app.jobs.scheduler.SessionLocal", side_effect=OSError("db down")):
            assert restore_athlete_jobs(scheduler) is False

    def test_it_schedules_a_retry(self, scheduler) -> None:
        """Without this the weekly cycle is gone until the next manual restart."""
        from app.jobs.scheduler import _RETRY_JOB_ID, restore_athlete_jobs

        with patch("app.jobs.scheduler.SessionLocal", side_effect=OSError("db down")):
            restore_athlete_jobs(scheduler)

        assert scheduler.add_job.call_count == 1
        assert scheduler.add_job.call_args.kwargs["id"] == _RETRY_JOB_ID

    def test_the_retry_replaces_the_pending_one(self, scheduler) -> None:
        """Two failures must leave one retry, not a queue of them."""
        from app.jobs.scheduler import restore_athlete_jobs

        with patch("app.jobs.scheduler.SessionLocal", side_effect=OSError("db down")):
            restore_athlete_jobs(scheduler)

        assert scheduler.add_job.call_args.kwargs["replace_existing"] is True

    def test_a_later_success_stops_the_retrying(self, scheduler) -> None:
        from app.jobs.scheduler import _RETRY_JOB_ID, restore_athlete_jobs

        with patch("app.jobs.scheduler.SessionLocal", side_effect=OSError("db down")):
            restore_athlete_jobs(scheduler)
        scheduler.add_job.reset_mock()

        with patch("app.jobs.scheduler.SessionLocal"), patch(
            "app.jobs.scheduler.restore_all_jobs"
        ), patch("app.jobs.scheduler.restore_weekly_cycles"):
            assert restore_athlete_jobs(scheduler) is True

        scheduler.add_job.assert_not_called()
        scheduler.remove_job.assert_called_once_with(_RETRY_JOB_ID)

    def test_removing_an_absent_retry_is_not_an_error(self, scheduler) -> None:
        """The first successful startup has no retry job to remove."""
        from app.jobs.scheduler import restore_athlete_jobs

        scheduler.remove_job.side_effect = KeyError("no such job")

        with patch("app.jobs.scheduler.SessionLocal"), patch(
            "app.jobs.scheduler.restore_all_jobs"
        ), patch("app.jobs.scheduler.restore_weekly_cycles"):
            assert restore_athlete_jobs(scheduler) is True


class TestStartup:
    def test_a_down_database_still_starts_the_api(self, scheduler) -> None:
        """The API answering is not conditional on Postgres being up first."""
        from app.jobs import scheduler as module

        with patch.object(module, "BackgroundScheduler", return_value=scheduler), patch.object(
            module, "SessionLocal", side_effect=OSError("db down")
        ):
            assert module.setup_scheduler() is scheduler

        scheduler.start.assert_called_once()
