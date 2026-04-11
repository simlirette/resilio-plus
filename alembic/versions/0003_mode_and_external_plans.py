# alembic/versions/0003_mode_and_external_plans.py
"""Mode system + external plans

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-11 00:00:00.000000

Adds:
- athletes.coaching_mode          VARCHAR NOT NULL DEFAULT 'full'
- training_plans.status           VARCHAR NOT NULL DEFAULT 'active'
- external_plans table
- external_sessions table
- session_logs.external_session_id VARCHAR FK (nullable)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # external_plans (must be created BEFORE external_sessions and before session_logs FK)
    op.create_table(
        "external_plans",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("athlete_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # external_sessions (must be created BEFORE session_logs FK references it)
    op.create_table(
        "external_sessions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("plan_id", sa.String(), nullable=False),
        sa.Column("athlete_id", sa.String(), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("sport", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("duration_min", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="planned"),
        sa.ForeignKeyConstraint(["plan_id"], ["external_plans.id"]),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # athletes — add coaching_mode
    op.add_column(
        "athletes",
        sa.Column("coaching_mode", sa.String(), nullable=False, server_default="full"),
    )

    # training_plans — add status
    op.add_column(
        "training_plans",
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
    )

    # session_logs — add external_session_id FK (nullable, references external_sessions)
    op.add_column(
        "session_logs",
        sa.Column("external_session_id", sa.String(), nullable=True),
    )
    op.create_foreign_key(
        "fk_session_logs_external_session",
        "session_logs",
        "external_sessions",
        ["external_session_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_session_logs_external_session", "session_logs", type_="foreignkey")
    op.drop_column("session_logs", "external_session_id")
    op.drop_column("training_plans", "status")
    op.drop_column("athletes", "coaching_mode")
    op.drop_table("external_sessions")
    op.drop_table("external_plans")
