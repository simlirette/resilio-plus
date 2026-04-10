"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # athletes table (no foreign keys — referenced by others)
    op.create_table(
        "athletes",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("sex", sa.String(), nullable=False),
        sa.Column("weight_kg", sa.Float(), nullable=False),
        sa.Column("height_cm", sa.Float(), nullable=False),
        sa.Column("primary_sport", sa.String(), nullable=False),
        sa.Column("target_race_date", sa.Date(), nullable=True),
        sa.Column("hours_per_week", sa.Float(), nullable=False),
        sa.Column("sleep_hours_typical", sa.Float(), nullable=True),
        sa.Column("stress_level", sa.Integer(), nullable=True),
        sa.Column("job_physical", sa.Boolean(), nullable=True),
        sa.Column("max_hr", sa.Integer(), nullable=True),
        sa.Column("resting_hr", sa.Integer(), nullable=True),
        sa.Column("ftp_watts", sa.Integer(), nullable=True),
        sa.Column("vdot", sa.Float(), nullable=True),
        sa.Column("css_per_100m", sa.Float(), nullable=True),
        sa.Column("sports_json", sa.Text(), nullable=False),
        sa.Column("goals_json", sa.Text(), nullable=False),
        sa.Column("available_days_json", sa.Text(), nullable=False),
        sa.Column("equipment_json", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # users table
    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("athlete_id", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    # training_plans table
    op.create_table(
        "training_plans",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("athlete_id", sa.String(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("phase", sa.String(), nullable=False),
        sa.Column("total_weekly_hours", sa.Float(), nullable=False),
        sa.Column("acwr", sa.Float(), nullable=False),
        sa.Column("weekly_slots_json", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # nutrition_plans table
    op.create_table(
        "nutrition_plans",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("athlete_id", sa.String(), nullable=False),
        sa.Column("weight_kg", sa.Float(), nullable=False),
        sa.Column("targets_json", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # weekly_reviews table
    op.create_table(
        "weekly_reviews",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("athlete_id", sa.String(), nullable=False),
        sa.Column("plan_id", sa.String(), nullable=True),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("week_number", sa.Integer(), nullable=False),
        sa.Column("planned_hours", sa.Float(), nullable=False),
        sa.Column("actual_hours", sa.Float(), nullable=True),
        sa.Column("acwr", sa.Float(), nullable=True),
        sa.Column("adjustment_applied", sa.Float(), nullable=True),
        sa.Column("readiness_score", sa.Float(), nullable=True),
        sa.Column("hrv_rmssd", sa.Float(), nullable=True),
        sa.Column("sleep_hours_avg", sa.Float(), nullable=True),
        sa.Column("athlete_comment", sa.Text(), nullable=True),
        sa.Column("results_json", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"]),
        sa.ForeignKeyConstraint(["plan_id"], ["training_plans.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # connector_credentials table
    op.create_table(
        "connector_credentials",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("athlete_id", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=True),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.Integer(), nullable=True),
        sa.Column("extra_json", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("athlete_id", "provider"),
    )

    # session_logs table
    op.create_table(
        "session_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("athlete_id", sa.String(), nullable=False),
        sa.Column("plan_id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False, index=True),
        sa.Column("actual_duration_min", sa.Integer(), nullable=True),
        sa.Column("skipped", sa.Boolean(), nullable=False),
        sa.Column("rpe", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("actual_data_json", sa.Text(), nullable=False),
        sa.Column(
            "logged_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"]),
        sa.ForeignKeyConstraint(["plan_id"], ["training_plans.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("athlete_id", "session_id"),
    )


def downgrade() -> None:
    op.drop_table("session_logs")
    op.drop_table("connector_credentials")
    op.drop_table("weekly_reviews")
    op.drop_table("nutrition_plans")
    op.drop_table("training_plans")
    op.drop_table("users")
    op.drop_table("athletes")
