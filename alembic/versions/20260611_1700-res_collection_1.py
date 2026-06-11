"""rename resource_group -> resource_collection (colecciones organizativas)

Revision ID: res_collection_1
Revises: res_group_1
Create Date: 2026-06-11
"""
from typing import Union, Sequence
from alembic import op

revision: str = 'res_collection_1'
down_revision: Union[str, None] = 'res_group_1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Sin datos que preservar (0 colecciones, todos los recursos sin agrupar):
    # se retira la tabla/columna 'group' y se crea la equivalente 'collection'.
    op.execute("ALTER TABLE opendata.resource DROP COLUMN IF EXISTS resource_group_id")
    op.execute("DROP TABLE IF EXISTS opendata.resource_group")
    op.execute("""
        CREATE TABLE IF NOT EXISTS opendata.resource_collection (
            id uuid PRIMARY KEY,
            name varchar(100) NOT NULL,
            origin varchar(20) NOT NULL DEFAULT 'organizativa',
            root_resource_id uuid REFERENCES opendata.resource(id) ON DELETE CASCADE,
            created_at timestamp,
            updated_at timestamp,
            created_by_id uuid,
            updated_by_id uuid,
            CONSTRAINT uq_resource_collection_name UNIQUE (name)
        )
    """)
    op.execute("ALTER TABLE opendata.resource ADD COLUMN IF NOT EXISTS resource_collection_id uuid REFERENCES opendata.resource_collection(id) ON DELETE SET NULL")


def downgrade() -> None:
    pass
