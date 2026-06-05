"""CrossDatasetFetcher — especie interna `CruceDatasets`.

Un recurso cuyo "transporte" es el propio almacén de ODM: cruza dos datasets ya
cosechados (vía la API GraphQL de datos) y produce un dataset derivado. Al ser
un recurso normal hereda gratis schedule, ejecuciones, salud, versionado y
linaje (diseño en docs/PENDIENTE_recursos_derivados.md).

Params:
  left_query / right_query   — queries de datos de los datasets a cruzar
  left_fields / right_fields — campos a leer de cada lado (JSON array)
  left_key / right_key       — clave de cruce en cada lado
  match                      — 'eq' (igualdad) | 'in_array' (la clave derecha es
                               una lista que contiene la izquierda)
  join                       — 'enrich' (left + campos del right; sin pareja se
                               conserva) | 'inner' (solo con pareja) | 'left'
                               (alias de enrich)
  select                     — (opcional) mapa {campo_salida: campo_del_right};
                               por defecto se vuelcan todos los right_fields
                               menos la clave
  odmgr_data_url             — (opcional) endpoint de la API de datos

Caso motivador: órganos BDNS (left, clave id) × puente DIR3 (right, clave ids,
match=in_array) → órganos con su código DIR3.
"""
import json
from typing import Any, Dict, List

from app.fetchers.base import BaseFetcher, RawData, ParsedData, DomainData
from app.fetchers.pivot_sources import fetch_odmgr_records


def _as_list(v) -> List[str]:
    if isinstance(v, str):
        v = json.loads(v) if v.strip() else []
    return list(v or [])


def _as_dict(v) -> Dict[str, str]:
    if isinstance(v, str):
        v = json.loads(v) if v.strip() else {}
    return dict(v or {})


def cruzar(left: List[Dict], right: List[Dict], *, left_key: str, right_key: str,
           match: str = "eq", join: str = "enrich",
           select: Dict[str, str] | None = None) -> List[Dict[str, Any]]:
    """Núcleo puro del cruce. Índice del right por clave; con match=in_array la
    clave derecha es una lista y se indexa cada elemento. A igualdad de clave
    gana la última fila del right (datasets ya deduplicados aguas arriba)."""
    indice: Dict[Any, Dict] = {}
    for r in right:
        k = r.get(right_key)
        claves = k if (match == "in_array" and isinstance(k, list)) else [k]
        for c in claves:
            if c is not None:
                indice[c] = r

    if select:
        campos = select
    else:
        campos = {c: c for c in (right[0].keys() if right else []) if c != right_key}

    out: List[Dict[str, Any]] = []
    for l in left:
        pareja = indice.get(l.get(left_key))
        if pareja is None:
            if join == "inner":
                continue
            out.append(dict(l))
        else:
            fila = dict(l)
            for salida, origen in campos.items():
                fila[salida] = pareja.get(origen)
            out.append(fila)
    return out


class CrossDatasetFetcher(BaseFetcher):

    def fetch(self) -> RawData:
        p = self.params
        for req in ("left_query", "right_query", "left_key", "right_key"):
            if not p.get(req):
                raise ValueError(f"CruceDatasets: el parámetro '{req}' es obligatorio")
        base = p.get("odmgr_data_url") or None
        left_fields = _as_list(p.get("left_fields"))
        right_fields = _as_list(p.get("right_fields"))
        if p["left_key"] not in left_fields:
            left_fields = [p["left_key"], *left_fields]
        if p["right_key"] not in right_fields:
            right_fields = [p["right_key"], *right_fields]
        left = fetch_odmgr_records(p["left_query"], left_fields, base_url=base)
        right = fetch_odmgr_records(p["right_query"], right_fields, base_url=base)
        filas = cruzar(
            left, right,
            left_key=p["left_key"], right_key=p["right_key"],
            match=(p.get("match") or "eq"),
            join=(p.get("join") or "enrich"),
            select=_as_dict(p.get("select")) or None,
        )
        limite = int(p.get("_preview_limit", 0) or 0)
        return filas[:limite] if limite else filas

    def parse(self, raw: RawData) -> ParsedData:
        return raw

    def normalize(self, parsed: ParsedData) -> DomainData:
        return parsed
