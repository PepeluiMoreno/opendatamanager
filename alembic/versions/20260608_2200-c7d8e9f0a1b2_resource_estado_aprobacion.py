"""resource.estado_aprobacion: gobernanza de propuestas (§11)

Revision ID: c7d8e9f0a1b2
Revises: e6f7a8b9c0d2
Create Date: 2026-06-08

Un recurso creado por una aplicación nace 'pendiente' y no se ejecuta hasta que
un admin lo aprueba; lo creado por humanos con permiso nace 'aprobado'. Default
'aprobado' para no afectar a lo existente. Idempotente (ADD COLUMN IF NOT
EXISTS).
"""
from typing import Union, Sequence

from alembic import op


revision: str = 'c7d8e9f0a1b2'
down_revision: Union[str, None] = 'e6f7a8b9c0d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE opendata.resource
            ADD COLUMN IF NOT EXISTS estado_aprobacion VARCHAR(20) NOT NULL DEFAULT 'aprobado'
    """)
    op.execute("""
        ALTER TABLE opendata.resource
            ADD COLUMN IF NOT EXISTS motivo_rechazo TEXT
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE opendata.resource DROP COLUMN IF EXISTS motivo_rechazo")
    op.execute("ALTER TABLE opendata.resource DROP COLUMN IF EXISTS estado_aprobacion")
