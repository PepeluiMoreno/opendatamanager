"""rename_fetcher_id_to_fetcher_id

Revision ID: a2755baacd0b
Revises: 09d82c6d1816
Create Date: 2026-01-10 07:23:21.283667+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2755baacd0b'
down_revision: Union[str, Sequence[str], None] = '09d82c6d1816'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rename column fetcher_id to fetcher_id in resource table
    op.alter_column('resource', 'fetcher_id',
                    new_column_name='fetcher_id',
                    schema='opendata')


def downgrade() -> None:
    """Downgrade schema."""
    # Rename column fetcher_id back to fetcher_id in resource table
    op.alter_column('resource', 'fetcher_id',
                    new_column_name='fetcher_id',
                    schema='opendata')
