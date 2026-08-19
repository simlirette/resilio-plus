"""Add pending approvals and the identity revision latch.

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-19 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pending_approvals",
        sa.Column("token", sa.String(), nullable=False),
        sa.Column(
            "athlete_id",
            sa.String(),
            sa.ForeignKey("athletes.id"),
            nullable=False,
        ),
        sa.Column("thread_id", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("token"),
    )
    op.create_index(
        "ix_pending_approvals_athlete_id",
        "pending_approvals",
        ["athlete_id"],
        unique=False,
    )
    op.add_column(
        "messaging_identities",
        sa.Column("awaiting_revision_for_token", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("messaging_identities", "awaiting_revision_for_token")
    op.drop_index(
        "ix_pending_approvals_athlete_id",
        table_name="pending_approvals",
    )
    op.drop_table("pending_approvals")
