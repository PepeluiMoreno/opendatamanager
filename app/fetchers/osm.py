"""
OSMFetcher - Fetcher para datos de OpenStreetMap via Overpass API.

Modelo de filtros (dos niveles):
  Cada "bloque de condición" es una lista de pares (key, value) AND'd entre sí.
  El resultado final es la UNION de todos los bloques seleccionados.

  Ejemplo:
    RELIGIOUS_CATHOLIC_STRICT = [
        ("amenity", "place_of_worship"),
        ("religion",     "christian"),
        ("denomination", "catholic"),
    ]
  → node["amenity"="place_of_worship"]["religion"="christian"]["denomination"="catholic"](area);
    way[...][...][...](area);

  RELIGIOUS_CATHOLIC_LOOSE = [("amenity","place_of_worship"),("religion","christian")]
  → unión separada con condiciones más amplias

Parámetros:
    use_types       Lista de presets separada por comas, p.ej. "EDUCATION,HEALTHCARE".
                    Cada preset genera un bloque de subquery que se UNION-a.
    filters_pairs   JSON alternativo al preset: [[key,val],[key,val],...]
                    Se trata como un bloque AND único.
    demarcacion     Nombre libre de demarcación española (CC.AA., provincia, ciudad, isla).
                    Resolución automática de bbox. Ejemplos: "Andalucía", "Tenerife".
    bbox            Bounding box manual "sur,oeste,norte,este" (default: España completa).
    area_name       Nombre de área Overpass (alternativo a bbox/demarcacion).
    element_types   Tipos OSM separados por coma: node,way,relation (default: node,way).
    out_format      center|geom|body|skel (default: center).
    timeout         Segundos de timeout Overpass (default: 60).
    max_elements    Límite de seguridad (default: 0 = sin límite).
    overpass_url    URL del servidor Overpass API.
"""
import json
import logging
import os
import time
import unicodedata
import requests
from typing import Dict, List, Optional, Tuple

from app.fetchers.base import BaseFetcher, RawData, ParsedData, DomainData

logger = logging.getLogger(__name__)

# Bounding box de España + Canarias (sur, oeste, norte, este — formato Overpass)
SPAIN_BBOX = "27.6,-18.2,43.8,4.3"

# Servidor local (inyectado por docker-compose vía OVERPASS_LOCAL_URL).
# Si no está configurado, se usan solo los mirrors públicos.
_LOCAL = os.environ.get("OVERPASS_LOCAL_URL", "").strip()

OVERPASS_URL = _LOCAL or "https://overpass-api.de/api/interpreter"

# Orden de preferencia: local primero, públicos como fallback.
OVERPASS_MIRRORS = [s for s in [
    _LOCAL,
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
] if s]

# ── Presets de uso: lista de pares (key, value) AND'd ─────────────────────────
# Nomenclatura:
#   _STRICT  = condiciones muy específicas (máxima precisión, menos falsos positivos)
#   _LOOSE   = condiciones más amplias (más cobertura, algo de ruido)
#   _EXTRA   = captura elementos pobremente etiquetados (solo building/historic/etc.)
#
# El campo "pairs" es List[Tuple[str,str]]: todas las condiciones se encadenan con AND.
# El campo "label" es para el UI.

