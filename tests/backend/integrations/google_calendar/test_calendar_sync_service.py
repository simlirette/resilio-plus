from __future__ import annotations

import uuid
from datetime import date
from typing import Any

import pytest
from app.db.models import (
    AthleteModel,
    CalendarEventModel,
    GoogleCalendarCredentialModel,
)
from app.integrations.google_calendar.calendar_sync_service import (
    CalendarSyncService,
    push_week_for_athlete,
)
from app.integrations.google_calendar.client import GoogleCalendarNotFoundError
from app.integrations.google_calendar.oauth_service import (
    GoogleCalendarNotConnectedError,
)
from sqlalchemy.orm import Session

ATHLETE_ID = "athlete-gcal"
CALENDAR_ID = "cal-resilio"


def _slot(slot_id: str, day: str, **overrides: Any) -> dict[str, Any]:
    slot: dict[str, Any] = {
        "id": slot_id,
        "date": day,
        "sport": "running",
        "workout_type": "easy",
        "duration_min": 45,
        "notes": "",
    }
    slot.update(overrides)
    return slot


def _plan(*slots: dict[str, Any]) -> dict[str, Any]:
    return {"phase": "base", "sessions": list(slots), "notes": ["Steady week."]}


class FakeClient:
    """Records every write so tests can assert "no API writes at all"."""

    def __init__(self, *, missing_calendar: bool = False) -> None:
        self.calls: list[tuple[str, Any]] = []
        self.missing_calendar = missing_calendar
        self.missing_events: set[str] = set()
        self._next_id = 0

    def get_calendar(self, calendar_id: str) -> dict[str, Any]:
        self.calls.append(("get_calendar", calendar_id))
        if self.missing_calendar:
            raise GoogleCalendarNotFoundError(404, "not found")
        return {"id": calendar_id}

    def create_calendar(self, summary: str, time_zone: str) -> dict[str, Any]:
        self.calls.append(("create_calendar", (summary, time_zone)))
        return {"id": CALENDAR_ID}

    def insert_event(self, calendar_id: str, body: Any) -> dict[str, Any]:
        self._next_id += 1
        self.calls.append(("insert", body["summary"]))
        return {"id": f"gcal-{self._next_id}"}

    def patch_event(self, calendar_id: str, event_id: str, body: Any) -> dict[str, Any]:
        self.calls.append(("patch", event_id))
        if event_id in self.missing_events:
            raise GoogleCalendarNotFoundError(404, "not found")
        return {"id": event_id}

    def delete_event(self, calendar_id: str, event_id: str) -> None:
        self.calls.append(("delete", event_id))

    @property
    def writes(self) -> list[tuple[str, Any]]:
        return [c for c in self.calls if c[0] in ("insert", "patch", "delete")]


@pytest.fixture
def athlete(db_session: Session) -> str:
    db_session.add(
        AthleteModel(
            id=ATHLETE_ID,
            name="Calendar Athlete",
            age=36,
            sex="F",
            weight_kg=61.0,
            height_cm=169.0,
            primary_sport="running",
            hours_per_week=7.0,
            sports_json='["running"]',
            goals_json="[]",
            available_days_json="[]",
            equipment_json="[]",
            timezone="America/Montreal",
            preferred_session_hour_json="{}",
        )
    )
    db_session.add(
        GoogleCalendarCredentialModel(
            athlete_id=ATHLETE_ID,
            refresh_token_enc="encrypted-refresh",
            calendar_id=CALENDAR_ID,
        )
    )
    db_session.commit()
    return ATHLETE_ID


def build(db_session: Session, client: FakeClient) -> CalendarSyncService:
    return CalendarSyncService(db_session, client=client)


