from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import Engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def test_messaging_tables_are_registered_and_created(sqlite_engine: Engine) -> None:
    from app.db.database import Base

    expected = {"messaging_identities", "messaging_link_codes", "outbound_messages"}

    assert expected <= set(Base.metadata.tables)
    assert expected <= set(inspect(sqlite_engine).get_table_names())


def test_messaging_identity_external_address_is_unique(
    db_session: Session, athlete_id: str
) -> None:
    from app.db.models import MessagingIdentityModel

    db_session.add(
        MessagingIdentityModel(
            id="identity-1",
            athlete_id=athlete_id,
            channel="whatsapp",
            external_id="+15555550123",
        )
    )
    db_session.commit()

    identity = db_session.get(MessagingIdentityModel, "identity-1")
    assert identity is not None
    assert identity.verified_at is not None
    assert identity.created_at is not None

    db_session.add(
        MessagingIdentityModel(
            id="identity-2",
            athlete_id=athlete_id,
            channel="whatsapp",
            external_id="+15555550123",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_messaging_link_code_uses_code_as_primary_key_and_allows_unconsumed(
    sqlite_engine: Engine, db_session: Session, athlete_id: str
) -> None:
    from app.db.models import MessagingLinkCodeModel

    table = inspect(sqlite_engine)
    assert table.get_pk_constraint("messaging_link_codes")["constrained_columns"] == ["code"]
    columns = {column["name"]: column for column in table.get_columns("messaging_link_codes")}
    assert columns["consumed_at"]["nullable"] is True

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
    db_session.add(
        MessagingLinkCodeModel(
            code="LINK-123",
            athlete_id=athlete_id,
            expires_at=expires_at,
        )
    )
    db_session.commit()

    link_code = db_session.get(MessagingLinkCodeModel, "LINK-123")
    assert link_code is not None
    assert link_code.consumed_at is None


def test_outbound_message_persists(db_session: Session, athlete_id: str) -> None:
    from app.db.models import OutboundMessageModel

    db_session.add(
        OutboundMessageModel(
            id="outbound-1",
            athlete_id=athlete_id,
            channel="whatsapp",
            external_id="+15555550123",
            provider_message_id="provider-message-1",
            body="Your recovery session starts at 18:00.",
            kind="session_reminder",
        )
    )
    db_session.commit()

    message = db_session.get(OutboundMessageModel, "outbound-1")
    assert message is not None
    assert message.athlete_id == athlete_id
    assert message.channel == "whatsapp"
    assert message.external_id == "+15555550123"
    assert message.provider_message_id == "provider-message-1"
    assert message.body == "Your recovery session starts at 18:00."
    assert message.kind == "session_reminder"
    assert message.created_at is not None


def test_outbound_message_enforces_athlete_foreign_key(db_session: Session) -> None:
    from app.db.models import OutboundMessageModel

    db_session.add(
        OutboundMessageModel(
            id="outbound-orphan",
            athlete_id="missing-athlete",
            channel="whatsapp",
            external_id="+15555550999",
            provider_message_id="provider-message-orphan",
            body="This message cannot be stored.",
            kind="session_reminder",
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()
