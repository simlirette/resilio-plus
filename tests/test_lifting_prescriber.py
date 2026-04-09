"""
Tests pour agents/lifting_coach/prescriber.py — DUP, MRV, Hevy format.
Aucun appel LLM ici — prescripteur 100% déterministe.
"""


def test_select_session_types_3x_week():
    """3 sessions/semaine → ['upper_a', 'lower', 'upper_b']."""
    from agents.lifting_coach.prescriber import LiftingPrescriber

    p = LiftingPrescriber()
    result = p._get_session_types(sessions_per_week=3, week=1)
    assert result == ["upper_a", "lower", "upper_b"]


def test_dup_base_building_upper_a(simon_agent_view_lifting):
    """Phase base_building, Upper A → 3 séries normales, reps <= 12, RPE 8."""
    from agents.lifting_coach.prescriber import LiftingPrescriber

    plan = LiftingPrescriber().build_week_plan(simon_agent_view_lifting)
    upper_a_sessions = [
        s for s in plan["sessions"] if s["hevy_workout"]["type"] == "upper_a"
    ]
    assert len(upper_a_sessions) >= 1, "Aucune session upper_a trouvée"
    for ex in upper_a_sessions[0]["hevy_workout"]["exercises"]:
        normal_sets = [s for s in ex["sets"] if s["type"] == "normal"]
        assert len(normal_sets) == 3, (
            f"Expected 3 normal sets for {ex['name']}, got {len(normal_sets)}"
        )
        for s in normal_sets:
            assert s["rpe"] == 8, f"Expected RPE 8, got {s['rpe']} for {ex['name']}"
            assert s["reps"] <= 12, f"Expected reps <= 12, got {s['reps']}"


def test_cns_blocks_tier3(simon_agent_view_lifting):
    """cns_load_7day_avg > 65 → aucun exercice Tier 3 dans le plan."""
    from agents.lifting_coach.prescriber import LiftingPrescriber

    view = dict(simon_agent_view_lifting)
    view["fatigue"] = {**view["fatigue"], "cns_load_7day_avg": 70}
    plan = LiftingPrescriber().build_week_plan(view)

    for session in plan["sessions"]:
        for ex in session["hevy_workout"]["exercises"]:
            assert ex["tier"] != 3, (
                f"Tier 3 exercice '{ex['name']}' trouvé malgré CNS overload (70 > 65)"
            )


def test_mrv_hybrid_enforced(simon_agent_view_lifting):
    """Volume total quadriceps sur la semaine <= mrv_hybrid (12 en base_building)."""
    from agents.lifting_coach.prescriber import LiftingPrescriber

    plan = LiftingPrescriber().build_week_plan(simon_agent_view_lifting)
    total_quad_sets = 0
    for session in plan["sessions"]:
        for ex in session["hevy_workout"]["exercises"]:
            if ex["muscle_primary"] == "quadriceps":
                total_quad_sets += sum(
                    1 for s in ex["sets"] if s["type"] == "normal"
                )
    # base_building: mrv_hybrid = 12, lower_body_mrv_multiplier = 1.0 → MRV = 12
    assert total_quad_sets <= 12, (
        f"Total quad sets {total_quad_sets} exceeds mrv_hybrid 12"
    )


def test_deload_reduces_volume(simon_agent_view_lifting):
    """Semaine de deload (week % 4 == 0) → total_sets <= 65% de la semaine normale."""
    from agents.lifting_coach.prescriber import LiftingPrescriber

    p = LiftingPrescriber()
    normal_plan = p.build_week_plan(simon_agent_view_lifting)

    deload_view = {
        **simon_agent_view_lifting,
        "current_phase": {**simon_agent_view_lifting["current_phase"], "mesocycle_week": 4},
    }
    deload_plan = p.build_week_plan(deload_view)

    def count_normal_sets(plan: dict) -> int:
        return sum(
            1
            for session in plan["sessions"]
            for ex in session["hevy_workout"]["exercises"]
            for s in ex["sets"]
            if s["type"] == "normal"
        )

    normal_sets = count_normal_sets(normal_plan)
    deload_sets = count_normal_sets(deload_plan)
    assert deload_sets <= normal_sets * 0.65, (
        f"Deload sets {deload_sets} > 65% of normal sets {normal_sets}"
    )


def test_build_week_plan_hevy_format(simon_agent_view_lifting):
    """Chaque session a hevy_workout.id, .exercises[], .exercises[].sets[], weight_kg=null."""
    from agents.lifting_coach.prescriber import LiftingPrescriber

    plan = LiftingPrescriber().build_week_plan(simon_agent_view_lifting)
    assert "sessions" in plan
    assert len(plan["sessions"]) >= 1

    for session in plan["sessions"]:
        assert "hevy_workout" in session
        hw = session["hevy_workout"]
        assert "id" in hw, "hevy_workout missing 'id'"
        assert "exercises" in hw, "hevy_workout missing 'exercises'"
        assert len(hw["exercises"]) >= 1

        for ex in hw["exercises"]:
            assert "sets" in ex, f"Exercise '{ex.get('name')}' missing 'sets'"
            assert len(ex["sets"]) >= 1
            for s in ex["sets"]:
                assert "weight_kg" in s
                assert s["weight_kg"] is None, (
                    f"weight_kg should be null (auto-regulation), got {s['weight_kg']}"
                )
