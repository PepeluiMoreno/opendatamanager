"""Enforcement RBAC en GraphQL.

Catálogo de transacciones (operación → funcionalidad requerida) al estilo del
RBAC de SIGA, y una clase de permiso de Strawberry parametrizada por código.

Las consultas (lectura) quedan abiertas al invitado salvo redacción de campos
sensibles (que se aplica en los resolvers). Las mutaciones son fail-closed:
sin la funcionalidad requerida en los permisos del contexto, se deniega.
"""
from typing import Any

from strawberry.permission import BasePermission

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
