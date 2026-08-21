"""Store how many sessions per sport the athlete wants, separately from hours.

The athlete said "je vise 3 sorties" and the extractor wrote
`hours_per_week = 3.0`, which capped the generated week at 1h30. Sessions and
hours are different quantities and there was only one column to put them in,
so the wrong one won.

Revision ID: 0019
Revises: 0018
Create Date: 2026-08-21 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0019"
down_revision: Union[str, None] = "0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "athletes",
        sa.Column("sessions_per_week_json", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("athletes", "sessions_per_week_json")
