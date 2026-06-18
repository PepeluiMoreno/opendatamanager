"""resource_collection: N:M (membership) + anidamiento (parent_collection_id)

F1 NO DESTRUCTIVA: añade la tabla de unión resource_collection_member y la columna
parent_collection_id, y hace backfill de la pertenencia 1:1 actual a membership.
Conserva resource.resource_collection_id (se retira en una fase final).

Revision ID: res_collection_nm_tree
Revises: res_collection_1
Create Date: 2026-06-18
"""
from typing import Union, Sequence
from alembic import op

revision: str = 'res_collection_nm_tree'
down_revision: Union[str, None] = 'res_collection_1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # N:M: un recurso puede estar en varias colecciones.
    op.execute("""
        CREATE TABLE IF NOT EXISTS opendata.resource_collection_member (
            resource_id uuid NOT NULL REFERENCES opendata.resource(id) ON DELETE CASCADE,
            collection_id uuid NOT NULL REFERENCES opendata.resource_collection(id) ON DELETE CASCADE,
            created_at timestamp DEFAULT now(),
            PRIMARY KEY (resource_id, collection_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_rcm_collection ON opendata.resource_collection_member(collection_id)")

    # Anidamiento: una colección puede colgar de otra (solo organizativas como padre).
    op.execute("ALTER TABLE opendata.resource_collection ADD COLUMN IF NOT EXISTS parent_collection_id uuid REFERENCES opendata.resource_collection(id) ON DELETE SET NULL")

    # Backfill: la pertenencia 1:1 actual (resource_collection_id) → membership.
    op.execute("""
        INSERT INTO opendata.resource_collection_member (resource_id, collection_id, created_at)
        SELECT id, resource_collection_id, now()
        FROM opendata.resource
        WHERE resource_collection_id IS NOT NULL
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE opendata.resource_collection DROP COLUMN IF EXISTS parent_collection_id")
    op.execute("DROP TABLE IF EXISTS opendata.resource_collection_member")
