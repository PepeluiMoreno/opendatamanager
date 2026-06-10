"""admision unificada: application(persona,email,telefono,github,proposito) + solicitud.consumption_mode

Revision ID: admision_unif_1
Revises: sol_admision_1
Create Date: 2026-06-10
"""
from typing import Union, Sequence
from alembic import op

revision: str = 'admision_unif_1'
down_revision: Union[str, None] = 'sol_admision_1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE opendata.application ADD COLUMN IF NOT EXISTS persona_contacto varchar(160)")
    op.execute("ALTER TABLE opendata.application ADD COLUMN IF NOT EXISTS email varchar(255)")
    op.execute("ALTER TABLE opendata.application ADD COLUMN IF NOT EXISTS telefono varchar(40)")
    op.execute("ALTER TABLE opendata.application ADD COLUMN IF NOT EXISTS github_url varchar(300)")
    op.execute("ALTER TABLE opendata.application ADD COLUMN IF NOT EXISTS proposito text")
    op.execute("ALTER TABLE opendata.solicitud_ingreso ADD COLUMN IF NOT EXISTS consumption_mode varchar(20)")


def downgrade() -> None:
    pass
