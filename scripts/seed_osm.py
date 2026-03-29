"""
Registra el fetcher OSM (Overpass API) en OpenDataManager y crea un resource
de ejemplo con equipamientos públicos en España.

El parámetro `filters` usa el tipo ad-hoc "json_filter_map":
  - Clave externa (enum): categoría OSM (amenity, building, shop…)
  - Valor (enum de enum): lista de valores permitidos para esa clave

Run dentro del contenedor:
  docker exec odmgr_app python scripts/seed_osm.py
"""
import sys
sys.path.insert(0, "/app")

import json
import os
from uuid import uuid4
from app.database import SessionLocal
from app.models import Fetcher, FetcherParams, Resource, ResourceParam

db = SessionLocal()

# ── Categorías OSM disponibles para el parámetro `filters` ──────────────────
# Estructura enum-dentro-de-enum: clave OSM → valores permitidos
OSM_FILTER_ENUM = {
    "amenity": [
        "school", "university", "college", "kindergarten", "library",
        "hospital", "clinic", "pharmacy", "doctors", "dentist",
        "police", "fire_station", "courthouse", "prison", "townhall", "post_office",
        "bank", "atm",
        "restaurant", "cafe", "bar", "fast_food", "pub",
        "fuel", "parking", "bicycle_parking",
        "place_of_worship", "community_centre", "social_facility",
        "theatre", "cinema", "arts_centre",
    ],
    "building": [
        "residential", "apartments", "house", "detached",
        "commercial", "retail", "office", "industrial", "warehouse",
        "school", "university", "hospital", "church", "government",
        "yes",
    ],
    "shop": [
        "supermarket", "convenience", "bakery", "butcher", "greengrocer",
        "clothes", "shoes", "electronics", "hardware", "books", "pharmacy",
        "hairdresser", "beauty",
    ],
    "leisure": [
        "park", "garden", "playground", "sports_centre", "stadium",
        "swimming_pool", "pitch", "track", "fitness_centre",
        "nature_reserve",
    ],
    "tourism": [
        "hotel", "hostel", "guest_house", "motel", "camp_site",
        "museum", "gallery", "attraction", "viewpoint", "monument",
        "information",
    ],
    "office": [
        "government", "company", "ngo", "educational_institution",
        "association", "diplomatic", "lawyer", "accountant",
    ],
    "historic": [
        "monument", "memorial", "castle", "ruins", "church",
        "archaeological_site", "building",
    ],
    "healthcare": [
        "hospital", "clinic", "pharmacy", "doctor", "dentist",
        "physiotherapist", "optometrist",
    ],
    "emergency": [
        "police", "fire_station", "ambulance_station",
        "defibrillator", "first_aid",
    ],
    "public_transport": [
        "stop_position", "platform", "station", "stop_area",
    ],
}

# ── Registrar / actualizar el fetcher OSM ────────────────────────────────────
fetcher = db.query(Fetcher).filter(
    Fetcher.class_path == "app.fetchers.osm.OSMFetcher"
).first()

if not fetcher:
    fetcher = Fetcher(
        id=uuid4(),
        code="OSM Overpass",
        class_path="app.fetchers.osm.OSMFetcher",
        description=(
            "Descarga datos de OpenStreetMap via Overpass API. "
            "Los filtros se expresan como un mapa de etiquetas OSM (enum-dentro-de-enum): "
            "clave = categoría OSM, valor = lista de valores permitidos o null para cualquier valor. "
            "La demarcación geográfica se define con bbox o area_name (default: España completa)."
        ),
    )
    db.add(fetcher)
    db.flush()
    print(f"✓ Fetcher OSM creado: {fetcher.id}")
else:
    fetcher.description = (
        "Descarga datos de OpenStreetMap via Overpass API. "
        "Los filtros se expresan como un mapa de etiquetas OSM (enum-dentro-de-enum): "
        "clave = categoría OSM, valor = lista de valores permitidos o null para cualquier valor. "
        "La demarcación geográfica se define con bbox o area_name (default: España completa)."
    )
    print(f"  Fetcher OSM ya existe: {fetcher.id}")

# ── Eliminar params_def anteriores y recrear ──────────────────────────────────
existing_params = db.query(FetcherParams).filter(
    FetcherParams.fetcher_id == fetcher.id
).all()
for p in existing_params:
    db.delete(p)
db.flush()

# ── Cargar demarcaciones para el param enum ──────────────────────────────────
_demar_path = os.path.join(os.path.dirname(__file__), "../app/fetchers/osm_demarcaciones_es.json")
with open(_demar_path, encoding="utf-8") as _f:
    _demar_raw = json.load(_f)

