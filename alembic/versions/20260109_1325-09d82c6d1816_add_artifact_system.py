"""add_artifact_system

Revision ID: 09d82c6d1816
Revises: ef2383fe082a
Create Date: 2026-01-09 13:25:59.798237+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '09d82c6d1816'
down_revision: Union[str, Sequence[str], None] = 'ef2383fe082a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add artifact system tables and fields."""

    # ResourceExecution - audit trail
    op.create_table(
        'resource_execution',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('total_records', sa.Integer(), nullable=True),
        sa.Column('records_loaded', sa.Integer(), nullable=True),
        sa.Column('staging_path', sa.String(length=500), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['resource_id'], ['opendata.resource.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='opendata'
    )

    # Artifact - versioned packages
    op.create_table(
        'artifact',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('execution_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('major_version', sa.Integer(), nullable=False),
        sa.Column('minor_version', sa.Integer(), nullable=False),
        sa.Column('patch_version', sa.Integer(), nullable=False),
        sa.Column('schema_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('data_path', sa.String(length=500), nullable=False),
        sa.Column('record_count', sa.Integer(), nullable=True),
        sa.Column('checksum', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['execution_id'], ['opendata.resource_execution.id'], ),
        sa.ForeignKeyConstraint(['resource_id'], ['opendata.resource.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='opendata'
    )

    # ArtifactSubscription - passive subscriptions
    op.create_table(
        'artifact_subscription',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('application_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('pinned_version', sa.String(length=20), nullable=True),
        sa.Column('auto_upgrade', sa.String(length=20), nullable=True),
        sa.Column('current_version', sa.String(length=20), nullable=True),
        sa.Column('notified_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['application_id'], ['opendata.application.id'], ),
        sa.ForeignKeyConstraint(['resource_id'], ['opendata.resource.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='opendata'
    )

    # ApplicationNotification - webhook log
    op.create_table(
        'application_notification',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('application_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('artifact_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('response_body', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['application_id'], ['opendata.application.id'], ),
        sa.ForeignKeyConstraint(['artifact_id'], ['opendata.artifact.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='opendata'
    )

    # Add new fields to Application
    op.add_column('application', sa.Column('webhook_url', sa.String(length=500), nullable=True), schema='opendata')
    op.add_column('application', sa.Column('webhook_secret', sa.String(length=100), nullable=True), schema='opendata')

    # Add new fields to Resource
    op.add_column('resource', sa.Column('enable_load', sa.Boolean(), nullable=True), schema='opendata')
    op.add_column('resource', sa.Column('load_mode', sa.String(length=20), nullable=True), schema='opendata')


def downgrade() -> None:
    """Remove artifact system tables and fields."""

    # Drop new fields from Resource
    op.drop_column('resource', 'load_mode', schema='opendata')
    op.drop_column('resource', 'enable_load', schema='opendata')

    # Drop new fields from Application
    op.drop_column('application', 'webhook_secret', schema='opendata')
    op.drop_column('application', 'webhook_url', schema='opendata')

    # Drop tables (in reverse order due to foreign keys)
    op.drop_table('application_notification', schema='opendata')
    op.drop_table('artifact_subscription', schema='opendata')
    op.drop_table('artifact', schema='opendata')
    op.drop_table('resource_execution', schema='opendata')
