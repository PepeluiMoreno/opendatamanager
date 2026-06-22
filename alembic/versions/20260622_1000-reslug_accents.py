"""resource_collection.slug — transliterar acentos (re-slug)

Revision ID: reslug_accents
Revises: collection_slug
Create Date: 2026-06-22

El slugify original convertía los acentos en '-' (p. ej. "Iglesia católica
(red nuclear)" → "iglesia-cat-lica-red-nuclear", "Inmuebles religiosos en
España" → "inmuebles-religiosos-en-espa-a"): slugs rotos como clave estable.
Ahora se transliteran (á→a, ñ→n, ü→u…). Esta migración recalcula el slug de
cada colección y lo actualiza si cambia, preservando unicidad. Idempotente.
"""
import re
import unicodedata
from typing import Union, Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'reslug_accents'
down_revision: Union[str, None] = 'collection_slug'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _slugify(name: str) -> str:
    decompuesto = unicodedata.normalize("NFKD", (name or "").lower())
    sin_acentos = "".join(c for c in decompuesto if unicodedata.category(c) != "Mn")
    base = re.sub(r"[^a-z0-9]+", "-", sin_acentos).strip("-")
    return (base or "coleccion")[:120]


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(sa.text(
        "SELECT id, name, slug FROM opendata.resource_collection "
        "ORDER BY created_at NULLS FIRST, name"
    )).fetchall()

    # Slugs deseados (recalculados) y los que ya están bien, para garantizar
    # unicidad sin pisar a otra colección.
    actuales = {r[0]: r[2] for r in rows}
    usados = set()
    cambios = []
    for rid, name, slug_actual in rows:
        deseado = _slugify(name)
        if deseado == slug_actual:
            usados.add(slug_actual)
        else:
            cambios.append((rid, deseado, slug_actual))

    for rid, base, slug_actual in cambios:
        slug = base
        n = 2
        # Evita colisión con slugs ya fijados (de otras colecciones).
        while slug in usados or any(slug == s for i, s in actuales.items() if i != rid and s):
            slug = f"{base[:115]}-{n}"
            n += 1
        usados.add(slug)
        actuales[rid] = slug
        conn.execute(
            sa.text("UPDATE opendata.resource_collection SET slug = :slug WHERE id = :id"),
            {"slug": slug, "id": rid},
        )


def downgrade() -> None:
    # No reversible de forma fiable (no guardamos el slug previo). No-op.
    pass
