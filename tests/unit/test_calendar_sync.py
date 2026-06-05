"""
Unit tests for Google Calendar sync — mapping and idempotence.

No real Google API calls (all mocked). Tests:
  1. Run event mapping (one per workout_type)
  2. Strength event mapping (one per strength_type)
  3. Deterministic UIDs — same inputs = same uid
  4. Idempotence — same plan twice → all skipped on second pass
  5. Diff — changed title → patch; removed event → delete; past event → untouched
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from resilio.core.calendar_sync import (
    PlanToCalendarSync,
    SyncReport,
    _resilio_uid,
    build_run_event,
    build_strength_event,
    _event_fingerprint,
)
from resilio.schemas.config import GoogleCalendarSettings
from resilio.schemas.plan import (
    StrengthSession,
    StrengthType,
    WeekPlan,
    WorkoutPrescription,
    WorkoutStructureHints,
    QualitySessionHints,
    LongRunHints,
    IntensityBalanceHints,
    WorkoutType,
)

# ============================================================
# FIXTURES
# ============================================================

MONDAY = date(2026, 6, 8)  # known Monday
SETTINGS = GoogleCalendarSettings()


def _hints() -> WorkoutStructureHints:
    return WorkoutStructureHints(
        quality=QualitySessionHints(max_sessions=1, types=["strides_only"]),
        long_run=LongRunHints(emphasis="easy", pct_range=[25.0, 35.0]),
        intensity_balance=IntensityBalanceHints(low_intensity_pct=0.9),
    )


def _workout(wtype: str, dow: int, dist: float = 5.0, week: int = 1) -> WorkoutPrescription:
    return WorkoutPrescription(
        date=MONDAY + timedelta(days=dow),
        day_of_week=dow,
        workout_type=wtype,  # type: ignore[arg-type]
        distance_km=dist,
        target_rpe=4,
        week_number=week,
        pace_range="6:00-6:30",
    )


def _strength(stype: str, dow: int, week: int = 1) -> StrengthSession:
    return StrengthSession(
        date=MONDAY + timedelta(days=dow),
        day_of_week=dow,
        session_type=stype,  # type: ignore[arg-type]
        week_number=week,
    )


def _week(workouts, strength=None, week_num=1) -> WeekPlan:
    return WeekPlan(
        week_number=week_num,
        phase="base",
        start_date=MONDAY,
        end_date=MONDAY + timedelta(days=6),
        target_volume_km=sum(w.distance_km for w in workouts if w.workout_type != "rest"),
        target_systemic_load_au=0.0,
        workout_structure_hints=_hints(),
        workouts=workouts,
        strength_sessions=strength or [],
    )


# ============================================================
# 1. RUN EVENT MAPPING
# ============================================================


class TestRunEventMapping:
    def test_easy_title(self):
        w = _workout("easy", 0, 8.0)
        ev = build_run_event(w, _week([w]), SETTINGS)
        assert ev["summary"] == "🏃 Easy 8km"

    def test_long_run_title(self):
        w = _workout("long_run", 6, 15.0)
        ev = build_run_event(w, _week([w]), SETTINGS)
        assert "Long run" in ev["summary"]
        assert "15km" in ev["summary"]

    def test_rest_is_all_day(self):
        w = _workout("rest", 4, 0.0)
        ev = build_run_event(w, _week([w]), SETTINGS)
        assert "date" in ev["start"]
        assert "dateTime" not in ev["start"]

    def test_rest_no_reminder(self):
        w = _workout("rest", 4, 0.0)
        ev = build_run_event(w, _week([w]), SETTINGS)
        assert ev["reminders"]["overrides"] == []

    def test_intervals_with_reps(self):
        w = _workout("intervals", 2, 8.0)
        w.intervals = [{"reps": 5, "distance": "1000m", "pace": "5:00", "recovery": "2:00"}]
        ev = build_run_event(w, _week([w]), SETTINGS)
        assert "5" in ev["summary"] and "1000m" in ev["summary"]

    def test_managed_marker_present(self):
        w = _workout("easy", 0)
        ev = build_run_event(w, _week([w]), SETTINGS)
        props = ev["extendedProperties"]["private"]
        assert props["resilio_managed"] == "1"
        assert props["resilio_uid"].startswith("resilio-")

    def test_long_run_weekend_time(self):
        # Sunday = dow 6 → weekend time
        w = _workout("long_run", 6, 15.0)
        ev = build_run_event(w, _week([w]), SETTINGS)
        start_time = ev["start"]["dateTime"].split("T")[1][:5]
        assert start_time == SETTINGS.default_times["long_run_weekend"]

    def test_long_run_weekday_time(self):
        w = _workout("long_run", 0, 15.0)  # Monday
        ev = build_run_event(w, _week([w]), SETTINGS)
        start_time = ev["start"]["dateTime"].split("T")[1][:5]
        assert start_time == SETTINGS.default_times["long_run_weekday"]


# ============================================================
# 2. STRENGTH EVENT MAPPING
# ============================================================


class TestStrengthEventMapping:
    @pytest.mark.parametrize("stype,expected_label", [
        ("legs", "Leg day"),
        ("upper", "Upper day"),
        ("chest_back", "Chest/Back day"),
        ("arms", "Arms day"),
    ])
    def test_title(self, stype, expected_label):
        s = _strength(stype, 1)
        ev = build_strength_event(s, SETTINGS)
        assert expected_label in ev["summary"]
        assert "🏋️" in ev["summary"]

    def test_description_hevy_only(self):
        s = _strength("legs", 1)
        ev = build_strength_event(s, SETTINGS)
        assert "Hevy" in ev["description"]
        assert len(ev["description"]) < 40  # no workout detail

    def test_managed_marker(self):
        s = _strength("arms", 3)
        ev = build_strength_event(s, SETTINGS)
        props = ev["extendedProperties"]["private"]
        assert props["resilio_managed"] == "1"
        assert "arms" in props["resilio_uid"]

    def test_default_evening_time(self):
        s = _strength("upper", 2)
        ev = build_strength_event(s, SETTINGS)
        start_time = ev["start"]["dateTime"].split("T")[1][:5]
        assert start_time == "18:00"


# ============================================================
# 3. DETERMINISTIC UIDs
# ============================================================


class TestUIDs:
    def test_same_inputs_same_uid(self):
        uid1 = _resilio_uid(date(2026, 6, 10), "easy", 2)
        uid2 = _resilio_uid(date(2026, 6, 10), "easy", 2)
        assert uid1 == uid2

    def test_different_date_different_uid(self):
        uid1 = _resilio_uid(date(2026, 6, 10), "easy", 2)
        uid2 = _resilio_uid(date(2026, 6, 11), "easy", 2)
        assert uid1 != uid2

    def test_different_type_different_uid(self):
        uid1 = _resilio_uid(date(2026, 6, 10), "easy", 2)
        uid2 = _resilio_uid(date(2026, 6, 10), "legs", 2)
        assert uid1 != uid2

    def test_uid_format(self):
        uid = _resilio_uid(date(2026, 6, 10), "easy", 3)
        assert uid == "resilio-2026-06-10-easy-w3"


# ============================================================
# 4. IDEMPOTENCE — same plan twice = no-op second time
# ============================================================


def _make_mock_client(existing_events: list[dict]):
    """Return a mock GoogleCalendarClient."""
    client = MagicMock()
    client.ensure_calendar.return_value = "cal_test_id"
    client.list_managed_events.return_value = existing_events
    client.create_event.side_effect = lambda cal_id, ev: {**ev, "id": "new_id"}
    client.patch_event.side_effect = lambda cal_id, ev_id, patch: {**patch, "id": ev_id}
    client.delete_event.return_value = None
    return client


class TestIdempotence:
    def test_first_sync_inserts(self, tmp_path):
        workouts = [_workout("easy", 0, 8.0), _workout("long_run", 6, 15.0)]
        strength = [_strength("legs", 1), _strength("upper", 2)]
        week = _week(workouts, strength)

        client = _make_mock_client([])
        state_path = tmp_path / "state.json"
        # Pre-seed calendar_id so ensure_calendar not called
        state_path.write_text(json.dumps({"calendar_id": "cal_test_id"}))

        syncer = PlanToCalendarSync(client, SETTINGS, state_path)
        report = syncer.sync([week])

        assert report.inserted == 4  # 2 runs + 2 lifts
        assert report.patched == 0
        assert report.deleted == 0
        assert report.errors == []

    def test_second_sync_is_noop(self, tmp_path):
        workouts = [_workout("easy", 0, 8.0)]
        strength = [_strength("arms", 3)]
        week = _week(workouts, strength)

        # Build what remote would look like after first sync
        run_ev = build_run_event(workouts[0], week, SETTINGS)
        str_ev = build_strength_event(strength[0], SETTINGS)
        run_uid = run_ev["extendedProperties"]["private"]["resilio_uid"]
        str_uid = str_ev["extendedProperties"]["private"]["resilio_uid"]
        remote = [
            {**run_ev, "id": "id1", "extendedProperties": {"private": {"resilio_managed": "1", "resilio_uid": run_uid}}},
            {**str_ev, "id": "id2", "extendedProperties": {"private": {"resilio_managed": "1", "resilio_uid": str_uid}}},
        ]

        client = _make_mock_client(remote)
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"calendar_id": "cal_test_id"}))

        syncer = PlanToCalendarSync(client, SETTINGS, state_path)
        report = syncer.sync([week])

        assert report.inserted == 0
        assert report.patched == 0
        assert report.deleted == 0
        assert report.skipped == 2


# ============================================================
# 5. DIFF — changed event → patch; removed → delete
# ============================================================


class TestDiff:
    def test_changed_workout_patched(self, tmp_path):
        w = _workout("easy", 0, 8.0)
        week = _week([w])
        ev = build_run_event(w, week, SETTINGS)
        uid = ev["extendedProperties"]["private"]["resilio_uid"]

        # Remote has old summary
        stale_ev = {**ev, "id": "old_id", "summary": "OLD SUMMARY"}
        stale_ev["extendedProperties"] = {"private": {"resilio_managed": "1", "resilio_uid": uid}}

        client = _make_mock_client([stale_ev])
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"calendar_id": "cal_test_id"}))

        syncer = PlanToCalendarSync(client, SETTINGS, state_path)
        report = syncer.sync([week])

        assert report.patched == 1
        assert report.inserted == 0

    def test_removed_workout_deleted(self, tmp_path):
        # Remote has a managed event that no longer exists in plan
        orphan_uid = "resilio-2026-06-08-easy-w1"
        orphan = {
            "id": "orphan_id",
            "summary": "🏃 Easy 5km",
            "start": {"dateTime": "2026-06-08T06:30:00-04:00"},
            "end": {"dateTime": "2026-06-08T07:00:00-04:00"},
            "reminders": {"useDefault": False, "overrides": []},
            "description": "",
            "extendedProperties": {"private": {"resilio_managed": "1", "resilio_uid": orphan_uid}},
        }
        # Plan has a DIFFERENT workout that day
        w = _workout("long_run", 6, 15.0)
        week = _week([w])

        client = _make_mock_client([orphan])
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"calendar_id": "cal_test_id"}))

        syncer = PlanToCalendarSync(client, SETTINGS, state_path)
        report = syncer.sync([week])

        assert report.deleted == 1
        assert report.inserted == 1  # long_run inserted

    def test_past_events_not_touched(self, tmp_path):
        # Past workout → filtered before sync, not deleted
        past_date = date.today() - timedelta(days=3)
        w = WorkoutPrescription(
            date=past_date,
            day_of_week=past_date.weekday(),
            workout_type="easy",
            distance_km=5.0,
            target_rpe=4,
            week_number=1,
        )
        # Week that spans past+future
        past_monday = past_date - timedelta(days=past_date.weekday())
        week = WeekPlan(
            week_number=1,
            phase="base",
            start_date=past_monday,
            end_date=past_monday + timedelta(days=6),
            target_volume_km=5.0,
            target_systemic_load_au=0.0,
            workout_structure_hints=_hints(),
            workouts=[w],
        )

        client = _make_mock_client([])
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"calendar_id": "cal_test_id"}))

        syncer = PlanToCalendarSync(client, SETTINGS, state_path)
        report = syncer.sync([week])

        # Past event not inserted
        assert report.inserted == 0
        client.create_event.assert_not_called()
