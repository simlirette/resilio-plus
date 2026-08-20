"""Record where readiness came from, and let onboarding survive a restart.

Two columns, both nullable, both about telling "we know nothing" apart from a
value that happens to look neutral.

`athlete_state_snapshots.readiness_source` -- `compute_readiness` returns a
*modifier* in [0.5, 1.5] where 1.0 means "no adjustment". That is correct for
the agents. But the snapshot stored 1.0 whether the signals were neutral or
simply absent, and `HeadCoachView` presented that number to the conversational
coach as a readiness *score*, so an athlete with no HRV device read as
perfectly fresh. The column says whether anything was actually measured.

`athletes.onboarding_state_json` -- onboarding thread state lived only in the
`_thread_states` module dict, so restarting the process mid-conversation sent
the athlete back to block 1.

Revision ID: 0018
Revises: 0017
Create Date: 2026-08-20 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0018"
down_revision: Union[str, None] = "0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "athlete_state_snapshots",
        sa.Column("readiness_source", sa.String(), nullable=True),
    )
    op.add_column(
        "athletes",
        sa.Column("onboarding_state_json", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("athletes", "onboarding_state_json")
    op.drop_column("athlete_state_snapshots", "readiness_source")
