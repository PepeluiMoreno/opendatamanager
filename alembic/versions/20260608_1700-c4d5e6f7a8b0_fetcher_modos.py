"""fetcher.modos: capacidad declarada de la especie (extraer / descubrir)

Revision ID: c4d5e6f7a8b0
Revises: b3c4d5e6f8a9
"""
from alembic import op

revision = "c4d5e6f7a8b0"
down_revision = "b3c4d5e6f8a9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IF NOT EXISTS puro (el entrypoint re-ejecuta migraciones en cada boot).
    op.execute("""
        ALTER TABLE opendata.fetcher
        ADD COLUMN IF NOT EXISTS modos JSONB NOT NULL DEFAULT '["extraer"]'::jsonb
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE opendata.fetcher DROP COLUMN IF EXISTS modos")
