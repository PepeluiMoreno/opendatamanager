"""resource_candidate: target_fetcher_code + target_params (promoción heterogénea)

Revision ID: cand_target_1
Revises: admision_unif_1
Create Date: 2026-06-11
"""
from typing import Union, Sequence
from alembic import op

revision: str = 'cand_target_1'
down_revision: Union[str, None] = 'admision_unif_1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE opendata.resource_candidate ADD COLUMN IF NOT EXISTS target_fetcher_code varchar(50)")
    op.execute("ALTER TABLE opendata.resource_candidate ADD COLUMN IF NOT EXISTS target_params jsonb")


def downgrade() -> None:
    pass
