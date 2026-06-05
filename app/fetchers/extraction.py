"""Categoría de variación: EXTRACCIÓN.

Aísla "dónde están los registros en la respuesta y cómo se aplanan" como un
vocabulario de estrategias con nombre, sobre un payload YA decodificado (objetos
Python: list/dict de JSON). Igual que el registro de paginación, es PURO y
testeable; los fetchers genéricos lo consumen vía el parámetro `extraction`.

Estrategias:
  passthrough     — los registros tal cual (tras seleccionar la lista).
  field_map       — aplana cada registro con {salida: ruta.con.puntos}.
  timeseries_long — formato largo estadístico (dimensiones + puntos de datos).
  bindings        — resultados SPARQL (results.bindings: {var:{value}} -> {var:value}).
"""
from typing import Any, Dict, List, Optional


def _dig(obj: Any, path: Optional[str]):
    if not path:
        return obj
    cur = obj
    for key in str(path).split("."):
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return None
    return cur


def _records(payload: Any, content_field: Optional[str]) -> List[Any]:
    """Localiza la lista de registros. Si el payload ya es lista, se usa tal cual
    (idempotente: no re-selecciona aunque haya content_field)."""
    if isinstance(payload, list):
        return payload
    if content_field:
        val = _dig(payload, content_field)
        return val if isinstance(val, list) else []
    return []


def _passthrough(payload, params):
    return list(_records(payload, params.get("content_field")))


def _field_map(payload, params):
    fmap = params.get("field_map") or {}
    if isinstance(fmap, str):
        import json
        fmap = json.loads(fmap) if fmap.strip() else {}
    out = []
    for rec in _records(payload, params.get("content_field")):
        if isinstance(rec, dict):
            out.append({salida: _dig(rec, ruta) for salida, ruta in fmap.items()})
        else:
            out.append(rec)
    return out


def _timeseries_long(payload, params):
    """Formato largo: cada serie aporta sus dimensiones y, por cada punto de datos,
    una fila {**dimensiones, periodo, valor}. Generaliza el patrón tipo INE Tempus."""
    series = _records(payload, params.get("content_field"))
    meta_container = params.get("meta_container", "MetaData")
    meta_dim_path = params.get("meta_dim_path", "Variable.Codigo")
    meta_name_field = params.get("meta_name_field", "Nombre")
    data_container = params.get("data_container", "Data")
    period_field = params.get("period_field", "Anyo")
    subperiod_field = params.get("subperiod_field", "")
    value_field = params.get("value_field", "Valor")

    filas = []
    for serie in series:
        if not isinstance(serie, dict):
            continue
        dims = {}
        for m in (serie.get(meta_container) or []):
            if isinstance(m, dict):
                code = _dig(m, meta_dim_path)
                if code is not None:
                    dims[str(code)] = m.get(meta_name_field)
        for punto in (serie.get(data_container) or []):
            if not isinstance(punto, dict):
                continue
            fila = dict(dims)
            fila["periodo"] = punto.get(period_field)
            if subperiod_field:
                fila["subperiodo"] = punto.get(subperiod_field)
            fila["valor"] = punto.get(value_field)
            filas.append(fila)
    return filas


def _bindings(payload, params):
    """SPARQL: results.bindings = [{var: {"value": v, ...}}] -> [{var: v}]."""
    binds = _dig(payload, params.get("bindings_path", "results.bindings")) or []
    out = []
    for b in binds:
        if isinstance(b, dict):
            out.append({k: (v.get("value") if isinstance(v, dict) else v) for k, v in b.items()})
    return out


REGISTRO = {
    "passthrough": _passthrough,
    "none": _passthrough,
    "field_map": _field_map,
    "timeseries_long": _timeseries_long,
    "bindings": _bindings,
}


def extract(nombre: Optional[str], payload: Any, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Aplica la estrategia de extracción. Desconocida/vacía → passthrough."""
    fn = REGISTRO.get((nombre or "passthrough").lower(), _passthrough)
    return fn(payload, params)
