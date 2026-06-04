"""enrich type_fetcher_params with hint, help_md, visible_when

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-06-04

Esquema de params autodescriptivo: ayuda en tres niveles (hint inline, help_md
para modal) y visibilidad condicional (visible_when). `group` y `enum_values`
ya existían; enum_values pasa a admitir objetos {value,label,help} sin cambio DDL.
"""
from typing import Union, Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB


revision: str = 'f2a3b4c5d6e7'
down_revision: Union[str, None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('type_fetcher_params',
                  sa.Column('hint', sa.String(length=255), nullable=True),
                  schema='opendata')
    op.add_column('type_fetcher_params',
                  sa.Column('help_md', sa.Text(), nullable=True),
                  schema='opendata')
    op.add_column('type_fetcher_params',
                  sa.Column('visible_when', JSONB(), nullable=True),
                  schema='opendata')


def downgrade() -> None:
    op.drop_column('type_fetcher_params', 'visible_when', schema='opendata')
    op.drop_column('type_fetcher_params', 'help_md', schema='opendata')
    op.drop_column('type_fetcher_params', 'hint', schema='opendata')
