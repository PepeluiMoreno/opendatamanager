"""CrossDatasetFetcher — especie interna `CruceDatasets`.

Un recurso cuyo "transporte" es el propio almacén de ODM: cruza dos datasets ya
cosechados (vía la API GraphQL de datos) y produce un dataset derivado. Al ser
un recurso normal hereda gratis schedule, ejecuciones, salud, versionado y
linaje (diseño en docs/PENDIENTE_recursos_derivados.md).

Direccionamiento de las fuentes (en orden de preferencia):
  left_resource / right_resource — nombre(s) de RECURSO (string o JSON array;
      con varios se concatena la unión de sus datasets). El nombre de query se
      deriva en runtime (dataset_query_name), así que sobrevive a regeneraciones
      del dataset, y la dependencia queda registrada como linaje
      (resource_dependency) al ejecutar.
  left_query / right_query — nombre de query de la API de datos, directo.
      Compatibilidad y casos avanzados; sin linaje a máquina.

Resto de params:
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

Caso motivador: órganos BDNS (left, 4 recursos por ámbito, clave id) × puente
DIR3 (right, clave ids, match=in_array) → órganos con su código DIR3.
"""
import json
from typing import Any, Dict, List, Optional, Tuple

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


def _names(v) -> List[str]:
    """'left_resource' admite un nombre o un JSON array de nombres."""
    if v is None:
        return []
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return []
        if s.startswith("["):
            return [str(x) for x in json.loads(s)]
        return [s]
    if isinstance(v, list):
        return [str(x) for x in v]
    return [str(v)]


def resolve_side(side: str, params: Dict[str, Any]) -> Tuple[List[str], List[Any]]:
    """Resuelve un lado del cruce a (nombres_de_query, resource_ids).

    Preferencia: '{side}_resource' (nombres de recurso; query derivada con
    dataset_query_name, ids para el linaje). Fallback: '{side}_query' directo
    (sin linaje). Lanza ValueError con mensaje claro si nada resuelve."""
    nombres = _names(params.get(f"{side}_resource"))
    if nombres:
        from app.database import SessionLocal
        from app.graphql_data.schema_builder import dataset_query_name
        from app.models import Resource
        db = SessionLocal()
        try:
            queries, ids = [], []
            for n in nombres:
                r = (db.query(Resource)
                       .filter(Resource.name == n, Resource.deleted_at.is_(None))
                       .first())
                if r is None:
                    raise ValueError(
                        f"CruceDatasets: el recurso '{n}' ({side}) no existe")
                queries.append(dataset_query_name(r.name))
                ids.append(r.id)
            return queries, ids
        finally:
            db.close()
    q = (params.get(f"{side}_query") or "").strip() if isinstance(params.get(f"{side}_query"), str) else params.get(f"{side}_query")
    if q:
        return [q], []
    raise ValueError(
        f"CruceDatasets: indica '{side}_resource' (nombre de recurso, preferido) "
        f"o '{side}_query' (query de la API de datos)")


def _norm_key(v: Any) -> Any:
    """Normaliza una clave textual para cruces por denominación: mayúsculas,
    sin acentos, espacios colapsados. No-strings se devuelven tal cual."""
    if not isinstance(v, str):
        return v
    import unicodedata
    s = unicodedata.normalize("NFKD", v)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.upper().split())


def cruzar(left: List[Dict], right: List[Dict], *, left_key: str, right_key: str,
           match: str = "eq", join: str = "enrich",
           select: Dict[str, str] | None = None,
           normalize_keys: bool = False) -> List[Dict[str, Any]]:
    """Núcleo puro del cruce. Índice del right por clave; con match=in_array la
    clave derecha es una lista y se indexa cada elemento. Con normalize_keys
    las claves textuales casan sin distinguir mayúsculas/acentos/espaciado
    (cruces por denominación). A igualdad de clave gana la última fila del
    right (datasets ya deduplicados aguas arriba)."""
    nk = _norm_key if normalize_keys else (lambda x: x)
    indice: Dict[Any, Dict] = {}
    for r in right:
        k = r.get(right_key)
        claves = k if (match == "in_array" and isinstance(k, list)) else [k]
        for c in claves:
            if c is not None:
                indice[nk(c)] = r

    if select:
        campos = select
    else:
        campos = {c: c for c in (right[0].keys() if right else []) if c != right_key}

    out: List[Dict[str, Any]] = []
    for l in left:
        pareja = indice.get(nk(l.get(left_key)))
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

    #: ids de recursos fuente resueltos en el último fetch — el manager los lee
    #: para sincronizar el linaje (resource_dependency).
    resolved_dependencies: Dict[str, List[Any]]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resolved_dependencies = {}

    def fetch(self) -> RawData:
        p = self.params
        for req in ("left_key", "right_key"):
            if not p.get(req):
                raise ValueError(f"CruceDatasets: el parámetro '{req}' es obligatorio")
        base = p.get("odmgr_data_url") or None
        left_queries, left_ids = resolve_side("left", p)
        right_queries, right_ids = resolve_side("right", p)
        self.resolved_dependencies = {"left": left_ids, "right": right_ids}

        left_fields = _as_list(p.get("left_fields"))
        right_fields = _as_list(p.get("right_fields"))
        if p["left_key"] not in left_fields:
            left_fields = [p["left_key"], *left_fields]
        if p["right_key"] not in right_fields:
            right_fields = [p["right_key"], *right_fields]

        left: List[Dict] = []
        for q in left_queries:
            left.extend(fetch_odmgr_records(q, left_fields, base_url=base))
        right: List[Dict] = []
        for q in right_queries:
            right.extend(fetch_odmgr_records(q, right_fields, base_url=base))

        filas = cruzar(
            left, right,
            left_key=p["left_key"], right_key=p["right_key"],
            match=(p.get("match") or "eq"),
            join=(p.get("join") or "enrich"),
            select=_as_dict(p.get("select")) or None,
            normalize_keys=str(p.get("normalize_keys", "")).lower() in ("1", "true", "yes", "si", "sí"),
        )
        limite = int(p.get("_preview_limit", 0) or 0)
        return filas[:limite] if limite else filas

    def parse(self, raw: RawData) -> ParsedData:
        return raw

    def normalize(self, parsed: ParsedData) -> DomainData:
        return parsed
