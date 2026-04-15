"""Background jobs: job_runs + athlete_state_snapshots tables

Revision ID: 0009
Revises: 0008
Create Date: 2026-04-14 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "job_runs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("athlete_id", sa.String(), sa.ForeignKey("athletes.id"), nullable=True),
        sa.Column("job_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_job_runs_type_created", "job_runs", ["job_type", "created_at"])

    op.create_table(
        "athlete_state_snapshots",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("athlete_id", sa.String(), sa.ForeignKey("athletes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("readiness", sa.Float(), nullable=False),
        sa.Column("strain_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("athlete_id", "snapshot_date", name="uq_snapshot_athlete_date"),
    )


def downgrade() -> None:
    op.drop_table("athlete_state_snapshots")
    op.drop_index("ix_job_runs_type_created", table_name="job_runs")
    op.drop_table("job_runs")
