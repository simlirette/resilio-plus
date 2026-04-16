from typing import Any
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import desc
from sqlalchemy.orm import Session

from ...db.models import SessionLogModel, TrainingPlanModel
from ...schemas.connector import HevyWorkout


def _get_latest_plan(athlete_id: str, db: Session) -> TrainingPlanModel | None:
    return (
        db.query(TrainingPlanModel)
        .filter(TrainingPlanModel.athlete_id == athlete_id)
        .order_by(desc(TrainingPlanModel.created_at))
        .first()
    )


def _slugify(text: str) -> str:
    return text.lower().replace(" ", "-").replace("/", "-")


def import_hevy_workouts(
    athlete_id: str,
    workouts: list[HevyWorkout],
    db: Session,
) -> dict[str, Any]:
    """Upsert HevyWorkout list into SessionLogModel.

    Matches each workout to a training plan lifting slot by date if available.
    Falls back to a standalone session_id when no plan slot is found.

    Returns a summary dict[str, Any] with per-workout results and totals.
    """
    plan = _get_latest_plan(athlete_id, db)
    plan_slots: list[dict[str, Any]] = json.loads(plan.weekly_slots_json) if plan else []

    results: list[dict[str, Any]] = []
    matched_count = 0
    standalone_count = 0

    for workout in workouts:
        date_key = workout.date.isoformat()
        slug = _slugify(workout.title)

        plan_session_id: str | None = next(
            (s["id"] for s in plan_slots if s["date"] == date_key and s["sport"] == "lifting"),
            None,
        )

        if plan_session_id:
            session_id = plan_session_id
            assert plan is not None  # plan is non-None when plan_session_id is set
            plan_id: str | None = plan.id
            matched = True
            matched_count += 1
        else:
            session_id = f"hevy-standalone-{date_key}-{slug}"
            plan_id = None
            matched = False
            standalone_count += 1

        sets_imported = sum(len(ex.sets) for ex in workout.exercises)

        actual_data = {
            "source": "hevy_csv",
            "hevy_workout_id": workout.id,
            "exercises": [
                {
                    "name": ex.name,
                    "sets": [
                        {
                            "reps": s.reps,
                            "weight_kg": s.weight_kg,
                            "rpe": s.rpe,
                            "set_type": s.set_type,
                        }
                        for s in ex.sets
                    ],
                }
                for ex in workout.exercises
            ],
        }

        existing = (
            db.query(SessionLogModel)
            .filter_by(athlete_id=athlete_id, session_id=session_id)
            .first()
        )

        if existing:
            existing.actual_data_json = json.dumps(actual_data)
            existing.logged_at = datetime.now(timezone.utc)
        else:
            db.add(
                SessionLogModel(
                    id=str(uuid.uuid4()),
                    athlete_id=athlete_id,
                    plan_id=plan_id,
                    session_id=session_id,
                    actual_duration_min=None,
                    skipped=False,
                    actual_data_json=json.dumps(actual_data),
                    logged_at=datetime.now(timezone.utc),
                )
            )

        results.append(
            {
                "date": date_key,
                "workout_name": workout.title,
                "session_id": session_id,
                "matched": matched,
                "sets_imported": sets_imported,
            }
        )

    db.commit()

    return {
        "total_workouts": len(workouts),
        "matched": matched_count,
        "standalone": standalone_count,
        "skipped": 0,
        "workouts": results,
    }
