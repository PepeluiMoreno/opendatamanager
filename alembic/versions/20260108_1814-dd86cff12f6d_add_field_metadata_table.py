"""add_field_metadata_table

Revision ID: dd86cff12f6d
Revises: 53a2c499cfbf
Create Date: 2026-01-08 18:14:00.965004+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dd86cff12f6d'
down_revision: Union[str, Sequence[str], None] = '53a2c499cfbf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Crear tabla para metadatos de campos
    op.create_table(
        'field_metadata',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('table_name', sa.String(100), nullable=False),
        sa.Column('field_name', sa.String(100), nullable=False),
        sa.Column('label', sa.String(255), nullable=True),
        sa.Column('help_text', sa.Text(), nullable=True),
        sa.Column('placeholder', sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('table_name', 'field_name', name='uq_table_field'),
        schema='opendata'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('field_metadata', schema='opendata')
