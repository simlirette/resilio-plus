"""Tests pour RecoveryPrescriber — S8."""


def test_fatigue_state_accepts_hr_rest_today():
    """FatigueState accepte le champ hr_rest_today optionnel."""
    from models.schemas import FatigueState

    state = FatigueState(hr_rest_today=65)
    assert state.hr_rest_today == 65


def test_recovery_view_includes_resting_hr(simon_pydantic_state):
    """_recovery_view expose resting_hr (baseline FC repos) dans identity."""
    from models.views import AgentType, get_agent_view

    view = get_agent_view(simon_pydantic_state, AgentType.recovery_coach)
    assert "resting_hr" in view["identity"]


# ─────────────────────────────────────────────────────────────
# Helper — construit une vue Recovery Coach de test
# ─────────────────────────────────────────────────────────────

def _make_view(
    hrv_today=None,
    hrv_baseline=None,
    sleep_hours=None,
    sleep_quality=None,
    acwr=None,
    hr_rest_today=None,
    resting_hr=None,
    fatigue_subjective=None,
):
    return {
        "identity": {
            "first_name": "Simon",
            "age": 32,
            "sex": "M",
            "weight_kg": 78.5,
            "resting_hr": resting_hr,
        },
        "constraints": {"injuries_history": []},
        "fatigue": {
            "acwr": acwr,
            "acwr_trend": None,
            "acwr_by_sport": {
                "running": None,
                "lifting": None,
                "biking": None,
                "swimming": None,
            },
            "weekly_fatigue_score": None,
            "fatigue_by_muscle": {},
            "cns_load_7day_avg": None,
            "recovery_score_today": None,
            "hrv_rmssd_today": hrv_today,
            "hrv_rmssd_baseline": hrv_baseline,
            "sleep_hours_last_night": sleep_hours,
            "sleep_quality_subjective": sleep_quality,
            "fatigue_subjective": fatigue_subjective,
            "hr_rest_today": hr_rest_today,
        },
        "weekly_volumes": {
            "running_km": 22.0,
            "lifting_sessions": 3,
            "swimming_km": 0.0,
            "biking_km": 0.0,
            "total_training_hours": 6.5,
        },
        "compliance": {
            "last_4_weeks_completion_rate": 0.88,
            "missed_sessions_this_week": [],
            "nutrition_adherence_7day": 0.75,
        },
        "current_phase": {
            "macrocycle": "base_building",
            "mesocycle_week": 3,
            "mesocycle_length": 4,
            "next_deload": None,
            "target_event": None,
            "target_event_date": None,
        },
    }


# ─────────────────────────────────────────────────────────────
# Tests prescriber
# ─────────────────────────────────────────────────────────────

def test_green_verdict_healthy_athlete():
    """Tous facteurs optimaux → readiness >= 75, color = 'green'."""
    from agents.recovery_coach.prescriber import RecoveryPrescriber

    view = _make_view(
        hrv_today=65,
        hrv_baseline=62,      # today > baseline → hrv_score 100
        sleep_hours=8.5,
        sleep_quality=9,       # >=8h + quality>=8 → sleep_score 100
        acwr=1.1,              # 0.8-1.3 → acwr_score 100
        hr_rest_today=57,
        resting_hr=58,         # today <= baseline → hr_rest_score 100
        fatigue_subjective=2,  # 1-3 → subjective_score 100
    )
    result = RecoveryPrescriber().evaluate(view)

    assert result["color"] == "green"
    assert result["readiness_score"] >= 75
    assert result["modification_params"]["intensity_reduction_pct"] == 0
    assert result["modification_params"]["tier_max"] == 3


def test_yellow_verdict_moderate_fatigue():
    """Facteurs modérés → 50 <= score < 75, color = 'yellow',
    modification_params.intensity_reduction_pct == 15."""
    from agents.recovery_coach.prescriber import RecoveryPrescriber

    view = _make_view(
        hrv_today=50,
        hrv_baseline=62,       # 50/62=0.806 → in [0.70, 0.85) → hrv_score 50
        sleep_hours=7.0,
        sleep_quality=7,       # 7h + quality>=7 → sleep_score 80
        acwr=1.35,             # 1.3 < acwr <= 1.4 → acwr_score 70
        hr_rest_today=60,
        resting_hr=58,         # diff=2 → hr_rest_score 70
        fatigue_subjective=5,  # 4-5 → subjective_score 70
    )
    # Expected: 0.30*50 + 0.25*80 + 0.25*70 + 0.10*70 + 0.10*70 = 66.5
    result = RecoveryPrescriber().evaluate(view)

    assert result["color"] == "yellow"
    assert 50 <= result["readiness_score"] < 75
    assert result["modification_params"]["intensity_reduction_pct"] == 15
    assert result["modification_params"]["tier_max"] == 1


def test_red_verdict_critical_fatigue():
    """ACWR 1.61, HRV -39%, sommeil 5h, fatigue_subjective 8
    → score < 50, color = 'red', tier_max == 0."""
    from agents.recovery_coach.prescriber import RecoveryPrescriber

    view = _make_view(
        hrv_today=38,
        hrv_baseline=62,       # 38/62=0.613 < 0.70 → hrv_score 25
        sleep_hours=5.1,
        sleep_quality=4,       # <6h AND quality<5 → sleep_score 20
        acwr=1.61,             # >1.5 → acwr_score 0
        hr_rest_today=67,
        resting_hr=58,         # diff=9 > 6 → hr_rest_score 10
        fatigue_subjective=8,  # 8-10 → subjective_score 10
    )
    # Expected: 0.30*25 + 0.25*20 + 0.25*0 + 0.10*10 + 0.10*10 = 14.5
    result = RecoveryPrescriber().evaluate(view)

    assert result["color"] == "red"
    assert result["readiness_score"] < 50
    assert result["modification_params"]["tier_max"] == 0
    assert result["modification_params"]["volume_reduction_pct"] == 100


def test_overtraining_alert_triggered_by_acwr():
    """acwr > 1.5 → overtraining_alert is True."""
    from agents.recovery_coach.prescriber import RecoveryPrescriber

    view = _make_view(acwr=1.55)
    result = RecoveryPrescriber().evaluate(view)
    assert result["overtraining_alert"] is True


def test_overtraining_alert_triggered_by_hrv():
    """hrv_today/baseline < 0.70 → overtraining_alert is True."""
    from agents.recovery_coach.prescriber import RecoveryPrescriber

    # 40/62 = 0.645 < 0.70
    view = _make_view(hrv_today=40, hrv_baseline=62)
    result = RecoveryPrescriber().evaluate(view)
    assert result["overtraining_alert"] is True


def test_fallback_when_all_data_missing():
    """Tous les champs fatigue à None → evaluate() ne crash pas,
    readiness_score est calculé avec les fallbacks, color est valide."""
    from agents.recovery_coach.prescriber import RecoveryPrescriber

    view = _make_view()  # tous None
    result = RecoveryPrescriber().evaluate(view)

    assert result["readiness_score"] >= 0
    assert result["color"] in ("green", "yellow", "red")
    assert "factors" in result
    assert "overtraining_alert" in result
