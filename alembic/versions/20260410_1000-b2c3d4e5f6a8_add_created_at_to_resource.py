"""add created_at to resource

Revision ID: b2c3d4e5f6a8
Revises: a1b2c3d4e5f7
Create Date: 2026-04-10 10:00:00.000000
"""
from typing import Union, Sequence
from datetime import datetime
import sqlalchemy as sa
from alembic import op

revision: str = 'b2c3d4e5f6a8'
down_revision: Union[str, None] = 'a1b2c3d4e5f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'resource',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        schema='opendata'
    )
    # Backfill: set created_at = now() for existing rows
    op.execute("UPDATE opendata.resource SET created_at = NOW() WHERE created_at IS NULL")


def downgrade() -> None:
    op.drop_column('resource', 'created_at', schema='opendata')
