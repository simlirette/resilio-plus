"""Tests for V3-C Energy Cycle Service — schemas, service, routes."""
import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# Task 1 — Pydantic schemas
# ---------------------------------------------------------------------------

def test_checkin_input_valid():
    from app.schemas.checkin import CheckInInput
    ci = CheckInInput(
        work_intensity="normal",
        stress_level="mild",
        legs_feeling="normal",
        energy_global="ok",
    )
    assert ci.work_intensity == "normal"
    assert ci.legs_feeling == "normal"
    assert ci.cycle_phase is None
    assert ci.comment is None


def test_checkin_input_rejects_invalid_legs():
    from app.schemas.checkin import CheckInInput
    with pytest.raises(ValidationError):
        CheckInInput(
            work_intensity="normal",
            stress_level="none",
            legs_feeling="bad",
            energy_global="ok",
        )


def test_checkin_input_rejects_invalid_energy():
    from app.schemas.checkin import CheckInInput
    with pytest.raises(ValidationError):
        CheckInInput(
            work_intensity="normal",
            stress_level="none",
            legs_feeling="fresh",
            energy_global="meh",
        )


def test_readiness_response_fields():
    from app.schemas.checkin import ReadinessResponse
    from datetime import date
    r = ReadinessResponse(
        date=date.today(),
        objective_score=70.0,
        subjective_score=40.0,
        final_readiness=52.0,
        divergence=30.0,
        divergence_flag="high",
        traffic_light="yellow",
        allostatic_score=30.0,
        energy_availability=45.0,
        intensity_cap=1.0,
        insights=["HRV normale mais jambes à dead. Ton ressenti compte."],
    )
    assert r.divergence_flag == "high"
    assert r.traffic_light == "yellow"


def test_hormonal_profile_update_valid():
    from app.schemas.checkin import HormonalProfileUpdate
    from datetime import date
    h = HormonalProfileUpdate(
        enabled=True,
        cycle_length_days=28,
        last_period_start=date.today(),
    )
    assert h.enabled is True
    assert h.cycle_length_days == 28


# ---------------------------------------------------------------------------
# Task 2 — ORM columns
# ---------------------------------------------------------------------------

def test_energy_snapshot_has_objective_score():
    from sqlalchemy import create_engine, inspect
    from sqlalchemy.pool import StaticPool
    from app.db.database import Base
    from app.db import models as _models  # noqa

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("energy_snapshots")}
    assert "objective_score" in cols
    assert "subjective_score" in cols


# ---------------------------------------------------------------------------
# Task 3 — EnergyCycleService unit tests
# ---------------------------------------------------------------------------

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import uuid
from datetime import datetime, timezone

from app.db.database import Base
from app.db import models as _db_models  # noqa


def _make_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


def _make_athlete(session, sex="M"):
    from app.db.models import AthleteModel
    athlete = AthleteModel(
        id=str(uuid.uuid4()),
        name="Test",
        age=28,
        sex=sex,
        weight_kg=70.0,
        height_cm=175.0,
        primary_sport="running",
        hours_per_week=8.0,
        sports_json='["running"]',
        goals_json='[]',
        available_days_json='[0,2,4]',
        equipment_json='[]',
    )
    session.add(athlete)
    session.commit()
    return athlete


def test_service_submit_checkin_creates_snapshot():
    from app.services.energy_cycle_service import EnergyCycleService
    from app.schemas.checkin import CheckInInput

    engine = _make_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    athlete = _make_athlete(session)

    svc = EnergyCycleService()
    checkin = CheckInInput(
        work_intensity="normal",
        stress_level="none",
        legs_feeling="fresh",
        energy_global="great",
    )
    result = svc.submit_checkin(athlete.id, session, checkin)

    assert result.final_readiness > 0
    assert result.traffic_light in ("green", "yellow", "red")
    assert result.divergence >= 0
    assert result.divergence_flag in ("none", "moderate", "high")
    session.close()


def test_service_no_duplicate_checkin_same_day():
    from app.services.energy_cycle_service import EnergyCycleService
    from app.schemas.checkin import CheckInInput
    from fastapi import HTTPException

    engine = _make_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    athlete = _make_athlete(session)

    svc = EnergyCycleService()
    checkin = CheckInInput(
        work_intensity="normal",
        stress_level="none",
        legs_feeling="normal",
        energy_global="ok",
    )
    svc.submit_checkin(athlete.id, session, checkin)

    with pytest.raises(HTTPException) as exc:
        svc.submit_checkin(athlete.id, session, checkin)
    assert exc.value.status_code == 409


def test_service_get_today_snapshot_returns_none_when_no_checkin():
    from app.services.energy_cycle_service import EnergyCycleService

    engine = _make_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    athlete = _make_athlete(session)

    svc = EnergyCycleService()
    result = svc.get_today_snapshot(athlete.id, session)
    assert result is None
    session.close()


def test_service_get_today_snapshot_returns_snapshot_after_checkin():
    from app.services.energy_cycle_service import EnergyCycleService
    from app.schemas.checkin import CheckInInput

    engine = _make_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    athlete = _make_athlete(session)

    svc = EnergyCycleService()
    checkin = CheckInInput(
        work_intensity="light",
        stress_level="none",
        legs_feeling="fresh",
        energy_global="great",
    )
    svc.submit_checkin(athlete.id, session, checkin)
    snap = svc.get_today_snapshot(athlete.id, session)
    assert snap is not None
    session.close()


