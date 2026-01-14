"""initial

Revision ID: 85702b3b0edd
Revises: 
Create Date: 2026-01-13 20:38:26.238727+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '85702b3b0edd'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
 pass

def downgrade() -> None:
    pass