"""add_schedule_to_resource

Revision ID: 3fde65ef49fa
Revises: add_cascade_deletes
Create Date: 2026-03-16 19:34:01.622835+00:00

Añade columna `schedule` (expresión cron) a la tabla opendata.resource.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '3fde65ef49fa'
down_revision: Union[str, Sequence[str], None] = 'add_cascade_deletes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'resource',
        sa.Column('schedule', sa.String(100), nullable=True),
        schema='opendata',
    )


def downgrade() -> None:
    op.drop_column('resource', 'schedule', schema='opendata')