def test_service_get_history_returns_last_n_days():
    from app.services.energy_cycle_service import EnergyCycleService
    from app.models.schemas import EnergySnapshotModel

    engine = _make_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    athlete = _make_athlete(session)

    # Seed 5 snapshots
    for i in range(5):
        snap = EnergySnapshotModel(
            id=str(uuid.uuid4()),
            athlete_id=athlete.id,
            timestamp=datetime.now(timezone.utc),
            allostatic_score=30.0,
            cognitive_load=20.0,
            energy_availability=45.0,
            sleep_quality=70.0,
            recommended_intensity_cap=1.0,
            veto_triggered=False,
            objective_score=70.0,
            subjective_score=80.0,
        )
        session.add(snap)
    session.commit()

    svc = EnergyCycleService()
    history = svc.get_history(athlete.id, session, days=7)
    assert len(history) == 5
    session.close()


def test_subjective_score_calculation():
    """Verify subjective_score formula from spec."""
    from app.services.energy_cycle_service import compute_subjective_score
    assert compute_subjective_score("fresh", "great") == 100.0
    assert compute_subjective_score("dead", "exhausted") == pytest.approx(12.5)
    assert compute_subjective_score("normal", "ok") == pytest.approx(77.5)


def test_divergence_flag_thresholds():
    """Verify divergence classification from spec."""
    from app.services.energy_cycle_service import classify_divergence
    assert classify_divergence(10.0) == "none"
    assert classify_divergence(20.0) == "moderate"
    assert classify_divergence(35.0) == "high"


# ---------------------------------------------------------------------------
# Task 4 — Route integration tests
# ---------------------------------------------------------------------------

def test_post_checkin_creates_readiness(authed_client):
    client, athlete_id = authed_client
    resp = client.post(
        f"/athletes/{athlete_id}/checkin",
        json={
            "work_intensity": "normal",
            "stress_level": "none",
            "legs_feeling": "fresh",
            "energy_global": "great",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "final_readiness" in body
    assert "traffic_light" in body
    assert body["traffic_light"] in ("green", "yellow", "red")
    assert "intensity_cap" in body


def test_post_checkin_rejects_duplicate(authed_client):
    client, athlete_id = authed_client
    payload = {
        "work_intensity": "normal",
        "stress_level": "none",
        "legs_feeling": "normal",
        "energy_global": "ok",
    }
    client.post(f"/athletes/{athlete_id}/checkin", json=payload)
    resp = client.post(f"/athletes/{athlete_id}/checkin", json=payload)
    assert resp.status_code == 409


def test_post_checkin_requires_auth(client):
    resp = client.post(
        "/athletes/some-id/checkin",
        json={
            "work_intensity": "normal",
            "stress_level": "none",
            "legs_feeling": "normal",
            "energy_global": "ok",
        },
    )
    assert resp.status_code == 401


def test_get_readiness_returns_404_when_no_checkin(authed_client):
    client, athlete_id = authed_client
    resp = client.get(f"/athletes/{athlete_id}/readiness")
    assert resp.status_code == 404


def test_get_readiness_returns_data_after_checkin(authed_client):
    client, athlete_id = authed_client
    client.post(
        f"/athletes/{athlete_id}/checkin",
        json={
            "work_intensity": "light",
            "stress_level": "none",
            "legs_feeling": "fresh",
            "energy_global": "great",
        },
    )
    resp = client.get(f"/athletes/{athlete_id}/readiness")
    assert resp.status_code == 200
    assert "final_readiness" in resp.json()


def test_get_energy_history_returns_list(authed_client):
    client, athlete_id = authed_client
    client.post(
        f"/athletes/{athlete_id}/checkin",
        json={
            "work_intensity": "heavy",
            "stress_level": "significant",
            "legs_feeling": "heavy",
            "energy_global": "low",
        },
    )
    resp = client.get(f"/athletes/{athlete_id}/energy/history")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) == 1


def test_patch_hormonal_profile(authed_client):
    client, athlete_id = authed_client
    from datetime import date
    resp = client.patch(
        f"/athletes/{athlete_id}/hormonal-profile",
        json={
            "enabled": True,
            "cycle_length_days": 28,
            "last_period_start": str(date.today()),
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["enabled"] is True
    assert body["cycle_length_days"] == 28


def test_checkin_with_cycle_phase(authed_client):
    client, athlete_id = authed_client
    resp = client.post(
        f"/athletes/{athlete_id}/checkin",
        json={
            "work_intensity": "normal",
            "stress_level": "mild",
            "legs_feeling": "normal",
            "energy_global": "ok",
            "cycle_phase": "follicular",
        },
    )
    assert resp.status_code == 201


def test_checkin_rejects_invalid_legs_value(authed_client):
    client, athlete_id = authed_client
    resp = client.post(
        f"/athletes/{athlete_id}/checkin",
        json={
            "work_intensity": "normal",
            "stress_level": "none",
            "legs_feeling": "terrible",
            "energy_global": "ok",
        },
    )
    assert resp.status_code == 422
