from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from sqlalchemy.orm import Session

from app.db.models import AthleteModel, MessagingIdentityModel, PendingApprovalModel
from app.messaging.approval_service import ApprovalService
from app.messaging.approvals import ApprovalOwnershipError, parse_callback
from app.messaging.base import Button

FIXED_NOW = datetime(2031, 5, 4, 12, 0, tzinfo=timezone.utc)

PLAN: dict[str, Any] = {
    "phase": "build",
    "sessions": [
        {
            "id": "slot-1",
            "date": "2031-05-05",
            "sport": "running",
            "workout_type": "tempo",
            "duration_min": 60,
            "notes": "",
        }
    ],
}

FINAL_PLAN: dict[str, Any] = {**PLAN, "db_plan_id": "plan-1"}


class FakeNotifier:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str, list[Button] | None]] = []

    def send(
        self,
        athlete_id: str,
        text: str,
        buttons: list[Button] | None = None,
    ) -> object:
        self.sent.append((athlete_id, text, buttons))
        return ["provider-1"]

    @property
    def last_text(self) -> str:
        return self.sent[-1][1]


class FakeCoaching:
    def __init__(self, results: list[dict[str, Any] | None] | None = None) -> None:
        self.calls: list[tuple[str, bool, str | None]] = []
        self._results = results or []

    def resume_plan(
        self,
        thread_id: str,
        approved: bool,
        feedback: str | None,
        db: Session,
    ) -> dict[str, Any] | None:
        self.calls.append((thread_id, approved, feedback))
        if self._results:
            return self._results.pop(0)
        return FINAL_PLAN if approved else PLAN


class FakeCalendar:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def __call__(
        self, athlete_id: str, plan: dict[str, Any], db: Session
    ) -> dict[str, int]:
        self.calls.append((athlete_id, plan))
        return {"created": 3, "updated": 1, "deleted": 0, "unchanged": 2}


@pytest.fixture
def identity(db_session: Session, athlete_id: str) -> str:
    db_session.add(
        MessagingIdentityModel(
            id="identity-1",
            athlete_id=athlete_id,
            channel="telegram",
            external_id="9001",
        )
    )
    db_session.commit()
    return "9001"


@pytest.fixture
def other_athlete_id(db_session: Session) -> str:
    other = "athlete-service-other"
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
    db_session.commit()
    return other


def build_service(
    db_session: Session,
    *,
    notifier: FakeNotifier,
    coaching: FakeCoaching | None = None,
    calendar: FakeCalendar | None = None,
) -> ApprovalService:
    return ApprovalService(
        db_session,
        notifier=notifier,
        coaching=coaching or FakeCoaching(),
        calendar_pusher=calendar,
        clock=lambda: FIXED_NOW,
    )


class TestSendPlanForApproval:
    def test_sends_week_with_three_buttons(
        self, db_session: Session, athlete_id: str
    ) -> None:
        notifier = FakeNotifier()
        service = build_service(db_session, notifier=notifier)

        token = service.send_plan_for_approval(
            athlete_id=athlete_id,
            thread_id="thread-1",
            kind="weekly_plan",
            plan=PLAN,
        )

        assert len(notifier.sent) == 1
        _, text, buttons = notifier.sent[0]
        assert "tempo" in text
        assert buttons is not None
        assert len(buttons) == 3
        assert [parse_callback(b.token)[1] for b in buttons] == [  # type: ignore[index]
            "approve",
            "revise",
            "reject",
        ]
        assert all(len(b.token.encode("utf-8")) <= 64 for b in buttons)

        row = db_session.get(PendingApprovalModel, token)
        assert row is not None
        assert row.thread_id == "thread-1"

    def test_degraded_sources_are_surfaced_to_the_athlete(
        self, db_session: Session, athlete_id: str
    ) -> None:
        notifier = FakeNotifier()
        service = build_service(db_session, notifier=notifier)

        service.send_plan_for_approval(
            athlete_id=athlete_id,
            thread_id="thread-1",
            kind="weekly_plan",
            plan=PLAN,
            degraded_sources=["hevy"],
        )

        assert "hevy" in notifier.last_text.lower()


