"""
TEST VIEWS — Validation du filtrage AthleteState par agent.
Tests sans DB — pas de fixtures async requis.
"""
from datetime import datetime
from uuid import UUID

from models.schemas import (
    ACWRBySport,
    AthleteProfile,
    AthleteStateSchema,
    Compliance,
    CurrentPhase,
    DayAvailability,
    Equipment,
    FatigueState,
    Goals,
    Injury,
    LiftingProfile,
    Lifestyle,
    MacrosTarget,
    NutritionProfile,
    RunningProfile,
    TrainingHistory,
    TrainingPaces,
    WeeklyVolumes,
)
from models.views import AgentType, get_agent_view

SIMON_ID = UUID("00000000-0000-0000-0000-000000000001")


def _make_state() -> AthleteStateSchema:
    """State Simon minimal pour les tests de vues."""
    return AthleteStateSchema(
        athlete_id=SIMON_ID,
        updated_at=datetime(2026, 4, 4, 10, 0, 0),
        profile=AthleteProfile(
            first_name="Simon",
            age=32,
            sex="M",
            weight_kg=78.5,
            height_cm=178,
            training_history=TrainingHistory(
                total_years_training=5,
                years_running=2,
                years_lifting=4,
                years_swimming=0.5,
                current_weekly_volume_hours=7,
            ),
            injuries_history=[
                Injury(type="shin_splints", year=2024, duration_weeks=6, recurrent=False)
            ],
            lifestyle=Lifestyle(
                work_type="desk_sedentary",
                work_hours_per_day=8,
                commute_active=False,
                sleep_avg_hours=7.2,
                stress_level="moderate",
            ),
            goals=Goals(primary="run_sub_25_5k", timeline_weeks=16),
            equipment=Equipment(gym_access=True),
            active_sports=["running", "lifting"],
            available_days={
                "monday": DayAvailability(available=True, max_hours=1.5, preferred_time="morning"),
            },
        ),
        current_phase=CurrentPhase(macrocycle="base_building", mesocycle_week=3),
        running_profile=RunningProfile(
            vdot=38.2,
            training_paces=TrainingPaces(
                easy_min_per_km="6:24",
                easy_max_per_km="7:06",
                threshold_pace_per_km="5:18",
                interval_pace_per_km="4:48",
                repetition_pace_per_km="4:24",
                long_run_pace_per_km="6:36",
            ),
            weekly_km_current=22,
            weekly_km_target=35,
            max_long_run_km=12,
        ),
        lifting_profile=LiftingProfile(training_split="upper_lower", sessions_per_week=3),
        nutrition_profile=NutritionProfile(
            tdee_estimated=2800,
            macros_target=MacrosTarget(protein_g=160, carbs_g=300, fat_g=80),
        ),
        fatigue=FatigueState(
            acwr=1.05,
            acwr_by_sport=ACWRBySport(running=1.08, lifting=1.02),
            fatigue_by_muscle={"quadriceps": 65, "hamstrings": 50},
            cns_load_7day_avg=45,
            recovery_score_today=72,
            hrv_rmssd_today=58,
        ),
        compliance=Compliance(last_4_weeks_completion_rate=0.88),
        weekly_volumes=WeeklyVolumes(running_km=22, lifting_sessions=3, total_training_hours=6.5),
    )


def test_running_coach_receives_running_profile():
    view = get_agent_view(_make_state(), AgentType.running_coach)
    assert "running_profile" in view
    assert view["running_profile"]["vdot"] == 38.2


def test_running_coach_does_not_receive_lifting_profile():
    view = get_agent_view(_make_state(), AgentType.running_coach)
    assert "lifting_profile" not in view


def test_running_coach_receives_correct_fatigue_subset():
    view = get_agent_view(_make_state(), AgentType.running_coach)
    assert "fatigue" in view
    fatigue = view["fatigue"]
    assert "acwr_by_sport_running" in fatigue
    assert fatigue["acwr_by_sport_running"] == 1.08
    assert "hrv_rmssd_today" in fatigue
    assert "recovery_score_today" in fatigue
    assert "fatigue_by_muscle" not in fatigue  # pas pour le Running Coach


def test_lifting_coach_receives_fatigue_by_muscle_and_cns():
    view = get_agent_view(_make_state(), AgentType.lifting_coach)
    assert "fatigue" in view
    fatigue = view["fatigue"]
    assert "fatigue_by_muscle" in fatigue
    assert "cns_load_7day_avg" in fatigue
    assert fatigue["cns_load_7day_avg"] == 45


def test_lifting_coach_does_not_receive_running_profile():
    view = get_agent_view(_make_state(), AgentType.lifting_coach)
    assert "running_profile" not in view


def test_nutrition_coach_receives_weekly_volumes_and_nutrition_profile():
    view = get_agent_view(_make_state(), AgentType.nutrition_coach)
    assert "weekly_volumes" in view
    assert "nutrition_profile" in view
    assert view["nutrition_profile"]["tdee_estimated"] == 2800


def test_nutrition_coach_does_not_receive_running_or_lifting_profile():
    view = get_agent_view(_make_state(), AgentType.nutrition_coach)
    assert "running_profile" not in view
    assert "lifting_profile" not in view


def test_recovery_coach_receives_full_fatigue():
    view = get_agent_view(_make_state(), AgentType.recovery_coach)
    assert "fatigue" in view
    fatigue = view["fatigue"]
    assert "acwr" in fatigue
    assert "fatigue_by_muscle" in fatigue
    assert "cns_load_7day_avg" in fatigue
    assert "hrv_rmssd_today" in fatigue
    assert "recovery_score_today" in fatigue


def test_recovery_coach_receives_compliance_and_weekly_volumes():
    view = get_agent_view(_make_state(), AgentType.recovery_coach)
    assert "compliance" in view
    assert "weekly_volumes" in view


def test_head_coach_receives_all_top_level_sections():
    view = get_agent_view(_make_state(), AgentType.head_coach)
    assert "running_profile" in view
    assert "lifting_profile" in view
    assert "fatigue" in view
    assert "nutrition_profile" in view
    assert "profile" in view
    assert "compliance" in view
    assert "weekly_volumes" in view


def test_no_specialist_agent_receives_training_history():
    """Aucun agent spécialiste ne reçoit training_history (trop verbeux)."""
    state = _make_state()
    specialist_agents = [
        AgentType.running_coach,
        AgentType.lifting_coach,
        AgentType.swimming_coach,
        AgentType.biking_coach,
        AgentType.nutrition_coach,
        AgentType.recovery_coach,
    ]
    for agent in specialist_agents:
        view = get_agent_view(state, agent)
        if "profile" in view:
            assert "training_history" not in view["profile"], f"{agent} leaked training_history"
        if "identity" in view:
            assert "training_history" not in view["identity"], f"{agent} leaked training_history"
