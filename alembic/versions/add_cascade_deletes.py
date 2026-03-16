"""add_cascade_deletes

Revision ID: add_cascade_deletes
Revises: d47f88170fe1
Create Date: 2026-02-10 00:00:00.000000

NOTE: Esta migración ya fue aplicada manualmente a la BD.
      Este fichero existe solo para reconstruir la cadena de Alembic.
"""
from alembic import op

revision = 'add_cascade_deletes'
down_revision = 'd47f88170fe1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ya aplicado manualmente — no-op
    pass


def downgrade() -> None:
    pass
