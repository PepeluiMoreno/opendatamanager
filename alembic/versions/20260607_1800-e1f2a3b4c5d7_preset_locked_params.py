"""Candado selectivo de la variante: fetcher_preset.locked_params.

Decisión §6 (opción c): la variante puede marcar parámetros como INVIOLABLES —
sus valores no son pisables por el recurso (la factory ignora el override y el
UI no ofrece sobrescribir). Los no marcados siguen siendo defaults pisables.

IMPORTANTE: el entrypoint borra opendata.alembic_version en cada arranque,
así que TODAS las migraciones se re-ejecutan en cada boot y deben ser
idempotentes (patrón de la casa: SQL crudo con IF NOT EXISTS).

Revision ID: e1f2a3b4c5d7
Revises: c9d0e1f2a3b4
Create Date: 2026-06-07
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'e1f2a3b4c5d7'
down_revision: Union[str, None] = 'c9d0e1f2a3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE opendata.fetcher_preset "
               "ADD COLUMN IF NOT EXISTS locked_params JSONB NOT NULL DEFAULT '[]'::jsonb")


def downgrade() -> None:
    op.execute("ALTER TABLE opendata.fetcher_preset DROP COLUMN IF EXISTS locked_params")
