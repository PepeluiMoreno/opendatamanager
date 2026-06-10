"""purge one-off de principales de aplicacion ckan-jerez (limpieza solicitada)

Revision ID: purge_ckan_princ_1
Revises: f0a1b2c3d4e5
Create Date: 2026-06-10

Borra TODOS los principales (Usuario tipo='aplicacion') con username que contiene
'ckan-jerez'. service_token.usuario_id es ON DELETE CASCADE; los FK de auditoria
son SET NULL. Una sola vez (marcador opendata._purge_markers). EXCEPTION ... NULL
para no abortar el arranque. Id de revision descriptivo a proposito (el esquema
hex rotado ya usaba b2c3d4e5f6a7 → versionado_recursos).
"""
from typing import Union, Sequence
from alembic import op

revision: str = 'purge_ckan_princ_1'
down_revision: Union[str, None] = 'f0a1b2c3d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS opendata._purge_markers (
            k  text PRIMARY KEY,
            ts timestamptz DEFAULT now()
        )
    """)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM opendata._purge_markers
                           WHERE k = 'ckan_principals_cleanup_1') THEN
                DELETE FROM opendata.usuario
                 WHERE tipo = 'aplicacion'
                   AND username LIKE '%ckan-jerez%';
                INSERT INTO opendata._purge_markers(k) VALUES ('ckan_principals_cleanup_1');
            END IF;
        EXCEPTION WHEN OTHERS THEN
            NULL;
        END $$;
    """)


def downgrade() -> None:
    pass
