from datetime import date, timedelta
from app.core.readiness import compute_readiness
from app.schemas.connector import TerraHealthData


def _terra(days_ago: int, hrv: float | None = None,
           sleep_h: float | None = None, sleep_s: float | None = None) -> TerraHealthData:
    return TerraHealthData(
        date=date(2026, 4, 7) - timedelta(days=days_ago),
        hrv_rmssd=hrv,
        sleep_duration_hours=sleep_h,
        sleep_score=sleep_s,
    )


def test_empty_data_returns_1_0():
    assert compute_readiness([]) == 1.0


def test_good_hrv_good_sleep_returns_bonus():
    # HRV ratio >= 1.0 -> +0.10; sleep >= 7h and >= 70 -> 0.0 -> total 1.10
    data = [_terra(i, hrv=60.0, sleep_h=7.5, sleep_s=80.0) for i in range(7)]
    result = compute_readiness(data, hrv_baseline=55.0)
    assert abs(result - 1.1) < 0.01


def test_low_hrv_reduces_modifier():
    # HRV ratio < 0.60 -> -0.30; sleep 7.5h/80 -> 0.0 -> total 0.70
    data = [_terra(i, hrv=25.0, sleep_h=7.5, sleep_s=80.0) for i in range(7)]
    result = compute_readiness(data, hrv_baseline=55.0)
    assert result <= 0.70


def test_poor_sleep_reduces_modifier():
    # Sleep < 6h -> -0.20; HRV ratio 1.0 -> +0.10 -> total 0.90
    data = [_terra(i, hrv=55.0, sleep_h=5.5, sleep_s=45.0) for i in range(7)]
    result = compute_readiness(data, hrv_baseline=55.0)
    assert abs(result - 0.90) < 0.01


def test_combined_low_hrv_and_poor_sleep_clamped():
    # HRV delta = -0.30, sleep delta = -0.20 -> 1.0 - 0.50 = 0.50 -> clamped 0.5
    data = [_terra(i, hrv=20.0, sleep_h=5.0, sleep_s=40.0) for i in range(7)]
    result = compute_readiness(data, hrv_baseline=55.0)
    assert result == 0.5


def test_no_hrv_baseline_cold_start_returns_neutral():
    # < 4 valid HRV entries -> cold start -> hrv_delta = 0
    # good sleep -> sleep_delta = 0 -> modifier = 1.0
    data = [
        _terra(0, hrv=60.0, sleep_h=7.5, sleep_s=80.0),
        _terra(1, hrv=None, sleep_h=7.5, sleep_s=80.0),
        _terra(2, hrv=None, sleep_h=7.5, sleep_s=80.0),
    ]
    result = compute_readiness(data)
    assert result == 1.0
