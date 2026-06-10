"""solicitud de alta: datos de admisión (descripcion, persona_contacto, email, telefono, github_url)

Revision ID: sol_admision_1
Revises: purge_ckan_princ_1
Create Date: 2026-06-10
"""
from typing import Union, Sequence
from alembic import op

revision: str = 'sol_admision_1'
down_revision: Union[str, None] = 'purge_ckan_princ_1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE opendata.solicitud_ingreso ADD COLUMN IF NOT EXISTS descripcion text")
    op.execute("ALTER TABLE opendata.solicitud_ingreso ADD COLUMN IF NOT EXISTS persona_contacto varchar(160)")
    op.execute("ALTER TABLE opendata.solicitud_ingreso ADD COLUMN IF NOT EXISTS email varchar(255)")
    op.execute("ALTER TABLE opendata.solicitud_ingreso ADD COLUMN IF NOT EXISTS telefono varchar(40)")
    op.execute("ALTER TABLE opendata.solicitud_ingreso ADD COLUMN IF NOT EXISTS github_url varchar(300)")


def downgrade() -> None:
    pass
