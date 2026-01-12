"""rename_fetcher_type_table_to_fetcher

Revision ID: ac57bef5fc6b
Revises: a2755baacd0b
Create Date: 2026-01-10 07:26:00.774105+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ac57bef5fc6b'
down_revision: Union[str, Sequence[str], None] = 'a2755baacd0b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rename table fetcher_type to fetcher
    op.rename_table('fetcher_type', 'fetcher', schema='opendata')


def downgrade() -> None:
    """Downgrade schema."""
    # Rename table fetcher back to fetcher_type
    op.rename_table('fetcher', 'fetcher_type', schema='opendata')