# Orden de grupos y etiquetas de grupo para el UI
_GRUPO_ORDER = ["pais", "region", "comunidad", "ciudad_autonoma", "provincia", "ciudad", "isla"]
_GRUPO_LABEL = {
    "pais":           "País / Región",
    "region":         "País / Región",
    "comunidad":      "Comunidades Autónomas",
    "ciudad_autonoma":"Ciudades Autónomas",
    "provincia":      "Provincias",
    "ciudad":         "Ciudades",
    "isla":           "Islas",
}

# Detectar nombres duplicados entre tipos para añadir "(provincia)" / "(ciudad)" solo cuando es necesario
_nombre_count: dict = {}
for _k, _v in _demar_raw.items():
    if _k.startswith("_"):
        continue
    _n = _v["nombre"].split(" (")[0]  # nombre base sin sufijo
    _nombre_count[_n] = _nombre_count.get(_n, 0) + 1

def _label_for(key, entry):
    """Genera la etiqueta legible para el dropdown, añadiendo tipo solo cuando hay ambigüedad."""
    nombre = entry["nombre"]
    tipo = entry["tipo"]
    base = nombre.split(" (")[0]
    if _nombre_count.get(base, 0) > 1 and "(" not in nombre:
        tipo_label = {
            "provincia": "provincia", "ciudad": "ciudad",
            "comunidad": "C.A.", "ciudad_autonoma": "C. Autónoma",
            "isla": "isla",
        }.get(tipo, tipo)
        return f"{base} ({tipo_label})"
    return nombre

# Lista de {value, label, group} ordenada por grupo y luego por label
DEMARCACION_OPTS = []
seen_groups = {}
for _tipo in _GRUPO_ORDER:
    _entries = sorted(
        [(k, v) for k, v in _demar_raw.items()
         if not k.startswith("_") and v.get("tipo") == _tipo],
        key=lambda kv: kv[1]["nombre"]
    )
    _group_label = _GRUPO_LABEL[_tipo]
    if _group_label not in seen_groups:
        seen_groups[_group_label] = True
    for _k, _v in _entries:
        DEMARCACION_OPTS.append({
            "value": _k,
            "label": _label_for(_k, _v),
            "group": _group_label,
        })

# ── Presets use_type ─────────────────────────────────────────────────────────
# Importar del módulo para mantener una sola fuente de verdad
import sys
sys.path.insert(0, "/app")
from app.fetchers.osm import OSM_USE_PRESETS, build_overpass_query

# ── Serializar presets para el UI ─────────────────────────────────────────────
# El OverpassQueryBuilder espera un dict {KEY: {label, pairs?, pairs_or?}}
# Lo pasamos tal cual desde OSM_USE_PRESETS (ya tiene esa estructura).
USE_PRESETS_UI = {
    k: {"label": v["label"], **({} if "pairs" not in v and "pairs_or" not in v else
        {"pairs": v["pairs"]} if "pairs" in v else {"pairs_or": list(v["pairs_or"])})}
    for k, v in OSM_USE_PRESETS.items()
}

