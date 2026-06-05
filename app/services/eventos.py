"""Eventos de novedades y su despacho por email (digest).

`registrar_evento` lo llaman el import de manifiestos y la detección de cambios
de origen. `enviar_digest` agrupa los no notificados y los manda a los usuarios
suscritos (notificar_email=True con email).
"""
import logging
from typing import Optional

from app.models import Evento, Usuario
from app.services.mailer import enviar_email, smtp_configurado

logger = logging.getLogger(__name__)

_ETIQUETAS = {
    "recurso.alta": "Nuevo recurso",
    "recurso.baja": "Recurso dado de baja (cambio en el origen)",
    "recurso.conflicto": "Conflicto de sincronización",
    "ejecucion.fallo": "Fallo de ejecución",
}


def registrar_evento(session, tipo: str, titulo: str, recurso=None, detalle: Optional[dict] = None) -> None:
    session.add(Evento(
        tipo=tipo,
        titulo=titulo,
        recurso_id=getattr(recurso, "id", None) if recurso is not None else None,
        detalle=detalle,
    ))


def _render(eventos) -> str:
    lineas = ["Novedades en OpenDataManager:", ""]
    for e in eventos:
        etiqueta = _ETIQUETAS.get(e.tipo, e.tipo)
        lineas.append(f"• [{etiqueta}] {e.titulo}")
    lineas += ["", "— OpenDataManager"]
    return "\n".join(lineas)


def enviar_digest(session) -> dict:
    """Despacha los eventos pendientes. Devuelve un resumen.

    - Sin suscriptores → marca notificados (no acumular).
    - Suscriptores pero SMTP sin configurar → deja pendientes (saldrán al configurarlo).
    - Suscriptores + SMTP → envía y marca los enviados con éxito.
    """
    pendientes = (
        session.query(Evento)
        .filter(Evento.notificado.is_(False))
        .order_by(Evento.created_at)
        .all()
    )
    if not pendientes:
        return {"eventos": 0, "emails": 0}

    suscriptores = [
        u.email for u in session.query(Usuario).filter(
            Usuario.is_active.is_(True),
            Usuario.notificar_email.is_(True),
            Usuario.email.isnot(None),
        ).all() if u.email
    ]

    if not suscriptores:
        for e in pendientes:
            e.notificado = True
        session.commit()
        return {"eventos": len(pendientes), "emails": 0, "nota": "sin suscriptores"}

    if not smtp_configurado():
        logger.warning("[eventos] %d evento(s) pendientes pero SMTP sin configurar.", len(pendientes))
        return {"eventos": len(pendientes), "emails": 0, "nota": "SMTP sin configurar"}

    asunto = f"OpenDataManager — {len(pendientes)} novedad(es)"
    cuerpo = _render(pendientes)
    enviados = sum(1 for d in suscriptores if enviar_email(d, asunto, cuerpo))
    if enviados:
        for e in pendientes:
            e.notificado = True
        session.commit()
    return {"eventos": len(pendientes), "emails": enviados}
