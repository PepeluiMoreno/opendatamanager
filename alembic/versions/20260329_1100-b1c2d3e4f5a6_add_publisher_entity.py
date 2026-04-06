"""add publisher entity

Revision ID: b1c2d3e4f5a6
Revises: a8b9c0d1e2f3
Create Date: 2026-03-29 11:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'b1c2d3e4f5a6'
down_revision = 'a8b9c0d1e2f3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'publisher',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('nombre', sa.String(200), nullable=False),
        sa.Column('acronimo', sa.String(30), nullable=True),
        sa.Column('nivel', sa.String(30), nullable=False),
        sa.Column('pais', sa.String(100), nullable=False, server_default='España'),
        sa.Column('comunidad_autonoma', sa.String(100), nullable=True),
        sa.Column('organismo', sa.String(200), nullable=True),
        sa.Column('portal_url', sa.String(500), nullable=True),
        sa.Column('dir3', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        schema='opendata',
    )

    # Ampliar publisher text de 50 → 200 y hacerlo nullable (ahora es fallback)
    op.alter_column('resource', 'publisher',
        existing_type=sa.String(50),
        type_=sa.String(200),
        nullable=True,
        schema='opendata',
    )

    op.add_column('resource',
        sa.Column('publisher_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('opendata.publisher.id'), nullable=True),
        schema='opendata',
    )


def downgrade():
    op.drop_column('resource', 'publisher_id', schema='opendata')
    op.alter_column('resource', 'publisher',
        existing_type=sa.String(200),
        type_=sa.String(50),
        nullable=False,
        schema='opendata',
    )
    op.drop_table('publisher', schema='opendata')
