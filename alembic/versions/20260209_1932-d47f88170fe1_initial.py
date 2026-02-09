
"""initial

Revision ID: d47f88170fe1
Revises: 
Create Date: 2026-02-09 19:32:57.480150+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd47f88170fe1'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================
    # Crear schema
    # =========================
    op.execute("CREATE SCHEMA IF NOT EXISTS opendata;")

    # =========================
    # fetcher
    # =========================
    op.create_table(
        'fetcher',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(50), nullable=False, unique=True),
        sa.Column('class_path', sa.String(255)),
        sa.Column('description', sa.Text),
        schema='opendata'
    )

    # type_fetcher_params
    op.create_table(
        'type_fetcher_params',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('fetcher_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('opendata.fetcher.id')),
        sa.Column('param_name', sa.String(100), nullable=False),
        sa.Column('required', sa.Boolean, default=True),
        sa.Column('data_type', sa.String(20), default='string'),
        sa.Column('default_value', postgresql.JSONB),
        schema='opendata'
    )

    # resource
    op.create_table(
        'resource',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text),
        sa.Column('publisher', sa.String(50), nullable=False),
        sa.Column('target_table', sa.String(100)),
        sa.Column('fetcher_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('opendata.fetcher.id')),
        sa.Column('active', sa.Boolean, default=True),
        sa.Column('enable_load', sa.Boolean, default=False),
        sa.Column('load_mode', sa.String(20), default='replace'),
        schema='opendata'
    )

    # resource_param
    op.create_table(
        'resource_param',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('opendata.resource.id', ondelete='CASCADE'), nullable=False),
        sa.Column('key', sa.String(100), nullable=False),
        sa.Column('value', sa.Text, nullable=False),
        schema='opendata'
    )

    # application
    op.create_table(
        'application',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text),
        sa.Column('models_path', sa.String(255), nullable=False),
        sa.Column('subscribed_resources', postgresql.JSONB, nullable=False, default=list),
        sa.Column('active', sa.Boolean, default=True),
        sa.Column('webhook_url', sa.String(500)),
        sa.Column('webhook_secret', sa.String(100)),
        schema='opendata'
    )

    # field_metadata
    op.create_table(
        'field_metadata',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('table_name', sa.String(100), nullable=False),
        sa.Column('field_name', sa.String(100), nullable=False),
        sa.Column('label', sa.String(255)),
        sa.Column('help_text', sa.Text),
        sa.Column('placeholder', sa.String(255)),
        schema='opendata'
    )

    # resource_execution
    op.create_table(
        'resource_execution',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('opendata.resource.id'), nullable=False),
        sa.Column('started_at', sa.DateTime, default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime),
        sa.Column('status', sa.String(20)),
        sa.Column('total_records', sa.Integer),
        sa.Column('records_loaded', sa.Integer),
        sa.Column('staging_path', sa.String(500)),
        sa.Column('error_message', sa.Text),
        schema='opendata'
    )

    # dataset
    op.create_table(
        'dataset',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('opendata.resource.id'), nullable=False),
        sa.Column('execution_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('opendata.resource_execution.id')),
        sa.Column('major_version', sa.Integer, nullable=False),
        sa.Column('minor_version', sa.Integer, nullable=False),
        sa.Column('patch_version', sa.Integer, nullable=False),
        sa.Column('schema_json', postgresql.JSONB, nullable=False),
        sa.Column('data_path', sa.String(500), nullable=False),
        sa.Column('record_count', sa.Integer),
        sa.Column('checksum', sa.String(64)),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        schema='opendata'
    )

    # dataset_subscription
    op.create_table(
        'dataset_subscription',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('application_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('opendata.application.id'), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('opendata.resource.id'), nullable=False),
        sa.Column('pinned_version', sa.String(20)),
        sa.Column('auto_upgrade', sa.String(20), default='patch'),
        sa.Column('current_version', sa.String(20)),
        sa.Column('notified_at', sa.DateTime),
        schema='opendata'
    )

    # application_notification
    op.create_table(
        'application_notification',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('application_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('opendata.application.id'), nullable=False),
        sa.Column('dataset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('opendata.dataset.id')),
        sa.Column('sent_at', sa.DateTime, default=sa.func.now()),
        sa.Column('status_code', sa.Integer),
        sa.Column('response_body', sa.Text),
        sa.Column('error_message', sa.Text),
        schema='opendata'
    )


def downgrade() -> None:
    op.drop_table('application_notification', schema='opendata')
    op.drop_table('dataset_subscription', schema='opendata')
    op.drop_table('dataset', schema='opendata')
    op.drop_table('resource_execution', schema='opendata')
    op.drop_table('field_metadata', schema='opendata')
    op.drop_table('application', schema='opendata')
    op.drop_table('resource_param', schema='opendata')
    op.drop_table('resource', schema='opendata')
    op.drop_table('type_fetcher_params', schema='opendata')
    op.drop_table('fetcher', schema='opendata')
    op.execute("DROP SCHEMA IF EXISTS opendata;")
