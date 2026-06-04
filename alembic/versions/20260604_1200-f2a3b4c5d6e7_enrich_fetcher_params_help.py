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
    # Idempotente: el entrypoint re-aplica todas las migraciones en cada arranque
    # (borra alembic_version), así que debe tolerar columnas ya existentes.
    op.execute("ALTER TABLE opendata.type_fetcher_params ADD COLUMN IF NOT EXISTS hint VARCHAR(255)")
    op.execute("ALTER TABLE opendata.type_fetcher_params ADD COLUMN IF NOT EXISTS help_md TEXT")
    op.execute("ALTER TABLE opendata.type_fetcher_params ADD COLUMN IF NOT EXISTS visible_when JSONB")


def downgrade() -> None:
    op.execute("ALTER TABLE opendata.type_fetcher_params DROP COLUMN IF EXISTS visible_when")
    op.execute("ALTER TABLE opendata.type_fetcher_params DROP COLUMN IF EXISTS help_md")
    op.execute("ALTER TABLE opendata.type_fetcher_params DROP COLUMN IF EXISTS hint")
