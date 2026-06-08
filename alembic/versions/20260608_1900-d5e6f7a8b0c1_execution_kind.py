"""resource_execution.kind: tipo de proceso (extraccion / discovering)

Revision ID: d5e6f7a8b0c1
Revises: c4d5e6f7a8b0
"""
from alembic import op

revision = "d5e6f7a8b0c1"
down_revision = "c4d5e6f7a8b0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE opendata.resource_execution
        ADD COLUMN IF NOT EXISTS kind VARCHAR(20) NOT NULL DEFAULT 'extraccion'
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE opendata.resource_execution DROP COLUMN IF EXISTS kind")
