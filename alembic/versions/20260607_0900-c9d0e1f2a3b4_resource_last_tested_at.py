"""Última prueba del recurso: resource.last_tested_at.

Sello de la última vez que el recurso se probó desde el UI (preview), con
éxito o sin él. Se muestra junto al Status en el listado de recursos.

IMPORTANTE: el entrypoint borra opendata.alembic_version en cada arranque,
así que TODAS las migraciones se re-ejecutan en cada boot y deben ser
idempotentes (patrón de la casa: SQL crudo con IF NOT EXISTS).

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-06-06
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'c9d0e1f2a3b4'
down_revision: Union[str, None] = 'b8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE opendata.resource ADD COLUMN IF NOT EXISTS last_tested_at TIMESTAMP")


def downgrade() -> None:
    op.execute("ALTER TABLE opendata.resource DROP COLUMN IF EXISTS last_tested_at")
