"""nullable target_table in resource table

Revision ID: 9c1ac94e8ec7
Revises: 85702b3b0edd
Create Date: 2026-01-13 20:46:13.100246+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9c1ac94e8ec7'
down_revision: Union[str, Sequence[str], None] = '85702b3b0edd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    # Asegurar que el schema existe (opcional, si no existe)
    # op.execute(CreateSchema('opendata'))
    
    # Cambiar target_table a nullable en el schema opendata
    op.alter_column('resource', 'target_table',
        schema='opendata',
        existing_type=sa.String(),
        nullable=True,
        existing_nullable=False)


def downgrade() -> None:
    # Revertir: hacer target_table NOT NULL en el schema opendata
    op.alter_column('resource', 'target_table',
        schema='opendata',
        existing_type=sa.String(),
        nullable=False,
        existing_nullable=True)