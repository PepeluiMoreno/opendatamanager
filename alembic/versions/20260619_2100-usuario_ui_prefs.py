"""usuario.ui_prefs — parámetros de UI por usuario (JSONB)

Revision ID: usuario_ui_prefs
Revises: res_collection_nm_tree
Create Date: 2026-06-19

Preferencias de interfaz por usuario (p. ej. "no volver a pedir confirmación al
arrastrar y soltar en el rail de colecciones"). JSON libre key→valor, distinto de
la configuración global (AppConfig). Idempotente (ADD COLUMN IF NOT EXISTS).
"""
from typing import Union, Sequence

from alembic import op


revision: str = 'usuario_ui_prefs'
down_revision: Union[str, None] = 'res_collection_nm_tree'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE opendata.usuario "
        "ADD COLUMN IF NOT EXISTS ui_prefs JSONB NOT NULL DEFAULT '{}'::jsonb"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE opendata.usuario DROP COLUMN IF EXISTS ui_prefs")