OSM_USE_PRESETS: Dict[str, Dict] = {
    # ── Religioso ─────────────────────────────────────────────────────────────
    "RELIGIOUS_CATHOLIC_STRICT": {
        "label": "Iglesias católicas (estricto)",
        "pairs": [
            ("amenity",      "place_of_worship"),
            ("religion",     "christian"),
            ("denomination", "catholic"),
        ],
    },
    "RELIGIOUS_CATHOLIC_LOOSE": {
        "label": "Lugares de culto cristiano",
        "pairs": [
            ("amenity",  "place_of_worship"),
            ("religion", "christian"),
        ],
    },
    "RELIGIOUS_ALL": {
        "label": "Todos los lugares de culto",
        "pairs": [
            ("amenity", "place_of_worship"),
        ],
    },
    "RELIGIOUS_BUILDING_EXTRA": {
        "label": "Edificios religiosos (building=church/cathedral/chapel)",
        "pairs_or": [
            ("building", "church"),
            ("building", "cathedral"),
            ("building", "chapel"),
        ],
    },

    # ── Educación ─────────────────────────────────────────────────────────────
    "EDUCATION_STRICT": {
        "label": "Colegios (school)",
        "pairs": [
            ("amenity", "school"),
        ],
    },
    "EDUCATION_LOOSE": {
        "label": "Centros educativos (todos los niveles)",
        "pairs_or": [
            ("amenity", "school"),
            ("amenity", "university"),
            ("amenity", "college"),
            ("amenity", "kindergarten"),
            ("amenity", "library"),
        ],
    },
    "EDUCATION_BUILDING_EXTRA": {
        "label": "Edificios educativos (building=school/university)",
        "pairs_or": [
            ("building", "school"),
            ("building", "university"),
        ],
    },

    # ── Salud ─────────────────────────────────────────────────────────────────
    "HEALTHCARE_STRICT": {
        "label": "Hospitales y clínicas",
        "pairs_or": [
            ("amenity", "hospital"),
            ("amenity", "clinic"),
        ],
    },
    "HEALTHCARE_LOOSE": {
        "label": "Centros sanitarios (todos)",
        "pairs_or": [
            ("amenity", "hospital"),
            ("amenity", "clinic"),
            ("amenity", "doctors"),
            ("amenity", "dentist"),
            ("amenity", "pharmacy"),
            ("amenity", "physiotherapist"),
        ],
    },
    "HEALTHCARE_BUILDING_EXTRA": {
        "label": "Edificios sanitarios (building=hospital)",
        "pairs": [
            ("building", "hospital"),
        ],
    },

    # ── Administración pública ─────────────────────────────────────────────────
    "PUBLIC_ADMIN_STRICT": {
        "label": "Ayuntamientos y sedes administrativas",
        "pairs_or": [
            ("amenity", "townhall"),
            ("amenity", "courthouse"),
            ("office",  "government"),
        ],
    },
    "PUBLIC_ADMIN_LOOSE": {
        "label": "Servicios públicos y comunitarios",
        "pairs_or": [
            ("amenity", "townhall"),
            ("amenity", "courthouse"),
            ("amenity", "community_centre"),
            ("amenity", "post_office"),
            ("amenity", "police"),
            ("amenity", "fire_station"),
            ("office",  "government"),
        ],
    },

    # ── Patrimonio ────────────────────────────────────────────────────────────
    "HERITAGE_STRICT": {
        "label": "Monumentos históricos",
        "pairs_or": [
            ("historic", "monument"),
            ("historic", "memorial"),
            ("historic", "castle"),
        ],
    },
    "HERITAGE_LOOSE": {
        "label": "Patrimonio histórico (cualquier etiqueta historic)",
        "pairs": [
            ("historic", "*"),  # cualquier valor — se expande a ["historic"]
        ],
    },

    # ── Turismo ───────────────────────────────────────────────────────────────
    "TOURISM": {
        "label": "Turismo y alojamiento",
        "pairs_or": [
            ("tourism", "hotel"),
            ("tourism", "hostel"),
            ("tourism", "guest_house"),
            ("tourism", "motel"),
            ("tourism", "museum"),
            ("tourism", "gallery"),
            ("tourism", "attraction"),
            ("tourism", "viewpoint"),
            ("tourism", "monument"),
        ],
    },

    # ── Emergencias ───────────────────────────────────────────────────────────
    "EMERGENCY": {
        "label": "Servicios de emergencia",
        "pairs_or": [
            ("amenity", "fire_station"),
            ("amenity", "police"),
            ("amenity", "ambulance_station"),
        ],
    },

    # ── Transporte público ────────────────────────────────────────────────────
    "TRANSPORT_STRICT": {
        "label": "Estaciones de transporte público",
        "pairs_or": [
            ("public_transport", "station"),
            ("amenity",          "bus_station"),
            ("railway",          "station"),
        ],
    },
    "TRANSPORT_LOOSE": {
        "label": "Paradas y estaciones de transporte",
        "pairs_or": [
            ("public_transport", "station"),
            ("public_transport", "platform"),
            ("public_transport", "stop_position"),
            ("amenity",          "bus_station"),
            ("railway",          "station"),
            ("railway",          "halt"),
        ],
    },
}


