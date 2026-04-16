"""Tests for Apple Health importer — DB upsert + side effects."""
from __future__ import annotations

import json
import uuid
from datetime import date, timedelta, timezone
from datetime import datetime as dt

import pytest
from sqlalchemy.orm import Session

from backend.app.db.models import (
    AppleHealthDailyModel,
    AthleteModel,
    ConnectorCredentialModel,
)
from backend.app.integrations.apple_health.aggregator import AppleHealthDailySummary
from backend.app.integrations.apple_health.importer import import_daily_summaries


def _make_athlete(db: Session, weight_kg: float = 75.0) -> AthleteModel:
    athlete = AthleteModel(
        id=str(uuid.uuid4()),
        name="Test",
        age=30,
        sex="M",
        weight_kg=weight_kg,
        height_cm=180.0,
        primary_sport="running",
        hours_per_week=8.0,
        sports_json="[]",
        goals_json="[]",
        available_days_json="[]",
    )
    db.add(athlete)
    db.commit()
    return athlete


def _make_summaries(
    dates: list[date],
    hrv: float = 42.0,
    sleep: float = 7.5,
    rhr: float = 52.0,
    mass: float | None = None,
    energy: float = 400.0,
) -> dict[date, AppleHealthDailySummary]:
    return {
        d: AppleHealthDailySummary(
            date=d,
            hrv_sdnn_avg=hrv,
            sleep_hours=sleep,
            rhr_bpm=rhr,
            body_mass_kg=mass,
            active_energy_kcal=energy,
        )
        for d in dates
    }


class TestBasicImport:
    def test_imports_correct_day_count(self, db_session: Session):
        athlete = _make_athlete(db_session)
        today = date.today()
        summaries = _make_summaries([today - timedelta(days=i) for i in range(3)])
        result = import_daily_summaries(athlete.id, summaries, db_session)
        assert result["days_imported"] == 3

    def test_rows_created_in_db(self, db_session: Session):
        athlete = _make_athlete(db_session)
        today = date.today()
        summaries = _make_summaries([today])
        import_daily_summaries(athlete.id, summaries, db_session)
        row = db_session.query(AppleHealthDailyModel).filter_by(
            athlete_id=athlete.id, record_date=today
        ).first()
        assert row is not None
        assert row.hrv_sdnn_avg == pytest.approx(42.0)
        assert row.sleep_hours == pytest.approx(7.5)
        assert row.rhr_bpm == pytest.approx(52.0)

    def test_date_range_returned(self, db_session: Session):
        athlete = _make_athlete(db_session)
        d1, d2 = date(2026, 4, 10), date(2026, 4, 15)
        summaries = _make_summaries([d1, d2])
        result = import_daily_summaries(athlete.id, summaries, db_session)
        assert result["date_range"]["from"] == "2026-04-10"
        assert result["date_range"]["to"] == "2026-04-15"


class TestUpsert:
    def test_reimport_same_day_updates_row(self, db_session: Session):
        athlete = _make_athlete(db_session)
        today = date.today()
        import_daily_summaries(athlete.id, _make_summaries([today], hrv=40.0), db_session)
        import_daily_summaries(athlete.id, _make_summaries([today], hrv=55.0), db_session)
        rows = db_session.query(AppleHealthDailyModel).filter_by(athlete_id=athlete.id).all()
        assert len(rows) == 1
        assert rows[0].hrv_sdnn_avg == pytest.approx(55.0)


class TestBodyMassUpdate:
    def test_weight_updated_when_recent(self, db_session: Session):
        athlete = _make_athlete(db_session, weight_kg=75.0)
        today = date.today()
        summaries = _make_summaries([today], mass=72.5)
        result = import_daily_summaries(athlete.id, summaries, db_session)
        assert result["weight_updated"] is True
        db_session.refresh(athlete)
        assert athlete.weight_kg == pytest.approx(72.5)

    def test_weight_not_updated_when_old(self, db_session: Session):
        athlete = _make_athlete(db_session, weight_kg=75.0)
        old_date = date.today() - timedelta(days=8)  # 8 days ago, beyond 7-day cutoff
        summaries = _make_summaries([old_date], mass=72.5)
        result = import_daily_summaries(athlete.id, summaries, db_session)
        assert result["weight_updated"] is False
        db_session.refresh(athlete)
        assert athlete.weight_kg == pytest.approx(75.0)  # unchanged

    def test_weight_not_updated_when_no_body_mass(self, db_session: Session):
        athlete = _make_athlete(db_session, weight_kg=75.0)
        today = date.today()
        summaries = _make_summaries([today], mass=None)
        result = import_daily_summaries(athlete.id, summaries, db_session)
        assert result["weight_updated"] is False


class TestConnectorCredential:
    def test_connector_credential_created_with_latest_values(self, db_session: Session):
        athlete = _make_athlete(db_session)
        today = date.today()
        summaries = _make_summaries([today], hrv=44.0, sleep=7.0, rhr=53.0)
        import_daily_summaries(athlete.id, summaries, db_session)
        cred = db_session.query(ConnectorCredentialModel).filter_by(
            athlete_id=athlete.id, provider="apple_health"
        ).first()
        assert cred is not None
        extra = json.loads(cred.extra_json)
        assert extra["last_hrv_sdnn"] == pytest.approx(44.0)
        assert extra["last_sleep_hours"] == pytest.approx(7.0)
        assert extra["last_hr_rest"] == 53


class TestEmptySummaries:
    def test_empty_summaries_returns_zero(self, db_session: Session):
        athlete = _make_athlete(db_session)
        result = import_daily_summaries(athlete.id, {}, db_session)
        assert result["days_imported"] == 0
        assert result["date_range"]["from"] is None
        assert result["date_range"]["to"] is None
