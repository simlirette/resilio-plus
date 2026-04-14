"""Strava V2: encrypted token columns + strava_activities table

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-14 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- connector_credentials: rename plaintext → encrypted + add last_sync_at ---
    with op.batch_alter_table("connector_credentials") as batch_op:
        batch_op.alter_column("access_token", new_column_name="access_token_enc")
        batch_op.alter_column("refresh_token", new_column_name="refresh_token_enc")
        batch_op.add_column(
            sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True)
        )

    # --- strava_activities table ---
    op.create_table(
        "strava_activities",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("athlete_id", sa.String(), sa.ForeignKey("athletes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("strava_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("sport_type", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_s", sa.Integer(), nullable=False),
        sa.Column("distance_m", sa.Float(), nullable=True),
        sa.Column("elevation_m", sa.Float(), nullable=True),
        sa.Column("avg_hr", sa.Integer(), nullable=True),
        sa.Column("max_hr", sa.Integer(), nullable=True),
        sa.Column("avg_watts", sa.Float(), nullable=True),
        sa.Column("perceived_exertion", sa.Float(), nullable=True),
        sa.Column("raw_json", sa.Text(), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_table("strava_activities")
    with op.batch_alter_table("connector_credentials") as batch_op:
        batch_op.drop_column("last_sync_at")
        batch_op.alter_column("access_token_enc", new_column_name="access_token")
        batch_op.alter_column("refresh_token_enc", new_column_name="refresh_token")
