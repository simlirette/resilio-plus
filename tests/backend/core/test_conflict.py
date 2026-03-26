from datetime import date

import pytest

from app.core.conflict import detect_conflicts, Conflict, ConflictSeverity
from app.schemas.athlete import Sport
from app.schemas.fatigue import FatigueScore
from app.schemas.plan import WorkoutSlot
from app.agents.base import AgentRecommendation


def _make_fatigue():
    return FatigueScore(local_muscular=20, cns_load=10, metabolic_cost=30, recovery_hours=8)


def _slot(sport: Sport, workout_type: str, day: date = date(2026, 4, 7)) -> WorkoutSlot:
    return WorkoutSlot(
        date=day,
        sport=sport,
        workout_type=workout_type,
        duration_min=60,
        fatigue_score=_make_fatigue(),
    )


def _rec(agent_name: str, sessions: list[WorkoutSlot]) -> AgentRecommendation:
    return AgentRecommendation(
        agent_name=agent_name,
        fatigue_score=_make_fatigue(),
        weekly_load=100.0,
        suggested_sessions=sessions,
    )


def test_no_conflict_with_single_agent():
    recs = [_rec("running", [_slot(Sport.RUNNING, "easy_z1")])]
    assert detect_conflicts(recs) == []


def test_hiit_and_lifting_same_day_is_critical():
    recs = [
        _rec("running", [_slot(Sport.RUNNING, "hiit_intervals")]),
        _rec("lifting", [_slot(Sport.LIFTING, "upper_body")]),
    ]
    conflicts = detect_conflicts(recs)
    assert any(c.severity == ConflictSeverity.CRITICAL for c in conflicts)
    assert any(c.rule == "hiit_strength_same_session" for c in conflicts)


def test_interval_keyword_also_triggers_hiit_rule():
    recs = [
        _rec("running", [_slot(Sport.RUNNING, "vo2max_intervals")]),
        _rec("lifting", [_slot(Sport.LIFTING, "squat_session")]),
    ]
    conflicts = detect_conflicts(recs)
    assert any(c.rule == "hiit_strength_same_session" for c in conflicts)


def test_z2_running_before_lifting_no_conflict():
    recs = [
        _rec("running", [_slot(Sport.RUNNING, "z2_easy_run")]),
        _rec("lifting", [_slot(Sport.LIFTING, "leg_day")]),
    ]
    conflicts = detect_conflicts(recs)
    # Z2/MICT + lifting → explicitly no conflict per §1.2
    assert conflicts == []


def test_endurance_before_lifting_warning():
    recs = [
        _rec("running", [_slot(Sport.RUNNING, "tempo_run")]),
        _rec("lifting", [_slot(Sport.LIFTING, "full_body")]),
    ]
    conflicts = detect_conflicts(recs)
    assert any(c.severity == ConflictSeverity.WARNING for c in conflicts)
    assert any(c.rule == "endurance_before_strength_gap" for c in conflicts)


def test_swimming_before_lifting_is_warning_not_critical():
    recs = [
        _rec("swimming", [_slot(Sport.SWIMMING, "threshold_set")]),
        _rec("lifting", [_slot(Sport.LIFTING, "upper_body")]),
    ]
    conflicts = detect_conflicts(recs)
    warnings = [c for c in conflicts if c.severity == ConflictSeverity.WARNING]
    criticals = [c for c in conflicts if c.severity == ConflictSeverity.CRITICAL]
    assert len(warnings) >= 1
    assert len(criticals) == 0
    assert any(c.rule == "swimming_before_strength_reduced" for c in conflicts)


def test_different_days_no_conflict():
    day1 = date(2026, 4, 7)
    day2 = date(2026, 4, 8)
    recs = [
        _rec("running", [_slot(Sport.RUNNING, "hiit_intervals", day=day1)]),
        _rec("lifting", [_slot(Sport.LIFTING, "squat_session", day=day2)]),
    ]
    conflicts = detect_conflicts(recs)
    assert conflicts == []


def test_conflict_contains_both_agent_names():
    recs = [
        _rec("running", [_slot(Sport.RUNNING, "hiit_session")]),
        _rec("lifting", [_slot(Sport.LIFTING, "lower_body")]),
    ]
    conflicts = detect_conflicts(recs)
    assert len(conflicts) > 0
    assert "running" in conflicts[0].agents
    assert "lifting" in conflicts[0].agents