# ── Diccionario de demarcaciones ──────────────────────────────────────────────
_DEMAR_PATH = os.path.join(os.path.dirname(__file__), "osm_demarcaciones_es.json")
_DEMARCACIONES: Optional[dict] = None


def _load_demarcaciones() -> dict:
    global _DEMARCACIONES
    if _DEMARCACIONES is None:
        try:
            with open(_DEMAR_PATH, encoding="utf-8") as f:
                data = json.load(f)
            _DEMARCACIONES = {k: v for k, v in data.items() if not k.startswith("_")}
        except Exception as e:
            logger.warning(f"No se pudo cargar osm_demarcaciones_es.json: {e}")
            _DEMARCACIONES = {}
    return _DEMARCACIONES


def _normalize_key(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = "".join(c for c in nfkd if not unicodedata.combining(c))
    key = ascii_str.lower().replace(" ", "_").replace("-", "_")
    return "".join(c for c in key if c.isalnum() or c == "_")


def resolve_demarcacion(name: str) -> Optional[Dict]:
    demar = _load_demarcaciones()
    key = _normalize_key(name)
    if key in demar:
        return demar[key]
    for entry in demar.values():
        if any(_normalize_key(a) == key for a in entry.get("alias", [])):
            return entry
    return None


# ── Construcción de queries Overpass ──────────────────────────────────────────

def _pair_to_filter(key: str, value: str) -> str:
    """Convierte un par (key, value) a fragmento Overpass: ["k"="v"] o ["k"]."""
    if not value or value == "*":
        return f'["{key}"]'
    return f'["{key}"="{value}"]'


def _build_subquery_and(
    pairs: List[Tuple[str, str]],
    element_types: List[str],
    geo_suffix: str,
) -> List[str]:
    """
    Un bloque AND: todos los pares se encadenan en la misma sentencia.
    Genera una línea por cada element_type.
    """
    tag_chain = "".join(_pair_to_filter(k, v) for k, v in pairs)
    return [f"  {etype}{tag_chain}{geo_suffix};" for etype in element_types]


def _build_subquery_or(
    pairs_or: List[Tuple[str, str]],
    element_types: List[str],
    geo_suffix: str,
) -> List[str]:
    """
    Bloques OR: cada par genera su propio conjunto de sentencias.
    Todas se UNION-an dentro del mismo ( ... ).
    """
    lines = []
    for (key, value) in pairs_or:
        tag_filter = _pair_to_filter(key, value)
        for etype in element_types:
            lines.append(f"  {etype}{tag_filter}{geo_suffix};")
    return lines


def _build_subquery_lines(
    preset: Dict,
    element_types: List[str],
    geo_suffix: str,
) -> List[str]:
    """Genera las líneas de sentencias Overpass para un preset dado."""
    if "pairs" in preset:
        return _build_subquery_and(preset["pairs"], element_types, geo_suffix)
    elif "pairs_or" in preset:
        return _build_subquery_or(preset["pairs_or"], element_types, geo_suffix)
    return []


def build_overpass_query(
    preset_keys: List[str],
    custom_pairs: Optional[List[Tuple[str, str]]],
    element_types: Optional[List[str]],
    bbox: Optional[str],
    area_name: Optional[str],
    timeout: int,
    out_format: str,
    inline_blocks: Optional[List[Dict]] = None,
    maxsize: int = 1_073_741_824,   # 1 GiB
) -> str:
    """
    Construye la query Overpass QL final como UNION de subqueries.

    Cada preset_key seleccionado genera su bloque de condiciones (AND o OR interno).
    inline_blocks son bloques directos del OverpassQueryBuilder con pares inline.
    custom_pairs se añade como un bloque AND adicional.
    Todos los bloques se UNION-an en el nivel exterior con ( ... ).
    """
    etypes = element_types or ["node", "way"]
    lines = [f"[out:json][timeout:{timeout}][maxsize:{maxsize}];"]

    if area_name:
        lines.append(f'area["name"="{area_name}"]->.searchArea;')
        geo_suffix = "(area.searchArea)"
    else:
        geo_suffix = f"({bbox or SPAIN_BBOX})"

    body_lines: List[str] = []

    for key in preset_keys:
        key_upper = key.strip().upper()
        if key_upper not in OSM_USE_PRESETS:
            logger.warning(f"Preset '{key_upper}' desconocido, se ignora.")
            continue
        preset = OSM_USE_PRESETS[key_upper]
        body_lines.extend(_build_subquery_lines(preset, etypes, geo_suffix))

    for block in (inline_blocks or []):
        pairs    = block.get("pairs", [])
        pairs_or = block.get("pairs_or", [])
        mode     = block.get("mode", "and")
        if mode == "or" or pairs_or:
            body_lines.extend(_build_subquery_or(pairs_or or pairs, etypes, geo_suffix))
        else:
            body_lines.extend(_build_subquery_and(pairs, etypes, geo_suffix))

    if custom_pairs:
        body_lines.extend(_build_subquery_and(custom_pairs, etypes, geo_suffix))

    if not body_lines:
        raise ValueError(
            f"Ningún preset válido ni filtro personalizado. "
            f"Presets disponibles: {', '.join(OSM_USE_PRESETS)}"
        )

    # Deduplicar sentencias idénticas (p.ej. EDUCATION_STRICT ⊂ EDUCATION_LOOSE)
    seen: set = set()
    deduped: List[str] = []
    for line in body_lines:
        if line not in seen:
            seen.add(line)
            deduped.append(line)

    lines.append("(")
    lines.extend(deduped)
    lines.append(");")
    lines.append(f"out {out_format};")

    return "\n".join(lines)


# ── Normalización de output ───────────────────────────────────────────────────

def _infer_use(element: dict, preset_keys: List[str]) -> Optional[str]:
    """
    Determina qué preset describe mejor al elemento inspeccionando sus tags.
    Devuelve el primer preset_key que coincide con los tags del elemento.
    """
    tags = element.get("tags", {})
    for key in preset_keys:
        key_upper = key.strip().upper()
        preset = OSM_USE_PRESETS.get(key_upper)
        if not preset:
            continue
        pairs = preset.get("pairs") or preset.get("pairs_or", [])
        if preset.get("pairs"):
            # AND: todos los pares deben coincidir
            if all(tags.get(k) == v or (v == "*" and k in tags) for k, v in pairs):
                return key_upper
        else:
            # OR: al menos un par debe coincidir
            if any(tags.get(k) == v for k, v in pairs):
                return key_upper
    return None


def _element_to_record(element: dict, preset_keys: List[str]) -> dict:
    """Convierte un elemento OSM a registro normalizado."""
    tags = element.get("tags", {})
    record: dict = {
        "osm_id":       element.get("id"),
        "osm_type":     element.get("type"),
        "lat":          None,
        "lon":          None,
        "geometry":     None,
        "tags":         tags,
        "name":         tags.get("name") or tags.get("name:es") or tags.get("ref"),
        "inferred_use": _infer_use(element, preset_keys),
    }

    if "lat" in element:
        record["lat"] = element["lat"]
        record["lon"] = element["lon"]
    elif "center" in element:
        record["lat"] = element["center"].get("lat")
        record["lon"] = element["center"].get("lon")
    elif "bounds" in element:
        b = element["bounds"]
        record["lat"] = round((b["minlat"] + b["maxlat"]) / 2, 7)
        record["lon"] = round((b["minlon"] + b["maxlon"]) / 2, 7)

    if "geometry" in element:
        record["geometry"] = element["geometry"]

    return record


# ── Fetcher ───────────────────────────────────────────────────────────────────

class OSMFetcher(BaseFetcher):
    """
    Fetcher para OpenStreetMap via Overpass API.

    La query final es la UNION de todos los use_types seleccionados.
    Cada use_type es un preset que expande a una lista de pares (key=value)
    con semántica AND o OR según su tipo (pairs / pairs_or).
    """

    def fetch(self) -> RawData:
        # ── Filtros ───────────────────────────────────────────────────────────
        use_types_raw = self.params.get("use_types", self.params.get("use_type", "")).strip()
        preset_keys: List[str] = []
        inline_blocks: List[Dict] = []  # bloques con pares inline del OverpassQueryBuilder

        if use_types_raw:
            try:
                parsed_blocks = json.loads(use_types_raw)
                if isinstance(parsed_blocks, list):
                    for b in parsed_blocks:
                        if isinstance(b, dict):
                            if b.get("preset"):
                                preset_keys.append(b["preset"].upper())
                            elif b.get("pairs") or b.get("pairs_or"):
                                inline_blocks.append(b)
                        else:
                            preset_keys.append(str(b).upper())
            except (json.JSONDecodeError, TypeError):
                preset_keys = [k.strip().upper() for k in use_types_raw.split(",") if k.strip()]

        # Filtro personalizado alternativo (JSON: [[key,val], ...])
        filters_raw = self.params.get("filters_pairs", self.params.get("filters", ""))
        custom_pairs: Optional[List[Tuple[str, str]]] = None
        if filters_raw:
            parsed = json.loads(filters_raw) if isinstance(filters_raw, str) else filters_raw
            if isinstance(parsed, dict):
                custom_pairs = [(k, v) for k, vals in parsed.items() for v in (vals or ["*"])]
            elif isinstance(parsed, list):
                custom_pairs = [tuple(p) for p in parsed]

        if not preset_keys and not inline_blocks and not custom_pairs:
            raise ValueError(
                "Especifica 'use_types' (preset) o 'filters_pairs' (JSON [[k,v],...]). "
                f"Presets disponibles: {', '.join(OSM_USE_PRESETS)}"
            )

        # ── Demarcación geográfica ─────────────────────────────────────────────
        demarcacion = self.params.get("demarcacion", "").strip()
        bbox = self.params.get("bbox", SPAIN_BBOX)
        area_name = self.params.get("area_name", "").strip() or None

        if demarcacion:
            entry = resolve_demarcacion(demarcacion)
            if entry:
                bbox = entry["bbox"]
                area_name = None
                logger.info(
                    f"Demarcación '{demarcacion}' → {entry['nombre']} [{entry['tipo']}], "
                    f"bbox={bbox}"
                )
            else:
                area_name = demarcacion
                bbox = None
                logger.warning(
                    f"Demarcación '{demarcacion}' no encontrada en diccionario, "
                    f"usando como area_name de Overpass."
                )

        element_types = [
            t.strip()
            for t in self.params.get("element_types", "node,way").split(",")
            if t.strip()
        ]
        timeout    = int(self.params.get("timeout", 60))
        max_elems  = int(self.params.get("max_elements", 0))
        out_format = self.params.get("out_format", "center")
        overpass_url = self.params.get("overpass_url", OVERPASS_URL)

        # Modo preview: limitar agresivamente para no bloquear el worker
        preview_limit = self.params.get("_preview_limit")
        if preview_limit:
            timeout = min(timeout, 20)
            self.params["timeout"] = str(timeout)   # también _request lo lee de params
            max_elems = int(preview_limit)

        # ── Advertencia de query potencialmente masiva ────────────────────────
        # HERITAGE_LOOSE usa ["historic"] sin valor → ~500k elem en España completa.
        # Si se usa sobre bbox grande sin max_elements, avisar en el log.
        _broad_presets = {k for k in preset_keys if k in ("HERITAGE_LOOSE",)}
        _spain_bbox = bbox and len(bbox.split(",")) == 4 and float(bbox.split(",")[2]) - float(bbox.split(",")[0]) > 10
        if _broad_presets and _spain_bbox and not max_elems:
            logger.warning(
                f"Presets de cobertura amplia ({', '.join(_broad_presets)}) sobre área grande "
                f"({bbox}). Considera acotar la demarcación o activar max_elements."
            )

        # ── Construir y ejecutar query ─────────────────────────────────────────
        query = build_overpass_query(
            preset_keys=preset_keys,
            inline_blocks=inline_blocks,
            custom_pairs=custom_pairs,
            element_types=element_types,
            bbox=bbox,
            area_name=area_name,
            timeout=timeout,
            out_format=out_format,
        )
        logger.info(f"Overpass query:\n{query}")

        elements = self._execute_overpass(query, overpass_url, timeout)

        if max_elems and len(elements) > max_elems:
            logger.warning(f"Limitando a {max_elems} de {len(elements)} elementos")
            elements = elements[:max_elems]

        # Adjuntar preset_keys para inferencia posterior en parse()
        all_keys = preset_keys + [b.get("preset") for b in inline_blocks if b.get("preset")]
        return {"elements": elements, "preset_keys": all_keys}

    def _execute_overpass(
        self,
        query: str,
        url: str,
        timeout: int,
        backoff: float = 30.0,
        retries_per_server: int = 2,
    ) -> List[dict]:
        """
        Ejecuta la query contra Overpass rotando por mirrors si falla.

        Servidor local (OVERPASS_LOCAL_URL): 1 intento, sin backoff, rota inmediatamente.
        Mirrors públicos: retries_per_server intentos con backoff progresivo.
        - 429/503 → respeta Retry-After; reintenta mismo servidor.
        - 400/403 → el servidor rechaza la query; rota al siguiente mirror.
        - 504/502 → servidor ocupado; reintenta con backoff antes de rotar.
        - respuesta vacía/no-JSON → rota inmediatamente.
        """
        http_timeout = timeout + 30
        servers = [url] + [m for m in OVERPASS_MIRRORS if m != url]
        req_headers = {
            "User-Agent": "OpenDataManager/1.0 (https://github.com/odmgr; admin@odmgr.local)",
            "Accept": "application/json",
        }
        last_exc: Exception = RuntimeError("Sin servidores Overpass disponibles")

        for i, server in enumerate(servers):
            is_local = bool(_LOCAL) and server == _LOCAL
            max_attempts = 1 if is_local else retries_per_server

            for attempt in range(1, max_attempts + 1):
                try:
                    logger.info(f"Overpass → {server}" + ("" if is_local else f" (intento {attempt}/{max_attempts})"))
                    response = requests.post(
                        server,
                        data={"data": query},
                        headers=req_headers,
                        timeout=http_timeout,
                    )

                    # Rate-limited: respetar Retry-After (solo mirrors públicos)
                    if response.status_code in (429, 503) and not is_local:
                        wait = int(response.headers.get("Retry-After", backoff))
                        logger.warning(f"{server} → {response.status_code}, esperando {wait}s…")
                        time.sleep(wait)
                        continue

                    # El servidor rechaza la query o no disponible → siguiente mirror
                    if response.status_code in (400, 403, 429, 503):
                        logger.warning(f"{server} → {response.status_code}, rotando…")
                        last_exc = requests.exceptions.HTTPError(response=response)
                        break

                    response.raise_for_status()

                    # Respuesta vacía o no-JSON → tratar como fallo de servidor
                    raw_text = response.text.strip()
                    if not raw_text:
                        logger.warning(f"{server} → respuesta vacía, rotando…")
                        last_exc = RuntimeError(f"{server}: respuesta vacía")
                        break

                    data = response.json()
                    elements = data.get("elements", [])
                    if "remark" in data:
                        logger.warning(f"Overpass remark: {data['remark']}")
                    logger.info(f"OSM: {len(elements)} elementos desde {server}")
                    return elements

                except requests.exceptions.HTTPError as exc:
                    last_exc = exc
                    wait = backoff * attempt
                    logger.warning(f"Overpass HTTP error en {server}: {exc}."
                                   + (f" Reintentando en {wait}s…" if attempt < max_attempts
                                      else " Rotando mirror…"))
                    if attempt < max_attempts:
                        time.sleep(wait)

                except (json.JSONDecodeError, ValueError) as exc:
                    last_exc = exc
                    logger.warning(f"Overpass respuesta no-JSON en {server}: {exc}. Rotando mirror…")
                    break  # no JSON → rotar directamente

                except Exception as exc:
                    last_exc = exc
                    logger.warning(f"Overpass error de red en {server}: {exc}. Rotando mirror…")
                    break

        raise last_exc

    def parse(self, raw: RawData) -> ParsedData:
        if isinstance(raw, dict):
            elements = raw.get("elements", [])
            preset_keys = raw.get("preset_keys", [])
        else:
            elements = raw
            preset_keys = []
        return [_element_to_record(e, preset_keys) for e in elements]

    def normalize(self, parsed: ParsedData) -> DomainData:
        return parsed
