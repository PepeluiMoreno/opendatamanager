"""add resource_candidate table

Revision ID: e1f2a3b4c5d6
Revises: d7e8f9a0b1c2
Create Date: 2026-04-25
"""
from typing import Union, Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, None] = 'd7e8f9a0b1c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # IDEMPOTENTE DE VERDAD (el entrypoint re-ejecuta TODAS las migraciones en
    # cada arranque): IF NOT EXISTS puro. La versión anterior abría con un
    # DROP TABLE CASCADE — válido una vez (limpiar el esquema rechazado del
    # spec file-granular) pero letal después: cada redeploy vaciaba TODAS las
    # candidatas, dejando huérfanos a los Resources hijos promovidos.
    op.execute("""
        CREATE TABLE IF NOT EXISTS opendata.resource_candidate (
            id UUID PRIMARY KEY,
            execution_id UUID REFERENCES opendata.resource_execution(id) ON DELETE SET NULL,
            crawler_resource_id UUID NOT NULL REFERENCES opendata.resource(id) ON DELETE CASCADE,
            path_template TEXT NOT NULL,
            dimensions JSONB NOT NULL DEFAULT '[]',
            matched_urls JSONB NOT NULL DEFAULT '[]',
            file_types JSONB NOT NULL DEFAULT '{}',
            suggested_name TEXT,
            confidence FLOAT,
            status VARCHAR(20) NOT NULL DEFAULT 'discovered',
            promoted_resource_id UUID REFERENCES opendata.resource(id) ON DELETE SET NULL,
            merged_into_id UUID REFERENCES opendata.resource_candidate(id) ON DELETE SET NULL,
            split_from_id UUID REFERENCES opendata.resource_candidate(id) ON DELETE SET NULL,
            detected_at TIMESTAMP NOT NULL DEFAULT now(),
            reviewed_at TIMESTAMP,
            reviewed_by VARCHAR(200),
            deleted_at TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_resource_candidate_crawler_status "
               "ON opendata.resource_candidate (crawler_resource_id, status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_resource_candidate_execution "
               "ON opendata.resource_candidate (execution_id)")


def downgrade() -> None:
    op.drop_index('ix_resource_candidate_execution', table_name='resource_candidate', schema='opendata')
    op.drop_index('ix_resource_candidate_crawler_status', table_name='resource_candidate', schema='opendata')
    op.drop_table('resource_candidate', schema='opendata')
