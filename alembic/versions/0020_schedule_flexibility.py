"""Record whether the athlete's schedule is fixed or flexible.

Step 1 of the goal document asks for "the schedule of the training plan, how
many sessions, which days, hour of the day, flexible or fixed".

`preferred_session_hour_json` already existed and is read by the calendar sync
to place events at the right time -- but nothing ever wrote it, so every event
landed at the default hour. Flexibility had nowhere to live at all, and it is
what decides whether the coach may move a session when the week goes wrong.

Revision ID: 0020
Revises: 0019
Create Date: 2026-08-21 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0020"
down_revision: Union[str, None] = "0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "athletes",
        sa.Column("schedule_flexibility", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("athletes", "schedule_flexibility")
