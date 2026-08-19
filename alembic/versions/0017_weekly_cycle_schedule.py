"""Add the athlete's weekly coaching-cycle schedule.

Revision ID: 0017
Revises: 0016
Create Date: 2026-08-19 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0017"
down_revision: Union[str, None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "athletes",
        sa.Column(
            "weekly_cycle_day",
            sa.Integer(),
            nullable=False,
            server_default="6",
        ),
    )
    op.add_column(
        "athletes",
        sa.Column(
            "weekly_cycle_hour",
            sa.Integer(),
            nullable=False,
            server_default="18",
        ),
    )


def downgrade() -> None:
    op.drop_column("athletes", "weekly_cycle_hour")
    op.drop_column("athletes", "weekly_cycle_day")
