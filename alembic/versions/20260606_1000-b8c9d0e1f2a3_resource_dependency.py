"""Linaje de recursos derivados: tabla resource_dependency.

Un recurso derivado (p. ej. especie CruceDatasets) depende de otros recursos
como fuentes. Hasta ahora esa dependencia vivía como strings en params; esta
tabla la hace trazable a máquina: linaje consultable, base para la señal
"fuente más nueva que derivado" y borrado coherente.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-06-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'resource_dependency',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('derived_resource_id', UUID(as_uuid=True),
                  sa.ForeignKey('opendata.resource.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_resource_id', UUID(as_uuid=True),
                  sa.ForeignKey('opendata.resource.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(10), nullable=False),  # 'left' | 'right'
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('derived_resource_id', 'source_resource_id', 'role',
                            name='uq_resource_dependency'),
        schema='opendata',
    )
    op.create_index('ix_resource_dependency_derived', 'resource_dependency',
                    ['derived_resource_id'], schema='opendata')
    op.create_index('ix_resource_dependency_source', 'resource_dependency',
                    ['source_resource_id'], schema='opendata')


def downgrade() -> None:
    op.drop_table('resource_dependency', schema='opendata')
