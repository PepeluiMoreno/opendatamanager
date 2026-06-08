"""Renombra dataset_subscription -> resource_subscription.

La suscripción siempre fue a un Resource (apunta a resource_id, con pinning de
versión); el nombre 'dataset' inducía a error. Se alinea el nombre con la sustancia.
La relación a nivel dataset (fijar/retener una versión concreta) es DatasetLease,
que es otra cosa.
"""
from alembic import op

revision = 'b3c4d5e6f8a9'
down_revision = 'a2b3c4d5e6f8'
branch_labels = None
depends_on = None

SCHEMA = "opendata"


def upgrade():
    op.rename_table("dataset_subscription", "resource_subscription", schema=SCHEMA)


def downgrade():
    op.rename_table("resource_subscription", "dataset_subscription", schema=SCHEMA)
