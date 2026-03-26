"""add pause_requested to resource_execution

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-03-25 18:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'f6a7b8c9d0e1'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'resource_execution',
        sa.Column('pause_requested', sa.Boolean(), nullable=False, server_default='false'),
        schema='opendata',
    )


def downgrade():
    op.drop_column('resource_execution', 'pause_requested', schema='opendata')
