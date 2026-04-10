import csv
import io
import uuid
from datetime import datetime

from ..connectors.base import BaseConnector
from ..schemas.connector import ConnectorCredential, HevyExercise, HevySet, HevyWorkout

HEVY_BASE = "https://api.hevyapp.com/v1"
PAGE_SIZE = 10
_LBS_TO_KG = 0.453592


# ── CSV Import ────────────────────────────────────────────────────────────────


def _parse_hevy_datetime(s: str) -> datetime:
    """Parse Hevy CSV datetime: '2 Apr 2026, 19:23'"""
    return datetime.strptime(s.strip(), "%d %b %Y, %H:%M")


def parse_hevy_csv(content: bytes) -> list[HevyWorkout]:
    """
    Parse a Hevy CSV export (2026 format) and return HevyWorkout objects.

    Expected columns:
        Title, Start Time, End Time, Description, Exercise Name,
        Superset ID, Exercise Notes, Set Order, Weight (lbs),
        Reps, RPE, Set Type, Seconds
    """
    try:
        text = content.decode("utf-8-sig")  # strip BOM if present
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))

    # workouts_raw keyed by (title, start_str)
    workouts_raw: dict[str, dict] = {}

    for row in reader:
        title = (row.get("Title") or "").strip()
        start_str = (row.get("Start Time") or "").strip()
        end_str = (row.get("End Time") or "").strip()
        ex_name = (row.get("Exercise Name") or "").strip()

        if not title or not start_str or not ex_name:
            continue

        key = f"{title}\x00{start_str}"
        if key not in workouts_raw:
            workouts_raw[key] = {
                "title": title,
                "start_str": start_str,
                "end_str": end_str,
                "exercises": {},
            }

        exercises = workouts_raw[key]["exercises"]
        if ex_name not in exercises:
            exercises[ex_name] = []

        weight_raw = (row.get("Weight (lbs)") or "").strip()
        weight_kg: float | None = None
        if weight_raw:
            try:
                weight_kg = round(float(weight_raw) * _LBS_TO_KG, 3)
            except ValueError:
                pass

        reps_raw = (row.get("Reps") or "").strip()
        reps: int | None = int(reps_raw) if reps_raw.isdigit() else None

        rpe_raw = (row.get("RPE") or "").strip()
        rpe: float | None = None
        if rpe_raw:
            try:
                rpe = float(rpe_raw)
            except ValueError:
                pass

        set_type = (row.get("Set Type") or "normal").strip() or "normal"

        exercises[ex_name].append(
            HevySet(reps=reps, weight_kg=weight_kg, rpe=rpe, set_type=set_type)
        )

    workouts: list[HevyWorkout] = []
    for raw in workouts_raw.values():
        try:
            start = _parse_hevy_datetime(raw["start_str"])
            end = _parse_hevy_datetime(raw["end_str"]) if raw["end_str"] else start
            duration_seconds = max(0, int((end - start).total_seconds()))
        except ValueError:
            continue  # skip rows with unparseable dates

        exercises_list = [
            HevyExercise(name=name, sets=sets)
            for name, sets in raw["exercises"].items()
        ]

        workouts.append(
            HevyWorkout(
                id=str(uuid.uuid4()),
                title=raw["title"],
                date=start.date(),
                duration_seconds=duration_seconds,
                exercises=exercises_list,
            )
        )

    return workouts


def _parse_set(item: dict) -> HevySet:
    return HevySet(
        reps=item.get("reps"),
        weight_kg=item.get("weight_kg"),
        rpe=item.get("rpe"),
        set_type=item.get("set_type", "normal"),
    )


def _parse_exercise(item: dict) -> HevyExercise:
    return HevyExercise(
        name=item["title"],
        sets=[_parse_set(s) for s in item.get("sets", [])],
    )


def _parse_workout(item: dict, start: datetime) -> HevyWorkout:
    end = datetime.fromisoformat(item["end_time"].replace("Z", "+00:00"))
    duration_seconds = int((end - start).total_seconds())
    return HevyWorkout(
        id=item["id"],
        title=item["title"],
        date=start.date(),
        duration_seconds=duration_seconds,
        exercises=[_parse_exercise(ex) for ex in item.get("exercises", [])],
    )


class HevyConnector(BaseConnector):
    provider = "hevy"

    def _do_refresh_token(self) -> ConnectorCredential:
        return self.credential  # API Key never expires

    def _api_key(self) -> str:
        return self.credential.extra.get("api_key") or self.client_id

    def fetch_workouts(
        self, since: datetime, until: datetime
    ) -> list[HevyWorkout]:
        headers = {"api-key": self._api_key()}
        workouts: list[HevyWorkout] = []
        page = 1
        while True:
            data = self._request(
                "GET",
                f"{HEVY_BASE}/workouts",
                headers=headers,
                params={"page": page, "pageCount": PAGE_SIZE},
            )
            for item in data.get("workouts", []):
                start = datetime.fromisoformat(
                    item["start_time"].replace("Z", "+00:00")
                )
                # Hevy returns workouts newest-first; once we go past since, we're done
                if start < since:
                    return workouts
                if start <= until:
                    workouts.append(_parse_workout(item, start))
            total_pages = data.get("page_count", 1)
            if page >= total_pages:
                break
            page += 1
        return workouts
