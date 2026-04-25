"""add deleted_at to dataset

Revision ID: d7e8f9a0b1c2
Revises: 0001_initial
Create Date: 2026-04-25
"""
from typing import Union, Sequence

from alembic import op


revision: str = 'd7e8f9a0b1c2'
down_revision: Union[str, None] = '0001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Idempotent: works on fresh DBs (column already added by 0001_initial)
    # and on existing prod DBs (adds the column if missing)
    op.execute("ALTER TABLE opendata.dataset ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP")


def downgrade() -> None:
    op.execute("ALTER TABLE opendata.dataset DROP COLUMN IF EXISTS deleted_at")
