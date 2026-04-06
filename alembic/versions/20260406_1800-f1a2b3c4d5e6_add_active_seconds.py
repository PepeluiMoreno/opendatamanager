"""add active_seconds to resource_execution

Revision ID: f1a2b3c4d5e6
Revises: e4f5a6b7c8d9
Create Date: 2026-04-06 18:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = 'f1a2b3c4d5e6'
down_revision = 'e4f5a6b7c8d9'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'resource_execution',
        sa.Column('active_seconds', sa.Integer(), nullable=True, server_default='0'),
        schema='opendata',
    )


def downgrade():
    op.drop_column('resource_execution', 'active_seconds', schema='opendata')
