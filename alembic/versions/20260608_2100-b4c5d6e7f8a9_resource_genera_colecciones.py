"""resource.genera_colecciones: cualifica un recurso como nave nodriza

Revision ID: b4c5d6e7f8a9
Revises: d5e6f7a8b0c1
Create Date: 2026-06-08

Separa la CAPACIDAD del fetcher (puede descubrir) de la INTENCIÓN del recurso
(actúa como generador de colecciones). Backfill por evidencia: se marca a los
recursos-madre que ya descubren (tienen candidatos o hijos promovidos), de modo
que el crawler operativo se conserva como Colección y los Web Tree que solo
extraen dejan de figurar como tales.

Idempotente (ADD COLUMN IF NOT EXISTS + UPDATE re-ejecutable): el entrypoint
borra alembic_version y re-aplica todas las migraciones en cada arranque.
"""
from typing import Union, Sequence

from alembic import op


revision: str = 'b4c5d6e7f8a9'
down_revision: Union[str, None] = 'd5e6f7a8b0c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE opendata.resource
            ADD COLUMN IF NOT EXISTS genera_colecciones BOOLEAN NOT NULL DEFAULT FALSE
    """)
    # Backfill por evidencia: un recurso-madre que ya tiene candidatos o hijos
    # estaba actuando como nave nodriza → se cualifica. Los demás (extractores)
    # quedan en FALSE. Re-ejecutable sin efecto adverso.
    op.execute("""
        UPDATE opendata.resource r
        SET genera_colecciones = TRUE
        WHERE r.parent_resource_id IS NULL
          AND r.deleted_at IS NULL
          AND r.genera_colecciones = FALSE
          AND (
                EXISTS (SELECT 1 FROM opendata.resource_candidate c
                        WHERE c.crawler_resource_id = r.id)
             OR EXISTS (SELECT 1 FROM opendata.resource h
                        WHERE h.parent_resource_id = r.id)
          )
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE opendata.resource DROP COLUMN IF EXISTS genera_colecciones")
