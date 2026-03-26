import json
import pytest
import respx
import httpx
from pathlib import Path
from datetime import datetime, timezone

from app.connectors.hevy import HevyConnector
from app.schemas.connector import HevyWorkout

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def connector(hevy_credential):
    c = HevyConnector(hevy_credential, client_id="", client_secret="")
    yield c
    c.close()


@respx.mock
def test_fetch_workouts_parses_fixture(connector):
    fixture = json.loads((FIXTURES_DIR / "hevy_workouts.json").read_text())
    respx.get("https://api.hevyapp.com/v1/workouts").mock(
        return_value=httpx.Response(200, json=fixture)
    )
    since = datetime(2026, 3, 1, tzinfo=timezone.utc)
    until = datetime(2026, 3, 31, tzinfo=timezone.utc)
    workouts = connector.fetch_workouts(since, until)
    assert len(workouts) == 1
    assert isinstance(workouts[0], HevyWorkout)
    assert workouts[0].title == "Push Day"
    assert workouts[0].duration_seconds == 3900  # 65 min = 3900 s


@respx.mock
def test_fetch_workouts_bodyweight_sets_parse_correctly(connector):
    fixture = json.loads((FIXTURES_DIR / "hevy_workouts.json").read_text())
    respx.get("https://api.hevyapp.com/v1/workouts").mock(
        return_value=httpx.Response(200, json=fixture)
    )
    since = datetime(2026, 3, 1, tzinfo=timezone.utc)
    until = datetime(2026, 3, 31, tzinfo=timezone.utc)
    workouts = connector.fetch_workouts(since, until)
    pullup_exercise = workouts[0].exercises[1]  # Pull-up (index 1)
    assert pullup_exercise.name == "Pull-up"
    assert pullup_exercise.sets[0].weight_kg is None


@respx.mock
def test_fetch_workouts_pagination_stops_at_since_boundary(hevy_credential):
    page1 = {
        "workouts": [{
            "id": "w1", "title": "In Range",
            "start_time": "2026-03-20T10:00:00Z",
            "end_time": "2026-03-20T11:00:00Z",
            "exercises": [],
        }],
        "page": 1, "page_count": 2,
    }
    page2 = {
        "workouts": [{
            "id": "w2", "title": "Before Range",
            "start_time": "2026-03-19T10:00:00Z",
            "end_time": "2026-03-19T11:00:00Z",
            "exercises": [],
        }],
        "page": 2, "page_count": 2,
    }
    route = respx.get("https://api.hevyapp.com/v1/workouts").mock(
        side_effect=[
            httpx.Response(200, json=page1),
            httpx.Response(200, json=page2),
        ]
    )
    c = HevyConnector(hevy_credential, client_id="", client_secret="")
    since = datetime(2026, 3, 20, tzinfo=timezone.utc)  # midnight March 20
    until = datetime(2026, 3, 31, tzinfo=timezone.utc)
    workouts = c.fetch_workouts(since, until)
    assert route.call_count == 2  # fetched page 2 before finding cutoff
    assert len(workouts) == 1  # w2 is before since, not included
    c.close()
