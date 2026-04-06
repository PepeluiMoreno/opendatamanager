"""Add provincia and municipio to publisher for local/provincial orgs

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-03-29 14:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = 'e4f5a6b7c8d9'
down_revision = 'd3e4f5a6b7c8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('publisher', sa.Column('provincia', sa.String(100), nullable=True), schema='opendata')
    op.add_column('publisher', sa.Column('municipio', sa.String(200), nullable=True), schema='opendata')


def downgrade():
    op.drop_column('publisher', 'provincia', schema='opendata')
    op.drop_column('publisher', 'municipio', schema='opendata')
