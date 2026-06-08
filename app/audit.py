"""Estampado automático de auditoría (AuditMixin) en cada transacción.

Un ContextVar guarda el id del usuario/aplicación de la petición en curso. Un
listener ``before_flush`` rellena ``created_by_id`` en filas nuevas y
``updated_by_id`` en filas modificadas de cualquier modelo que use ``AuditMixin``
— sin que cada mutation tenga que acordarse de hacerlo. ``created_at``/``updated_at``
los gestiona el propio mixin (default / onupdate).

Para activarlo basta importar este módulo una vez al arrancar (lo hace main.py)
y fijar el usuario por petición con ``set_usuario_actual(...)``.
"""
from contextvars import ContextVar

from sqlalchemy import event
from sqlalchemy.orm import Session

from app.models import AuditMixin

# Id del usuario/aplicación de la petición en curso (None para invitado/sistema).
usuario_actual_id: ContextVar = ContextVar("usuario_actual_id", default=None)


def set_usuario_actual(uid) -> None:
    """Fija el principal de la petición en curso (llamar desde el contexto)."""
    usuario_actual_id.set(uid)


@event.listens_for(Session, "before_flush")
def _estampar_auditoria(session, flush_context, instances):
    uid = usuario_actual_id.get()
    if uid is None:
        return
    for obj in session.new:
        if isinstance(obj, AuditMixin):
            if getattr(obj, "created_by_id", None) is None:
                obj.created_by_id = uid
            if getattr(obj, "updated_by_id", None) is None:
                obj.updated_by_id = uid
    for obj in session.dirty:
        if isinstance(obj, AuditMixin) and session.is_modified(obj, include_collections=False):
            obj.updated_by_id = uid