class TestApprove:
    def test_resumes_graph_and_pushes_calendar_once(
        self, db_session: Session, athlete_id: str, identity: str
    ) -> None:
        notifier = FakeNotifier()
        coaching = FakeCoaching()
        calendar = FakeCalendar()
        service = build_service(
            db_session, notifier=notifier, coaching=coaching, calendar=calendar
        )
        token = service.send_plan_for_approval(
            athlete_id=athlete_id,
            thread_id="thread-1",
            kind="weekly_plan",
            plan=PLAN,
        )

        outcome = service.handle_button(
            athlete_id=athlete_id,
            channel="telegram",
            external_id=identity,
            token=token,
            resolution="approve",
        )

        assert coaching.calls == [("thread-1", True, None)]
        assert len(calendar.calls) == 1
        assert calendar.calls[0][0] == athlete_id
        assert calendar.calls[0][1]["db_plan_id"] == "plan-1"
        assert outcome.resolution == "approve"
        assert outcome.calendar == {
            "created": 3,
            "updated": 1,
            "deleted": 0,
            "unchanged": 2,
        }
        assert "3" in notifier.last_text

    def test_without_calendar_backend_says_so_and_still_approves(
        self, db_session: Session, athlete_id: str, identity: str
    ) -> None:
        notifier = FakeNotifier()
        coaching = FakeCoaching()
        service = build_service(db_session, notifier=notifier, coaching=coaching)
        token = service.send_plan_for_approval(
            athlete_id=athlete_id,
            thread_id="thread-1",
            kind="weekly_plan",
            plan=PLAN,
        )

        outcome = service.handle_button(
            athlete_id=athlete_id,
            channel="telegram",
            external_id=identity,
            token=token,
            resolution="approve",
        )

        assert coaching.calls == [("thread-1", True, None)]
        assert outcome.calendar is None
        assert "agenda" in notifier.last_text.lower()

    def test_replayed_button_does_not_resume_twice(
        self, db_session: Session, athlete_id: str, identity: str
    ) -> None:
        notifier = FakeNotifier()
        coaching = FakeCoaching()
        service = build_service(db_session, notifier=notifier, coaching=coaching)
        token = service.send_plan_for_approval(
            athlete_id=athlete_id,
            thread_id="thread-1",
            kind="weekly_plan",
            plan=PLAN,
        )
        service.handle_button(
            athlete_id=athlete_id,
            channel="telegram",
            external_id=identity,
            token=token,
            resolution="approve",
        )

        outcome = service.handle_button(
            athlete_id=athlete_id,
            channel="telegram",
            external_id=identity,
            token=token,
            resolution="approve",
        )

        assert len(coaching.calls) == 1
        assert outcome.resolution == "ignored"
        assert "déjà" in notifier.last_text.lower()

    def test_expired_button_is_explained_and_does_not_resume(
        self, db_session: Session, athlete_id: str, identity: str
    ) -> None:
        notifier = FakeNotifier()
        coaching = FakeCoaching()
        service = ApprovalService(
            db_session,
            notifier=notifier,
            coaching=coaching,
            clock=lambda: FIXED_NOW,
        )
        token = service.send_plan_for_approval(
            athlete_id=athlete_id,
            thread_id="thread-1",
            kind="weekly_plan",
            plan=PLAN,
        )
        late = ApprovalService(
            db_session,
            notifier=notifier,
            coaching=coaching,
            clock=lambda: FIXED_NOW + timedelta(days=8),
        )

        outcome = late.handle_button(
            athlete_id=athlete_id,
            channel="telegram",
            external_id=identity,
            token=token,
            resolution="approve",
        )

        assert coaching.calls == []
        assert outcome.resolution == "ignored"
        assert "expiré" in notifier.last_text.lower()

    def test_cross_athlete_button_raises_and_touches_nothing(
        self,
        db_session: Session,
        athlete_id: str,
        identity: str,
        other_athlete_id: str,
    ) -> None:
        notifier = FakeNotifier()
        coaching = FakeCoaching()
        service = build_service(db_session, notifier=notifier, coaching=coaching)
        token = service.send_plan_for_approval(
            athlete_id=athlete_id,
            thread_id="thread-1",
            kind="weekly_plan",
            plan=PLAN,
        )

        with pytest.raises(ApprovalOwnershipError):
            service.handle_button(
                athlete_id=other_athlete_id,
                channel="telegram",
                external_id="7777",
                token=token,
                resolution="approve",
            )

        assert coaching.calls == []
        row = db_session.get(PendingApprovalModel, token)
        assert row is not None and row.resolved_at is None

    def test_unknown_token_is_explained(
        self, db_session: Session, athlete_id: str, identity: str
    ) -> None:
        notifier = FakeNotifier()
        service = build_service(db_session, notifier=notifier)

        outcome = service.handle_button(
            athlete_id=athlete_id,
            channel="telegram",
            external_id=identity,
            token="nope",
            resolution="approve",
        )

        assert outcome.resolution == "ignored"
        assert notifier.sent


