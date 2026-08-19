from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.db.models import AthleteModel, MessagingIdentityModel, PendingApprovalModel
from app.messaging.approvals import (
    AlreadyResolvedApprovalError,
    ApprovalOwnershipError,
    ExpiredApprovalError,
    UnknownApprovalError,
    arm_revision_latch,
    create_approval,
    encode_callback,
    parse_callback,
    pop_revision_latch,
    resolve,
)

FIXED_NOW = datetime(2031, 5, 4, 12, 0, tzinfo=timezone.utc)


def _clock(now: datetime = FIXED_NOW):
    return lambda: now


@pytest.fixture
def other_athlete_id(db_session: Session) -> str:
    other_id = "athlete-approvals-other"
    db_session.add(
        AthleteModel(
            id=other_id,
            name="Other Athlete",
            age=41,
            sex="M",
            weight_kg=78.0,
            height_cm=182.0,
            primary_sport="running",
            hours_per_week=6.0,
            sports_json='["running"]',
            goals_json="[]",
            available_days_json="[]",
            equipment_json="[]",
        )
    )
    db_session.commit()
    return other_id


class TestCreateApproval:
    def test_returns_16_char_token_and_persists_row(
        self, db_session: Session, athlete_id: str
    ) -> None:
        token = create_approval(
            db_session,
            athlete_id=athlete_id,
            thread_id="thread-1",
            kind="weekly_plan",
            clock=_clock(),
        )

        assert len(token) == 16
        row = db_session.get(PendingApprovalModel, token)
        assert row is not None
        assert row.athlete_id == athlete_id
        assert row.thread_id == "thread-1"
        assert row.kind == "weekly_plan"
        assert row.resolved_at is None
        assert row.resolution is None

    def test_default_ttl_is_seven_days(
        self, db_session: Session, athlete_id: str
    ) -> None:
        token = create_approval(
            db_session,
            athlete_id=athlete_id,
            thread_id="thread-1",
            kind="weekly_plan",
            clock=_clock(),
        )
        row = db_session.get(PendingApprovalModel, token)
        assert row is not None
        expires = row.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        assert expires == FIXED_NOW + timedelta(days=7)

    def test_payload_is_stored_as_json(
        self, db_session: Session, athlete_id: str
    ) -> None:
        token = create_approval(
            db_session,
            athlete_id=athlete_id,
            thread_id="thread-1",
            kind="weekly_plan",
            payload={"week_start": "2031-05-05"},
            clock=_clock(),
        )
        row = db_session.get(PendingApprovalModel, token)
        assert row is not None
        assert row.payload_json == '{"week_start": "2031-05-05"}'

    def test_tokens_are_unique(self, db_session: Session, athlete_id: str) -> None:
        tokens = {
            create_approval(
                db_session,
                athlete_id=athlete_id,
                thread_id="thread-1",
                kind="weekly_plan",
                clock=_clock(),
            )
            for _ in range(25)
        }
        assert len(tokens) == 25


