"""avisos por email: usuario.notificar_email + tabla evento

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-04

Idempotente.
"""
from typing import Union, Sequence

from alembic import op


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE opendata.usuario ADD COLUMN IF NOT EXISTS notificar_email BOOLEAN NOT NULL DEFAULT FALSE")
    op.execute("""
        CREATE TABLE IF NOT EXISTS opendata.evento (
            id UUID PRIMARY KEY,
            tipo VARCHAR(40) NOT NULL,
            recurso_id UUID REFERENCES opendata.resource(id) ON DELETE SET NULL,
            titulo VARCHAR(300) NOT NULL,
            detalle JSONB,
            created_at TIMESTAMP DEFAULT now(),
            notificado BOOLEAN NOT NULL DEFAULT FALSE
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_evento_notificado ON opendata.evento (notificado, created_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS opendata.evento CASCADE")
    op.execute("ALTER TABLE opendata.usuario DROP COLUMN IF EXISTS notificar_email")
