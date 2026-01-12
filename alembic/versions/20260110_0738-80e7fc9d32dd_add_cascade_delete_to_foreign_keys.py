"""add_cascade_delete_to_foreign_keys

Revision ID: 80e7fc9d32dd
Revises: 9b97976c1005
Create Date: 2026-01-10 07:38:31.712724+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '80e7fc9d32dd'
down_revision: Union[str, Sequence[str], None] = '9b97976c1005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add CASCADE delete to resource_execution.resource_id
    op.drop_constraint('resource_execution_resource_id_fkey', 'resource_execution', schema='opendata', type_='foreignkey')
    op.create_foreign_key(
        'resource_execution_resource_id_fkey',
        'resource_execution', 'resource',
        ['resource_id'], ['id'],
        source_schema='opendata', referent_schema='opendata',
        ondelete='CASCADE'
    )

    # Add CASCADE delete to dataset.resource_id
    op.drop_constraint('dataset_resource_id_fkey', 'dataset', schema='opendata', type_='foreignkey')
    op.create_foreign_key(
        'dataset_resource_id_fkey',
        'dataset', 'resource',
        ['resource_id'], ['id'],
        source_schema='opendata', referent_schema='opendata',
        ondelete='CASCADE'
    )

    # Add CASCADE delete to dataset.execution_id
    op.drop_constraint('dataset_execution_id_fkey', 'dataset', schema='opendata', type_='foreignkey')
    op.create_foreign_key(
        'dataset_execution_id_fkey',
        'dataset', 'resource_execution',
        ['execution_id'], ['id'],
        source_schema='opendata', referent_schema='opendata',
        ondelete='CASCADE'
    )

    # Add CASCADE delete to dataset_subscription.resource_id
    op.drop_constraint('dataset_subscription_resource_id_fkey', 'dataset_subscription', schema='opendata', type_='foreignkey')
    op.create_foreign_key(
        'dataset_subscription_resource_id_fkey',
        'dataset_subscription', 'resource',
        ['resource_id'], ['id'],
        source_schema='opendata', referent_schema='opendata',
        ondelete='CASCADE'
    )

    # Add CASCADE delete to dataset_subscription.application_id
    op.drop_constraint('dataset_subscription_application_id_fkey', 'dataset_subscription', schema='opendata', type_='foreignkey')
    op.create_foreign_key(
        'dataset_subscription_application_id_fkey',
        'dataset_subscription', 'application',
        ['application_id'], ['id'],
        source_schema='opendata', referent_schema='opendata',
        ondelete='CASCADE'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove CASCADE from resource_execution.resource_id
    op.drop_constraint('resource_execution_resource_id_fkey', 'resource_execution', schema='opendata', type_='foreignkey')
    op.create_foreign_key(
        'resource_execution_resource_id_fkey',
        'resource_execution', 'resource',
        ['resource_id'], ['id'],
        source_schema='opendata', referent_schema='opendata'
    )

    # Remove CASCADE from dataset.resource_id
    op.drop_constraint('dataset_resource_id_fkey', 'dataset', schema='opendata', type_='foreignkey')
    op.create_foreign_key(
        'dataset_resource_id_fkey',
        'dataset', 'resource',
        ['resource_id'], ['id'],
        source_schema='opendata', referent_schema='opendata'
    )

    # Remove CASCADE from dataset.execution_id
    op.drop_constraint('dataset_execution_id_fkey', 'dataset', schema='opendata', type_='foreignkey')
    op.create_foreign_key(
        'dataset_execution_id_fkey',
        'dataset', 'resource_execution',
        ['execution_id'], ['id'],
        source_schema='opendata', referent_schema='opendata'
    )

    # Remove CASCADE from dataset_subscription.resource_id
    op.drop_constraint('dataset_subscription_resource_id_fkey', 'dataset_subscription', schema='opendata', type_='foreignkey')
    op.create_foreign_key(
        'dataset_subscription_resource_id_fkey',
        'dataset_subscription', 'resource',
        ['resource_id'], ['id'],
        source_schema='opendata', referent_schema='opendata'
    )

    # Remove CASCADE from dataset_subscription.application_id
    op.drop_constraint('dataset_subscription_application_id_fkey', 'dataset_subscription', schema='opendata', type_='foreignkey')
    op.create_foreign_key(
        'dataset_subscription_application_id_fkey',
        'dataset_subscription', 'application',
        ['application_id'], ['id'],
        source_schema='opendata', referent_schema='opendata'
    )
