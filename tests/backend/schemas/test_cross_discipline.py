"""D2 TDD — CrossDisciplineLoadV1 + V2 schemas (DEP-C4-004)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestCrossDisciplineLoadV1:
    def test_valid_v1(self):
        from app.schemas.cross_discipline import CrossDisciplineLoadV1
        v = CrossDisciplineLoadV1(
            weekly_running_sessions=3,
            weekly_biking_sessions=2,
            weekly_swimming_sessions=1,
        )
        assert v.weekly_running_sessions == 3

    def test_defaults_zero(self):
        from app.schemas.cross_discipline import CrossDisciplineLoadV1
        v = CrossDisciplineLoadV1()
        assert v.weekly_running_sessions == 0
        assert v.weekly_biking_sessions == 0
        assert v.weekly_swimming_sessions == 0

    def test_negative_sessions_raises(self):
        from app.schemas.cross_discipline import CrossDisciplineLoadV1
        with pytest.raises(ValidationError):
            CrossDisciplineLoadV1(weekly_running_sessions=-1)


class TestDisciplineLoadDetail:
    def test_valid_detail(self):
        from app.schemas.cross_discipline import DisciplineLoadDetail
        d = DisciplineLoadDetail(
            weekly_sessions_count=3,
            weekly_volume_zscore=1.2,
            has_long_session_day="2026-05-03",
            has_intensity_day="2026-05-01",
            leg_impact_index=0.9,
        )
        assert d.leg_impact_index == 0.9

    def test_optional_day_fields_null(self):
        from app.schemas.cross_discipline import DisciplineLoadDetail
        d = DisciplineLoadDetail(
            weekly_sessions_count=2,
            weekly_volume_zscore=-0.5,
            leg_impact_index=0.4,
        )
        assert d.has_long_session_day is None
        assert d.has_intensity_day is None

    def test_leg_impact_out_of_range_raises(self):
        from app.schemas.cross_discipline import DisciplineLoadDetail
        with pytest.raises(ValidationError):
            DisciplineLoadDetail(
                weekly_sessions_count=1,
                weekly_volume_zscore=0.0,
                leg_impact_index=1.5,  # > 1.0
            )

    def test_negative_sessions_raises(self):
        from app.schemas.cross_discipline import DisciplineLoadDetail
        with pytest.raises(ValidationError):
            DisciplineLoadDetail(
                weekly_sessions_count=-1,
                weekly_volume_zscore=0.0,
                leg_impact_index=0.5,
            )


class TestCrossDisciplineLoadV2:
    def test_all_disciplines_present(self):
        from app.schemas.cross_discipline import CrossDisciplineLoadV2, DisciplineLoadDetail
        detail = DisciplineLoadDetail(
            weekly_sessions_count=3,
            weekly_volume_zscore=0.5,
            leg_impact_index=0.8,
        )
        v2 = CrossDisciplineLoadV2(running=detail, biking=detail, swimming=detail)
        assert v2.running is not None
        assert v2.biking is not None

    def test_null_disciplines_valid(self):
        from app.schemas.cross_discipline import CrossDisciplineLoadV2
        v2 = CrossDisciplineLoadV2()
        assert v2.running is None
        assert v2.biking is None
        assert v2.swimming is None

    def test_partial_disciplines_valid(self):
        from app.schemas.cross_discipline import CrossDisciplineLoadV2, DisciplineLoadDetail
        running = DisciplineLoadDetail(
            weekly_sessions_count=4,
            weekly_volume_zscore=1.0,
            leg_impact_index=1.0,
        )
        v2 = CrossDisciplineLoadV2(running=running)
        assert v2.running is not None
        assert v2.biking is None
        assert v2.swimming is None