class TestResolve:
    def test_approve_marks_resolved_and_returns_snapshot(
        self, db_session: Session, athlete_id: str
    ) -> None:
        token = create_approval(
            db_session,
            athlete_id=athlete_id,
            thread_id="thread-42",
            kind="weekly_plan",
            payload={"plan": "x"},
            clock=_clock(),
        )

        approval = resolve(
            db_session,
            token=token,
            resolution="approve",
            athlete_id=athlete_id,
            clock=_clock(),
        )

        assert approval.token == token
        assert approval.thread_id == "thread-42"
        assert approval.kind == "weekly_plan"
        assert approval.resolution == "approve"
        assert approval.payload == {"plan": "x"}

        row = db_session.get(PendingApprovalModel, token)
        assert row is not None
        assert row.resolution == "approve"
        assert row.resolved_at is not None

    @pytest.mark.parametrize("resolution", ["approve", "revise", "reject"])
    def test_every_resolution_is_accepted(
        self, db_session: Session, athlete_id: str, resolution: str
    ) -> None:
        token = create_approval(
            db_session,
            athlete_id=athlete_id,
            thread_id="thread-1",
            kind="weekly_plan",
            clock=_clock(),
        )
        approval = resolve(
            db_session,
            token=token,
            resolution=resolution,  # type: ignore[arg-type]
            athlete_id=athlete_id,
            clock=_clock(),
        )
        assert approval.resolution == resolution

    def test_unknown_token_raises(self, db_session: Session, athlete_id: str) -> None:
        with pytest.raises(UnknownApprovalError):
            resolve(
                db_session,
                token="does-not-exist",
                resolution="approve",
                athlete_id=athlete_id,
                clock=_clock(),
            )

    def test_expired_token_raises(self, db_session: Session, athlete_id: str) -> None:
        token = create_approval(
            db_session,
            athlete_id=athlete_id,
            thread_id="thread-1",
            kind="weekly_plan",
            clock=_clock(),
        )
        with pytest.raises(ExpiredApprovalError):
            resolve(
                db_session,
                token=token,
                resolution="approve",
                athlete_id=athlete_id,
                clock=_clock(FIXED_NOW + timedelta(days=7, seconds=1)),
            )

    def test_replayed_token_raises(self, db_session: Session, athlete_id: str) -> None:
        token = create_approval(
            db_session,
            athlete_id=athlete_id,
            thread_id="thread-1",
            kind="weekly_plan",
            clock=_clock(),
        )
        resolve(
            db_session,
            token=token,
            resolution="approve",
            athlete_id=athlete_id,
            clock=_clock(),
        )
        with pytest.raises(AlreadyResolvedApprovalError):
            resolve(
                db_session,
                token=token,
                resolution="approve",
                athlete_id=athlete_id,
                clock=_clock(),
            )

    def test_cross_athlete_token_raises_ownership_error(
        self, db_session: Session, athlete_id: str, other_athlete_id: str
    ) -> None:
        token = create_approval(
            db_session,
            athlete_id=athlete_id,
            thread_id="thread-1",
            kind="weekly_plan",
            clock=_clock(),
        )
        with pytest.raises(ApprovalOwnershipError):
            resolve(
                db_session,
                token=token,
                resolution="approve",
                athlete_id=other_athlete_id,
                clock=_clock(),
            )
        row = db_session.get(PendingApprovalModel, token)
        assert row is not None
        assert row.resolved_at is None

    def test_expiry_is_checked_after_ownership(
        self, db_session: Session, athlete_id: str, other_athlete_id: str
    ) -> None:
        token = create_approval(
            db_session,
            athlete_id=athlete_id,
            thread_id="thread-1",
            kind="weekly_plan",
            clock=_clock(),
        )
        with pytest.raises(ApprovalOwnershipError):
            resolve(
                db_session,
                token=token,
                resolution="approve",
                athlete_id=other_athlete_id,
                clock=_clock(FIXED_NOW + timedelta(days=30)),
            )


class TestCallbackCodec:
    @pytest.mark.parametrize("resolution", ["approve", "revise", "reject"])
    def test_round_trip(self, resolution: str) -> None:
        data = encode_callback("abcdefghijklmnop", resolution)  # type: ignore[arg-type]
        assert parse_callback(data) == ("abcdefghijklmnop", resolution)

    def test_callback_data_fits_telegram_64_byte_limit(self) -> None:
        data = encode_callback("abcdefghijklmnop", "approve")
        assert 1 <= len(data.encode("utf-8")) <= 64

    @pytest.mark.parametrize(
        "data",
        ["", "garbage", "ap:", "ap:token", "ap:token:z", "xx:token:a", "ap:tok:a:extra"],
    )
    def test_invalid_callback_data_returns_none(self, data: str) -> None:
        assert parse_callback(data) is None


class TestRevisionLatch:
    def _identity(self, db_session: Session, athlete_id: str) -> None:
        db_session.add(
            MessagingIdentityModel(
                id="identity-1",
                athlete_id=athlete_id,
                channel="telegram",
                external_id="4242",
            )
        )
        db_session.commit()

    def test_arm_then_pop_returns_token_once(
        self, db_session: Session, athlete_id: str
    ) -> None:
        self._identity(db_session, athlete_id)

        arm_revision_latch(
            db_session, channel="telegram", external_id="4242", token="tok-1"
        )

        assert (
            pop_revision_latch(db_session, channel="telegram", external_id="4242")
            == "tok-1"
        )
        assert (
            pop_revision_latch(db_session, channel="telegram", external_id="4242")
            is None
        )

    def test_pop_without_arm_returns_none(
        self, db_session: Session, athlete_id: str
    ) -> None:
        self._identity(db_session, athlete_id)
        assert (
            pop_revision_latch(db_session, channel="telegram", external_id="4242")
            is None
        )

    def test_pop_for_unknown_identity_returns_none(self, db_session: Session) -> None:
        assert (
            pop_revision_latch(db_session, channel="telegram", external_id="nope")
            is None
        )
