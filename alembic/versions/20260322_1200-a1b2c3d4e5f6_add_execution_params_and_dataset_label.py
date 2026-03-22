"""add_execution_params_and_dataset_label

Revision ID: a1b2c3d4e5f6
Revises: 3fde65ef49fa
Create Date: 2026-03-22 12:00:00.000000+00:00

Añade:
- opendata.resource_execution.execution_params (JSONB) — parámetros runtime que
  sobreescriben/amplían los ResourceParam estáticos de una ejecución concreta.
- opendata.dataset.label (VARCHAR 100) — etiqueta legible para el dataset
  (ej: "2023", "Q1-2024").
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '3fde65ef49fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'resource_execution',
        sa.Column('execution_params', JSONB, nullable=True),
        schema='opendata',
    )
    op.add_column(
        'dataset',
        sa.Column('label', sa.String(100), nullable=True),
        schema='opendata',
    )


def downgrade() -> None:
    op.drop_column('resource_execution', 'execution_params', schema='opendata')
    op.drop_column('dataset', 'label', schema='opendata')
