"""Tests for MuscleStrainScore Pydantic model."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError


def test_muscle_strain_score_import():
    from app.models.athlete_state import MuscleStrainScore  # noqa: F401


def test_muscle_strain_score_default_zeros():
    from app.models.athlete_state import MuscleStrainScore
    s = MuscleStrainScore(computed_at=datetime(2026, 4, 13, tzinfo=timezone.utc))
    assert s.quads == 0.0
    assert s.posterior_chain == 0.0
    assert s.glutes == 0.0
    assert s.calves == 0.0
    assert s.chest == 0.0
    assert s.upper_pull == 0.0
    assert s.shoulders == 0.0
    assert s.triceps == 0.0
    assert s.biceps == 0.0
    assert s.core == 0.0


def test_muscle_strain_score_valid_values():
    from app.models.athlete_state import MuscleStrainScore
    s = MuscleStrainScore(
        quads=75.0,
        posterior_chain=60.0,
        glutes=55.0,
        calves=30.0,
        chest=20.0,
        upper_pull=80.0,
        shoulders=45.0,
        triceps=40.0,
        biceps=35.0,
        core=50.0,
        computed_at=datetime(2026, 4, 13, tzinfo=timezone.utc),
    )
    assert s.quads == 75.0
    assert s.upper_pull == 80.0


def test_muscle_strain_score_above_100_raises():
    from app.models.athlete_state import MuscleStrainScore
    with pytest.raises(ValidationError):
        MuscleStrainScore(
            quads=101.0,
            computed_at=datetime(2026, 4, 13, tzinfo=timezone.utc),
        )


def test_muscle_strain_score_below_zero_raises():
    from app.models.athlete_state import MuscleStrainScore
    with pytest.raises(ValidationError):
        MuscleStrainScore(
            quads=-1.0,
            computed_at=datetime(2026, 4, 13, tzinfo=timezone.utc),
        )


def test_muscle_strain_score_computed_at_is_datetime():
    from app.models.athlete_state import MuscleStrainScore
    s = MuscleStrainScore(computed_at=datetime(2026, 4, 13, 8, 0, tzinfo=timezone.utc))
    assert isinstance(s.computed_at, datetime)


def test_athlete_metrics_muscle_strain_defaults_none():
    from datetime import date
    from app.models.athlete_state import AthleteMetrics
    m = AthleteMetrics(date=date(2026, 4, 13))
    assert m.muscle_strain is None


def test_athlete_metrics_accepts_muscle_strain():
    from datetime import date
    from app.models.athlete_state import AthleteMetrics, MuscleStrainScore
    strain = MuscleStrainScore(
        quads=50.0,
        computed_at=datetime(2026, 4, 13, tzinfo=timezone.utc),
    )
    m = AthleteMetrics(date=date(2026, 4, 13), muscle_strain=strain)
    assert m.muscle_strain is not None
    assert m.muscle_strain.quads == 50.0
