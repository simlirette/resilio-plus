"""chat_messages table for Phase D chat_turn graph

Adds the chat_messages table storing user + assistant message pairs
from the chat_turn graph (Phase D - D4).

Revision ID: 0012
Revises: 0011
Create Date: 2026-04-26 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("athlete_id", sa.String(), sa.ForeignKey("athletes.id"), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("intent_decision", sa.String(), nullable=True),
        sa.Column("specialists_consulted", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_messages_athlete_id", "chat_messages", ["athlete_id"])


def downgrade() -> None:
    op.drop_index("ix_chat_messages_athlete_id", table_name="chat_messages")
    op.drop_table("chat_messages")
