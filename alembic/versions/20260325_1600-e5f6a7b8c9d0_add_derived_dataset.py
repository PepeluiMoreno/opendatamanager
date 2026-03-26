"""add derived_dataset_config and derived_dataset_entry tables

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-03-25 16:00:00.000000
"""
from typing import Union, Sequence
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'derived_dataset_config',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('source_resource_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('opendata.resource.id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_name', sa.String(100), nullable=False),
        sa.Column('key_field', sa.String(100), nullable=False),
        sa.Column('extract_fields', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('merge_strategy', sa.String(20), nullable=False, server_default='upsert'),
        sa.Column('enabled', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()')),
        schema='opendata',
    )

    op.create_table(
        'derived_dataset_entry',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('config_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('opendata.derived_dataset_config.id', ondelete='CASCADE'), nullable=False),
        sa.Column('key_value', sa.String(500), nullable=False),
        sa.Column('data', postgresql.JSONB, nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('now()')),
        sa.UniqueConstraint('config_id', 'key_value', name='uq_derived_entry_config_key'),
        schema='opendata',
    )


def downgrade() -> None:
    op.drop_table('derived_dataset_entry', schema='opendata')
    op.drop_table('derived_dataset_config', schema='opendata')
