"""solicitud_ingreso.callback_url / callback_secret (§12 push de resolución)

Revision ID: e9f0a1b2c3d4
Revises: d8e9f0a1b2c3
Create Date: 2026-06-09

La solicitud puede llevar un callback (URL + secreto) al que ODM empuja por
webhook la resolución (aprobada/rechazada + motivo), porque al solicitar la
aplicación aún no está materializada (no tiene webhook registrado). Idempotente
(ADD COLUMN IF NOT EXISTS); no afecta a lo existente.
"""
from typing import Union, Sequence

from alembic import op


revision: str = 'e9f0a1b2c3d4'
down_revision: Union[str, None] = 'd8e9f0a1b2c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE opendata.solicitud_ingreso
            ADD COLUMN IF NOT EXISTS callback_url VARCHAR(500)
    """)
    op.execute("""
        ALTER TABLE opendata.solicitud_ingreso
            ADD COLUMN IF NOT EXISTS callback_secret VARCHAR(200)
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE opendata.solicitud_ingreso DROP COLUMN IF EXISTS callback_secret")
    op.execute("ALTER TABLE opendata.solicitud_ingreso DROP COLUMN IF EXISTS callback_url")
