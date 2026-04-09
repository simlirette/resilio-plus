"""Unit tests for WeeklyAnalyzer and WeeklyAdjuster."""
import pytest

from models.weekly_review import ActualWorkout


# ── helpers ──────────────────────────────────────────────────────────────────

def _run(date="2026-04-07", completed=True, duration_min=60, workout_type="easy", avg_hr=None):
    actual_data: dict = {"duration_min": duration_min, "type": workout_type}
    if avg_hr is not None:
        actual_data["avg_hr"] = avg_hr
    return ActualWorkout(sport="running", date=date, completed=completed, actual_data=actual_data)


def _lift(date="2026-04-08", completed=True, duration_min=60, session_type="hypertrophy"):
    return ActualWorkout(
        sport="lifting",
        date=date,
        completed=completed,
        actual_data={"duration_min": duration_min, "session_type": session_type},
    )


# ── WeeklyAnalyzer ────────────────────────────────────────────────────────────

def test_analyzer_all_completed():
    """All sessions completed → completion_rate=1.0."""
    from core.weekly_review import WeeklyAnalyzer

    workouts = [_run("2026-04-07"), _lift("2026-04-08")]
    planned = [{"id": 1}, {"id": 2}]
    result = WeeklyAnalyzer().analyze(planned, workouts)
    assert result["completion_rate"] == 1.0
    assert result["sessions_completed"] == 2
    assert result["sessions_planned"] == 2


def test_analyzer_partial_completion():
    """3 of 5 sessions completed → completion_rate=0.6."""
    from core.weekly_review import WeeklyAnalyzer

    workouts = [
        _run("2026-04-07", completed=True),
        _run("2026-04-08", completed=False),
        _lift("2026-04-09", completed=True),
        _lift("2026-04-10", completed=False),
        _run("2026-04-11", completed=True),
    ]
    planned = [{"id": i} for i in range(5)]
    result = WeeklyAnalyzer().analyze(planned, workouts)
    assert result["completion_rate"] == pytest.approx(0.6)
    assert result["sessions_completed"] == 3
    assert result["sessions_planned"] == 5


def test_analyzer_trimp_running_easy():
    """Easy run 60 min → TRIMP=60 (factor 1.0). 2026-04-06 is a Monday → week_loads[0]=60."""
    from core.weekly_review import WeeklyAnalyzer

    workout = _run("2026-04-06", duration_min=60, workout_type="easy")
    result = WeeklyAnalyzer().analyze([], [workout])
    assert result["trimp_total"] == pytest.approx(60.0)
    assert result["trimp_by_sport"]["running"] == pytest.approx(60.0)
    assert result["week_loads"][0] == pytest.approx(60.0)  # Monday = index 0
    assert len(result["week_loads"]) == 7
