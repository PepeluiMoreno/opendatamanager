"""variantes de fetcher: fetcher.preset_params (bloque de params inyectable)

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-05

Idempotente.
"""
from typing import Union, Sequence
from alembic import op

revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE opendata.fetcher ADD COLUMN IF NOT EXISTS preset_params JSONB")


def downgrade() -> None:
    op.execute("ALTER TABLE opendata.fetcher DROP COLUMN IF EXISTS preset_params")
