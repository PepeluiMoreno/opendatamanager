"""add source_param and application tables

Revision ID: a1b2c3d4e5f6
Revises: 65c4949bf4df
Create Date: 2026-01-08 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '65c4949bf4df'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Crear tabla source_param
    op.create_table(
        'source_param',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['source_id'], ['opendata.source.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='opendata'
    )

    # Crear tabla application
    op.create_table(
        'application',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('models_path', sa.String(length=255), nullable=False),
        sa.Column('subscribed_projects', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        schema='opendata'
    )

    # Eliminar columna params de source si existe
    try:
        op.drop_column('source', 'params', schema='opendata')
    except Exception:
        pass


def downgrade() -> None:
    # Agregar de vuelta columna params a source
    op.add_column('source', sa.Column('params', postgresql.JSONB(astext_type=sa.Text()), nullable=True), schema='opendata')

    # Eliminar tablas
    op.drop_table('application', schema='opendata')
    op.drop_table('source_param', schema='opendata')