class TestFirstPush:
    def test_creates_one_event_per_slot(
        self, db_session: Session, athlete: str
    ) -> None:
        client = FakeClient()
        plan = _plan(_slot("a", "2031-06-02"), _slot("b", "2031-06-04"))

        report = build(db_session, client).push_week(athlete, plan)

        assert report.created == 2
        assert report.updated == 0
        assert report.deleted == 0
        assert len([c for c in client.writes if c[0] == "insert"]) == 2

        rows = db_session.query(CalendarEventModel).all()
        assert {row.slot_id for row in rows} == {"a", "b"}
        assert {row.slot_date for row in rows} == {date(2031, 6, 2), date(2031, 6, 4)}

    def test_last_sync_is_stamped(self, db_session: Session, athlete: str) -> None:
        build(db_session, FakeClient()).push_week(
            athlete, _plan(_slot("a", "2031-06-02"))
        )
        row = db_session.get(GoogleCalendarCredentialModel, athlete)
        assert row is not None and row.last_sync_at is not None


class TestRePush:
    def test_identical_week_writes_nothing(
        self, db_session: Session, athlete: str
    ) -> None:
        plan = _plan(_slot("a", "2031-06-02"), _slot("b", "2031-06-04"))
        build(db_session, FakeClient()).push_week(athlete, plan)

        second_client = FakeClient()
        report = build(db_session, second_client).push_week(athlete, plan)

        assert report == type(report)(unchanged=2)
        assert second_client.writes == []

    def test_changed_duration_patches_instead_of_duplicating(
        self, db_session: Session, athlete: str
    ) -> None:
        build(db_session, FakeClient()).push_week(
            athlete, _plan(_slot("a", "2031-06-02"))
        )

        client = FakeClient()
        report = build(db_session, client).push_week(
            athlete, _plan(_slot("a", "2031-06-02", duration_min=75))
        )

        assert report.updated == 1
        assert report.created == 0
        assert [c[0] for c in client.writes] == ["patch"]
        assert db_session.query(CalendarEventModel).count() == 1

    def test_removed_slot_is_deleted(
        self, db_session: Session, athlete: str
    ) -> None:
        build(db_session, FakeClient()).push_week(
            athlete, _plan(_slot("a", "2031-06-02"), _slot("b", "2031-06-04"))
        )

        client = FakeClient()
        report = build(db_session, client).push_week(
            athlete, _plan(_slot("a", "2031-06-02"))
        )

        assert report.deleted == 1
        assert [c[0] for c in client.writes] == ["delete"]
        assert {r.slot_id for r in db_session.query(CalendarEventModel).all()} == {"a"}

    def test_other_weeks_are_never_pruned(
        self, db_session: Session, athlete: str
    ) -> None:
        build(db_session, FakeClient()).push_week(
            athlete, _plan(_slot("old", "2031-05-26"))
        )

        client = FakeClient()
        report = build(db_session, client).push_week(
            athlete, _plan(_slot("new", "2031-06-02"))
        )

        assert report.deleted == 0
        assert {r.slot_id for r in db_session.query(CalendarEventModel).all()} == {
            "old",
            "new",
        }

    def test_event_deleted_upstream_is_recreated_on_patch(
        self, db_session: Session, athlete: str
    ) -> None:
        build(db_session, FakeClient()).push_week(
            athlete, _plan(_slot("a", "2031-06-02"))
        )
        row = db_session.query(CalendarEventModel).one()
        client = FakeClient()
        client.missing_events = {row.gcal_event_id}

        report = build(db_session, client).push_week(
            athlete, _plan(_slot("a", "2031-06-02", duration_min=90))
        )

        assert report.updated == 1
        assert [c[0] for c in client.writes] == ["patch", "insert"]


