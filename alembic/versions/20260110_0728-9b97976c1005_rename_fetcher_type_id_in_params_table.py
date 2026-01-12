"""rename_fetcher_id_in_params_table

Revision ID: 9b97976c1005
Revises: fe129e483278
Create Date: 2026-01-10 07:28:24.337746+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9b97976c1005'
down_revision: Union[str, Sequence[str], None] = 'fe129e483278'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rename column fetcher_id to fetcher_id in type_fetcher_params table
    op.alter_column('type_fetcher_params', 'fetcher_id',
                    new_column_name='fetcher_id',
                    schema='opendata')


def downgrade() -> None:
    """Downgrade schema."""
    # Rename column fetcher_id back to fetcher_id in type_fetcher_params table
    op.alter_column('type_fetcher_params', 'fetcher_id',
                    new_column_name='fetcher_id',
                    schema='opendata')
