"""versionado y procedencia de recursos + historial de manifiestos

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-04

Idempotente (el entrypoint reaplica todas las migraciones en cada arranque).
"""
from typing import Union, Sequence

from alembic import op


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE opendata.resource ADD COLUMN IF NOT EXISTS manifest_version INTEGER NOT NULL DEFAULT 1")
    op.execute("ALTER TABLE opendata.resource ADD COLUMN IF NOT EXISTS manifest_hash VARCHAR(64)")
    op.execute("ALTER TABLE opendata.resource ADD COLUMN IF NOT EXISTS last_synced_hash VARCHAR(64)")
    op.execute("ALTER TABLE opendata.resource ADD COLUMN IF NOT EXISTS origin VARCHAR(20) NOT NULL DEFAULT 'ui'")
    op.execute("""
        CREATE TABLE IF NOT EXISTS opendata.resource_manifest_version (
            id UUID PRIMARY KEY,
            resource_id UUID NOT NULL REFERENCES opendata.resource(id) ON DELETE CASCADE,
            version INTEGER NOT NULL,
            manifest_json JSONB NOT NULL,
            hash VARCHAR(64) NOT NULL,
            origin VARCHAR(20) NOT NULL,
            author VARCHAR(120),
            created_at TIMESTAMP DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_rmv_resource ON opendata.resource_manifest_version (resource_id, version)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS opendata.resource_manifest_version CASCADE")
    for col in ("manifest_version", "manifest_hash", "last_synced_hash", "origin"):
        op.execute(f"ALTER TABLE opendata.resource DROP COLUMN IF EXISTS {col}")
