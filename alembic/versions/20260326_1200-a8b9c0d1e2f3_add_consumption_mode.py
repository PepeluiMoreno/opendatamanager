"""add consumption_mode to application

Revision ID: a8b9c0d1e2f3
Revises: f6a7b8c9d0e1
Create Date: 2026-03-26 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'a8b9c0d1e2f3'
down_revision = 'f6a7b8c9d0e1'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'application',
        sa.Column(
            'consumption_mode',
            sa.String(20),
            nullable=False,
            server_default='webhook',
        ),
        schema='opendata',
    )


def downgrade():
    op.drop_column('application', 'consumption_mode', schema='opendata')
