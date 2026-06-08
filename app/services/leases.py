"""Ciclo de vida de datasets: arrendamientos (leases), permanencia efectiva y
candidatos a desalojo.

El dataset es la extracción de una pipeline ETL re-ejecutable, así que el
almacenamiento es una caché provisionada bajo demanda: un dataset vive mientras
tenga algún lease activo, una versión fijada por un suscriptor o esté dentro del
suelo de versiones mínimas de su recurso. Ver docs/diseno_ciclo_vida_datasets.md.

El cálculo del plazo concedible en función del disco y la acumulación programada
(simulador de capacidad) es la siguiente capa; aquí queda el gancho `plazo_concedible`
con política estática.
"""
from datetime import datetime, timedelta
from typing import List, Optional

from app.models import Dataset, DatasetLease, ResourceSubscription, Resource

ESTADO_ACTIVO = "activo"
ESTADO_LIBERADO = "liberado"
ESTADO_EXPIRADO = "expirado"


def plazo_concedible(resource: Resource, solicitada_dias: Optional[int],
                     ahora: Optional[datetime] = None) -> Optional[int]:
    """Días que ODM puede conceder a una petición. Devuelve None si la retención
    es permanente.

    v1: política estática (permanente, o min(solicitada, ttl_base)).
    GANCHO (siguiente capa): aquí entrará el simulador de capacidad —
    espacio libre − acumulación programada + liberaciones previstas + reclamable—
    que recortará este valor al mayor plazo que el disco pueda sostener.
    """
    if resource.retencion_permanente:
        return None
    tope = resource.retencion_ttl_dias
    if solicitada_dias is None:
        return tope
    if tope is None:
        return solicitada_dias
    return min(solicitada_dias, tope)


def conceder_lease(session, resource: Resource, *, titular_tipo: str,
                   titular_id=None, email: Optional[str] = None,
                   dataset: Optional[Dataset] = None,
                   solicitada_dias: Optional[int] = None,
                   ahora: Optional[datetime] = None) -> DatasetLease:
    """Concede un arrendamiento. El plazo sale de `plazo_concedible`; si es None
    (permanente o sin tope), el lease no expira por tiempo."""
    ahora = ahora or datetime.utcnow()
    dias = plazo_concedible(resource, solicitada_dias, ahora)
    permanente = resource.retencion_permanente
    hasta = None if (permanente or dias is None) else ahora + timedelta(days=dias)
    lease = DatasetLease(
        resource_id=resource.id,
        dataset_id=(dataset.id if dataset else None),
        titular_tipo=titular_tipo, titular_id=titular_id, email_contacto=email,
        retencion_solicitada_dias=solicitada_dias, permanente=permanente,
        concedido_hasta=hasta, estado=ESTADO_ACTIVO, created_at=ahora,
    )
    session.add(lease)
    session.flush()
    return lease


def liberar_lease(session, lease: DatasetLease,
                  ahora: Optional[datetime] = None) -> DatasetLease:
    """Liberación anticipada por el proceso consumidor o por el usuario: el lease
    deja de retener. Es lo mismo por dentro venga de donde venga."""
    lease.estado = ESTADO_LIBERADO
    lease.released_at = ahora or datetime.utcnow()
    session.flush()
    return lease


def leases_activos(session, dataset_id, ahora: Optional[datetime] = None) -> List[DatasetLease]:
    """Leases que aún retienen este dataset (permanentes o no expirados)."""
    ahora = ahora or datetime.utcnow()
    q = session.query(DatasetLease).filter(
        DatasetLease.dataset_id == dataset_id,
        DatasetLease.estado == ESTADO_ACTIVO,
    )
    return [l for l in q if l.permanente or l.concedido_hasta is None or l.concedido_hasta > ahora]


def _pinned(session, resource_id) -> bool:
    """¿Algún suscriptor ha fijado una versión de este recurso? (candado duro).
    Afinar más adelante: comparar el `pinned_version` con la semver del dataset."""
    return session.query(ResourceSubscription).filter(
        ResourceSubscription.resource_id == resource_id,
        ResourceSubscription.pinned_version.isnot(None),
    ).first() is not None


def datasets_desalojables(session, ahora: Optional[datetime] = None) -> List[Dataset]:
    """Candidatos que el recolector puede desalojar con seguridad: solo de recursos
    re-derivables y no permanentes, conservando siempre las `retencion_min_versiones`
    más nuevas, y excluyendo los que tengan lease activo o versión fijada.

    El orden de prioridad de desalojo (demanda, coste de rehacer) lo aplicará el
    recolector sobre esta lista en la siguiente capa.
    """
    ahora = ahora or datetime.utcnow()
    candidatos: List[Dataset] = []
    recursos = session.query(Resource).filter(Resource.deleted_at.is_(None)).all()
    for r in recursos:
        if r.retencion_permanente or not r.rederivable:
            continue  # no se toca lo permanente ni lo que no se puede recuperar
        ds = (session.query(Dataset)
              .filter(Dataset.resource_id == r.id)
              .order_by(Dataset.major_version.desc(), Dataset.minor_version.desc(),
                        Dataset.patch_version.desc())
              .all())
        if _pinned(session, r.id):
            continue  # candado: hay versión fijada, no desalojar de este recurso
        for d in ds[max(r.retencion_min_versiones, 0):]:  # conserva las N más nuevas
            if leases_activos(session, d.id, ahora):
                continue
            candidatos.append(d)
    return candidatos
