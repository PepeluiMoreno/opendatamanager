"""add_target_table_to_source

Revision ID: 3e06ae5bdf50
Revises: dd86cff12f6d
Create Date: 2026-01-08 23:27:07.190893+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3e06ae5bdf50'
down_revision: Union[str, Sequence[str], None] = 'dd86cff12f6d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add target_table column to source table."""
    op.add_column('source', sa.Column('target_table', sa.String(100), nullable=True), schema='opendata')

    # Update existing rows: use project value as initial target_table
    op.execute("UPDATE opendata.source SET target_table = project")

    # Make it not nullable after populating
    op.alter_column('source', 'target_table', nullable=False, schema='opendata')


def downgrade() -> None:
    """Remove target_table column from source table."""
    op.drop_column('source', 'target_table', schema='opendata')
