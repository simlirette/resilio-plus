import json
from datetime import date


def test_training_plan_response_from_model():
    from app.schemas.plan import TrainingPlanResponse, WorkoutSlot
    from app.schemas.athlete import Sport
    from app.schemas.fatigue import FatigueScore

    slot = WorkoutSlot(
        date=date(2026, 4, 7),
        sport=Sport.RUNNING,
        workout_type="easy_z2",
        duration_min=45,
        fatigue_score=FatigueScore(
            local_muscular=0, cns_load=0, metabolic_cost=0,
            recovery_hours=0, affected_muscles=[],
        ),
    )

    class FakeModel:
        id = "plan-1"
        athlete_id = "ath-1"
        start_date = date(2026, 4, 7)
        end_date = date(2026, 4, 13)
        phase = "general_prep"
        total_weekly_hours = 5.0
        acwr = 1.05
        weekly_slots_json = json.dumps([slot.model_dump(mode="json")])

    resp = TrainingPlanResponse.from_model(FakeModel())
    assert resp.id == "plan-1"
    assert resp.athlete_id == "ath-1"
    assert resp.phase == "general_prep"
    assert resp.acwr == 1.05
    assert len(resp.sessions) == 1
    assert resp.sessions[0].sport == Sport.RUNNING
    assert resp.sessions[0].workout_type == "easy_z2"


def test_training_plan_response_id_is_str():
    from app.schemas.plan import TrainingPlanResponse
    hints = TrainingPlanResponse.model_fields
    assert hints["id"].annotation is str
    assert hints["athlete_id"].annotation is str
