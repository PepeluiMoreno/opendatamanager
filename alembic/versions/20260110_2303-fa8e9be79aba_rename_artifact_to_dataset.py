"""rename_dataset_to_dataset

Revision ID: fa8e9be79aba
Revises: 991235a5f13e
Create Date: 2026-01-10 23:03:23.280957+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fa8e9be79aba'
down_revision: Union[str, Sequence[str], None] = '991235a5f13e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rename dataset table to dataset
    op.rename_table('dataset', 'dataset', schema='opendata')

    # Rename dataset_subscription table to dataset_subscription
    op.rename_table('dataset_subscription', 'dataset_subscription', schema='opendata')

    # Rename dataset_id column in application_notification to dataset_id
    op.alter_column('application_notification', 'dataset_id',
                    new_column_name='dataset_id', schema='opendata')


def downgrade() -> None:
    """Downgrade schema."""
    # Revert dataset_id column back to dataset_id
    op.alter_column('application_notification', 'dataset_id',
                    new_column_name='dataset_id', schema='opendata')

    # Revert dataset_subscription table back to dataset_subscription
    op.rename_table('dataset_subscription', 'dataset_subscription', schema='opendata')

    # Revert dataset table back to dataset
    op.rename_table('dataset', 'dataset', schema='opendata')
