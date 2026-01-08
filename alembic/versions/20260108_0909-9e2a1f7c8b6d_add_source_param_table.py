"""add source param table

Revision ID: 9e2a1f7c8b6d
Revises: 65c4949bf4df
Create Date: 2026-01-08
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# Revision identifiers, used by Alembic.
revision = "9e2a1f7c8b6d"
down_revision = "65c4949bf4df"
branch_labels = None
depends_on = None

SCHEMA = "opendata"


def upgrade():
    op.create_table(
        "source_param",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_id"],
            [f"{SCHEMA}.source.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("source_id", "key", name="uq_source_param_key"),
        schema=SCHEMA,
    )

    # Eliminar columna JSONB antigua si existía
    with op.batch_alter_table("source", schema=SCHEMA) as batch_op:
        try:
            batch_op.drop_column("params")
        except Exception:
            pass


def downgrade():
    with op.batch_alter_table("source", schema=SCHEMA) as batch_op:
        batch_op.add_column(
            sa.Column("params", postgresql.JSONB(), nullable=True)
        )

    op.drop_table("source_param", schema=SCHEMA)

