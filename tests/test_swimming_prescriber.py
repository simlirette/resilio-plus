"""
Tests pour SwimmingPrescriber — CSS zones, session count, session structure.
"""
import pytest

from agents.swimming_coach.prescriber import SwimmingPrescriber


@pytest.fixture
def prescriber():
    return SwimmingPrescriber()


def test_css_from_reference_times(prescriber):
    """CSS calculé depuis reference_times : 200m=3.5min, 400m=7.5min → 120 s/100m."""
    view = {
        "swimming_profile": {
            "reference_times": {"200m": 3.5, "400m": 7.5},
            "technique_level": "beginner",
            "weekly_volume_km": 0.0,
        }
    }
    result = prescriber.prescribe(view)
    # css_m_per_s = 200 / ((7.5 - 3.5) * 60) = 200/240 = 0.8333
    # css_sec_per_100m = 100 / 0.8333 = 120.0
    assert result["css_sec_per_100m"] == pytest.approx(120.0, abs=0.1)


def test_css_default_beginner(prescriber):
    """Pas de reference_times + technique_level='beginner' → 150 s/100m."""
    view = {
        "swimming_profile": {
            "reference_times": {},
            "technique_level": "beginner",
            "weekly_volume_km": 0.0,
        }
    }
    result = prescriber.prescribe(view)
    assert result["css_sec_per_100m"] == 150.0


def test_css_default_intermediate(prescriber):
    """Pas de reference_times + technique_level='intermediate' → 110 s/100m."""
    view = {
        "swimming_profile": {
            "reference_times": {},
            "technique_level": "intermediate",
            "weekly_volume_km": 0.0,
        }
    }
    result = prescriber.prescribe(view)
    assert result["css_sec_per_100m"] == 110.0


def test_css_default_advanced(prescriber):
    """Pas de reference_times + technique_level='advanced' → 90 s/100m."""
    view = {
        "swimming_profile": {
            "reference_times": {},
            "technique_level": "advanced",
            "weekly_volume_km": 0.0,
        }
    }
    result = prescriber.prescribe(view)
    assert result["css_sec_per_100m"] == 90.0


def test_session_count_zero_volume(prescriber):
    """weekly_volume_km=0 → 0 sessions."""
    view = {
        "swimming_profile": {
            "reference_times": {},
            "technique_level": "beginner",
            "weekly_volume_km": 0.0,
        }
    }
    result = prescriber.prescribe(view)
    assert result["sessions"] == []


def test_session_count_one_session(prescriber):
    """weekly_volume_km=1.0 → 1 session."""
    view = {
        "swimming_profile": {
            "reference_times": {},
            "technique_level": "beginner",
            "weekly_volume_km": 1.0,
        }
    }
    result = prescriber.prescribe(view)
    assert len(result["sessions"]) == 1


def test_session_count_two_sessions(prescriber):
    """weekly_volume_km=2.0 → 2 sessions."""
    view = {
        "swimming_profile": {
            "reference_times": {},
            "technique_level": "beginner",
            "weekly_volume_km": 2.0,
        }
    }
    result = prescriber.prescribe(view)
    assert len(result["sessions"]) == 2


def test_prescribe_output_structure(prescriber):
    """prescribe() avec volume=2.0km retourne la structure complète attendue."""
    view = {
        "swimming_profile": {
            "reference_times": {},
            "technique_level": "beginner",
            "weekly_volume_km": 2.0,
        }
    }
    result = prescriber.prescribe(view)

    # Clés de base
    assert result["agent"] == "swimming_coach"
    assert "technique_level" in result
    assert "css_sec_per_100m" in result
    assert "weekly_volume_km" in result
    assert "sessions" in result
    assert "coaching_notes" in result
    assert "notes" in result

    # Structure d'une session
    session = result["sessions"][0]
    assert "session_number" in session
    assert "session_type" in session
    assert "total_distance_m" in session
    assert "css_target_sec_per_100m" in session
    assert "sets" in session
    assert "coaching_cues" in session

    # Structure d'un set
    s = session["sets"][0]
    assert "type" in s
    assert "distance_m" in s
    assert "pace_zone" in s
    assert "description" in s


def test_session_number_is_one_based(prescriber):
    """Les session_number commencent à 1."""
    view = {
        "swimming_profile": {
            "reference_times": {},
            "technique_level": "beginner",
            "weekly_volume_km": 2.0,
        }
    }
    result = prescriber.prescribe(view)
    numbers = [s["session_number"] for s in result["sessions"]]
    assert numbers == [1, 2]


def test_session_types_cycle(prescriber):
    """Avec 3 sessions, les types sont technique, aerobic_endurance, threshold."""
    view = {
        "swimming_profile": {
            "reference_times": {},
            "technique_level": "beginner",
            "weekly_volume_km": 4.0,  # 3 < x <= 5 → 3 sessions
        }
    }
    result = prescriber.prescribe(view)
    types = [s["session_type"] for s in result["sessions"]]
    assert types == ["technique", "aerobic_endurance", "threshold"]


def test_coaching_notes_initially_empty(prescriber):
    """coaching_notes est une liste vide (à remplir par l'agent LLM)."""
    view = {
        "swimming_profile": {
            "reference_times": {},
            "technique_level": "beginner",
            "weekly_volume_km": 1.0,
        }
    }
    result = prescriber.prescribe(view)
    assert result["coaching_notes"] == []
    assert result["notes"] == ""
