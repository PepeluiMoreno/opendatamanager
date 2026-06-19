"""resource_subscription.collection_id — suscripción a colección (no solo a recurso)

Revision ID: subscription_collection
Revises: usuario_ui_prefs
Create Date: 2026-06-19

Una suscripción puede apuntar a un recurso O a una colección. La suscripción a
colección cubre sus miembros (resueltos en cada entrega). `resource_id` pasa a
nullable. Idempotente.
"""
from typing import Union, Sequence

from alembic import op


revision: str = 'subscription_collection'
down_revision: Union[str, None] = 'usuario_ui_prefs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE opendata.resource_subscription "
        "ADD COLUMN IF NOT EXISTS collection_id UUID REFERENCES opendata.resource_collection(id)"
    )
    op.execute("ALTER TABLE opendata.resource_subscription ALTER COLUMN resource_id DROP NOT NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE opendata.resource_subscription DROP COLUMN IF EXISTS collection_id")
    # resource_id vuelve a NOT NULL solo si no hay filas de suscripción a colección.
    op.execute(
        "ALTER TABLE opendata.resource_subscription ALTER COLUMN resource_id SET NOT NULL"
    )
