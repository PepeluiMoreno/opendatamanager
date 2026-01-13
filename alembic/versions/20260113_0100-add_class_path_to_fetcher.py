"""add class_path to fetcher

Revision ID: add_class_path_fetcher
Revises: 20260111_0100
Create Date: 2026-01-13 01:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_class_path_fetcher'
down_revision: Union[str, Sequence[str], None] = '20260111_0100'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add class_path column to fetcher table
    op.add_column(
        'fetcher',
        sa.Column('class_path', sa.String(255), nullable=True),
        schema='opendata'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove class_path column from fetcher table
    op.drop_column('fetcher', 'class_path', schema='opendata')
