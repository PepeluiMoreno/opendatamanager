"""add_class_path_to_fetcher

Revision ID: 53a2c499cfbf
Revises: b2c3d4e5f6a7
Create Date: 2026-01-08 17:42:27.077476+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '53a2c499cfbf'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add class_path column to fetcher table
    op.add_column('fetcher',
                  sa.Column('class_path', sa.String(255), nullable=False, server_default=''),
                  schema='opendata')
    # Remove server default after column creation
    op.alter_column('fetcher', 'class_path', server_default=None, schema='opendata')


def downgrade() -> None:
    """Downgrade schema."""
    # Drop class_path column
    op.drop_column('fetcher', 'class_path', schema='opendata')
