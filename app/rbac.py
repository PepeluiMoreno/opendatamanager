"""Enforcement RBAC en GraphQL.

Catálogo de transacciones (operación → funcionalidad requerida) al estilo del
RBAC de SIGA, y una clase de permiso de Strawberry parametrizada por código.

Las consultas (lectura) quedan abiertas al invitado salvo redacción de campos
sensibles (que se aplica en los resolvers). Las mutaciones son fail-closed:
sin la funcionalidad requerida en los permisos del contexto, se deniega.
"""
from typing import Any

try:
    from strawberry.permission import BasePermission
except ImportError:  # entorno de tests sin strawberry instalado
    class BasePermission:  # type: ignore
        pass

# Operación GraphQL (nombre del método del resolver) → funcionalidad requerida.
MAPA_TRANSACCIONES = {
    # Recursos
    "create_resource": "recursos.crear",
    "import_manifest": "recursos.crear",
    "clone_resource": "recursos.crear",
    "update_resource": "recursos.editar",
    "delete_resource": "recursos.borrar",
    "restore_resource": "recursos.borrar",
    # Candidatos (flujo de alta de recursos)
    "promote_candidate": "recursos.crear",
    "discard_candidate": "recursos.crear",
    "merge_candidates": "recursos.crear",
    "split_candidate": "recursos.crear",
    # Ejecuciones (lanzar/parar reales → admin)
    "execute_resource": "ejecuciones.lanzar",
    "execute_all_resources": "ejecuciones.lanzar",
    "abort_execution": "ejecuciones.parar",
    "pause_execution": "ejecuciones.parar",
    "resume_execution": "ejecuciones.lanzar",
    "delete_execution": "ejecuciones.parar",
    "restore_execution": "ejecuciones.lanzar",
    # Fetchers (motor → admin)
    "create_fetcher": "fetchers.gestionar",
    "update_fetcher": "fetchers.gestionar",
    "delete_fetcher": "fetchers.gestionar",
    "restore_fetcher": "fetchers.gestionar",
    "create_type_fetcher_param": "fetchers.gestionar",
    "update_type_fetcher_param": "fetchers.gestionar",
    "delete_type_fetcher_param": "fetchers.gestionar",
    # Programación / datasets derivados (automatización → admin)
    "create_derived_dataset_config": "programacion.gestionar",
    "update_derived_dataset_config": "programacion.gestionar",
    "delete_derived_dataset_config": "programacion.gestionar",
    "toggle_derived_dataset_config": "programacion.gestionar",
    # Publishers
    "create_publisher": "publishers.gestionar",
    "update_publisher": "publishers.gestionar",
    "delete_publisher": "publishers.gestionar",
    "restore_publisher": "publishers.gestionar",
    # Aplicaciones y suscripciones
    "create_application": "aplicaciones.gestionar",
    "update_application": "aplicaciones.gestionar",
    "delete_application": "aplicaciones.gestionar",
    "activate_application": "aplicaciones.gestionar",
    "set_application_webhook": "aplicaciones.gestionar",
    "remove_application_webhook": "aplicaciones.gestionar",
    "restore_application": "aplicaciones.gestionar",
    "subscribe_resource": "aplicaciones.gestionar",
    "unsubscribe_resource": "aplicaciones.gestionar",
    # Configuración
    "set_config": "settings.gestionar",
    # Consulta de prueba (operador puede testar sin persistir)
    "preview_resource_data": "recursos.testar",
}


def requiere(code: str):
    """Devuelve una clase de permiso de Strawberry que exige `code` en los
    permisos efectivos del contexto."""

    class _PermisoRequerido(BasePermission):
        message = "No autorizado para esta operación."

        def has_permission(self, source: Any, info: Any, **kwargs) -> bool:
            permisos = set()
            ctx = getattr(info, "context", None)
            if ctx is not None:
                permisos = ctx.get("permisos", set()) if isinstance(ctx, dict) else getattr(ctx, "permisos", set())
            return code in permisos

    _PermisoRequerido.__name__ = f"Requiere_{code.replace('.', '_')}"
    return _PermisoRequerido


# ── Redacción de datos sensibles en lecturas ─────────────────────────────
import re as _re

_CLAVES_SENSIBLES = _re.compile(
    r"(token|secret|password|passwd|api[_-]?key|apikey|authorization|"
    r"client[_-]?secret|cookie|credential|bearer)",
    _re.I,
)
_REDACTADO = "•••redactado•••"


def es_clave_sensible(nombre: str) -> bool:
    return bool(_CLAVES_SENSIBLES.search(nombre or ""))


def puede(info: Any, code: str) -> bool:
    ctx = getattr(info, "context", None) or {}
    permisos = ctx.get("permisos", set()) if isinstance(ctx, dict) else getattr(ctx, "permisos", set())
    return code in permisos


def _redactar_dict(d):
    return {k: (_REDACTADO if es_clave_sensible(str(k)) else v) for k, v in d.items()}


def redactar_recurso(rt) -> None:
    """Enmascara valores de params con nombre sensible (y claves sensibles
    dentro de params tipo dict, p. ej. headers con Authorization)."""
    for p in (getattr(rt, "params", None) or []):
        nombre = getattr(p, "param_name", "") or ""
        valor = getattr(p, "param_value", None)
        if es_clave_sensible(nombre):
            p.param_value = _REDACTADO
        elif isinstance(valor, dict):
            p.param_value = _redactar_dict(valor)


def redactar_ejecucion(et) -> None:
    ep = getattr(et, "execution_params", None)
    if isinstance(ep, dict):
        et.execution_params = _redactar_dict(ep)
