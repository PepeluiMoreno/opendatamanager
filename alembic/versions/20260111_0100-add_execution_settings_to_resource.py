"""add_execution_settings_to_resource

Revision ID: 20260111_0100
Revises: fa8e9be79aba
Create Date: 2026-01-11 01:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260111_0100'
down_revision: Union[str, Sequence[str], None] = 'fa8e9be79aba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add execution settings fields to resource table."""
    # Add execution configuration fields
    op.add_column('resource',
        sa.Column('max_workers', sa.Integer(), nullable=True, server_default='1'),
        schema='opendata'
    )
    op.add_column('resource',
        sa.Column('timeout_seconds', sa.Integer(), nullable=True, server_default='300'),
        schema='opendata'
    )
    op.add_column('resource',
        sa.Column('retry_attempts', sa.Integer(), nullable=True, server_default='0'),
        schema='opendata'
    )
    op.add_column('resource',
        sa.Column('retry_delay_seconds', sa.Integer(), nullable=True, server_default='60'),
        schema='opendata'
    )
    op.add_column('resource',
        sa.Column('execution_priority', sa.Integer(), nullable=True, server_default='0'),
        schema='opendata'
    )

    # Update existing rows to have the default values
    op.execute("UPDATE opendata.resource SET max_workers = 1 WHERE max_workers IS NULL")
    op.execute("UPDATE opendata.resource SET timeout_seconds = 300 WHERE timeout_seconds IS NULL")
    op.execute("UPDATE opendata.resource SET retry_attempts = 0 WHERE retry_attempts IS NULL")
    op.execute("UPDATE opendata.resource SET retry_delay_seconds = 60 WHERE retry_delay_seconds IS NULL")
    op.execute("UPDATE opendata.resource SET execution_priority = 0 WHERE execution_priority IS NULL")

    # Make columns not nullable
    op.alter_column('resource', 'max_workers', nullable=False, schema='opendata')
    op.alter_column('resource', 'timeout_seconds', nullable=False, schema='opendata')
    op.alter_column('resource', 'retry_attempts', nullable=False, schema='opendata')
    op.alter_column('resource', 'retry_delay_seconds', nullable=False, schema='opendata')
    op.alter_column('resource', 'execution_priority', nullable=False, schema='opendata')


def downgrade() -> None:
    """Remove execution settings fields from resource table."""
    op.drop_column('resource', 'execution_priority', schema='opendata')
    op.drop_column('resource', 'retry_delay_seconds', schema='opendata')
    op.drop_column('resource', 'retry_attempts', schema='opendata')
    op.drop_column('resource', 'timeout_seconds', schema='opendata')
    op.drop_column('resource', 'max_workers', schema='opendata')
