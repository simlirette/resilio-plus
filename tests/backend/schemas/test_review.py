import pytest
from datetime import date
from pydantic import ValidationError


def make_activity(**overrides):
    defaults = {
        "date": date(2026, 4, 7),
        "sport": "running",
        "planned_duration_min": 60,
    }
    defaults.update(overrides)
    return defaults


def make_review(**overrides):
    defaults = {
        "athlete_id": "00000000-0000-0000-0000-000000000001",
        "plan_id": "00000000-0000-0000-0000-000000000002",
        "week_start": date(2026, 4, 7),
    }
    defaults.update(overrides)
    return defaults


# --- ActivityResult ---

def test_activity_result_valid_minimal():
    from app.schemas.review import ActivityResult
    a = ActivityResult(**make_activity())
    assert a.actual_duration_min is None
    assert a.rpe_actual is None
    assert a.notes == ""


def test_activity_result_with_actual():
    from app.schemas.review import ActivityResult
    a = ActivityResult(**make_activity(actual_duration_min=55, rpe_actual=7))
    assert a.actual_duration_min == 55
    assert a.rpe_actual == 7


def test_activity_result_zero_planned_duration_raises():
    from app.schemas.review import ActivityResult
    with pytest.raises(ValidationError):
        ActivityResult(**make_activity(planned_duration_min=0))


def test_activity_result_rpe_below_1_raises():
    from app.schemas.review import ActivityResult
    with pytest.raises(ValidationError):
        ActivityResult(**make_activity(rpe_actual=0))


def test_activity_result_rpe_above_10_raises():
    from app.schemas.review import ActivityResult
    with pytest.raises(ValidationError):
        ActivityResult(**make_activity(rpe_actual=11))


def test_activity_result_invalid_sport_raises():
    from app.schemas.review import ActivityResult
    with pytest.raises(ValidationError):
        ActivityResult(**make_activity(sport="yoga"))


def test_activity_result_negative_actual_duration_raises():
    from app.schemas.review import ActivityResult
    with pytest.raises(ValidationError):
        ActivityResult(**make_activity(actual_duration_min=-1))


def test_weekly_review_negative_hrv_raises():
    from app.schemas.review import WeeklyReview
    with pytest.raises(ValidationError):
        WeeklyReview(**make_review(hrv_rmssd=-1.0))


def test_weekly_review_readiness_above_100_raises():
    from app.schemas.review import WeeklyReview
    with pytest.raises(ValidationError):
        WeeklyReview(**make_review(readiness_score=101.0))


# --- WeeklyReview ---

def test_weekly_review_valid_empty_results():
    from app.schemas.review import WeeklyReview
    review = WeeklyReview(**make_review())
    assert review.results == []
    assert review.readiness_score is None
    assert review.hrv_rmssd is None
    assert review.sleep_hours_avg is None
    assert review.athlete_comment == ""


def test_weekly_review_id_generated():
    from app.schemas.review import WeeklyReview
    r1 = WeeklyReview(**make_review())
    r2 = WeeklyReview(**make_review())
    assert r1.id != r2.id


def test_weekly_review_with_results():
    from app.schemas.review import WeeklyReview
    review = WeeklyReview(**make_review(
        results=[make_activity(), make_activity(sport="lifting")]
    ))
    assert len(review.results) == 2
    assert review.results[0].sport.value == "running"
    assert review.results[1].sport.value == "lifting"


def test_weekly_review_with_recovery_metrics():
    from app.schemas.review import WeeklyReview
    review = WeeklyReview(**make_review(
        readiness_score=78.5,
        hrv_rmssd=42.3,
        sleep_hours_avg=7.5,
    ))
    assert review.readiness_score == 78.5
    assert review.hrv_rmssd == 42.3
    assert review.sleep_hours_avg == 7.5


def test_weekly_review_empty_results_json_not_null():
    from app.schemas.review import WeeklyReview
    import json
    review = WeeklyReview(**make_review())
    json_str = review.model_dump_json()
    data = json.loads(json_str)
    # results serializes as [] not null
    assert data["results"] == []


def test_weekly_review_json_round_trip():
    from app.schemas.review import WeeklyReview
    review = WeeklyReview(**make_review(
        results=[make_activity(actual_duration_min=58, rpe_actual=6)],
        readiness_score=80.0,
    ))
    json_str = review.model_dump_json()
    review2 = WeeklyReview.model_validate_json(json_str)
    assert review == review2
