"""salud del origen: resource.source_status

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-05

Idempotente.
"""
from typing import Union, Sequence
from alembic import op

revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE opendata.resource ADD COLUMN IF NOT EXISTS source_status VARCHAR(20) NOT NULL DEFAULT 'ok'")


def downgrade() -> None:
    op.execute("ALTER TABLE opendata.resource DROP COLUMN IF EXISTS source_status")
