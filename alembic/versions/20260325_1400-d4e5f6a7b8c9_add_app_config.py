"""add app_config table with default settings

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-03-25 14:00:00.000000
"""
from typing import Union, Sequence
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_SETTINGS = [
    ("max_concurrent_processes", 3,
     "Maximum number of fetcher processes that can run simultaneously"),
    ("default_fetch_timeout", 120,
     "Default HTTP timeout in seconds for fetcher requests"),
    ("log_retention_days", 30,
     "Number of days to keep execution log files on disk"),
    ("execution_retention_days", 90,
     "Number of days to keep execution records in the database"),
    ("auto_run_on_startup", False,
     "Run all active resources automatically when the backend starts"),
    ("max_pages_per_run", 0,
     "Global cap on paginated fetcher pages per run (0 = unlimited)"),
    ("notify_on_failure", False,
     "Send a notification when a resource execution fails"),
    ("default_page_size", 100,
     "Default page size used by paginated fetchers if not specified in params"),
]


def upgrade() -> None:
    op.create_table(
        'app_config',
        sa.Column('key', sa.String(100), primary_key=True),
        sa.Column('value', postgresql.JSONB, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=True),
        schema='opendata',
    )
    conn = op.get_bind()
    for key, value, description in DEFAULT_SETTINGS:
        import json
        conn.execute(
            sa.text(
                "INSERT INTO opendata.app_config (key, value, description, updated_at) "
                "VALUES (:key, CAST(:value AS jsonb), :desc, now()) "
                "ON CONFLICT (key) DO NOTHING"
            ),
            {"key": key, "value": json.dumps(value), "desc": description}
        )


def downgrade() -> None:
    op.drop_table('app_config', schema='opendata')
