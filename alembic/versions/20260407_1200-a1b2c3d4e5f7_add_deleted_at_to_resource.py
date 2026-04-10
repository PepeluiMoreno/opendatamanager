"""add deleted_at to resource

Revision ID: a1b2c3d4e5f7
Revises: f1a2b3c4d5e6
Create Date: 2026-04-07 12:00:00.000000
"""
from typing import Union, Sequence
import sqlalchemy as sa
from alembic import op

revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'resource',
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        schema='opendata'
    )


def downgrade() -> None:
    op.drop_column('resource', 'deleted_at', schema='opendata')