class TestRevise:
    def test_button_arms_latch_and_leaves_approval_open(
        self, db_session: Session, athlete_id: str, identity: str
    ) -> None:
        notifier = FakeNotifier()
        coaching = FakeCoaching()
        service = build_service(db_session, notifier=notifier, coaching=coaching)
        token = service.send_plan_for_approval(
            athlete_id=athlete_id,
            thread_id="thread-1",
            kind="weekly_plan",
            plan=PLAN,
        )

        outcome = service.handle_button(
            athlete_id=athlete_id,
            channel="telegram",
            external_id=identity,
            token=token,
            resolution="revise",
        )

        assert outcome.resolution == "revise"
        assert coaching.calls == []
        row = db_session.get(PendingApprovalModel, token)
        assert row is not None and row.resolved_at is None
        db_session.expire_all()
        identity_row = db_session.get(MessagingIdentityModel, "identity-1")
        assert identity_row is not None
        assert identity_row.awaiting_revision_for_token == token
        assert "change" in notifier.last_text.lower()

    def test_free_text_routes_to_revise_and_re_texts_the_week(
        self, db_session: Session, athlete_id: str, identity: str
    ) -> None:
        notifier = FakeNotifier()
        revised = {**PLAN, "phase": "recovery"}
        coaching = FakeCoaching(results=[revised])
        service = build_service(db_session, notifier=notifier, coaching=coaching)
        token = service.send_plan_for_approval(
            athlete_id=athlete_id,
            thread_id="thread-1",
            kind="weekly_plan",
            plan=PLAN,
        )
        service.handle_button(
            athlete_id=athlete_id,
            channel="telegram",
            external_id=identity,
            token=token,
            resolution="revise",
        )

        outcome = service.handle_revision_text(
            athlete_id=athlete_id,
            channel="telegram",
            external_id=identity,
            token=token,
            text="too much volume Wednesday",
        )

        assert coaching.calls == [("thread-1", False, "too much volume Wednesday")]
        assert outcome.new_token is not None and outcome.new_token != token
        old = db_session.get(PendingApprovalModel, token)
        assert old is not None and old.resolution == "revise"
        _, text, buttons = notifier.sent[-1]
        assert buttons is not None and len(buttons) == 3
        assert "récupération" in text

    def test_latch_is_consumed_so_the_next_message_is_normal_chat(
        self, db_session: Session, athlete_id: str, identity: str
    ) -> None:
        from app.messaging.approvals import pop_revision_latch

        notifier = FakeNotifier()
        service = build_service(db_session, notifier=notifier)
        token = service.send_plan_for_approval(
            athlete_id=athlete_id,
            thread_id="thread-1",
            kind="weekly_plan",
            plan=PLAN,
        )
        service.handle_button(
            athlete_id=athlete_id,
            channel="telegram",
            external_id=identity,
            token=token,
            resolution="revise",
        )
        service.handle_revision_text(
            athlete_id=athlete_id,
            channel="telegram",
            external_id=identity,
            token=token,
            text="less volume",
        )

        assert (
            pop_revision_latch(db_session, channel="telegram", external_id=identity)
            is None
        )


