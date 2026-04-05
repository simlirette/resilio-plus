"""
Tests unitaires HevyConnector — httpx.MockTransport, pas de vraies requêtes réseau.
"""

import httpx
import pytest
from sqlalchemy import select

from connectors.hevy import HevyConnector
from models.database import LiftingSession, LiftingSet

# ── test_validate_api_key_valid ───────────────────────────────────────────────

async def test_validate_api_key_valid():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"workouts": [], "page_count": 0})

    connector = HevyConnector(transport=httpx.MockTransport(mock_handler))
    result = await connector.validate_api_key("valid_key")
    assert result is True


# ── test_validate_api_key_invalid ────────────────────────────────────────────

async def test_validate_api_key_invalid():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "unauthorized"})

    connector = HevyConnector(transport=httpx.MockTransport(mock_handler))
    result = await connector.validate_api_key("bad_key")
    assert result is False


# ── test_ingest_workouts_upsert ───────────────────────────────────────────────

async def test_ingest_workouts_upsert(db_session, simon_athlete):
    workout = {
        "id": "workout_abc",
        "title": "Upper Body",
        "start_time": "2026-01-15T10:00:00Z",
        "end_time": "2026-01-15T11:00:00Z",
        "exercises": [
            {
                "title": "Bench Press",
                "sets": [
                    {"index": 0, "type": "normal", "weight_kg": 80, "reps": 8, "rpe": 7},
                ],
            }
        ],
    }

    connector = HevyConnector()
    count1 = await connector.ingest_workouts(simon_athlete.id, [workout], db_session)
    count2 = await connector.ingest_workouts(simon_athlete.id, [workout], db_session)

    assert count1 == 1
    assert count2 == 1

    result = await db_session.execute(
        select(LiftingSession).where(LiftingSession.hevy_workout_id == "workout_abc")
    )
    sessions_in_db = result.scalars().all()
    assert len(sessions_in_db) == 1


# ── test_weight_conversion_lbs_to_kg ─────────────────────────────────────────

async def test_weight_conversion_lbs_to_kg(db_session, simon_athlete):
    workout = {
        "id": "workout_lbs",
        "title": "Lower Body",
        "start_time": "2026-01-16T10:00:00Z",
        "end_time": "2026-01-16T11:00:00Z",
        "exercises": [
            {
                "title": "Squat",
                "sets": [
                    {"index": 0, "type": "normal", "weight_lbs": 176.37, "reps": 5},
                ],
            }
        ],
    }

    connector = HevyConnector()
    await connector.ingest_workouts(simon_athlete.id, [workout], db_session)

    result = await db_session.execute(
        select(LiftingSet)
        .join(LiftingSession)
        .where(LiftingSession.hevy_workout_id == "workout_lbs")
    )
    lifting_set = result.scalar_one()
    # 176.37 lbs × 0.453592 ≈ 80.0 kg
    assert lifting_set.weight_kg == pytest.approx(80.0, abs=0.1)


# ── test_volume_calculated ───────────────────────────────────────────────────

async def test_volume_calculated(db_session, simon_athlete):
    workout = {
        "id": "workout_volume",
        "title": "Volume Test",
        "start_time": "2026-01-17T10:00:00Z",
        "end_time": "2026-01-17T11:00:00Z",
        "exercises": [
            {
                "title": "Deadlift",
                "sets": [
                    {"index": 0, "type": "normal", "weight_kg": 80, "reps": 8},
                    {"index": 1, "type": "normal", "weight_kg": 80, "reps": 8},
                    {"index": 2, "type": "normal", "weight_kg": 80, "reps": 8},
                ],
            }
        ],
    }

    connector = HevyConnector()
    await connector.ingest_workouts(simon_athlete.id, [workout], db_session)

    result = await db_session.execute(
        select(LiftingSession).where(LiftingSession.hevy_workout_id == "workout_volume")
    )
    session_obj = result.scalar_one()
    # 3 sets × 80 kg × 8 reps = 1920.0
    assert session_obj.total_volume_kg == pytest.approx(1920.0)
