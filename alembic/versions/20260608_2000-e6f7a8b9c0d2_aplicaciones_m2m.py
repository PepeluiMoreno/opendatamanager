"""aplicaciones M2M (§12): usuario.tipo, solicitud_ingreso, service_token

Revision ID: e6f7a8b9c0d2
Revises: d5e6f7a8b0c1
Create Date: 2026-06-08

Idempotente (ADD COLUMN / CREATE ... IF NOT EXISTS): el entrypoint borra
alembic_version y re-aplica todas las migraciones en cada arranque.
"""
from typing import Union, Sequence

from alembic import op


revision: str = 'e6f7a8b9c0d2'
down_revision: Union[str, None] = 'd5e6f7a8b0c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Discriminador de principal en usuario.
    op.execute("""
        ALTER TABLE opendata.usuario
            ADD COLUMN IF NOT EXISTS tipo VARCHAR(20) NOT NULL DEFAULT 'humano'
    """)

    # Solicitud de ingreso (self-service); no crea nada operativo por sí sola.
    op.execute("""
        CREATE TABLE IF NOT EXISTS opendata.solicitud_ingreso (
            id UUID PRIMARY KEY,
            nombre VARCHAR(120) NOT NULL,
            contacto VARCHAR(255),
            proposito TEXT,
            ambito_solicitado JSONB,
            estado VARCHAR(20) NOT NULL DEFAULT 'pendiente',
            motivo TEXT,
            resuelta_at TIMESTAMP,
            usuario_id UUID REFERENCES opendata.usuario(id) ON DELETE SET NULL,
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now(),
            created_by_id UUID REFERENCES opendata.usuario(id) ON DELETE SET NULL,
            updated_by_id UUID REFERENCES opendata.usuario(id) ON DELETE SET NULL
        )
    """)

    # Credenciales Bearer de las aplicaciones (en reposo solo el hash).
    op.execute("""
        CREATE TABLE IF NOT EXISTS opendata.service_token (
            id UUID PRIMARY KEY,
            usuario_id UUID NOT NULL REFERENCES opendata.usuario(id) ON DELETE CASCADE,
            label VARCHAR(120),
            prefix VARCHAR(24) NOT NULL,
            token_hash VARCHAR(64) NOT NULL UNIQUE,
            last_used_at TIMESTAMP,
            expires_at TIMESTAMP,
            revoked_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now(),
            created_by_id UUID REFERENCES opendata.usuario(id) ON DELETE SET NULL,
            updated_by_id UUID REFERENCES opendata.usuario(id) ON DELETE SET NULL
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_service_token_prefix ON opendata.service_token (prefix)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_service_token_token_hash ON opendata.service_token (token_hash)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS opendata.service_token")
    op.execute("DROP TABLE IF EXISTS opendata.solicitud_ingreso")
    op.execute("ALTER TABLE opendata.usuario DROP COLUMN IF EXISTS tipo")
