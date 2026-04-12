"""Add energy pattern detection tables and columns

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-12 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add raw checkin fields to energy_snapshots for pattern analysis
    op.add_column(
        "energy_snapshots",
        sa.Column("legs_feeling", sa.String(), nullable=True),
    )
    op.add_column(
        "energy_snapshots",
        sa.Column("stress_level", sa.String(), nullable=True),
    )
    # Create dedicated head_coach_messages table
    op.create_table(
        "head_coach_messages",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("athlete_id", sa.String(), sa.ForeignKey("athletes.id"), nullable=False),
        sa.Column("pattern_type", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("head_coach_messages")
    op.drop_column("energy_snapshots", "stress_level")
    op.drop_column("energy_snapshots", "legs_feeling")
