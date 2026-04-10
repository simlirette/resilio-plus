"""V3 AthleteState — energy_snapshots, hormonal_profiles, allostatic_entries

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-10 00:00:00.000000

Ajoute trois tables pour les nouveaux modèles V3 :
- energy_snapshots        : EnergySnapshot par athlète (historique)
- hormonal_profiles       : HormonalProfile par athlète (1:1)
- allostatic_entries      : AllostaticEntry quotidien par athlète (28 j)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # energy_snapshots
    op.create_table(
        "energy_snapshots",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("athlete_id", sa.String(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("allostatic_score", sa.Float(), nullable=False),
        sa.Column("cognitive_load", sa.Float(), nullable=False),
        sa.Column("energy_availability", sa.Float(), nullable=False),
        sa.Column("cycle_phase", sa.String(), nullable=True),
        sa.Column("sleep_quality", sa.Float(), nullable=False),
        sa.Column("recommended_intensity_cap", sa.Float(), nullable=False),
        sa.Column("veto_triggered", sa.Boolean(), nullable=False),
        sa.Column("veto_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # hormonal_profiles (1:1 avec athletes)
    op.create_table(
        "hormonal_profiles",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("athlete_id", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("cycle_length_days", sa.Integer(), nullable=False),
        sa.Column("current_cycle_day", sa.Integer(), nullable=True),
        sa.Column("current_phase", sa.String(), nullable=True),
        sa.Column("last_period_start", sa.Date(), nullable=True),
        sa.Column("tracking_source", sa.String(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("athlete_id"),
    )

    # allostatic_entries
    op.create_table(
        "allostatic_entries",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("athlete_id", sa.String(), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("allostatic_score", sa.Float(), nullable=False),
        sa.Column("components_json", sa.Text(), nullable=False),
        sa.Column("intensity_cap_applied", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("athlete_id", "entry_date"),
    )


def downgrade() -> None:
    op.drop_table("allostatic_entries")
    op.drop_table("hormonal_profiles")
    op.drop_table("energy_snapshots")
