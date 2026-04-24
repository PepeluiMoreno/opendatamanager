"""add created_at to fetcher

Revision ID: a1b2c3d4e5f8
Revises: 0001_initial
Create Date: 2026-04-24
"""
from typing import Union, Sequence
import sqlalchemy as sa
from alembic import op

revision: str = 'a1b2c3d4e5f8'
down_revision: Union[str, None] = '0001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'fetcher',
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        schema='opendata',
    )
    # Backfill existing rows with current timestamp
    op.execute("UPDATE opendata.fetcher SET created_at = NOW() WHERE created_at IS NULL")


def downgrade() -> None:
    op.drop_column('fetcher', 'created_at', schema='opendata')