class TestReject:
    def test_marks_resolved_without_resuming_or_writing_calendar(
        self, db_session: Session, athlete_id: str, identity: str
    ) -> None:
        notifier = FakeNotifier()
        coaching = FakeCoaching()
        calendar = FakeCalendar()
        service = build_service(
            db_session, notifier=notifier, coaching=coaching, calendar=calendar
        )
        token = service.send_plan_for_approval(
            athlete_id=athlete_id,
            thread_id="thread-1",
            kind="weekly_plan",
            plan=PLAN,
        )

        outcome = service.handle_button(
            athlete_id=athlete_id,
            channel="telegram",
            external_id=identity,
            token=token,
            resolution="reject",
        )

        assert outcome.resolution == "reject"
        assert coaching.calls == []
        assert calendar.calls == []
        row = db_session.get(PendingApprovalModel, token)
        assert row is not None and row.resolution == "reject"


class ExplodingCoaching(FakeCoaching):
    def resume_plan(
        self,
        thread_id: str,
        approved: bool,
        feedback: str | None,
        db: Session,
    ) -> dict[str, Any] | None:
        self.calls.append((thread_id, approved, feedback))
        raise RuntimeError("graph unavailable")


class ExplodingCalendar(FakeCalendar):
    def __call__(
        self, athlete_id: str, plan: dict[str, Any], db: Session
    ) -> dict[str, int]:
        self.calls.append((athlete_id, plan))
        raise RuntimeError("google unavailable")


class TestFailuresAreVisible:
    def test_a_failing_graph_tells_the_athlete_instead_of_raising(
        self, db_session: Session, athlete_id: str, identity: str
    ) -> None:
        notifier = FakeNotifier()
        coaching = ExplodingCoaching()
        service = build_service(db_session, notifier=notifier, coaching=coaching)
        token = service.send_plan_for_approval(
            athlete_id=athlete_id,
            thread_id="thread-1",
            kind="weekly_plan",
            plan=PLAN,
        )

        outcome = service.handle_button(
            athlete_id=athlete_id,
            channel="telegram",
            external_id=identity,
            token=token,
            resolution="approve",
        )

        assert outcome.resolution == "error"
        assert "/plan" in notifier.last_text
        assert "agenda" in notifier.last_text.lower()

    def test_a_failing_calendar_says_the_plan_is_still_saved(
        self, db_session: Session, athlete_id: str, identity: str
    ) -> None:
        notifier = FakeNotifier()
        coaching = FakeCoaching()
        service = build_service(
            db_session,
            notifier=notifier,
            coaching=coaching,
            calendar=ExplodingCalendar(),
        )
        token = service.send_plan_for_approval(
            athlete_id=athlete_id,
            thread_id="thread-1",
            kind="weekly_plan",
            plan=PLAN,
        )

        outcome = service.handle_button(
            athlete_id=athlete_id,
            channel="telegram",
            external_id=identity,
            token=token,
            resolution="approve",
        )

        assert outcome.resolution == "approve"
        assert outcome.calendar is None
        assert "approuvée et enregistrée" in notifier.last_text
        assert coaching.calls == [("thread-1", True, None)]

    def test_a_failing_revision_tells_the_athlete(
        self, db_session: Session, athlete_id: str, identity: str
    ) -> None:
        notifier = FakeNotifier()
        coaching = ExplodingCoaching()
        service = build_service(db_session, notifier=notifier, coaching=coaching)
        token = service.send_plan_for_approval(
            athlete_id=athlete_id,
            thread_id="thread-1",
            kind="weekly_plan",
            plan=PLAN,
        )
        service.handle_button(
            athlete_id=athlete_id,
            channel="telegram",
            external_id=identity,
            token=token,
            resolution="revise",
        )

        outcome = service.handle_revision_text(
            athlete_id=athlete_id,
            channel="telegram",
            external_id=identity,
            token=token,
            text="less volume",
        )

        assert outcome.resolution == "error"
        assert "/plan" in notifier.last_text
