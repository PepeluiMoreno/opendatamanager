"""Categoría de variación: CONSTRUCCIÓN DE LA PETICIÓN.

Aísla "qué se envía" (método + cuerpo + cabeceras de contenido) como un vocabulario
de estrategias con nombre. Es lo último que separa a REST Loop (POST con plantilla
+ pivote) de la especie REST, y deja el terreno para GraphQL/SPARQL/SOAP.

Cada estrategia, dado el bloque de parámetros y el valor de pivote actual (si lo
hay, viene de la paginación pivot_loop), devuelve un dict normalizado:
    {"method": "GET"|"POST", "json": dict|None, "data": dict|str|None, "headers": {}}
El fetcher fusiona estas cabeceras con las suyas y reenvía json/data a requests.

PURO y testeable (no hace HTTP).
"""
import json as _json
from typing import Any, Dict, Optional


def _sub_pivot(texto: str, pivot: Optional[str]) -> str:
    return texto.replace("{pivot}", str(pivot)) if (pivot is not None and texto) else texto


def _plantilla_a_dict(template: Any, pivot: Optional[str]) -> Any:
    """Sustituye {pivot} en una plantilla (dict o str JSON) y devuelve el dict."""
    if isinstance(template, dict):
        crudo = _sub_pivot(_json.dumps(template), pivot)
        return _json.loads(crudo)
    if isinstance(template, str) and template.strip():
        return _json.loads(_sub_pivot(template, pivot))
    return {}


def _query(params, pivot):
    return {"method": (params.get("method", "GET") or "GET").upper(),
            "json": None, "data": None, "headers": {}}


def _json_body(params, pivot):
    body = _plantilla_a_dict(params.get("payload_template") or params.get("body") or {}, pivot)
    return {"method": (params.get("method", "POST") or "POST").upper(),
            "json": body, "data": None, "headers": {}}


def _form(params, pivot):
    body = _plantilla_a_dict(params.get("payload_template") or params.get("body") or {}, pivot)
    return {"method": (params.get("method", "POST") or "POST").upper(),
            "json": None, "data": body, "headers": {}}


def _graphql(params, pivot):
    query = _sub_pivot(params.get("graphql_query", "") or "", pivot)
    variables = params.get("graphql_variables") or {}
    if isinstance(variables, str):
        variables = _json.loads(variables) if variables.strip() else {}
    return {"method": "POST",
            "json": {"query": query, "variables": variables},
            "data": None, "headers": {"Content-Type": "application/json"}}


def _sparql(params, pivot):
    query = _sub_pivot(params.get("sparql_query", "") or "", pivot)
    return {"method": (params.get("method", "POST") or "POST").upper(),
            "json": None, "data": {"query": query},
            "headers": {"Accept": "application/sparql-results+json"}}


def _form_submit(params, pivot):
    """Envío de formulario HTML: cuerpo = hidden inputs descubiertos + campo de búsqueda
    con el valor de pivote + extras. El descubrimiento de hidden inputs/action lo hace
    el fetcher (es HTTP); aquí solo se ensambla el cuerpo."""
    body = dict(_plantilla_a_dict(params.get("form_hidden") or {}, None))
    field = params.get("search_field_name")
    if field and pivot is not None:
        body[field] = pivot
    body.update(_plantilla_a_dict(params.get("form_extra") or {}, pivot))
    return {"method": (params.get("method", "POST") or "POST").upper(),
            "json": None, "data": body, "headers": {}}


REGISTRO = {
    "query": _query,
    "none": _query,
    "json_body": _json_body,
    "form": _form,
    "form_submit": _form_submit,
    "graphql": _graphql,
    "sparql": _sparql,
}


def build_request(nombre: Optional[str], params: Dict[str, Any], pivot: Optional[str] = None) -> Dict[str, Any]:
    fn = REGISTRO.get((nombre or "query").lower(), _query)
    return fn(params, pivot)
