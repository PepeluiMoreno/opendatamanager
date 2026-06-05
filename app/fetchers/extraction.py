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


def _tree_flatten(payload, params):
    """Aplana una respuesta arbórea en una fila por nodo, conservando TODOS los
    campos propios del nodo (norma general: no se descarta información) más la
    jerarquía: nivel, id/descripción del padre y ruta completa de descripciones.
    Caso típico: /organos de BDNS (ministerio → órgano → subórgano).

    Params:
      children_field — campo con los hijos (default: 'children')
      label_field    — campo descriptivo para componer la ruta (default: 'descripcion')
      id_field_tree  — campo identificador del nodo (default: 'id')
      path_separator — separador de la ruta (default: ' > ')
    """
    hijos_f = params.get("children_field", "children")
    label_f = params.get("label_field", "descripcion")
    id_f = params.get("id_field_tree", "id")
    sep = params.get("path_separator", " > ")
    out: List[Dict[str, Any]] = []

    def _walk(nodo, nivel, padre, ruta):
        if not isinstance(nodo, dict):
            return
        propios = {k: v for k, v in nodo.items() if k != hijos_f}
        etiqueta = nodo.get(label_f)
        ruta_aqui = ruta + [str(etiqueta)] if etiqueta is not None else list(ruta)
        fila = dict(propios)
        fila["nivel"] = nivel
        fila["padre_id"] = padre.get(id_f) if isinstance(padre, dict) else None
        fila["padre_descripcion"] = padre.get(label_f) if isinstance(padre, dict) else None
        fila["ruta"] = sep.join(ruta_aqui)
        out.append(fila)
        hijos = nodo.get(hijos_f)
        if isinstance(hijos, dict):
            hijos = [hijos]
        for h in (hijos or []):
            _walk(h, nivel + 1, nodo, ruta_aqui)

    for raiz in _records(payload, params.get("content_field")):
        _walk(raiz, 0, None, [])
    return out


REGISTRO = {
    "passthrough": _passthrough,
    "none": _passthrough,
    "field_map": _field_map,
    "timeseries_long": _timeseries_long,
    "bindings": _bindings,
    "tree_flatten": _tree_flatten,
}


def extract(nombre: Optional[str], payload: Any, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Aplica la estrategia de extracción. Desconocida/vacía → passthrough.
    Si params trae 'const_fields' (dict o JSON), sus pares se añaden a cada fila
    (campos constantes de contexto del recurso, p. ej. tipo_admon en BDNS)."""
    fn = REGISTRO.get((nombre or "passthrough").lower(), _passthrough)
    filas = fn(payload, params)
    const = params.get("const_fields")
    if isinstance(const, str) and const.strip():
        import json
        try:
            const = json.loads(const)
        except ValueError:
            const = None
    if isinstance(const, dict) and const:
        filas = [{**f, **const} if isinstance(f, dict) else f for f in filas]
    return filas
