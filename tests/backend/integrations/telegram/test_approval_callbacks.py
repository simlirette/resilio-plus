from __future__ import annotations

import uuid
from typing import Any

import pytest
from app.db.models import AthleteModel, MessagingIdentityModel
from app.integrations.telegram.runtime import build_approval_callback_handler
from app.messaging.approvals import ApprovalOwnershipError, encode_callback
from sqlalchemy.orm import Session


class RecordingApprovalService:
    def __init__(self, *, raises: Exception | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self._raises = raises

    def handle_button(
        self,
        *,
        athlete_id: str,
        channel: str,
        external_id: str,
        token: str,
        resolution: str,
    ) -> object:
        self.calls.append(
            {
                "athlete_id": athlete_id,
                "channel": channel,
                "external_id": external_id,
                "token": token,
                "resolution": resolution,
            }
        )
        if self._raises is not None:
            raise self._raises
        return object()


@pytest.fixture
def linked_chat(db_session: Session) -> str:
    db_session.add(
        AthleteModel(
            id="athlete-cb",
            name="Callback Athlete",
            age=35,
            sex="F",
            weight_kg=60.0,
            height_cm=168.0,
            primary_sport="running",
            hours_per_week=7.0,
            sports_json='["running"]',
            goals_json="[]",
            available_days_json="[]",
            equipment_json="[]",
        )
    )
    db_session.add(
        MessagingIdentityModel(
            id=str(uuid.uuid4()),
            athlete_id="athlete-cb",
            channel="telegram",
            external_id="777",
        )
    )
    db_session.commit()
    return "777"


def _callback(data: str, chat_id: object = 777) -> dict[str, Any]:
    return {
        "id": "cb-1",
        "data": data,
        "message": {"chat": {"id": chat_id, "type": "private"}},
    }


def test_resolves_athlete_from_the_chat_and_forwards_the_decision(
    db_session: Session, linked_chat: str
) -> None:
    service = RecordingApprovalService()
    handler = build_approval_callback_handler(lambda _db: service)

    handler(_callback(encode_callback("abcdefghijklmnop", "approve")), db_session)

    assert service.calls == [
        {
            "athlete_id": "athlete-cb",
            "channel": "telegram",
            "external_id": "777",
            "token": "abcdefghijklmnop",
            "resolution": "approve",
        }
    ]


@pytest.mark.parametrize("resolution", ["approve", "revise", "reject"])
def test_every_button_reaches_the_service(
    db_session: Session, linked_chat: str, resolution: str
) -> None:
    service = RecordingApprovalService()
    handler = build_approval_callback_handler(lambda _db: service)

    handler(
        _callback(encode_callback("abcdefghijklmnop", resolution)),  # type: ignore[arg-type]
        db_session,
    )

    assert service.calls[0]["resolution"] == resolution


@pytest.mark.parametrize("data", ["", "not-an-approval", "ap:tok:z"])
def test_non_approval_callback_data_is_ignored(
    db_session: Session, linked_chat: str, data: str
) -> None:
    service = RecordingApprovalService()
    handler = build_approval_callback_handler(lambda _db: service)

    handler(_callback(data), db_session)

    assert service.calls == []


def test_unlinked_chat_is_ignored(db_session: Session) -> None:
    service = RecordingApprovalService()
    handler = build_approval_callback_handler(lambda _db: service)

    handler(_callback(encode_callback("abcdefghijklmnop", "approve")), db_session)

    assert service.calls == []


def test_missing_chat_is_ignored(db_session: Session, linked_chat: str) -> None:
    service = RecordingApprovalService()
    handler = build_approval_callback_handler(lambda _db: service)

    handler({"id": "cb-1", "data": encode_callback("tok", "approve")}, db_session)

    assert service.calls == []


def test_boolean_chat_id_is_rejected(db_session: Session, linked_chat: str) -> None:
    service = RecordingApprovalService()
    handler = build_approval_callback_handler(lambda _db: service)

    handler(
        _callback(encode_callback("abcdefghijklmnop", "approve"), chat_id=True),
        db_session,
    )

    assert service.calls == []


def test_cross_athlete_denial_does_not_escape_the_handler(
    db_session: Session, linked_chat: str
) -> None:
    service = RecordingApprovalService(raises=ApprovalOwnershipError())
    handler = build_approval_callback_handler(lambda _db: service)

    handler(_callback(encode_callback("abcdefghijklmnop", "approve")), db_session)

    assert len(service.calls) == 1


class ExplodingGateway:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def resolve_athlete(self, channel: str, external_id: str) -> str | None:
        return "athlete-cb"

    def link_identity(self, channel: str, external_id: str, link_code: str) -> str:
        raise AssertionError("known senders must not enter the link flow")

    def handle_inbound(self, channel: str, external_id: str, text: str) -> None:
        self.calls.append(text)
        raise RuntimeError("graph unavailable")


class RecordingChannel:
    name = "telegram"

    def __init__(self) -> None:
        self.sent: list[str] = []

    def send(self, external_id: str, text: str) -> str:
        self.sent.append(text)
        return "m1"

    def send_typing(self, external_id: str) -> None:
        return None

    def answer_callback_query(self, callback_query_id: str) -> None:
        return None

    def format(self, text: str) -> str:
        return text


def test_a_failing_inbound_answers_the_athlete_and_does_not_escape() -> None:
    from contextlib import nullcontext

    from app.integrations.telegram.runtime import TelegramUpdateProcessor

    channel = RecordingChannel()
    gateway = ExplodingGateway()
    processor = TelegramUpdateProcessor(
        channel=channel,  # type: ignore[arg-type]
        session_factory=lambda: nullcontext(object()),  # type: ignore[arg-type]
        gateway_factory=lambda _db: gateway,
    )

    processor.process_update(
        {
            "message": {
                "chat": {"id": 4242, "type": "private"},
                "text": "how did last week go?",
            }
        }
    )

    assert gateway.calls == ["how did last week go?"]
    assert "could not answer" in channel.sent[-1]
