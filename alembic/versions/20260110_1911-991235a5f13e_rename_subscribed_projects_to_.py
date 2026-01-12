"""rename subscribed_projects to subscribed_resources

Revision ID: 991235a5f13e
Revises: 20260110_1430
Create Date: 2026-01-10 19:11:11.532732+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '991235a5f13e'
down_revision: Union[str, Sequence[str], None] = '20260110_1430'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rename column subscribed_projects to subscribed_resources in application table
    op.alter_column(
        'application',
        'subscribed_projects',
        new_column_name='subscribed_resources',
        schema='opendata'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Rename back to subscribed_projects
    op.alter_column(
        'application',
        'subscribed_resources',
        new_column_name='subscribed_projects',
        schema='opendata'
    )
