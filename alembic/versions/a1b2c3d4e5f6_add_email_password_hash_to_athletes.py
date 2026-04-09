"""add email and password_hash to athletes

Revision ID: a1b2c3d4e5f6
Revises: 37168fe9feab
Create Date: 2026-04-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '37168fe9feab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add email and password_hash columns to athletes table."""
    # Add with server_default so existing rows are not null
    op.add_column(
        'athletes',
        sa.Column('email', sa.String(length=255), nullable=False, server_default='')
    )
    op.add_column(
        'athletes',
        sa.Column('password_hash', sa.String(length=255), nullable=False, server_default='')
    )
    # Create unique index (serves as both index and unique constraint)
    op.create_index(op.f('ix_athletes_email'), 'athletes', ['email'], unique=True)
    # Remove the server defaults — new rows must supply explicit values
    op.alter_column('athletes', 'email', server_default=None)
    op.alter_column('athletes', 'password_hash', server_default=None)


def downgrade() -> None:
    """Remove email and password_hash columns from athletes table."""
    op.drop_index(op.f('ix_athletes_email'), table_name='athletes')
    op.drop_column('athletes', 'password_hash')
    op.drop_column('athletes', 'email')
