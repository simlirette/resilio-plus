"""CoordinatorService state machine columns on athletes

Adds journey_phase, overlay booleans, and persistent thread ID columns
required by CoordinatorService (Phase D - D1).

Revision ID: 0011
Revises: 0010
Create Date: 2026-04-26 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "athletes",
        sa.Column("journey_phase", sa.String(), nullable=False, server_default="signup"),
    )
    op.add_column(
        "athletes",
        sa.Column("recovery_takeover_active", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "athletes",
        sa.Column("onboarding_reentry_active", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "athletes",
        sa.Column("active_onboarding_thread_id", sa.String(), nullable=True),
    )
    op.add_column(
        "athletes",
        sa.Column("active_recovery_thread_id", sa.String(), nullable=True),
    )
    op.add_column(
        "athletes",
        sa.Column("active_followup_thread_id", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("athletes", "active_followup_thread_id")
    op.drop_column("athletes", "active_recovery_thread_id")
    op.drop_column("athletes", "active_onboarding_thread_id")
    op.drop_column("athletes", "onboarding_reentry_active")
    op.drop_column("athletes", "recovery_takeover_active")
    op.drop_column("athletes", "journey_phase")
