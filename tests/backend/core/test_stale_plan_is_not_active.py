"""A plan whose week is over is not the plan the athlete is on.

Seen in Simon's live facts block on 2026-08-21::

    - plan actif : {'start_date': '2026-04-14', 'end_date': '2026-04-20', ...}

That week ended four months earlier. `_active_plan_summary` returns the most
recently created plan and never looks at its dates, so the coach was told a
dead April week was the current one — and would happily discuss Wednesday's
session, which happened in the spring.

Same shape as the passed race in `core/objective.py`: nothing in the system
noticed a date going by. Hiding the plan instead would lose real history, so it
is kept and labelled. `over` is the fact; what to do about it is the coach's
judgement.
"""
from __future__ import annotations

import json
from datetime import date, timedelta

import pytest

from app.core.head_coach_view_builder import _active_plan_summary

TODAY = date.today()


class _Plan:
    def __init__(self, start: date, end: date) -> None:
        self.phase = "general_prep"
        self.start_date = start
        self.end_date: date | None = end
        self.total_weekly_hours = 4.0
        self.acwr = 1.0
        self.status = "active"
        self.weekly_slots_json = json.dumps(
            [{"date": start.isoformat(), "sport": "running", "duration_min": 45}]
        )


class _Db:
    def __init__(self, plan: object | None) -> None:
        self._plan = plan

    def query(self, *_a, **_k):
        return self

    def filter(self, *_a, **_k):
        return self

    def order_by(self, *_a, **_k):
        return self

    def first(self):
        return self._plan


class TestAPlanInItsWeek:
    def test_is_reported_as_current(self) -> None:
        plan = _Plan(TODAY - timedelta(days=2), TODAY + timedelta(days=4))

        summary = _active_plan_summary("a1", _Db(plan))

        assert summary is not None
        assert summary["over"] is False

    def test_its_last_day_still_counts(self) -> None:
        """Sunday's session is still ahead of an athlete reading this on Sunday."""
        plan = _Plan(TODAY - timedelta(days=6), TODAY)

        assert _active_plan_summary("a1", _Db(plan))["over"] is False


class TestAPlanWhoseWeekIsOver:
    def test_is_marked_over(self) -> None:
        plan = _Plan(TODAY - timedelta(days=130), TODAY - timedelta(days=124))

        assert _active_plan_summary("a1", _Db(plan))["over"] is True

    def test_says_how_long_ago(self) -> None:
        """Four months stale and one day stale are different conversations."""
        plan = _Plan(TODAY - timedelta(days=130), TODAY - timedelta(days=124))

        assert _active_plan_summary("a1", _Db(plan))["days_since_end"] == 124

    def test_is_still_returned(self) -> None:
        """The last plan written is real history, even when its week has passed."""
        plan = _Plan(TODAY - timedelta(days=130), TODAY - timedelta(days=124))

        summary = _active_plan_summary("a1", _Db(plan))

        assert summary["sessions_total"] == 1


class TestEdges:
    def test_no_plan_stays_none(self) -> None:
        assert _active_plan_summary("a1", _Db(None)) is None

    def test_a_plan_without_an_end_date_is_not_declared_over(self) -> None:
        """Absence of a date is not evidence the week has passed."""
        plan = _Plan(TODAY, TODAY)
        plan.end_date = None

        assert _active_plan_summary("a1", _Db(plan))["over"] is False


class TestItReachesTheCoach:
    @pytest.mark.parametrize("over", [True, False])
    def test_the_facts_block_says_which(self, over: bool) -> None:
        from app.services.profile_provenance import describe_profile

        class _View:
            def __init__(self) -> None:
                self.today = TODAY
                self.age = 24
                self.sex = "M"
                self.weight_kg = 77.0
                self.height_cm = 183.0
                self.hours_per_week = 8.0
                self.sports = ["running"]
                self.goals = []
                self.target_race_date = None
                self.days_to_race = None
                self.vdot = None
                self.vdot_source = None
                self.acwr_ratio = None
                self.acwr_status = None
                self.readiness = None
                self.muscle_strain = None
                self.recent_sessions = []
                self.goal_feasibility = None
                self.active_plan_summary = {
                    "over": over,
                    "days_since_end": 124 if over else 0,
                    "sessions_total": 1,
                }

        class _NoDb:
            def query(self, *_a, **_k):
                raise RuntimeError("no db")

            def get(self, *_a, **_k):
                return None

        text = describe_profile(_View(), _NoDb(), "a1")

        assert ("terminé" in text.lower()) is over
