"""rbac: usuarios, roles, funcionalidades y sesiones

Revision ID: a1b2c3d4e5f6
Revises: f2a3b4c5d6e7
Create Date: 2026-06-04

Idempotente (CREATE ... IF NOT EXISTS): el entrypoint re-aplica todas las
migraciones en cada arranque.
"""
from typing import Union, Sequence

from alembic import op


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f2a3b4c5d6e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS opendata.usuario (
            id UUID PRIMARY KEY,
            username VARCHAR(80) NOT NULL UNIQUE,
            email VARCHAR(255) UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT now(),
            last_login_at TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS opendata.rol (
            id UUID PRIMARY KEY,
            code VARCHAR(50) NOT NULL UNIQUE,
            nombre VARCHAR(120) NOT NULL,
            descripcion TEXT,
            is_system BOOLEAN NOT NULL DEFAULT FALSE
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS opendata.funcionalidad (
            id UUID PRIMARY KEY,
            code VARCHAR(80) NOT NULL UNIQUE,
            nombre VARCHAR(160) NOT NULL,
            descripcion TEXT,
            modulo VARCHAR(80),
            es_lectura BOOLEAN NOT NULL DEFAULT FALSE
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS opendata.usuario_rol (
            usuario_id UUID NOT NULL REFERENCES opendata.usuario(id) ON DELETE CASCADE,
            rol_id UUID NOT NULL REFERENCES opendata.rol(id) ON DELETE CASCADE,
            PRIMARY KEY (usuario_id, rol_id)
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS opendata.rol_funcionalidad (
            rol_id UUID NOT NULL REFERENCES opendata.rol(id) ON DELETE CASCADE,
            funcionalidad_id UUID NOT NULL REFERENCES opendata.funcionalidad(id) ON DELETE CASCADE,
            PRIMARY KEY (rol_id, funcionalidad_id)
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS opendata.sesion (
            id UUID PRIMARY KEY,
            usuario_id UUID NOT NULL REFERENCES opendata.usuario(id) ON DELETE CASCADE,
            token_hash VARCHAR(64) NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT now(),
            expires_at TIMESTAMP NOT NULL,
            last_seen_at TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_sesion_token_hash ON opendata.sesion (token_hash)")


def downgrade() -> None:
    for t in ("sesion", "rol_funcionalidad", "usuario_rol", "funcionalidad", "rol", "usuario"):
        op.execute(f"DROP TABLE IF EXISTS opendata.{t} CASCADE")
