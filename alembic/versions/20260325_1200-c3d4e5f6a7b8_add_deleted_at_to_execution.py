"""add deleted_at to resource_execution

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-25 12:00:00.000000
"""
from typing import Union, Sequence
import sqlalchemy as sa
from alembic import op

revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'resource_execution',
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        schema='opendata'
    )


def downgrade() -> None:
    op.drop_column('resource_execution', 'deleted_at', schema='opendata')
