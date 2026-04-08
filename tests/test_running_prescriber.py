"""Tests pour agents/running_coach/prescriber.py — logique déterministe."""


def test_select_sessions_base_building():
    """Phase base_building, ACWR safe → sessions pyramidales standard."""
    from agents.running_coach.prescriber import RunningPrescriber

    p = RunningPrescriber()
    result = p._select_session_types("base_building", 1.0, 3)
    assert result == ["easy_run", "tempo_run", "long_run"]


def test_acwr_danger_drops_to_easy():
    """ACWR > 1.5 (danger) → uniquement easy_run et long_run (pas de qualité)."""
    from agents.running_coach.prescriber import RunningPrescriber

    p = RunningPrescriber()
    result = p._select_session_types("base_building", 1.6, 3)
    assert "tempo_run" not in result
    assert "interval_run" not in result
    assert "easy_run" in result


def test_acwr_caution_downgrades_intensity():
    """ACWR 1.4 (caution) en phase build → interval_run rétrogradé en tempo_run."""
    from agents.running_coach.prescriber import RunningPrescriber

    p = RunningPrescriber()
    result = p._select_session_types("build", 1.4, 3)
    assert "interval_run" not in result
    assert "tempo_run" in result


def test_volume_cap_10_percent():
    """Semaine normale sans shin_splints → progression 5%, dans la limite 10%."""
    from agents.running_coach.prescriber import RunningPrescriber

    p = RunningPrescriber()
    result = p._compute_target_km(22.0, 3, False)
    assert result == 23.1  # 22.0 * 1.05
    assert result <= 22.0 * 1.10  # Dans la limite 10%


def test_deload_week():
    """Semaine 4 (deload) → volume × 0.75."""
    from agents.running_coach.prescriber import RunningPrescriber

    p = RunningPrescriber()
    result = p._compute_target_km(22.0, 4, False)
    assert result == 16.5  # 22.0 * 0.75


def test_build_week_plan_returns_required_fields(simon_pydantic_state):
    """build_week_plan() retourne tous les champs requis du format de sortie."""
    from agents.running_coach.prescriber import RunningPrescriber
    from models.views import AgentType, get_agent_view

    p = RunningPrescriber()
    view = get_agent_view(simon_pydantic_state, AgentType.running_coach)
    plan = p.build_week_plan(view)

    assert plan["agent"] == "running_coach"
    assert "week" in plan
    assert "phase" in plan
    assert "tid_model" in plan
    assert "total_km_prescribed" in plan
    assert "sessions" in plan
    assert isinstance(plan["sessions"], list)
    assert len(plan["sessions"]) > 0
