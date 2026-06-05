"""Linaje de recursos derivados: tabla resource_dependency.

Un recurso derivado (p. ej. especie CruceDatasets) depende de otros recursos
como fuentes. Hasta ahora esa dependencia vivía como strings en params; esta
tabla la hace trazable a máquina: linaje consultable, base para la señal
"fuente más nueva que derivado" y borrado coherente.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-06-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # IMPORTANTE: el entrypoint borra opendata.alembic_version en cada arranque,
    # así que TODAS las migraciones se re-ejecutan en cada boot y deben ser
    # idempotentes (patrón de la casa: SQL crudo con IF NOT EXISTS).
    op.execute("""
        CREATE TABLE IF NOT EXISTS opendata.resource_dependency (
            id UUID PRIMARY KEY,
            derived_resource_id UUID NOT NULL
                REFERENCES opendata.resource(id) ON DELETE CASCADE,
            source_resource_id UUID NOT NULL
                REFERENCES opendata.resource(id) ON DELETE CASCADE,
            role VARCHAR(10) NOT NULL,
            created_at TIMESTAMP,
            CONSTRAINT uq_resource_dependency
                UNIQUE (derived_resource_id, source_resource_id, role)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_resource_dependency_derived "
               "ON opendata.resource_dependency (derived_resource_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_resource_dependency_source "
               "ON opendata.resource_dependency (source_resource_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS opendata.resource_dependency")
