"""add cascade delete to fetcher params

Revision ID: 20260110_1430
Revises: 9b97976c1005
Create Date: 2026-01-10 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260110_1430'
down_revision = '80e7fc9d32dd'
branch_labels = None
depends_on = None


def upgrade():
    # Drop the existing foreign key constraint
    op.drop_constraint('type_fetcher_params_fetcher_id_fkey', 'type_fetcher_params', schema='opendata', type_='foreignkey')

    # Add the foreign key constraint with CASCADE delete
    op.create_foreign_key(
        'type_fetcher_params_fetcher_id_fkey',
        'type_fetcher_params', 'fetcher',
        ['fetcher_id'], ['id'],
        source_schema='opendata',
        referent_schema='opendata',
        ondelete='CASCADE'
    )


def downgrade():
    # Drop the CASCADE constraint
    op.drop_constraint('type_fetcher_params_fetcher_id_fkey', 'type_fetcher_params', schema='opendata', type_='foreignkey')

    # Restore the original foreign key without CASCADE
    op.create_foreign_key(
        'type_fetcher_params_fetcher_id_fkey',
        'type_fetcher_params', 'fetcher',
        ['fetcher_id'], ['id'],
        source_schema='opendata',
        referent_schema='opendata'
    )
