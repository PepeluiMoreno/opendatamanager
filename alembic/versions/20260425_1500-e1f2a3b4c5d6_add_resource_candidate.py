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
    # Idempotente: si una migración previa rechazada (file-granular) creó la tabla
    # con un esquema distinto, la tiramos antes de recrearla con el esquema actual.
    # Seguro porque entre el merge descartado y este deploy no pudo haber datos
    # útiles persistidos.
    op.execute("DROP TABLE IF EXISTS opendata.resource_candidate CASCADE")

    op.create_table(
        'resource_candidate',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('execution_id', UUID(as_uuid=True),
                  sa.ForeignKey('opendata.resource_execution.id', ondelete='SET NULL'),
                  nullable=True),
        sa.Column('crawler_resource_id', UUID(as_uuid=True),
                  sa.ForeignKey('opendata.resource.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('path_template', sa.Text(), nullable=False),
        sa.Column('dimensions', JSONB(), nullable=False, server_default='[]'),
        sa.Column('matched_urls', JSONB(), nullable=False, server_default='[]'),
        sa.Column('file_types', JSONB(), nullable=False, server_default='{}'),
        sa.Column('suggested_name', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='discovered'),
        sa.Column('promoted_resource_id', UUID(as_uuid=True),
                  sa.ForeignKey('opendata.resource.id', ondelete='SET NULL'),
                  nullable=True),
        sa.Column('merged_into_id', UUID(as_uuid=True),
                  sa.ForeignKey('opendata.resource_candidate.id', ondelete='SET NULL'),
                  nullable=True),
        sa.Column('split_from_id', UUID(as_uuid=True),
                  sa.ForeignKey('opendata.resource_candidate.id', ondelete='SET NULL'),
                  nullable=True),
        sa.Column('detected_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('reviewed_by', sa.String(200), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        schema='opendata',
    )
    op.create_index(
        'ix_resource_candidate_crawler_status',
        'resource_candidate',
        ['crawler_resource_id', 'status'],
        schema='opendata',
    )
    op.create_index(
        'ix_resource_candidate_execution',
        'resource_candidate',
        ['execution_id'],
        schema='opendata',
    )


def downgrade() -> None:
    op.drop_index('ix_resource_candidate_execution', table_name='resource_candidate', schema='opendata')
    op.drop_index('ix_resource_candidate_crawler_status', table_name='resource_candidate', schema='opendata')
    op.drop_table('resource_candidate', schema='opendata')
