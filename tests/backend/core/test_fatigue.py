from app.core.fatigue import aggregate_fatigue, GlobalFatigue
from app.schemas.fatigue import FatigueScore


def _make_score(local=0.0, cns=0.0, metabolic=0.0, recovery=0.0, muscles=None):
    return FatigueScore(
        local_muscular=local,
        cns_load=cns,
        metabolic_cost=metabolic,
        recovery_hours=recovery,
        affected_muscles=muscles or [],
    )


def test_empty_list_returns_zeros():
    result = aggregate_fatigue([])
    assert result.total_local_muscular == 0.0
    assert result.total_cns_load == 0.0
    assert result.total_metabolic_cost == 0.0
    assert result.peak_recovery_hours == 0.0
    assert result.all_affected_muscles == []


def test_single_score_passthrough():
    score = _make_score(local=30.0, cns=20.0, metabolic=40.0, recovery=12.0, muscles=["quads"])
    result = aggregate_fatigue([score])
    assert result.total_local_muscular == 30.0
    assert result.total_cns_load == 20.0
    assert result.total_metabolic_cost == 40.0
    assert result.peak_recovery_hours == 12.0
    assert result.all_affected_muscles == ["quads"]


def test_sum_clamped_at_100():
    s1 = _make_score(local=70.0, cns=60.0, metabolic=80.0, recovery=24.0)
    s2 = _make_score(local=60.0, cns=50.0, metabolic=40.0, recovery=12.0)
    result = aggregate_fatigue([s1, s2])
    assert result.total_local_muscular == 100.0  # 70+60 clamped
    assert result.total_cns_load == 100.0        # 60+50 clamped
    assert result.total_metabolic_cost == 100.0  # 80+40 clamped


def test_peak_recovery_hours_is_max():
    s1 = _make_score(recovery=6.0)
    s2 = _make_score(recovery=24.0)
    s3 = _make_score(recovery=12.0)
    result = aggregate_fatigue([s1, s2, s3])
    assert result.peak_recovery_hours == 24.0


def test_muscle_union_deduplicates():
    s1 = _make_score(muscles=["quads", "hamstrings"])
    s2 = _make_score(muscles=["hamstrings", "glutes"])
    result = aggregate_fatigue([s1, s2])
    # Order preserved, no duplicates
    assert result.all_affected_muscles == ["quads", "hamstrings", "glutes"]


def test_muscle_union_preserves_insertion_order():
    s1 = _make_score(muscles=["chest", "triceps"])
    s2 = _make_score(muscles=["back", "biceps"])
    result = aggregate_fatigue([s1, s2])
    assert result.all_affected_muscles == ["chest", "triceps", "back", "biceps"]
