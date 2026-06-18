"""
Colecciones matriz de las naves nodriza.

Una **nave nodriza** (recurso con `genera_colecciones=True`, fetcher que declara
modo `descubrir` y sin padre — i.e. `Resource.es_coleccion`) **es** una colección:
preside una `ResourceCollection(origin='matriz', root_resource_id=recurso)` que
lleva su mismo nombre, y dentro van **el propio recurso madre** y **sus hijos
descubiertos**. Así "Sin agrupar" queda solo con recursos sueltos.

El modelo soportaba esto (campo `origin`, `root_resource_id`, icono 🛰️ en el rail)
pero nada creaba la colección matriz. Este servicio es esa pieza, idempotente,
invocada desde el seed de manifests (backfill de las existentes), al promover
candidatos (los hijos caen dentro) y al marcar un recurso como nave nodriza.
"""
from __future__ import annotations

from uuid import uuid4

from app.models import Resource, ResourceCollection


def ensure_matriz_collection(session, resource) -> ResourceCollection | None:
    """Asegura la colección matriz de una nave nodriza y mete dentro al recurso
    madre y a sus hijos. Idempotente. Devuelve la colección, o None si el recurso
    no es nave nodriza."""
    if not getattr(resource, "es_coleccion", False):
        return None

    col = (
        session.query(ResourceCollection)
        .filter(ResourceCollection.root_resource_id == resource.id)
        .first()
    )

    def _nombre_libre(nombre: str) -> str:
        # El nombre de colección es único: si otra colección ya lo usa, sufijo defensivo.
        choca = (
            session.query(ResourceCollection)
            .filter(ResourceCollection.name == nombre)
            .filter(ResourceCollection.root_resource_id != resource.id)
            .first()
        )
        return nombre if not choca else f"{nombre} ({str(resource.id)[:8]})"

    if col is None:
        col = ResourceCollection(
            id=uuid4(),
            name=_nombre_libre(resource.name),
            origin="matriz",
            root_resource_id=resource.id,
        )
        session.add(col)
        session.flush()
    else:
        if col.origin != "matriz":
            col.origin = "matriz"
        # Mantener el nombre sincronizado con el del recurso madre.
        if col.name != resource.name:
            col.name = _nombre_libre(resource.name)

    # El recurso madre, miembro de su propia colección.
    if resource.resource_collection_id != col.id:
        resource.resource_collection_id = col.id

    # Los hijos descubiertos, dentro también.
    hijos = (
        session.query(Resource)
        .filter(Resource.parent_resource_id == resource.id, Resource.deleted_at.is_(None))
        .all()
    )
    for h in hijos:
        if h.resource_collection_id != col.id:
            h.resource_collection_id = col.id

    return col


def backfill_matriz_collections(session) -> int:
    """Recorre todas las naves nodriza y asegura su colección matriz. Para el seed.
    Devuelve cuántas naves nodriza se procesaron. Hace commit."""
    naves = (
        session.query(Resource)
        .filter(
            Resource.deleted_at.is_(None),
            Resource.parent_resource_id.is_(None),
            Resource.genera_colecciones == True,  # noqa: E712
        )
        .all()
    )
    n = 0
    for r in naves:
        if ensure_matriz_collection(session, r) is not None:
            n += 1
    session.commit()
    return n
