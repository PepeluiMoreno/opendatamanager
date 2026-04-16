"""add group to fetcher_params

Revision ID: c3d4e5f6a7b9
Revises: b2c3d4e5f6a8
Create Date: 2026-04-11 12:00:00.000000
"""
from typing import Union, Sequence
import sqlalchemy as sa
from alembic import op

revision: str = 'c3d4e5f6a7b9'
down_revision: Union[str, None] = 'b2c3d4e5f6a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'type_fetcher_params',
        sa.Column('group', sa.String(100), nullable=True),
        schema='opendata',
    )


def downgrade() -> None:
    op.drop_column('type_fetcher_params', 'group', schema='opendata')
