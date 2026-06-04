"""
Soporte de fetch incremental (opt-in por recurso).

Objetivo: traer solo lo nuevo desde la última versión, en lugar de un full pull
cada vez (p. ej. BDNS baja 1,56M filas enteras en cada ejecución).

Diseño deliberadamente NO invasivo y sin inventar comportamiento por fuente:

  - Un recurso declara su soporte incremental con dos ResourceParam:
      incremental_field : nombre del campo del dataset cuyo máximo es el watermark
                          (p. ej. "fecha_alta", "last_modified", "id").
      incremental_param : nombre EXACTO del parámetro que la fuente entiende para
                          "desde" (p. ej. "fechaDesde", "since", "modified-after").
                          Lo declara el operador porque solo él sabe si la fuente
                          lo soporta; sin este param, no se inyecta nada.

  - Antes de ejecutar, el manager calcula el watermark (máximo de incremental_field
    en el último dataset) e inyecta {incremental_param: watermark} en los
    execution_params. Los fetchers que entienden ese param lo usan; el resto lo
    ignoran. Si el recurso no declara incremental_param, todo sigue como full pull.

Este módulo expone el cálculo del watermark. La inyección en el manager es el
único punto de integración y se activa solo cuando ambos params están presentes.
"""
from typing import Any, Dict, List, Optional


def max_watermark(records: List[Dict[str, Any]], field: str) -> Optional[Any]:
    """Máximo valor (no nulo) de `field` sobre una lista de registros.

    Función pura y testeable. Devuelve None si no hay valores.
    """
    valores = [r.get(field) for r in records if isinstance(r, dict) and r.get(field) is not None]
    if not valores:
        return None
    try:
        return max(valores)
    except TypeError:
        # Tipos heterogéneos: comparar como cadenas (orden lexicográfico estable
        # para fechas ISO y para ids con ceros a la izquierda).
        return max(valores, key=lambda v: str(v))


def resource_incremental_config(resource) -> Optional[Dict[str, str]]:
    """Devuelve {'field':..., 'param':...} si el recurso declara incremental, o None."""
    params = {p.key: p.value for p in (getattr(resource, "params", None) or [])}
    field = params.get("incremental_field")
    param = params.get("incremental_param")
    if field and param:
        return {"field": field, "param": param}
    return None


def compute_watermark(session, resource) -> Optional[Any]:
    """Watermark = máximo de incremental_field en el último dataset del recurso.

    Server-side y defensivo: devuelve None ante cualquier problema (sin dataset
    previo, fichero ausente, campo inexistente), de modo que el recurso recae con
    seguridad en un full pull.
    """
    cfg = resource_incremental_config(resource)
    if not cfg:
        return None
    try:
        import json
        from app.models import Dataset

        latest = (
            session.query(Dataset)
            .filter(Dataset.resource_id == resource.id)
            .filter(Dataset.deleted_at.is_(None))
            .order_by(
                Dataset.major_version.desc(),
                Dataset.minor_version.desc(),
                Dataset.patch_version.desc(),
            )
            .first()
        )
        if not latest or not latest.data_path:
            return None
        records: List[Dict[str, Any]] = []
        with open(latest.data_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return max_watermark(records, cfg["field"])
    except Exception:
        return None
