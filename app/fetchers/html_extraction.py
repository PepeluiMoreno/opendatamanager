"""Categoría de variación EXTRACCIÓN, sabor HTML.

El primo HTML de `extraction.py`: convierte un documento HTML en registros planos
mediante selectores CSS. Unifica el dialecto de selección que hoy está duplicado y
divergente entre las clases html / paginated_html / searchloop_html / url_loop_html.
PURO y testeable (bs4 sobre una cadena HTML).

Estrategias:
  fields — un registro por fila (rows_selector) o uno por documento (sin él),
           con cuatro tipos de selector de campo:
             field_selectors        {campo: css}              → texto del primer match
             field_attr_selectors    {campo: {selector, attr}} → atributo (p. ej. href)
             field_all_selectors      {campo: css}              → todos los matches, unidos
             field_label_selectors    {campo: {container, label}} → valor junto a una etiqueta
  table  — tabla HTML → registros (cabecera + celdas td).
"""
import json
import re
from typing import Any, Dict, List
from bs4 import BeautifulSoup


def _clean(s):
    return re.sub(r"\s+", " ", s).strip() if s else s


def _text(el):
    return _clean(el.get_text(strip=True)) if el else None


def _as_dict(v) -> Dict[str, Any]:
    if isinstance(v, str):
        return json.loads(v) if v.strip() else {}
    return v or {}


def _record_from(scope, params: Dict[str, Any]) -> Dict[str, Any]:
    """Extrae un registro de un ámbito (una fila o el documento entero)."""
    rec: Dict[str, Any] = {}
    sep = params.get("field_all_separator", " | ")

    for field, sel in _as_dict(params.get("field_selectors")).items():
        rec[field] = _text(scope.select_one(sel))

    for field, cfg in _as_dict(params.get("field_attr_selectors")).items():
        el = scope.select_one(cfg.get("selector", ""))
        rec[field] = el.get(cfg.get("attr", "href")) if el else None

    for field, sel in _as_dict(params.get("field_all_selectors")).items():
        els = scope.select(sel)
        rec[field] = sep.join(_text(e) for e in els) if els else None

    # alias de field_all_selectors usado por url_loop
    for field, sel in _as_dict(params.get("field_all_text")).items():
        els = scope.select(sel)
        rec[field] = sep.join(_text(e) for e in els) if els else None

    # atributo en el propio elemento de la fila/ámbito (p. ej. data-id) — url_loop
    for field, attr in _as_dict(params.get("field_attrs")).items():
        rec[field] = scope.get(attr) if hasattr(scope, "get") else None

    for field, cfg in _as_dict(params.get("field_label_selectors")).items():
        container = scope.select_one(cfg.get("container", "body")) or scope
        label = (cfg.get("label", "") or "").lower()
        rec[field] = None
        for sp in container.find_all(["span", "strong", "b", "dt"]):
            if label in sp.get_text(strip=True).lower():
                sib = sp.find_next_sibling()
                rec[field] = _text(sib) if sib else None
                break
    return rec


def _fields(html: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html or "", "html.parser")
    rows_selector = params.get("rows_selector")
    if rows_selector:
        return [_record_from(r, params) for r in soup.select(rows_selector)]
    return [_record_from(soup, params)]


def _table(html: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html or "", "html.parser")
    rows = soup.select(params.get("rows_selector", "table tr"))
    if not rows:
        return []
    if params.get("has_header", True):
        headers = [_text(c) for c in (rows[0].select("th") or rows[0].select("td"))]
        start = 1
    else:
        headers = None
        start = 0
    out = []
    for row in rows[start:]:
        cells = row.select("td")
        if not cells:
            continue
        if headers:
            rec = {(headers[i] if i < len(headers) and headers[i] else f"col{i}"): _text(c)
                   for i, c in enumerate(cells)}
        else:
            rec = {f"col{i}": _text(c) for i, c in enumerate(cells)}
        out.append(rec)
    return out


REGISTRO = {"fields": _fields, "table": _table}


def extract_html(nombre: str, html: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    fn = REGISTRO.get((nombre or "fields").lower(), _fields)
    return fn(html, params)
