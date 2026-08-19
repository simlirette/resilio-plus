"""Add single-use provider deep-link tokens.

Revision ID: 0015
Revises: 0014
Create Date: 2026-08-19 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "deep_link_tokens",
        sa.Column("token", sa.String(), nullable=False),
        sa.Column(
            "athlete_id",
            sa.String(),
            sa.ForeignKey("athletes.id"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("token"),
    )
    op.create_index(
        "ix_deep_link_tokens_athlete_id",
        "deep_link_tokens",
        ["athlete_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_deep_link_tokens_athlete_id", table_name="deep_link_tokens")
    op.drop_table("deep_link_tokens")
