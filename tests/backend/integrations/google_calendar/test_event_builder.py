from __future__ import annotations

from datetime import date

import pytest
from app.integrations.google_calendar.event_builder import (
    REMINDER_MINUTES,
    SLOT_ID_PROPERTY,
    SPORT_COLOR_ID,
    InvalidSlotError,
    build_event,
    content_hash,
    preferred_hour,
    resolve_zone,
    slot_date,
)

MONTREAL = "America/Montreal"

SLOT = {
    "id": "slot-1",
    "date": "2031-06-04",
    "sport": "running",
    "workout_type": "tempo",
    "duration_min": 60,
    "fatigue_score": {
        "local_muscular": 40.0,
        "cns_load": 30.0,
        "metabolic_cost": 55.0,
        "recovery_hours": 20.0,
        "affected_muscles": ["quads"],
    },
    "notes": "8 km @ 4:35/km",
}


class TestBuildEvent:
    def test_summary_carries_sport_type_and_key_metric(self) -> None:
        event = build_event(SLOT, timezone_name=MONTREAL)
        assert event["summary"] == "🏃 tempo — 8 km @ 4:35/km"

    def test_summary_falls_back_to_duration_without_notes(self) -> None:
        event = build_event({**SLOT, "notes": ""}, timezone_name=MONTREAL)
        assert event["summary"] == "🏃 tempo — 60 min"

    def test_start_uses_the_default_hour_in_athlete_local_time(self) -> None:
        event = build_event(SLOT, timezone_name=MONTREAL)
        assert event["start"]["dateTime"].startswith("2031-06-04T07:00:00")
        assert event["start"]["timeZone"] == MONTREAL

    def test_end_is_start_plus_duration(self) -> None:
        event = build_event(SLOT, timezone_name=MONTREAL)
        assert event["end"]["dateTime"].startswith("2031-06-04T08:00:00")

    def test_preferred_hour_per_sport_is_honoured(self) -> None:
        event = build_event(
            SLOT, timezone_name=MONTREAL, preferences={"running": 18}
        )
        assert event["start"]["dateTime"].startswith("2031-06-04T18:00:00")

    def test_description_carries_prescription_fatigue_and_rationale(self) -> None:
        event = build_event(
            SLOT, timezone_name=MONTREAL, rationale="Volume held flat this week."
        )
        assert "8 km @ 4:35/km" in event["description"]
        assert "Fatigue" in event["description"]
        assert "Volume held flat this week." in event["description"]

    def test_reminder_is_a_popup_two_hours_before(self) -> None:
        event = build_event(SLOT, timezone_name=MONTREAL)
        assert event["reminders"] == {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": REMINDER_MINUTES}],
        }

    def test_slot_id_travels_in_private_extended_properties(self) -> None:
        event = build_event(SLOT, timezone_name=MONTREAL)
        assert event["extendedProperties"]["private"][SLOT_ID_PROPERTY] == "slot-1"

    def test_colour_is_stable_per_sport(self) -> None:
        for sport, color in SPORT_COLOR_ID.items():
            event = build_event({**SLOT, "sport": sport}, timezone_name=MONTREAL)
            assert event["colorId"] == color

    def test_unknown_sport_still_builds(self) -> None:
        event = build_event({**SLOT, "sport": "rowing"}, timezone_name=MONTREAL)
        assert "steady" not in event["summary"]
        assert event["colorId"]

    def test_missing_date_is_rejected(self) -> None:
        with pytest.raises(InvalidSlotError):
            build_event({**SLOT, "date": None}, timezone_name=MONTREAL)

    def test_unparseable_date_is_rejected(self) -> None:
        with pytest.raises(InvalidSlotError):
            build_event({**SLOT, "date": "not-a-date"}, timezone_name=MONTREAL)


class TestDaylightSaving:
    """America/Montreal falls back on the first Sunday of November."""

    def test_seven_am_stays_seven_am_across_the_fall_back(self) -> None:
        before = build_event(
            {**SLOT, "date": "2031-10-31"}, timezone_name=MONTREAL
        )
        after = build_event({**SLOT, "date": "2031-11-03"}, timezone_name=MONTREAL)

        assert before["start"]["dateTime"].startswith("2031-10-31T07:00:00")
        assert after["start"]["dateTime"].startswith("2031-11-03T07:00:00")
        assert before["start"]["dateTime"].endswith("-04:00")
        assert after["start"]["dateTime"].endswith("-05:00")

    def test_the_switch_day_itself_keeps_the_wall_clock(self) -> None:
        event = build_event({**SLOT, "date": "2031-11-02"}, timezone_name=MONTREAL)
        assert event["start"]["dateTime"].startswith("2031-11-02T07:00:00")


class TestHelpers:
    def test_unknown_timezone_falls_back_to_the_default(self) -> None:
        assert resolve_zone("Mars/Olympus").key == "America/Montreal"

    def test_preferred_hour_defaults_to_seven(self) -> None:
        assert preferred_hour("running", None) == 7
        assert preferred_hour("running", {}) == 7
        assert preferred_hour("running", {"default": 6}) == 6
        assert preferred_hour("running", {"running": 19}) == 19

    def test_preferred_hour_rejects_nonsense(self) -> None:
        assert preferred_hour("running", {"running": 99}) == 7
        assert preferred_hour("running", {"running": True}) == 7
        assert preferred_hour("running", {"running": "six"}) == 7

    def test_slot_date_accepts_date_objects(self) -> None:
        assert slot_date({"date": date(2031, 6, 4)}) == date(2031, 6, 4)


class TestContentHash:
    def test_same_body_hashes_the_same(self) -> None:
        first = build_event(SLOT, timezone_name=MONTREAL)
        second = build_event(SLOT, timezone_name=MONTREAL)
        assert content_hash(first) == content_hash(second)

    def test_changed_duration_changes_the_hash(self) -> None:
        first = build_event(SLOT, timezone_name=MONTREAL)
        second = build_event({**SLOT, "duration_min": 75}, timezone_name=MONTREAL)
        assert content_hash(first) != content_hash(second)
