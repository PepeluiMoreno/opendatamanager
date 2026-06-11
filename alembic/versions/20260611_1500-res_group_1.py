"""resource_group: agrupaciones organizativas de recursos + FK en resource

Revision ID: res_group_1
Revises: cand_target_1
Create Date: 2026-06-11
"""
from typing import Union, Sequence
from alembic import op

revision: str = 'res_group_1'
down_revision: Union[str, None] = 'cand_target_1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Entidad de primera clase: la agrupación existe por sí sola (puede estar
    # vacía). origin 'organizativa' (a mano) | 'matriz' (presidida por root_resource_id).
    op.execute("""
        CREATE TABLE IF NOT EXISTS opendata.resource_group (
            id uuid PRIMARY KEY,
            name varchar(100) NOT NULL,
            origin varchar(20) NOT NULL DEFAULT 'organizativa',
            root_resource_id uuid REFERENCES opendata.resource(id) ON DELETE CASCADE,
            created_at timestamp,
            updated_at timestamp,
            created_by_id uuid,
            updated_by_id uuid,
            CONSTRAINT uq_resource_group_name UNIQUE (name)
        )
    """)
    # Pertenencia única; al borrar la agrupación el miembro queda «sin agrupar».
    op.execute("ALTER TABLE opendata.resource ADD COLUMN IF NOT EXISTS resource_group_id uuid REFERENCES opendata.resource_group(id) ON DELETE SET NULL")


def downgrade() -> None:
    pass
