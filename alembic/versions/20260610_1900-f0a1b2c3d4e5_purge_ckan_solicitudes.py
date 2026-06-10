"""purge one-off de solicitudes de alta de ckan-jerez (limpieza solicitada)

Revision ID: f0a1b2c3d4e5
Revises: e9f0a1b2c3d4
Create Date: 2026-06-10

Borra TODAS las solicitudes de ingreso con nombre 'ckan-jerez' (las lanzadas
desde la consola del consumidor). Se ejecuta UNA SOLA VEZ gracias a un marcador
persistente (opendata._purge_markers): el entrypoint re-corre todas las
migraciones en cada arranque, pero tras la primera el marcador impide repetir el
DELETE, de modo que NO afecta a futuras solicitudes legítimas de ckan-jerez.
Envuelto en EXCEPTION ... NULL para no abortar nunca el arranque.
"""
from typing import Union, Sequence

from alembic import op


revision: str = 'f0a1b2c3d4e5'
down_revision: Union[str, None] = 'e9f0a1b2c3d4'
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
                           WHERE k = 'ckan_solicitudes_cleanup_1') THEN
                DELETE FROM opendata.solicitud_ingreso WHERE nombre = 'ckan-jerez';
                INSERT INTO opendata._purge_markers(k) VALUES ('ckan_solicitudes_cleanup_1');
            END IF;
        EXCEPTION WHEN OTHERS THEN
            NULL;
        END $$;
    """)


def downgrade() -> None:
    pass
