"""Ciclo de vida de datasets: política de retención en resource, rastro de acceso
en dataset y tabla dataset_lease (arrendamientos).

Ver docs/diseno_ciclo_vida_datasets.md.
"""
from typing import Union, Sequence
from alembic import op

revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Política de retención / caché por recurso
    op.execute("ALTER TABLE opendata.resource ADD COLUMN IF NOT EXISTS rederivable BOOLEAN NOT NULL DEFAULT true")
    op.execute("ALTER TABLE opendata.resource ADD COLUMN IF NOT EXISTS coste_rederivacion VARCHAR(10) NOT NULL DEFAULT 'medio'")
    op.execute("ALTER TABLE opendata.resource ADD COLUMN IF NOT EXISTS retencion_permanente BOOLEAN NOT NULL DEFAULT false")
    op.execute("ALTER TABLE opendata.resource ADD COLUMN IF NOT EXISTS retencion_ttl_dias INTEGER")
    op.execute("ALTER TABLE opendata.resource ADD COLUMN IF NOT EXISTS retencion_min_versiones INTEGER NOT NULL DEFAULT 1")
    op.execute("ALTER TABLE opendata.resource ADD COLUMN IF NOT EXISTS prioridad_base INTEGER NOT NULL DEFAULT 0")

    # Rastro de acceso (demanda) por dataset
    op.execute("ALTER TABLE opendata.dataset ADD COLUMN IF NOT EXISTS last_served_at TIMESTAMP")
    op.execute("ALTER TABLE opendata.dataset ADD COLUMN IF NOT EXISTS accesos INTEGER NOT NULL DEFAULT 0")

    # Arrendamientos
    op.execute("""
        CREATE TABLE IF NOT EXISTS opendata.dataset_lease (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            resource_id UUID NOT NULL REFERENCES opendata.resource(id) ON DELETE CASCADE,
            dataset_id UUID REFERENCES opendata.dataset(id) ON DELETE SET NULL,
            titular_tipo VARCHAR(20) NOT NULL,
            titular_id UUID,
            email_contacto VARCHAR(255),
            retencion_solicitada_dias INTEGER,
            permanente BOOLEAN NOT NULL DEFAULT false,
            concedido_hasta TIMESTAMP,
            estado VARCHAR(20) NOT NULL DEFAULT 'activo',
            created_at TIMESTAMP,
            released_at TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_dataset_lease_dataset ON opendata.dataset_lease(dataset_id, estado)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_dataset_lease_resource ON opendata.dataset_lease(resource_id, estado)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS opendata.dataset_lease")
    for col in ("rederivable", "coste_rederivacion", "retencion_permanente",
                "retencion_ttl_dias", "retencion_min_versiones", "prioridad_base"):
        op.execute(f"ALTER TABLE opendata.resource DROP COLUMN IF EXISTS {col}")
    op.execute("ALTER TABLE opendata.dataset DROP COLUMN IF EXISTS last_served_at")
    op.execute("ALTER TABLE opendata.dataset DROP COLUMN IF EXISTS accesos")