class TestEnsureCalendar:
    def test_reuses_the_stored_calendar(
        self, db_session: Session, athlete: str
    ) -> None:
        client = FakeClient()
        assert build(db_session, client).ensure_calendar(athlete) == CALENDAR_ID
        assert ("create_calendar", ("Resilio Training", "America/Montreal")) not in (
            client.calls
        )

    def test_creates_when_none_is_stored(
        self, db_session: Session, athlete: str
    ) -> None:
        row = db_session.get(GoogleCalendarCredentialModel, athlete)
        assert row is not None
        row.calendar_id = None
        db_session.commit()
        client = FakeClient()

        calendar_id = build(db_session, client).ensure_calendar(athlete)

        assert calendar_id == CALENDAR_ID
        assert client.calls[0] == (
            "create_calendar",
            ("Resilio Training", "America/Montreal"),
        )

    def test_recreates_when_deleted_upstream_and_forgets_stale_events(
        self, db_session: Session, athlete: str
    ) -> None:
        build(db_session, FakeClient()).push_week(
            athlete, _plan(_slot("a", "2031-06-02"))
        )
        assert db_session.query(CalendarEventModel).count() == 1

        client = FakeClient(missing_calendar=True)
        calendar_id = build(db_session, client).ensure_calendar(athlete)

        assert calendar_id == CALENDAR_ID
        assert db_session.query(CalendarEventModel).count() == 0

    def test_unconnected_athlete_is_rejected(
        self, db_session: Session, athlete: str
    ) -> None:
        row = db_session.get(GoogleCalendarCredentialModel, athlete)
        assert row is not None
        row.refresh_token_enc = None
        db_session.commit()

        with pytest.raises(GoogleCalendarNotConnectedError):
            build(db_session, FakeClient()).ensure_calendar(athlete)


class TestDegenerateInput:
    def test_slot_without_id_is_skipped(
        self, db_session: Session, athlete: str
    ) -> None:
        plan = {"sessions": [{"date": "2031-06-02", "sport": "running"}]}
        report = build(db_session, FakeClient()).push_week(athlete, plan)
        assert report.skipped == 1
        assert report.created == 0

    def test_slot_with_bad_date_is_skipped_not_fatal(
        self, db_session: Session, athlete: str
    ) -> None:
        plan = _plan(_slot("a", "2031-06-02"), _slot("b", "nope"))
        report = build(db_session, FakeClient()).push_week(athlete, plan)
        assert report.created == 1
        assert report.skipped == 1

    def test_empty_plan_is_a_no_op(self, db_session: Session, athlete: str) -> None:
        client = FakeClient()
        report = build(db_session, client).push_week(athlete, {"sessions": []})
        assert report.created == 0
        assert client.writes == []

    def test_none_plan_is_a_no_op(self, db_session: Session, athlete: str) -> None:
        report = build(db_session, FakeClient()).push_week(athlete, None)
        assert report.created == 0

    def test_unknown_athlete_raises(self, db_session: Session, athlete: str) -> None:
        with pytest.raises(ValueError):
            build(db_session, FakeClient()).push_week("ghost", _plan())


class TestSeam:
    def test_push_week_for_athlete_returns_plain_counts(
        self, db_session: Session, athlete: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client = FakeClient()
        monkeypatch.setattr(
            "app.integrations.google_calendar.calendar_sync_service.CalendarSyncService._client_for",
            lambda self, athlete_id: client,
        )

        counts = push_week_for_athlete(
            athlete, _plan(_slot("a", "2031-06-02")), db_session
        )

        assert counts["created"] == 1
        assert set(counts) == {"created", "updated", "deleted", "unchanged", "skipped"}


def test_slot_ids_are_scoped_per_athlete(db_session: Session, athlete: str) -> None:
    other = "athlete-gcal-2"
    db_session.add(
        AthleteModel(
            id=other,
            name="Other",
            age=30,
            sex="M",
            weight_kg=70.0,
            height_cm=175.0,
            primary_sport="running",
            hours_per_week=5.0,
            sports_json='["running"]',
            goals_json="[]",
            available_days_json="[]",
            equipment_json="[]",
        )
    )
    db_session.add(
        GoogleCalendarCredentialModel(
            athlete_id=other,
            refresh_token_enc="encrypted-refresh",
            calendar_id="cal-other",
        )
    )
    db_session.commit()

    build(db_session, FakeClient()).push_week(athlete, _plan(_slot("a", "2031-06-02")))
    build(db_session, FakeClient()).push_week(other, _plan(_slot("a", "2031-06-02")))

    rows = db_session.query(CalendarEventModel).all()
    assert len(rows) == 2
    assert {r.athlete_id for r in rows} == {ATHLETE_ID, other}
    assert len({r.id for r in rows}) == 2
    assert uuid.UUID(rows[0].id)
