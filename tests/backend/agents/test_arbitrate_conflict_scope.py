"""Conflict arbitration must act on the day that is actually in conflict.

Rule 3 of `HeadCoach._arbitrate` drops the shorter of the sessions involved in
a CRITICAL conflict. Its comment says it finds "sessions belonging to the
conflicting agents on the same date" -- but the filter only ever matched on
sport, never on date. So it gathered every session of those sports across the
whole week, dropped the shortest one anywhere in it, and left the collision
standing.

Reproduced 2026-08-20:

    in   running HIIT 24/08 | lifting 24/08 | easy run 26/08
    out  running HIIT 24/08 | lifting 24/08

The easy run on the 26th was deleted. The two sessions that triggered the
conflict both survived. Strictly harmful in both directions: it removes
training the athlete should do and keeps the clash that caused the flag.

These tests pin the scope of the rule, not its severity policy -- whether a
same-day clash should be moved rather than dropped is a coaching decision and
is deliberately left alone here.
"""
from __future__ import annotations

from datetime import date

from app.agents.head_coach import HeadCoach
from app.core.acwr import ACWRResult, ACWRStatus
from app.core.conflict import Conflict, ConflictSeverity
from app.schemas.athlete import Sport
from app.schemas.fatigue import FatigueScore
from app.schemas.plan import WorkoutSlot

MONDAY = date(2026, 8, 24)
WEDNESDAY = date(2026, 8, 26)


def _fatigue() -> FatigueScore:
    return FatigueScore(
        local_muscular=50,
        cns_load=50,
        metabolic_cost=50,
        recovery_hours=24,
        affected_muscles=["quads"],
    )


def _slot(
    slot_id: str, day: date, sport: Sport, workout_type: str, minutes: int
) -> WorkoutSlot:
    return WorkoutSlot(
        id=slot_id,
        date=day,
        sport=sport,
        workout_type=workout_type,
        duration_min=minutes,
        description=slot_id,
        fatigue_score=_fatigue(),
    )


def _safe_acwr() -> ACWRResult:
    return ACWRResult(
        acute_7d=100.0,
        chronic_28d=100.0,
        ratio=1.0,
        status=ACWRStatus.SAFE,
        max_safe_weekly_load=130.0,
    )


def _critical() -> Conflict:
    return Conflict(
        severity=ConflictSeverity.CRITICAL,
        rule="hiit_lifting_same_day",
        agents=["running", "lifting"],
        message="HIIT and lifting on the same day",
    )


def _arbitrate(sessions: list[WorkoutSlot], conflicts: list[Conflict]) -> list[WorkoutSlot]:
    coach = HeadCoach.__new__(HeadCoach)
    return coach._arbitrate(sessions, conflicts, _safe_acwr(), 1.0)


class TestOnlyTheConflictingDayIsTouched:
    def test_a_session_on_another_day_is_not_deleted(self) -> None:
        sessions = [
            _slot("hiit", MONDAY, Sport.RUNNING, "intervals_z3", 60),
            _slot("lift", MONDAY, Sport.LIFTING, "strength_lower", 75),
            _slot("easy", WEDNESDAY, Sport.RUNNING, "easy_z1", 45),
        ]

        kept = {s.id for s in _arbitrate(sessions, [_critical()])}

        assert "easy" in kept, "an unrelated session on another day was dropped"

    def test_the_clash_itself_is_resolved(self) -> None:
        sessions = [
            _slot("hiit", MONDAY, Sport.RUNNING, "intervals_z3", 60),
            _slot("lift", MONDAY, Sport.LIFTING, "strength_lower", 75),
            _slot("easy", WEDNESDAY, Sport.RUNNING, "easy_z1", 45),
        ]

        result = _arbitrate(sessions, [_critical()])
        on_monday = [s for s in result if s.date == MONDAY]

        assert len(on_monday) == 1, "both conflicting sessions survived the conflict"

    def test_the_shorter_of_the_clashing_pair_is_the_one_dropped(self) -> None:
        sessions = [
            _slot("hiit", MONDAY, Sport.RUNNING, "intervals_z3", 45),
            _slot("lift", MONDAY, Sport.LIFTING, "strength_lower", 75),
        ]

        kept = {s.id for s in _arbitrate(sessions, [_critical()])}

        assert kept == {"lift"}


class TestNoConflict:
    def test_a_non_critical_conflict_changes_nothing(self) -> None:
        warning = Conflict(
            severity=ConflictSeverity.WARNING,
            rule="hiit_lifting_same_day",
            agents=["running", "lifting"],
            message="Consider separating",
        )
        sessions = [
            _slot("hiit", MONDAY, Sport.RUNNING, "intervals_z3", 60),
            _slot("lift", MONDAY, Sport.LIFTING, "strength_lower", 75),
        ]

        assert len(_arbitrate(sessions, [warning])) == 2

    def test_no_conflicts_changes_nothing(self) -> None:
        sessions = [
            _slot("hiit", MONDAY, Sport.RUNNING, "intervals_z3", 60),
            _slot("easy", WEDNESDAY, Sport.RUNNING, "easy_z1", 45),
        ]

        assert len(_arbitrate(sessions, [])) == 2

    def test_the_named_sports_on_separate_days_are_left_alone(self) -> None:
        """A conflict can only be about a collision, and there is none here."""
        sessions = [
            _slot("hiit", MONDAY, Sport.RUNNING, "intervals_z3", 60),
            _slot("lift", WEDNESDAY, Sport.LIFTING, "strength_lower", 75),
        ]

        assert len(_arbitrate(sessions, [_critical()])) == 2


class TestSeveralConflictingDays:
    def test_each_conflicting_day_is_resolved_independently(self) -> None:
        friday = date(2026, 8, 28)
        sessions = [
            _slot("hiit_mon", MONDAY, Sport.RUNNING, "intervals_z3", 60),
            _slot("lift_mon", MONDAY, Sport.LIFTING, "strength_lower", 75),
            _slot("hiit_fri", friday, Sport.RUNNING, "intervals_z3", 50),
            _slot("lift_fri", friday, Sport.LIFTING, "strength_upper", 80),
        ]

        result = _arbitrate(sessions, [_critical()])

        assert len([s for s in result if s.date == MONDAY]) == 1
        assert len([s for s in result if s.date == friday]) == 1