PARAMS_DEF = [
    {
        "param_name": "use_types",
        "required": False,
        "data_type": "overpass_query",   # UI: OverpassQueryBuilder
        "default_value": None,
        "enum_values": USE_PRESETS_UI,   # dict de presets para el builder
        "description": (
            "Selección de tipos de uso OSM. Cada preset seleccionado genera un bloque "
            "de condiciones (pares key=value) que se UNION-an en la query Overpass. "
            "Presets disponibles: " + ", ".join(OSM_USE_PRESETS.keys())
        ),
    },
    {
        "param_name": "filters_pairs",
        "required": False,
        "data_type": "string",           # JSON [[key,val],...] — avanzado
        "default_value": None,
        "enum_values": None,
        "description": (
            "Filtros OSM manuales avanzados (JSON). Lista de pares [[key,val],...]. "
            "Todos los pares se aplican como AND. "
            "Tiene prioridad sobre use_types si ambos se especifican. "
            "Ejemplo: [[\"amenity\",\"school\"],[\"wheelchair\",\"yes\"]]"
        ),
    },
    {
        "param_name": "demarcacion",
        "required": False,
        "data_type": "string",
        "default_value": "España",
        "enum_values": None,
        "description": (
            "Nombre del ámbito geográfico de búsqueda. "
            "Acepta CC.AA., provincias, ciudades e islas españolas. "
            "Ejemplos: 'Andalucía', 'Barcelona', 'Tenerife', 'Castilla y León'. "
            "Si se especifica, tiene prioridad sobre bbox y area_name."
        ),
    },
    {
        "param_name": "bbox",
        "required": False,
        "data_type": "string",
        "default_value": "27.6,-18.2,43.8,4.3",
        "enum_values": None,
        "description": (
            "Bounding box manual en formato Overpass: \"sur,oeste,norte,este\". "
            "Solo se usa si no se especifica demarcacion. "
            "Default: España completa (27.6,-18.2,43.8,4.3)."
        ),
    },
    {
        "param_name": "area_name",
        "required": False,
        "data_type": "string",
        "default_value": None,
        "enum_values": None,
        "description": (
            "Nombre de área Overpass (alternativo a bbox/demarcacion). "
            "Ejemplo: \"España\", \"Cataluña\". "
            "Solo se usa si no se especifica demarcacion."
        ),
    },
    {
        "param_name": "element_types",
        "required": False,
        "data_type": "string",
        "default_value": "node,way",
        "enum_values": ["node", "way", "relation"],
        "description": (
            "Tipos de elementos OSM a consultar, separados por coma. "
            "node = puntos, way = polígonos/líneas, relation = relaciones. "
            "Default: node,way"
        ),
    },
    {
        "param_name": "out_format",
        "required": False,
        "data_type": "enum",
        "default_value": "center",
        "enum_values": ["center", "geom", "body", "skel"],
        "description": (
            "Formato de geometría en la respuesta Overpass. "
            "center = centroide del polígono (más ligero), "
            "geom = geometría completa, "
            "body = datos completos, "
            "skel = solo IDs y tipos."
        ),
    },
    {
        "param_name": "timeout",
        "required": False,
        "data_type": "integer",
        "default_value": 60,
        "enum_values": None,
        "description": "Timeout de la query Overpass en segundos (default: 60).",
    },
    {
        "param_name": "max_elements",
        "required": False,
        "data_type": "integer",
        "default_value": 0,
        "enum_values": None,
        "description": (
            "Límite máximo de elementos a procesar (default: 0 = sin límite). "
            "Útil para queries muy amplias como precaución."
        ),
    },
    {
        "param_name": "overpass_url",
        "required": False,
        "data_type": "string",
        "default_value": "https://overpass-api.de/api/interpreter",
        "enum_values": None,
        "description": (
            "URL del servidor Overpass API. "
            "Alternativas: https://overpass.kumi.systems/api/interpreter, "
            "https://maps.mail.ru/osm/tools/overpass/api/interpreter"
        ),
    },
]

for pdef in PARAMS_DEF:
    db.add(FetcherParams(
        id=uuid4(),
        fetcher_id=fetcher.id,
        **pdef,
    ))

print(f"  {len(PARAMS_DEF)} params_def registrados")

# ── Resource de ejemplo: Equipamientos públicos en España ────────────────────
RESOURCE_NAME = "OSM - Equipamientos públicos en España"

r = db.query(Resource).filter(Resource.name == RESOURCE_NAME).first()
if not r:
    r = Resource(
        id=uuid4(),
        name=RESOURCE_NAME,
        description=(
            "Colegios, hospitales, farmacias, bibliotecas y otros equipamientos "
            "públicos de España extraídos de OpenStreetMap via Overpass API."
        ),
        publisher="OpenStreetMap contributors",
        fetcher_id=fetcher.id,
        active=True,
        enable_load=False,
        load_mode="replace",
    )
    db.add(r)
    db.flush()

    import json as _json
    # use_types: JSON array de bloques para OverpassQueryBuilder
    _blocks = [
        {"preset": "EDUCATION_STRICT", "pairs": list(OSM_USE_PRESETS["EDUCATION_STRICT"]["pairs"]), "mode": "and"},
    ]
    params = {
        "use_types":     _json.dumps(_blocks),
        "demarcacion":   "Madrid",      # área manejable para tests
        "element_types": "node",
        "out_format":    "center",
        "timeout":       "60",
        "max_elements":  "200",
    }
    for k, v in params.items():
        db.add(ResourceParam(id=uuid4(), resource_id=r.id, key=k, value=v))

    print(f"✓ Resource '{RESOURCE_NAME}' creado: {r.id}")
else:
    print(f"  Resource '{RESOURCE_NAME}' ya existe: {r.id}")

db.commit()
db.close()
print("Done.")
