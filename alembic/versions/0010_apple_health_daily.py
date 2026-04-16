"""Apple Health daily metrics table

Revision ID: 0010
Revises: 0009
Create Date: 2026-04-16 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "apple_health_daily",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("athlete_id", sa.String(), sa.ForeignKey("athletes.id"), nullable=False),
        sa.Column("record_date", sa.Date(), nullable=False),
        sa.Column("hrv_sdnn_avg", sa.Float(), nullable=True),
        sa.Column("sleep_hours", sa.Float(), nullable=True),
        sa.Column("rhr_bpm", sa.Float(), nullable=True),
        sa.Column("body_mass_kg", sa.Float(), nullable=True),
        sa.Column("active_energy_kcal", sa.Float(), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("athlete_id", "record_date"),
    )
    op.create_index("ix_apple_health_daily_athlete_date", "apple_health_daily", ["athlete_id", "record_date"])


def downgrade() -> None:
    op.drop_index("ix_apple_health_daily_athlete_date", table_name="apple_health_daily")
    op.drop_table("apple_health_daily")
