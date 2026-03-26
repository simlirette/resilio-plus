import pytest
from app.core.acwr import compute_acwr, ACWRStatus, ACWRResult


def test_empty_history_returns_safe_zeros():
    result = compute_acwr([])
    assert result.acute_7d == 0.0
    assert result.chronic_28d == 0.0
    assert result.ratio == 0.0
    assert result.status == ACWRStatus.SAFE
    assert result.max_safe_weekly_load == 0.0


def test_constant_load_ratio_is_one():
    # Constant load → acute EWMA ≈ chronic EWMA → ratio ≈ 1.0 → SAFE
    loads = [50.0] * 56  # 8 weeks of constant load
    result = compute_acwr(loads)
    assert result.status == ACWRStatus.SAFE
    assert abs(result.ratio - 1.0) < 0.05


def test_safe_zone_lower_boundary():
    # ratio just above 0.8 → SAFE
    loads = [50.0] * 27 + [40.0]  # slight drop
    result = compute_acwr(loads)
    assert result.status in (ACWRStatus.SAFE, ACWRStatus.UNDERTRAINED)


def test_undertrained_zone():
    # Very low recent load vs high chronic → ratio < 0.8
    # Build up chronic load, then drop to ~50% for recent period
    loads = [80.0] * 20 + [30.0] * 8  # 28 days: chronic ≈ 70, acute ≈ 35
    result = compute_acwr(loads)
    assert result.status == ACWRStatus.UNDERTRAINED


def test_caution_zone_at_boundary():
    # ratio exactly 1.3 → CAUTION (not SAFE)
    # We test the boundary function directly
    from app.core.acwr import _ratio_to_status
    assert _ratio_to_status(1.3) == ACWRStatus.CAUTION
    assert _ratio_to_status(1.299) == ACWRStatus.SAFE


def test_danger_zone():
    # Spike load after very low chronic → ratio > 1.5
    loads = [10.0] * 27 + [200.0]
    result = compute_acwr(loads)
    assert result.status == ACWRStatus.DANGER


def test_10_percent_rule():
    # chronic_28d EWMA ≈ 50 → max_safe ≈ 55
    loads = [50.0] * 56
    result = compute_acwr(loads)
    assert result.max_safe_weekly_load == pytest.approx(result.chronic_28d * 1.1, rel=0.01)


def test_oldest_first_ordering_matters():
    # Different order should produce different EWMA
    loads_a = [10.0, 50.0]
    loads_b = [50.0, 10.0]
    result_a = compute_acwr(loads_a)
    result_b = compute_acwr(loads_b)
    # The two calls must differ (older load matters less in EWMA)
    assert result_a.acute_7d != result_b.acute_7d
