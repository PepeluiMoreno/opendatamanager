"""rename_source_to_resource

Revision ID: ef2383fe082a
Revises: 135ef1d2a543
Create Date: 2026-01-09 08:50:19.087305+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ef2383fe082a'
down_revision: Union[str, Sequence[str], None] = '135ef1d2a543'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename source table to resource and source_param to resource_param."""
    # Rename source table to resource
    op.rename_table('source', 'resource', schema='opendata')

    # Rename source_param table to resource_param
    op.rename_table('source_param', 'resource_param', schema='opendata')

    # Rename source_id column to resource_id in resource_param table
    op.alter_column('resource_param', 'source_id', new_column_name='resource_id', schema='opendata')

    # Update foreign key constraint
    # First drop the old constraint
    op.drop_constraint('source_param_source_id_fkey', 'resource_param', type_='foreignkey', schema='opendata')

    # Create new constraint with updated names
    op.create_foreign_key(
        'resource_param_resource_id_fkey',
        'resource_param', 'resource',
        ['resource_id'], ['id'],
        source_schema='opendata', referent_schema='opendata',
        ondelete='CASCADE'
    )


def downgrade() -> None:
    """Revert resource table back to source and resource_param back to source_param."""
    # Drop new foreign key constraint
    op.drop_constraint('resource_param_resource_id_fkey', 'resource_param', type_='foreignkey', schema='opendata')

    # Create old constraint
    op.create_foreign_key(
        'source_param_source_id_fkey',
        'resource_param', 'resource',
        ['resource_id'], ['id'],
        source_schema='opendata', referent_schema='opendata',
        ondelete='CASCADE'
    )

    # Rename resource_id column back to source_id
    op.alter_column('resource_param', 'resource_id', new_column_name='source_id', schema='opendata')

    # Rename resource_param table back to source_param
    op.rename_table('resource_param', 'source_param', schema='opendata')

    # Rename resource table back to source
    op.rename_table('resource', 'source', schema='opendata')
