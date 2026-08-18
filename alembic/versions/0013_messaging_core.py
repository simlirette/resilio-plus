"""Add messaging identities, link codes, and outbound messages.

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-18 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "messaging_identities",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "athlete_id",
            sa.String(),
            sa.ForeignKey("athletes.id"),
            nullable=False,
        ),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column(
            "verified_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "channel",
            "external_id",
            name="uq_messaging_identities_channel_external_id",
        ),
    )
    op.create_index(
        "ix_messaging_identities_athlete_id",
        "messaging_identities",
        ["athlete_id"],
        unique=False,
    )

    op.create_table(
        "messaging_link_codes",
        sa.Column("code", sa.String(), nullable=False),
        sa.Column(
            "athlete_id",
            sa.String(),
            sa.ForeignKey("athletes.id"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("code"),
    )

    op.create_table(
        "outbound_messages",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "athlete_id",
            sa.String(),
            sa.ForeignKey("athletes.id"),
            nullable=False,
        ),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("provider_message_id", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("outbound_messages")
    op.drop_table("messaging_link_codes")
    op.drop_index(
        "ix_messaging_identities_athlete_id",
        table_name="messaging_identities",
    )
    op.drop_table("messaging_identities")
