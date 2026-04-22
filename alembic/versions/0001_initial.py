"""initial — schema completo consolidado

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-23

Migración única que crea el esquema opendata al completo.
Reemplaza todas las migraciones anteriores.
Los datos iniciales se cargan via seed_data.py (entrypoint).
"""
from typing import Union, Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = '0001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS opendata;")

    # ── fetcher ────────────────────────────────────────────────────────────
    op.create_table(
        'fetcher',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(50), nullable=False, unique=True),
        sa.Column('class_path', sa.String(255)),
        sa.Column('description', sa.Text),
        schema='opendata',
    )

    # ── type_fetcher_params ────────────────────────────────────────────────
    op.create_table(
        'type_fetcher_params',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('fetcher_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('opendata.fetcher.id')),
        sa.Column('param_name', sa.String(100), nullable=False),
        sa.Column('required', sa.Boolean, default=True),
        sa.Column('data_type', sa.String(20), default='string'),
        sa.Column('default_value', postgresql.JSONB),
        sa.Column('enum_values', postgresql.JSONB, nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('group', sa.String(100), nullable=True),
        schema='opendata',
    )

    # ── publisher ──────────────────────────────────────────────────────────
    op.create_table(
        'publisher',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('nombre', sa.String(200), nullable=False),
        sa.Column('acronimo', sa.String(30), nullable=True),
        sa.Column('nivel', sa.String(30), nullable=False),
        sa.Column('pais', sa.String(100), nullable=False, server_default='España'),
        sa.Column('comunidad_autonoma', sa.String(100), nullable=True),
        sa.Column('portal_url', sa.String(500), nullable=True),
        sa.Column('email', sa.String(200), nullable=True),
        sa.Column('telefono', sa.String(50), nullable=True),
        sa.Column('provincia', sa.String(100), nullable=True),
        sa.Column('municipio', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        schema='opendata',
    )

    # ── resource ───────────────────────────────────────────────────────────
    op.create_table(
        'resource',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text),
        sa.Column('publisher', sa.String(200), nullable=True),
        sa.Column('publisher_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('opendata.publisher.id'), nullable=True),
        sa.Column('target_table', sa.String(100)),
        sa.Column('fetcher_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('opendata.fetcher.id')),
        sa.Column('active', sa.Boolean, default=True),
        sa.Column('enable_load', sa.Boolean, default=False),
        sa.Column('load_mode', sa.String(20), default='replace'),
        sa.Column('schedule', sa.String(100), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        schema='opendata',
    )

    # ── resource_param ─────────────────────────────────────────────────────
    op.create_table(
        'resource_param',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('opendata.resource.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('key', sa.String(100), nullable=False),
        sa.Column('value', sa.Text, nullable=False),
        sa.Column('is_external', sa.Boolean, nullable=False, server_default='false'),
        schema='opendata',
    )

    # ── application ────────────────────────────────────────────────────────
    op.create_table(
        'application',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text),
        sa.Column('models_path', sa.String(255), nullable=False),
        sa.Column('subscribed_resources', postgresql.JSONB, nullable=False,
                  server_default='[]'),
        sa.Column('active', sa.Boolean, default=True),
        sa.Column('webhook_url', sa.String(500)),
        sa.Column('webhook_secret', sa.String(100)),
        sa.Column('consumption_mode', sa.String(20), nullable=False,
                  server_default='webhook'),
        schema='opendata',
    )

    # ── field_metadata ─────────────────────────────────────────────────────
    op.create_table(
        'field_metadata',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('table_name', sa.String(100), nullable=False),
        sa.Column('field_name', sa.String(100), nullable=False),
        sa.Column('label', sa.String(255)),
        sa.Column('help_text', sa.Text),
        sa.Column('placeholder', sa.String(255)),
        schema='opendata',
    )

    # ── resource_execution ─────────────────────────────────────────────────
    op.create_table(
        'resource_execution',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('opendata.resource.id'), nullable=False),
        sa.Column('started_at', sa.DateTime, default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime),
        sa.Column('status', sa.String(20)),
        sa.Column('total_records', sa.Integer),
        sa.Column('records_loaded', sa.Integer),
        sa.Column('staging_path', sa.String(500)),
        sa.Column('error_message', sa.Text),
        sa.Column('execution_params', postgresql.JSONB, nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('pause_requested', sa.Boolean(), nullable=False,
                  server_default='false'),
        sa.Column('active_seconds', sa.Integer(), nullable=True,
                  server_default='0'),
        schema='opendata',
    )

    # ── dataset ────────────────────────────────────────────────────────────
    op.create_table(
        'dataset',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('opendata.resource.id'), nullable=False),
        sa.Column('execution_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('opendata.resource_execution.id')),
        sa.Column('major_version', sa.Integer, nullable=False),
        sa.Column('minor_version', sa.Integer, nullable=False),
        sa.Column('patch_version', sa.Integer, nullable=False),
        sa.Column('schema_json', postgresql.JSONB, nullable=False),
        sa.Column('data_path', sa.String(500), nullable=False),
        sa.Column('record_count', sa.Integer),
        sa.Column('checksum', sa.String(64)),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('label', sa.String(100), nullable=True),
        schema='opendata',
    )

    # ── dataset_subscription ───────────────────────────────────────────────
    op.create_table(
        'dataset_subscription',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('application_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('opendata.application.id'), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('opendata.resource.id'), nullable=False),
        sa.Column('pinned_version', sa.String(20)),
        sa.Column('auto_upgrade', sa.String(20), default='patch'),
        sa.Column('current_version', sa.String(20)),
        sa.Column('notified_at', sa.DateTime),
        schema='opendata',
    )

    # ── application_notification ───────────────────────────────────────────
    op.create_table(
        'application_notification',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('application_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('opendata.application.id'), nullable=False),
        sa.Column('dataset_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('opendata.dataset.id')),
        sa.Column('sent_at', sa.DateTime, default=sa.func.now()),
        sa.Column('status_code', sa.Integer),
        sa.Column('response_body', sa.Text),
        sa.Column('error_message', sa.Text),
        schema='opendata',
    )

    # ── app_config ─────────────────────────────────────────────────────────
    op.create_table(
        'app_config',
        sa.Column('key', sa.String(100), primary_key=True),
        sa.Column('value', postgresql.JSONB, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=True),
        schema='opendata',
    )

    # ── derived_dataset_config ─────────────────────────────────────────────
    op.create_table(
        'derived_dataset_config',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('source_resource_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('opendata.resource.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('target_name', sa.String(100), nullable=False),
        sa.Column('key_field', sa.String(100), nullable=False),
        sa.Column('extract_fields', postgresql.JSONB, nullable=False,
                  server_default='[]'),
        sa.Column('merge_strategy', sa.String(20), nullable=False,
                  server_default='upsert'),
        sa.Column('enabled', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()')),
        schema='opendata',
    )

    # ── derived_dataset_entry ──────────────────────────────────────────────
    op.create_table(
        'derived_dataset_entry',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('config_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('opendata.derived_dataset_config.id',
                                ondelete='CASCADE'), nullable=False),
        sa.Column('key_value', sa.String(500), nullable=False),
        sa.Column('data', postgresql.JSONB, nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('now()')),
        sa.UniqueConstraint('config_id', 'key_value',
                            name='uq_derived_entry_config_key'),
        schema='opendata',
    )


def downgrade() -> None:
    op.drop_table('derived_dataset_entry', schema='opendata')
    op.drop_table('derived_dataset_config', schema='opendata')
    op.drop_table('app_config', schema='opendata')
    op.drop_table('application_notification', schema='opendata')
    op.drop_table('dataset_subscription', schema='opendata')
    op.drop_table('dataset', schema='opendata')
    op.drop_table('resource_execution', schema='opendata')
    op.drop_table('field_metadata', schema='opendata')
    op.drop_table('application', schema='opendata')
    op.drop_table('resource_param', schema='opendata')
    op.drop_table('resource', schema='opendata')
    op.drop_table('publisher', schema='opendata')
    op.drop_table('type_fetcher_params', schema='opendata')
    op.drop_table('fetcher', schema='opendata')
    op.execute("DROP SCHEMA IF EXISTS opendata;")
