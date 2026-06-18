"""Pertenencia N:M de recursos a colecciones y anidamiento de colecciones.

Fuente de verdad: tabla `resource_collection_member` (un recurso en VARIAS
colecciones). `Resource.resource_collection_id` se mantiene como **espejo** de una
pertenencia "primaria" por compatibilidad hasta la fase final (F4), donde se
retira. "Sin agrupar" = recurso sin ninguna membership.

Reglas de anidamiento (`parent_collection_id`): el padre solo puede ser una
colección **organizativa** (nada cuelga de una 'matriz', ni una matriz de otra);
sin ciclos; profundidad libre.
"""
from sqlalchemy import insert, delete, select

from app.models import Resource, ResourceCollection, resource_collection_member as RCM


def collection_ids_of(session, resource_id) -> list[str]:
    rows = session.execute(select(RCM.c.collection_id).where(RCM.c.resource_id == resource_id)).all()
    return [str(r[0]) for r in rows]


def member_resource_ids(session, collection_id) -> list:
    rows = session.execute(select(RCM.c.resource_id).where(RCM.c.collection_id == collection_id)).all()
    return [r[0] for r in rows]


def member_count(session, collection_id) -> int:
    return session.query(RCM).filter(RCM.c.collection_id == collection_id).count()


def _sync_primary(session, resource_id) -> None:
    """Espejo legado: resource_collection_id = una de las memberships (o None)."""
    ids = session.execute(select(RCM.c.collection_id).where(RCM.c.resource_id == resource_id)).all()
    r = session.query(Resource).filter(Resource.id == resource_id).first()
    if r is not None:
        r.resource_collection_id = ids[0][0] if ids else None


def add_members(session, collection_id, resource_ids) -> None:
    """Añade recursos a una colección (idempotente). Sincroniza el espejo."""
    for rid in resource_ids:
        existe = session.execute(
            select(RCM.c.resource_id).where(RCM.c.resource_id == rid, RCM.c.collection_id == collection_id)
        ).first()
        if not existe:
            session.execute(insert(RCM).values(resource_id=rid, collection_id=collection_id))
        _sync_primary(session, rid)


def remove_member(session, collection_id, resource_id) -> None:
    session.execute(delete(RCM).where(RCM.c.resource_id == resource_id, RCM.c.collection_id == collection_id))
    _sync_primary(session, resource_id)


def set_membership_single(session, resource_id, collection_id_or_none) -> None:
    """Compat con el 'set' 1:1 antiguo: deja al recurso SOLO en esa colección (o en
    ninguna). Lo usa update_resource mientras el front mande un único collectionId."""
    session.execute(delete(RCM).where(RCM.c.resource_id == resource_id))
    if collection_id_or_none:
        session.execute(insert(RCM).values(resource_id=resource_id, collection_id=collection_id_or_none))
    _sync_primary(session, resource_id)


def validate_parent(session, child: ResourceCollection, parent_id):
    """Valida un `parent_collection_id` para `child`. Devuelve (ok, error|None)."""
    if not parent_id:
        return True, None
    if str(parent_id) == str(child.id):
        return False, "Una colección no puede colgar de sí misma."
    parent = session.query(ResourceCollection).filter(ResourceCollection.id == parent_id).first()
    if parent is None:
        return False, "La colección padre no existe."
    if (parent.origin or "organizativa") != "organizativa":
        return False, "Solo una colección organizativa puede contener otras (nada cuelga de una matriz)."
    # Anti-ciclos: subir por la cadena de padres desde 'parent' no debe topar con 'child'.
    visto = set()
    cur = parent
    while cur is not None:
        if cur.id == child.id:
            return False, "Anidamiento cíclico."
        if cur.id in visto or not cur.parent_collection_id:
            break
        visto.add(cur.id)
        cur = session.query(ResourceCollection).filter(ResourceCollection.id == cur.parent_collection_id).first()
    return True, None
