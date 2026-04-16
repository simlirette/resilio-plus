import csv
import io
from datetime import date
from typing import Any

from ...schemas.connector import HevyExercise, HevySet, HevyWorkout

_REQUIRED_COLUMNS = {"Date", "Workout Name", "Exercise Name", "Weight", "Reps", "RPE"}


def _slugify(text: str) -> str:
    return text.lower().replace(" ", "-").replace("/", "-")


def parse_hevy_csv(content: bytes, unit: str = "kg") -> list[HevyWorkout]:
    """Parse Hevy CSV export bytes into HevyWorkout objects.

    Args:
        content: Raw CSV file bytes.
        unit: Weight unit in the file — "kg" (default) or "lbs".

    Returns:
        List of HevyWorkout, one per unique (Date, Workout Name) pair.

    Raises:
        ValueError: If unit is invalid, required columns are missing, or no data rows.

    Note:
        Standard Hevy CSV export does not include Set Type or workout duration.
        All sets are stored as set_type="normal". duration_seconds is set to 0.
    """
    if unit not in ("kg", "lbs"):
        raise ValueError(f"Invalid unit: {unit!r}. Must be 'kg' or 'lbs'")

    text = content.decode("utf-8-sig")  # handle BOM from Windows exports
    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None:
        raise ValueError("no workouts found")

    missing = _REQUIRED_COLUMNS - set(reader.fieldnames)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    rows = list(reader)
    if not rows:
        raise ValueError("no workouts found")

    # Group by (Date, Workout Name) preserving CSV order
    workout_map: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (row["Date"].strip(), row["Workout Name"].strip())
        if key not in workout_map:
            workout_map[key] = []
        workout_map[key].append(row)

    workouts: list[HevyWorkout] = []

    for (date_str, workout_name), workout_rows in workout_map.items():
        try:
            workout_date = date.fromisoformat(date_str)
        except ValueError:
            raise ValueError(f"Invalid date: {date_str!r}")

        # Group rows by exercise name, preserving first-appearance order
        exercise_map: dict[str, list[dict[str, Any]]] = {}
        for row in workout_rows:
            ex_name = row["Exercise Name"].strip()
            if ex_name not in exercise_map:
                exercise_map[ex_name] = []
            exercise_map[ex_name].append(row)

        exercises: list[HevyExercise] = []
        for ex_name, ex_rows in exercise_map.items():
            sets: list[HevySet] = []
            for row in ex_rows:
                weight_raw = row["Weight"].strip()
                reps_raw = row["Reps"].strip()
                rpe_raw = row["RPE"].strip()

                try:
                    weight_kg = None
                    if weight_raw:
                        w = float(weight_raw)
                        weight_kg = w * 0.453592 if unit == "lbs" else w

                    reps = int(reps_raw) if reps_raw else None
                    rpe = (float(rpe_raw) or None) if rpe_raw else None  # 0.0 treated as unset

                    sets.append(
                        HevySet(
                            reps=reps,
                            weight_kg=weight_kg,
                            rpe=rpe,
                            set_type="normal",
                        )
                    )
                except (ValueError, Exception) as e:
                    raise ValueError(f"Invalid data in row for exercise '{ex_name}': {e}") from e
            exercises.append(HevyExercise(name=ex_name, sets=sets))

        workout_id = f"{workout_date.isoformat()}-{_slugify(workout_name)}"
        workouts.append(
            HevyWorkout(
                id=workout_id,
                title=workout_name,
                date=workout_date,
                duration_seconds=0,
                exercises=exercises,
            )
        )

    return workouts
