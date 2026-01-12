"""rename_fetcher_columns

Revision ID: fe129e483278
Revises: ac57bef5fc6b
Create Date: 2026-01-10 07:27:24.205416+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fe129e483278'
down_revision: Union[str, Sequence[str], None] = 'ac57bef5fc6b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rename column code to name in fetcher table
    op.alter_column('fetcher', 'code',
                    new_column_name='name',
                    schema='opendata')

    # Drop class_path column as it's no longer needed
    op.drop_column('fetcher', 'class_path', schema='opendata')


def downgrade() -> None:
    """Downgrade schema."""
    # Rename column name back to code in fetcher table
    op.alter_column('fetcher', 'name',
                    new_column_name='code',
                    schema='opendata')

    # Add back class_path column
    op.add_column('fetcher',
                  sa.Column('class_path', sa.String(255), nullable=True),
                  schema='opendata')
