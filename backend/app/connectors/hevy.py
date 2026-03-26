from datetime import datetime, timezone

from app.connectors.base import BaseConnector
from app.schemas.connector import ConnectorCredential, HevyExercise, HevySet, HevyWorkout

HEVY_BASE = "https://api.hevyapp.com/v1"
PAGE_SIZE = 10


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


def _parse_workout(item: dict) -> HevyWorkout:
    start = datetime.fromisoformat(item["start_time"].replace("Z", "+00:00"))
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
                if start < since:
                    return workouts  # past the date range — stop
                if start <= until:
                    workouts.append(_parse_workout(item))
            total_pages = data.get("page_count", 1)
            if page >= total_pages:
                break
            page += 1
        return workouts
