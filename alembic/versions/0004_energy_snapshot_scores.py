"""Add objective_score + subjective_score to energy_snapshots

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-11 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "energy_snapshots",
        sa.Column("objective_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "energy_snapshots",
        sa.Column("subjective_score", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("energy_snapshots", "subjective_score")
    op.drop_column("energy_snapshots", "objective_score")
