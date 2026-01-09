"""rename_project_to_publisher

Revision ID: 135ef1d2a543
Revises: 3e06ae5bdf50
Create Date: 2026-01-08 23:34:15.490796+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '135ef1d2a543'
down_revision: Union[str, Sequence[str], None] = '3e06ae5bdf50'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename project column to publisher in source table."""
    op.alter_column('source', 'project', new_column_name='publisher', schema='opendata')


def downgrade() -> None:
    """Rename publisher column back to project in source table."""
    op.alter_column('source', 'publisher', new_column_name='project', schema='opendata')
