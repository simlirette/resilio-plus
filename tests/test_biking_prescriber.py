"""
Tests unitaires — BikingPrescriber (Coggan FTP zones)

Couvre : _zone_target(), session_count(), prescribe() structure,
         session types cycle, sessions templates.
"""
import pytest

from agents.biking_coach.prescriber import BikingPrescriber


@pytest.fixture
def prescriber() -> BikingPrescriber:
    return BikingPrescriber()


# ── Zone target ──────────────────────────────────────────────────────────────

def test_zone_target_with_ftp(prescriber):
    """Z2 avec ftp=250W → '137–187 W' (int floor, pas banker's rounding)."""
    result = prescriber._zone_target("Z2", 250.0)
    assert result == "137–187 W"


def test_zone_target_without_ftp(prescriber):
    """Z2 sans FTP → RPE string."""
    result = prescriber._zone_target("Z2", None)
    assert result == "RPE 4-5/10"


def test_zone_target_z1_without_ftp(prescriber):
    """Z1 sans FTP → RPE 2-3/10."""
    result = prescriber._zone_target("Z1", None)
    assert result == "RPE 2-3/10"


def test_zone_target_z5_without_ftp(prescriber):
    """Z5 sans FTP → RPE 8-9/10."""
    result = prescriber._zone_target("Z5", None)
    assert result == "RPE 8-9/10"


def test_zone_target_z3_with_ftp(prescriber):
    """Z3 avec ftp=200W → int(200*0.75)=150, int(200*0.90)=180 → '150–180 W'."""
    result = prescriber._zone_target("Z3", 200.0)
    assert result == "150–180 W"


# ── Session count ─────────────────────────────────────────────────────────────

def test_session_count_zero_volume(prescriber):
    """0 km → 0 sessions."""
    plan = prescriber.prescribe({"biking_profile": {"ftp_watts": None, "weekly_volume_km": 0.0}})
    assert len(plan["sessions"]) == 0


def test_session_count_one_session(prescriber):
    """20 km (0 < x ≤ 30) → 1 session."""
    plan = prescriber.prescribe({"biking_profile": {"ftp_watts": None, "weekly_volume_km": 20.0}})
    assert len(plan["sessions"]) == 1


def test_session_count_two_sessions(prescriber):
    """50 km (30 < x ≤ 80) → 2 sessions."""
    plan = prescriber.prescribe({"biking_profile": {"ftp_watts": None, "weekly_volume_km": 50.0}})
    assert len(plan["sessions"]) == 2


def test_session_count_three_sessions(prescriber):
    """100 km (80 < x ≤ 150) → 3 sessions."""
    plan = prescriber.prescribe({"biking_profile": {"ftp_watts": None, "weekly_volume_km": 100.0}})
    assert len(plan["sessions"]) == 3


def test_session_count_four_sessions(prescriber):
    """160 km (> 150) → 4 sessions."""
    plan = prescriber.prescribe({"biking_profile": {"ftp_watts": None, "weekly_volume_km": 160.0}})
    assert len(plan["sessions"]) == 4


# ── Output structure ─────────────────────────────────────────────────────────

def test_prescribe_output_structure(prescriber):
    """prescribe() retourne toutes les clés requises."""
    plan = prescriber.prescribe({"biking_profile": {"ftp_watts": 250.0, "weekly_volume_km": 50.0}})
    assert plan["agent"] == "biking_coach"
    assert "ftp_watts" in plan
    assert "weekly_volume_km" in plan
    assert "sessions" in plan
    assert "coaching_notes" in plan
    assert isinstance(plan["coaching_notes"], list)
    assert "notes" in plan
    assert plan["notes"] == ""  # rempli par l'agent


def test_session_structure_keys(prescriber):
    """Chaque session a toutes les clés requises."""
    plan = prescriber.prescribe({"biking_profile": {"ftp_watts": 250.0, "weekly_volume_km": 50.0}})
    assert len(plan["sessions"]) == 2
    for s in plan["sessions"]:
        assert "session_number" in s
        assert "session_type" in s
        assert "duration_minutes" in s
        assert "tss_estimated" in s
        assert "blocks" in s
        assert "coaching_notes_session" in s
        assert isinstance(s["blocks"], list)
        assert len(s["blocks"]) > 0


def test_blocks_have_required_keys(prescriber):
    """Chaque bloc a zone, duration_minutes, watts_or_rpe, description."""
    plan = prescriber.prescribe({"biking_profile": {"ftp_watts": 250.0, "weekly_volume_km": 50.0}})
    for s in plan["sessions"]:
        for b in s["blocks"]:
            assert "zone" in b
            assert "duration_minutes" in b
            assert "watts_or_rpe" in b
            assert "description" in b


# ── Session types cycle ───────────────────────────────────────────────────────

def test_session_types_cycle(prescriber):
    """3 sessions → [endurance, tempo, vo2max] dans l'ordre."""
    plan = prescriber.prescribe({"biking_profile": {"ftp_watts": None, "weekly_volume_km": 100.0}})
    types = [s["session_type"] for s in plan["sessions"]]
    assert types == ["endurance", "tempo", "vo2max"]


def test_session_types_four(prescriber):
    """4 sessions → [endurance, tempo, vo2max, endurance] cycle."""
    plan = prescriber.prescribe({"biking_profile": {"ftp_watts": None, "weekly_volume_km": 160.0}})
    types = [s["session_type"] for s in plan["sessions"]]
    assert types == ["endurance", "tempo", "vo2max", "endurance"]


# ── Session content ───────────────────────────────────────────────────────────

def test_endurance_session_short_volume(prescriber):
    """Volume < 30 km → endurance session 60 min."""
    plan = prescriber.prescribe({"biking_profile": {"ftp_watts": None, "weekly_volume_km": 20.0}})
    session = plan["sessions"][0]
    assert session["session_type"] == "endurance"
    assert session["duration_minutes"] == 60


def test_endurance_session_normal_volume(prescriber):
    """Volume ≥ 30 km → endurance session 90 min."""
    plan = prescriber.prescribe({"biking_profile": {"ftp_watts": None, "weekly_volume_km": 50.0}})
    endurance = plan["sessions"][0]
    assert endurance["session_type"] == "endurance"
    assert endurance["duration_minutes"] == 90


def test_tss_estimated_positive(prescriber):
    """TSS estimé doit être > 0 pour toute session avec des blocs."""
    plan = prescriber.prescribe({"biking_profile": {"ftp_watts": 250.0, "weekly_volume_km": 100.0}})
    for s in plan["sessions"]:
        assert s["tss_estimated"] > 0


def test_session_numbers_are_sequential(prescriber):
    """session_number est séquentiel 1, 2, 3."""
    plan = prescriber.prescribe({"biking_profile": {"ftp_watts": None, "weekly_volume_km": 100.0}})
    numbers = [s["session_number"] for s in plan["sessions"]]
    assert numbers == [1, 2, 3]
