"""purge one-off de principales de aplicación ckan-jerez (limpieza solicitada)

Revision ID: b2c3d4e5f6a7
Revises: f0a1b2c3d4e5
Create Date: 2026-06-10

Borra TODOS los principales (Usuario tipo='aplicacion') cuyo username contiene
'ckan-jerez' (app-ckan-jerez, app-ckan-jerez-10/11/12, …). El FK
service_token.usuario_id es ON DELETE CASCADE → sus tokens caen en cascada; los
FK de auditoría son SET NULL. Se ejecuta UNA SOLA VEZ (marcador persistente
opendata._purge_markers); el consumidor re-hace el alta limpia con el flujo de
token autogenerado. Envuelto en EXCEPTION ... NULL para no abortar el arranque.
"""
from typing import Union, Sequence

from alembic import op


revision: str = 'b2c3d4e5f6a7'
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
