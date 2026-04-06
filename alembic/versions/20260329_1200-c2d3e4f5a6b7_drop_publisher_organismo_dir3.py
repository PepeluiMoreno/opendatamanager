"""Drop organismo and dir3 from publisher (redundant fields)

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-03-29 12:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = 'c2d3e4f5a6b7'
down_revision = 'b1c2d3e4f5a6'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('publisher', 'organismo', schema='opendata')
    op.drop_column('publisher', 'dir3', schema='opendata')


def downgrade():
    op.add_column('publisher', sa.Column('organismo', sa.String(200), nullable=True), schema='opendata')
    op.add_column('publisher', sa.Column('dir3', sa.String(20), nullable=True), schema='opendata')
