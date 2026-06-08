"""Renombra dataset_subscription -> resource_subscription.

La suscripción siempre fue a un Resource (apunta a resource_id, con pinning de
versión); el nombre 'dataset' inducía a error. Se alinea el nombre con la sustancia.
La relación a nivel dataset (fijar/retener una versión concreta) es DatasetLease,
que es otra cosa.
"""
from alembic import op
import sqlalchemy as sa

revision = 'b3c4d5e6f8a9'
down_revision = 'a2b3c4d5e6f8'
branch_labels = None
depends_on = None

SCHEMA = "opendata"


def _has_table(insp, name):
    try:
        return insp.has_table(name, schema=SCHEMA)
    except Exception:
        return False


def upgrade():
    insp = sa.inspect(op.get_bind())
    # Idempotente: el entrypoint re-aplica desde base en cada arranque.
    if _has_table(insp, "dataset_subscription") and not _has_table(insp, "resource_subscription"):
        op.rename_table("dataset_subscription", "resource_subscription", schema=SCHEMA)


def downgrade():
    insp = sa.inspect(op.get_bind())
    if _has_table(insp, "resource_subscription") and not _has_table(insp, "dataset_subscription"):
        op.rename_table("resource_subscription", "dataset_subscription", schema=SCHEMA)
