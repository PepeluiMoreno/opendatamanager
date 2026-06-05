"""Fuentes de valores de pivote para fetchers con recorrido por valor (pivot_loop).

Hoy una sola fuente: el propio almacén de ODM vía la API GraphQL de datos
(`pivot_source_odmgr_query`). Compartido por HTMLFetcher y RESTFetcher para que
un recurso pueda iterar sobre los valores de un dataset ya cosechado (p. ej.
códigos DIR3 del catálogo oficial contra /organos/codigo de BDNS).

Params reconocidos:
  pivot_source_odmgr_query  — nombre de la query GraphQL del dataset fuente
  pivot_source_field        — campo del item cuyo valor se itera
  pivot_source_filter_field — (opcional) campo de filtro
  pivot_source_filter_value — (opcional) valor del filtro
  pivot_source_odmgr_url    — (opcional) endpoint; default env ODMGR_DATA_URL
"""
import os
from typing import Any, Dict, List

import requests


def pivots_from_odmgr(params: Dict[str, Any]) -> List[Any]:
    """Devuelve la lista de valores (sin duplicados, en orden de aparición) del
    campo `pivot_source_field` de la query `pivot_source_odmgr_query`."""
    query_name = params.get("pivot_source_odmgr_query")
    field = params.get("pivot_source_field")
    if not query_name or not field:
        raise ValueError(
            "pivot_source_odmgr_query requiere también 'pivot_source_field'"
        )
    base = (params.get("pivot_source_odmgr_url")
            or os.environ.get("ODMGR_DATA_URL", "http://localhost:8000/graphql/data"))
    ff = params.get("pivot_source_filter_field", "")
    fv = params.get("pivot_source_filter_value", "")
    limit, offset, out = 5000, 0, []
    while True:
        farg = f', {ff}: "{fv}"' if ff and fv else ""
        gql = f"{{ {query_name}(limit: {limit}, offset: {offset}{farg}) {{ total items {{ {field} }} }} }}"
        body = requests.post(base, json={"query": gql}, timeout=30).json()
        if "errors" in body:
            raise ValueError(f"Fuente de pivotes ODM: {body['errors'][0].get('message')}")
        page = body["data"][query_name]
        out.extend(it[field] for it in page["items"] if it.get(field))
        offset += limit
        if offset >= page["total"]:
            break
    seen = set()
    return [v for v in out if not (v in seen or seen.add(v))]
