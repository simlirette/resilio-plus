import json
import uuid
from datetime import date

from app.db.models import AthleteModel, SessionLogModel
from app.integrations.hevy.importer import import_hevy_workouts
from app.schemas.connector import HevyExercise, HevySet, HevyWorkout


def _make_athlete(db_session) -> AthleteModel:
    athlete = AthleteModel(
        id=str(uuid.uuid4()),
        name="Test Athlete",
        age=30,
        sex="M",
        weight_kg=75.0,
        height_cm=180.0,
        primary_sport="lifting",
        hours_per_week=5.0,
        sports_json='["lifting"]',
        goals_json='["strength"]',
        available_days_json='[0, 2, 4]',
        equipment_json='[]',
    )
    db_session.add(athlete)
    db_session.commit()
    return athlete


def _make_workout(title: str = "Push Day A", workout_date: date = date(2026, 4, 1)) -> HevyWorkout:
    slug = title.lower().replace(" ", "-")
    return HevyWorkout(
        id=f"{workout_date.isoformat()}-{slug}",
        title=title,
        date=workout_date,
        duration_seconds=0,
        exercises=[
            HevyExercise(
                name="Squat",
                sets=[
                    HevySet(reps=5, weight_kg=100.0, rpe=8.0, set_type="normal"),
                    HevySet(reps=5, weight_kg=100.0, rpe=9.0, set_type="normal"),
                ],
            )
        ],
    )


def test_import_creates_standalone_when_no_plan(db_session):
    athlete = _make_athlete(db_session)
    result = import_hevy_workouts(athlete.id, [_make_workout()], db_session)

    assert result["total_workouts"] == 1
    assert result["standalone"] == 1
    assert result["matched"] == 0
    assert result["skipped"] == 0

    log = db_session.query(SessionLogModel).filter_by(athlete_id=athlete.id).first()
    assert log is not None
    assert log.session_id.startswith("hevy-standalone-")
    assert log.plan_id is None


def test_import_upsert_does_not_create_duplicate(db_session):
    athlete = _make_athlete(db_session)
    workout = _make_workout()
    import_hevy_workouts(athlete.id, [workout], db_session)
    import_hevy_workouts(athlete.id, [workout], db_session)  # second import

    count = db_session.query(SessionLogModel).filter_by(athlete_id=athlete.id).count()
    assert count == 1


def test_import_actual_data_json_structure(db_session):
    athlete = _make_athlete(db_session)
    import_hevy_workouts(athlete.id, [_make_workout()], db_session)

    log = db_session.query(SessionLogModel).filter_by(athlete_id=athlete.id).first()
    data = json.loads(log.actual_data_json)

    assert data["source"] == "hevy_csv"
    assert "hevy_workout_id" in data
    assert len(data["exercises"]) == 1
    assert data["exercises"][0]["name"] == "Squat"
    assert len(data["exercises"][0]["sets"]) == 2
    assert data["exercises"][0]["sets"][0]["weight_kg"] == 100.0


def test_import_multiple_workouts_creates_separate_logs(db_session):
    athlete = _make_athlete(db_session)
    workouts = [
        _make_workout("Push Day A", date(2026, 4, 1)),
        _make_workout("Leg Day", date(2026, 4, 3)),
    ]
    result = import_hevy_workouts(athlete.id, workouts, db_session)

    assert result["total_workouts"] == 2
    count = db_session.query(SessionLogModel).filter_by(athlete_id=athlete.id).count()
    assert count == 2


def test_import_response_includes_workout_details(db_session):
    athlete = _make_athlete(db_session)
    result = import_hevy_workouts(athlete.id, [_make_workout()], db_session)

    assert len(result["workouts"]) == 1
    w = result["workouts"][0]
    assert w["date"] == "2026-04-01"
    assert w["workout_name"] == "Push Day A"
    assert w["sets_imported"] == 2
    assert "session_id" in w
    assert isinstance(w["matched"], bool)


def test_import_sets_imported_count(db_session):
    athlete = _make_athlete(db_session)
    workout = HevyWorkout(
        id="2026-04-01-push-day-a",
        title="Push Day A",
        date=date(2026, 4, 1),
        duration_seconds=0,
        exercises=[
            HevyExercise(
                name="Bench Press",
                sets=[
                    HevySet(reps=8, weight_kg=80.0, set_type="normal"),
                    HevySet(reps=6, weight_kg=82.5, set_type="normal"),
                ],
            ),
            HevyExercise(
                name="Overhead Press",
                sets=[HevySet(reps=10, weight_kg=50.0, set_type="normal")],
            ),
        ],
    )
    result = import_hevy_workouts(athlete.id, [workout], db_session)
    assert result["workouts"][0]["sets_imported"] == 3
