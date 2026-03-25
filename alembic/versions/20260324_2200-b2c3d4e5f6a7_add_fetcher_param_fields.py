"""add enum_values, description to type_fetcher_params; is_external to resource_param

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-24 22:00:00.000000
"""
from typing import Union, Sequence
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'type_fetcher_params',
        sa.Column('enum_values', postgresql.JSONB, nullable=True),
        schema='opendata',
    )
    op.add_column(
        'type_fetcher_params',
        sa.Column('description', sa.Text, nullable=True),
        schema='opendata',
    )
    op.add_column(
        'resource_param',
        sa.Column('is_external', sa.Boolean, nullable=False, server_default='false'),
        schema='opendata',
    )


def downgrade() -> None:
    op.drop_column('type_fetcher_params', 'enum_values', schema='opendata')
    op.drop_column('type_fetcher_params', 'description', schema='opendata')
    op.drop_column('resource_param', 'is_external', schema='opendata')
