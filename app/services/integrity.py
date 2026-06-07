"""Integridad del contrato frente a suscriptores (política *fail-safe*).

Un recurso con **suscripciones activas** no debe sufrir cambios que *puedan*
romper su contrato de extracción (fetcher, preset o params). En vez de arriesgar
una rotura silenciosa aguas abajo, ODM **bloquea** el cambio en el momento de la
edición y sugiere **clonar** el recurso: el clon nace sin suscriptores y sobre él
se aplica la modificación; los consumidores migran cuando quieren. Lo mismo al
borrar un recurso suscrito o al editar los params de un preset que usan recursos
suscritos (el cambio se propagaría a todos).

Es conservador a propósito: como los fetchers no declaran (todavía) un esquema de
params, cualquier cambio del contrato se trata como potencialmente rompedor.
"""
from __future__ import annotations

from typing import Any


def active_subscription_count(session, resource_id) -> int:
    """Nº de suscripciones vivas (no borradas) de Applications activas a un recurso."""
    from app.models import Application, DatasetSubscription
    return (
        session.query(DatasetSubscription)
        .join(Application, Application.id == DatasetSubscription.application_id)
        .filter(
            DatasetSubscription.resource_id == resource_id,
            DatasetSubscription.deleted_at.is_(None),
            Application.active.is_(True),
        )
        .count()
    )


def preset_active_subscription_count(session, preset_id) -> int:
    """Suma de suscripciones activas sobre los recursos vivos que usan un preset."""
    from app.models import Resource
    recursos = (
        session.query(Resource)
        .filter(Resource.preset_id == preset_id, Resource.deleted_at.is_(None))
        .all()
    )
    return sum(active_subscription_count(session, r.id) for r in recursos)


def _current_params(session, resource_id) -> dict:
    from app.models import ResourceParam
    return {p.key: p.value for p in
            session.query(ResourceParam).filter(ResourceParam.resource_id == resource_id)}


def contract_changes(resource, input, current_params: dict) -> set:
    """Partes del CONTRATO de extracción que un UpdateResourceInput modifica:
    'fetcher', 'preset', 'params'. Pura. (name/description/active/schedule/
    target_table/publisher NO son contrato.)"""
    changes: set[str] = set()

    new_fetcher = getattr(input, "fetcher_id", None)
    if new_fetcher is not None and str(new_fetcher) != str(resource.fetcher_id):
        changes.add("fetcher")

    new_preset = getattr(input, "preset_id", None)
    if new_preset is not None:
        nuevo = None if new_preset == "" else str(new_preset)
        actual = str(resource.preset_id) if getattr(resource, "preset_id", None) else None
        if nuevo != actual:
            changes.add("preset")

    new_params = getattr(input, "params", None)
    if new_params is not None:
        nuevos = {p.key: p.value for p in new_params}
        if nuevos != (current_params or {}):
            changes.add("params")

    return changes


def guard_resource_update(session, resource, input) -> None:
    """Bloquea un update que cambie el contrato de un recurso con suscripciones activas."""
    changes = contract_changes(resource, input, _current_params(session, resource.id))
    if not changes:
        return
    n = active_subscription_count(session, resource.id)
    if n:
        raise ValueError(
            f"Cambio bloqueado: el recurso '{resource.name}' tiene {n} suscripción(es) "
            f"activa(s) y el cambio afecta a su contrato de extracción "
            f"({', '.join(sorted(changes))}). Clónalo (cloneResource) y aplica el cambio "
            f"al clon, o desuscribe primero a los consumidores."
        )


def guard_resource_delete(session, resource) -> None:
    """Bloquea borrar un recurso con suscripciones activas."""
    n = active_subscription_count(session, resource.id)
    if n:
        raise ValueError(
            f"Borrado bloqueado: el recurso '{resource.name}' tiene {n} suscripción(es) "
            f"activa(s). Desuscribe a los consumidores antes de eliminarlo."
        )


def guard_preset_update(session, preset, *, changing_contract: bool) -> None:
    """Bloquea editar los params de un preset si lo usan recursos con suscripciones activas."""
    if not changing_contract:
        return
    n = preset_active_subscription_count(session, preset.id)
    if n:
        raise ValueError(
            f"Cambio bloqueado: el preset '{preset.code}' lo usan recursos con {n} "
            f"suscripción(es) activa(s); editar sus params los afectaría a todos. Crea un "
            f"preset nuevo (createFetcherPreset) y reapunta/clona los recursos al nuevo."
        )
