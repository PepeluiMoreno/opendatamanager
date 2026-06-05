"""Vigilante de salud de fuentes.

Detecta la "baja por cambio en el origen": cuando las últimas ejecuciones de un
recurso fallan de forma sostenida (la fuente desapareció, cambió de formato o
dejó de responder), marca `source_status='baja'` y emite `recurso.baja` UNA vez
(en la transición). Si vuelve a completar con éxito, se recupera (`ok`) y emite
`recurso.recuperado`.

No desactiva el recurso (no toca `active`): así el scheduler lo sigue intentando
y la recuperación es detectable. La baja es un AVISO, no un apagado.
"""
import logging

from app.models import Resource, ResourceExecution
from app.services.eventos import registrar_evento

logger = logging.getLogger(__name__)

UMBRAL_FALLOS = 3  # nº de ejecuciones recientes que deben fallar para declarar baja


def revisar_salud_fuentes(session, umbral: int = UMBRAL_FALLOS) -> dict:
    """Recorre los recursos activos y transiciona su `source_status` según las
    últimas ejecuciones. Devuelve un resumen {bajas, recuperaciones}."""
    bajas = recuperaciones = 0
    recursos = session.query(Resource).filter(
        Resource.active.is_(True),
        Resource.deleted_at.is_(None),
    ).all()

    for r in recursos:
        ultimas = (
            session.query(ResourceExecution)
            .filter(
                ResourceExecution.resource_id == r.id,
                ResourceExecution.status.in_(("completed", "failed")),
            )
            .order_by(ResourceExecution.started_at.desc())
            .limit(umbral)
            .all()
        )
        if not ultimas:
            continue

        todas_fallan = len(ultimas) >= umbral and all(e.status == "failed" for e in ultimas)
        ultima_ok = ultimas[0].status == "completed"
        estado = r.source_status or "ok"

        if todas_fallan and estado != "baja":
            r.source_status = "baja"
            registrar_evento(
                session, "recurso.baja", r.name, r,
                {"motivo": "origen sin respuesta", "fallos_consecutivos": len(ultimas)},
            )
            bajas += 1
            logger.warning("[salud] baja por origen: %s", r.name)
        elif ultima_ok and estado == "baja":
            r.source_status = "ok"
            registrar_evento(
                session, "recurso.recuperado", r.name, r,
                {"motivo": "el origen vuelve a responder"},
            )
            recuperaciones += 1
            logger.info("[salud] recuperado: %s", r.name)

    session.commit()
    return {"bajas": bajas, "recuperaciones": recuperaciones, "revisados": len(recursos)}
