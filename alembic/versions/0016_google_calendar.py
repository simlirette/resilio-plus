"""Add Google Calendar credentials, event mapping, and athlete scheduling prefs.

Revision ID: 0016
Revises: 0015
Create Date: 2026-08-19 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0016"
down_revision: Union[str, None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "google_calendar_credentials",
        sa.Column(
            "athlete_id",
            sa.String(),
            sa.ForeignKey("athletes.id"),
            nullable=False,
        ),
        sa.Column("refresh_token_enc", sa.Text(), nullable=True),
        sa.Column("access_token_enc", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.Integer(), nullable=True),
        sa.Column("calendar_id", sa.String(), nullable=True),
        sa.Column("scope", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("athlete_id"),
    )

    op.create_table(
        "calendar_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "athlete_id",
            sa.String(),
            sa.ForeignKey("athletes.id"),
            nullable=False,
        ),
        sa.Column("slot_id", sa.String(), nullable=False),
        sa.Column("slot_date", sa.Date(), nullable=False),
        sa.Column("gcal_event_id", sa.String(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "athlete_id", "slot_id", name="uq_calendar_events_athlete_slot"
        ),
    )
    op.create_index(
        "ix_calendar_events_athlete_id",
        "calendar_events",
        ["athlete_id"],
        unique=False,
    )

    op.add_column(
        "athletes",
        sa.Column(
            "timezone",
            sa.String(),
            nullable=False,
            server_default="America/Montreal",
        ),
    )
    op.add_column(
        "athletes",
        sa.Column(
            "preferred_session_hour_json",
            sa.Text(),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    op.drop_column("athletes", "preferred_session_hour_json")
    op.drop_column("athletes", "timezone")
    op.drop_index("ix_calendar_events_athlete_id", table_name="calendar_events")
    op.drop_table("calendar_events")
    op.drop_table("google_calendar_credentials")
