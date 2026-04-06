"""Add email and telefono to publisher

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-03-29 13:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = 'd3e4f5a6b7c8'
down_revision = 'c2d3e4f5a6b7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('publisher', sa.Column('email', sa.String(200), nullable=True), schema='opendata')
    op.add_column('publisher', sa.Column('telefono', sa.String(50), nullable=True), schema='opendata')


def downgrade():
    op.drop_column('publisher', 'email', schema='opendata')
    op.drop_column('publisher', 'telefono', schema='opendata')
