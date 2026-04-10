from datetime import date, timedelta
import pytest
from app.core.recovery_logic import compute_recovery_status, RecoveryStatus
from app.schemas.connector import TerraHealthData


def _terra(days=7, hrv=55.0, sleep=7.5, score=75.0):
    today = date.today()
    return [
        TerraHealthData(
            date=today - timedelta(days=i),
            hrv_rmssd=hrv,
            sleep_duration_hours=sleep,
            sleep_score=score,
        )
        for i in range(days)
    ]


def test_returns_recovery_status():
    result = compute_recovery_status([], None, date.today())
    assert isinstance(result, RecoveryStatus)


def test_cold_start_readiness_is_one():
    result = compute_recovery_status([], None, date.today())
    assert result.readiness_modifier == 1.0


def test_good_hrv_sleep_readiness_above_one():
    result = compute_recovery_status(_terra(hrv=65.0, sleep=8.0, score=85.0), None, date.today())
    assert result.readiness_modifier >= 1.0


def test_poor_sleep_reduces_readiness():
    result = compute_recovery_status(_terra(hrv=50.0, sleep=5.0, score=40.0), None, date.today())
    assert result.readiness_modifier < 1.0


def test_hrv_trend_values():
    result = compute_recovery_status(_terra(), None, date.today())
    assert result.hrv_trend in ("improving", "stable", "declining")


def test_sleep_banking_active_near_race():
    near_race = date.today() + timedelta(weeks=1)
    result = compute_recovery_status(_terra(), near_race, date.today())
    assert result.sleep_banking_active is True


def test_sleep_banking_inactive_far_race():
    far_race = date.today() + timedelta(weeks=20)
    result = compute_recovery_status(_terra(), far_race, date.today())
    assert result.sleep_banking_active is False
