"""resource_collection.slug — identificador estable y neutro de colección

Revision ID: collection_slug
Revises: subscription_collection
Create Date: 2026-06-20

El `slug` es la clave estable (no editable, portable entre entornos) que los
consumidores usan para suscribirse por colección y para enrutar el webhook. Se
añade la columna, se rellena (slugify del nombre, con desambiguación) y se crea
índice único. Idempotente.
"""
import re
from typing import Union, Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'collection_slug'
down_revision: Union[str, None] = 'subscription_collection'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return (base or "coleccion")[:120]


def upgrade() -> None:
    op.execute("ALTER TABLE opendata.resource_collection ADD COLUMN IF NOT EXISTS slug VARCHAR(120)")

    # Backfill: slug a partir del nombre, garantizando unicidad (-2, -3, …).
    conn = op.get_bind()
    rows = conn.execute(sa.text(
        "SELECT id, name FROM opendata.resource_collection WHERE slug IS NULL ORDER BY created_at NULLS FIRST, name"
    )).fetchall()
    usados = set(
        r[0] for r in conn.execute(sa.text(
            "SELECT slug FROM opendata.resource_collection WHERE slug IS NOT NULL"
        )).fetchall()
    )
    for rid, name in rows:
        base = _slugify(name)
        slug = base
        n = 2
        while slug in usados:
            slug = f"{base[:115]}-{n}"
            n += 1
        usados.add(slug)
        conn.execute(
            sa.text("UPDATE opendata.resource_collection SET slug = :slug WHERE id = :id"),
            {"slug": slug, "id": rid},
        )

    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_resource_collection_slug "
        "ON opendata.resource_collection (slug)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS opendata.uq_resource_collection_slug")
    op.execute("ALTER TABLE opendata.resource_collection DROP COLUMN IF EXISTS slug")
