"""
Seeding inicial de OpenDataManager.
Idempotente: safe to run on every startup. Uses upsert-by-name semantics.

Orden:
  1. Fetchers   — sincroniza tipos de fetcher desde el código
  2. Publishers — organismos base del estado español
  3. Resources  — recursos fundacionales (referencia: DIR3, geografía)
"""
import uuid
from app.database import SessionLocal
from app.models import Fetcher, FetcherParams, Publisher, Resource, ResourceParam


# ---------------------------------------------------------------------------
# 1. FETCHERS
# ---------------------------------------------------------------------------

FETCHER_DEFS = [
    {
        "code": "API REST",
        "class_path": "app.fetchers.rest.RestFetcher",
        "description": "RESTful API with JSON/XML support",
        "params": [
            {"param_name": "url",         "data_type": "string",  "required": True},
            {"param_name": "method",      "data_type": "string",  "required": False, "default_value": "GET"},
            {"param_name": "timeout",     "data_type": "integer", "required": False, "default_value": 30},
            {"param_name": "max_retries", "data_type": "integer", "required": False, "default_value": 3},
        ],
    },
    {
        "code": "API REST Paginada",
        "class_path": "app.fetchers.paginated_rest.PaginatedRestFetcher",
        "description": "Paginated REST API — iterates pages until empty",
        "params": [
            {"param_name": "url",            "data_type": "string",  "required": True},
            {"param_name": "method",         "data_type": "string",  "required": False, "default_value": "GET"},
            {"param_name": "timeout",        "data_type": "integer", "required": False, "default_value": 60},
            {"param_name": "id_field",       "data_type": "string",  "required": False},
            {"param_name": "bounding_field", "data_type": "string",  "required": False},
        ],
    },
    {
        "code": "Feeds ATOM/RSS",
        "class_path": "app.fetchers.atom.AtomFetcher",
        "description": "ATOM/RSS feed reader",
        "params": [
            {"param_name": "url",       "data_type": "string",  "required": True},
            {"param_name": "max_items", "data_type": "integer", "required": False, "default_value": 1000},
        ],
    },
    {
        "code": "PLACSP Atom",
        "class_path": "app.fetchers.placsp_atom.PlacspAtomFetcher",
        "description": "PLACSP Atom paging feed with optional year/month filtering",
        "params": [
            {"param_name": "url",       "data_type": "string",  "required": True},
            {"param_name": "max_pages", "data_type": "integer", "required": False, "default_value": 100},
            {"param_name": "timeout",   "data_type": "integer", "required": False, "default_value": 60},
            {"param_name": "anio",      "data_type": "integer", "required": False},
            {"param_name": "mes",       "data_type": "integer", "required": False},
        ],
    },
    {
        "code": "File Download",
        "class_path": "app.fetchers.file_download.FileDownloadFetcher",
        "description": "Downloads a static file (CSV, JSON, Excel, XML)",
        "params": [
            {"param_name": "url",     "data_type": "string", "required": True},
            {"param_name": "format",  "data_type": "string", "required": False, "default_value": "json"},
            {"param_name": "timeout", "data_type": "integer","required": False, "default_value": 60},
        ],
    },
    {
        "code": "HTML SearchLoop",
        "class_path": "app.fetchers.searchloop_html.SearchLoopHtmlFetcher",
        "description": "HTML scraper that pivots over <select> option values",
        "params": [
            {"param_name": "url",    "data_type": "string", "required": True},
            {"param_name": "levels", "data_type": "json",   "required": True},
        ],
    },
    {
        "code": "HTML Paginated",
        "class_path": "app.fetchers.paginated_html.PaginatedHtmlFetcher",
        "description": "HTML scraper with automatic pagination",
        "params": [
            {"param_name": "url",            "data_type": "string", "required": True},
            {"param_name": "row_selector",   "data_type": "string", "required": True},
            {"param_name": "next_selector",  "data_type": "string", "required": False},
        ],
    },
    {
        "code": "HTML Forms",
        "class_path": "app.fetchers.html.HtmlFetcher",
        "description": "Simple HTML form GET/POST scraper",
        "params": [
            {"param_name": "url",    "data_type": "string", "required": True},
            {"param_name": "method", "data_type": "string", "required": False, "default_value": "GET"},
        ],
    },
    {
        "code": "Portales CKAN",
        "class_path": "app.fetchers.ckan.CkanFetcher",
        "description": "CKAN open data portal API",
        "params": [
            {"param_name": "url",         "data_type": "string", "required": True},
            {"param_name": "resource_id", "data_type": "string", "required": True},
        ],
    },
    {
        "code": "OSM Overpass",
        "class_path": "app.fetchers.osm.OsmFetcher",
        "description": "OpenStreetMap Overpass API query",
        "params": [
            {"param_name": "query",   "data_type": "overpass_query", "required": True},
            {"param_name": "timeout", "data_type": "integer",        "required": False, "default_value": 120},
        ],
    },
    {
        "code": "Servicios Geográficos",
        "class_path": "app.fetchers.geo.GeoFetcher",
        "description": "WFS/WMS geographic services",
        "params": [
            {"param_name": "url",      "data_type": "string", "required": True},
            {"param_name": "layer",    "data_type": "string", "required": True},
            {"param_name": "format",   "data_type": "string", "required": False, "default_value": "GeoJSON"},
        ],
    },
    {
        "code": "Servicios SOAP/WSDL",
        "class_path": "app.fetchers.soap.SoapFetcher",
        "description": "SOAP/WSDL web service",
        "params": [
            {"param_name": "wsdl",      "data_type": "string", "required": True},
            {"param_name": "operation", "data_type": "string", "required": True},
        ],
    },
    {
        "code": "REST Loop",
        "class_path": "app.fetchers.rest_loop.RestLoopFetcher",
        "description": "REST API iterated over a list of pivot values (e.g. province codes)",
        "params": [
            {"param_name": "url",              "data_type": "string",  "required": True},
            {"param_name": "method",           "data_type": "string",  "required": False, "default_value": "POST"},
            {"param_name": "payload_template", "data_type": "json",    "required": False},
            {"param_name": "pivot_values",     "data_type": "json",    "required": False},
            {"param_name": "id_field",         "data_type": "string",  "required": False},
            {"param_name": "delay",            "data_type": "number",  "required": False, "default_value": 2},
            {"param_name": "timeout",          "data_type": "integer", "required": False, "default_value": 30},
            {"param_name": "headers",          "data_type": "json",    "required": False},
        ],
    },
]


# ---------------------------------------------------------------------------
# 2. PUBLISHERS
# ---------------------------------------------------------------------------

PUBLISHER_DEFS = [
    {
        "acronimo": "MPTFP",
        "nombre":   "Secretaría de Estado de Función Pública",
        "nivel":    "ESTATAL",
        "pais":     "España",
        "portal_url": "https://administracionelectronica.gob.es",
    },
    {
        "acronimo": "INE",
        "nombre":   "Instituto Nacional de Estadística",
        "nivel":    "ESTATAL",
        "pais":     "España",
        "portal_url": "https://www.ine.es",
    },
    {
        "acronimo": "MINHAC",
        "nombre":   "Ministerio de Hacienda",
        "nivel":    "ESTATAL",
        "pais":     "España",
        "portal_url": "https://www.hacienda.gob.es",
    },
    {
        "acronimo": "PLACSP",
        "nombre":   "Plataforma de Contratación del Sector Público",
        "nivel":    "ESTATAL",
        "pais":     "España",
        "portal_url": "https://contrataciondelestado.es",
    },
    {
        "acronimo": "IGAE",
        "nombre":   "Intervención General de la Administración del Estado",
        "nivel":    "ESTATAL",
        "pais":     "España",
        "portal_url": "https://www.igae.pap.hacienda.gob.es",
    },
    {
        "acronimo": "MJUST",
        "nombre":   "Ministerio de Justicia",
        "nivel":    "ESTATAL",
        "pais":     "España",
        "portal_url": "https://www.mjusticia.gob.es",
    },
    {
        "acronimo": "FGE",
        "nombre":   "Fiscalía General del Estado",
        "nivel":    "ESTATAL",
        "pais":     "España",
        "portal_url": "https://www.fiscalia.es",
    },
    {
        "acronimo": "CGN",
        "nombre":   "Consejo General del Notariado",
        "nivel":    "ESTATAL",
        "pais":     "España",
        "portal_url": "https://www.notariado.org",
    },
]


# ---------------------------------------------------------------------------
# 3. FOUNDATION RESOURCES
# ---------------------------------------------------------------------------
# These are reference datasets the application itself depends on.
# Listed as (name, fetcher_code, publisher_acronimo, target_table, params_dict, schedule)

RESOURCE_DEFS = [
    {
        "name":             "DIR3 - Unidades Orgánicas",
        "fetcher_code":     "API REST Paginada",
        "publisher_acronimo": "MPTFP",
        "target_table":     "dir3_unidades",
        "schedule":         "0 3 * * 0",   # weekly, Sunday 03:00
        "params": {
            "url":             "https://datos.juntadeandalucia.es/api/v0/dir3/all?format=json",
            "method":          "GET",
            "timeout":         "120",
            "id_field":        "id",
            "bounding_field":  "hierarchical_level",
        },
    },
    {
        "name":             "España - Municipios (INE)",
        "fetcher_code":     "API REST",
        "publisher_acronimo": "INE",
        "target_table":     "geo_municipios",
        "schedule":         "0 4 1 1 *",   # yearly, 1 Jan 04:00
        "params": {
            "url":     "https://servicios.ine.es/wstempus/js/ES/MUNICIPIOS",
            "method":  "GET",
            "timeout": "60",
        },
    },
    {
        "name":             "España - Provincias (INE)",
        "fetcher_code":     "API REST",
        "publisher_acronimo": "INE",
        "target_table":     "geo_provincias",
        "schedule":         "0 4 1 1 *",   # yearly, 1 Jan 04:00
        "params": {
            "url":     "https://servicios.ine.es/wstempus/js/ES/PROVINCIA",
            "method":  "GET",
            "timeout": "60",
        },
    },
    {
        "name":             "España - Comunidades Autónomas (INE)",
        "fetcher_code":     "API REST",
        "publisher_acronimo": "INE",
        "target_table":     "geo_ccaa",
        "schedule":         "0 4 1 1 *",   # yearly, 1 Jan 04:00
        "params": {
            "url":     "https://servicios.ine.es/wstempus/js/ES/CCAA",
            "method":  "GET",
            "timeout": "60",
        },
    },
    {
        "name":             "FACE - Relaciones OC/OG/UT (Nacional)",
        "fetcher_code":     "API REST Paginada",
        "publisher_acronimo": "MPTFP",
        "target_table":     "face_relations",
        "schedule":         "0 4 * * 0",   # weekly, Sunday 04:00
        "params": {
            "url":            "https://proveedores.face.gob.es/api/v1/relations",
            "method":         "GET",
            "timeout":        "60",
            "page_param":     "page",
            "page_size_param": "limit",
            "page_size":      "1000",
            "content_field":  "items",
            "id_field":       "",           # no dedup — dedup done at search time
            "headers":        '{"User-Agent": "Python/requests", "Accept": "application/json"}',
            "page_start":     "1",
        },
    },
    {
        "name":             "Notarías - Guía Notarial (CGN)",
        "fetcher_code":     "REST Loop",
        "publisher_acronimo": "CGN",
        "target_table":     "notarios",
        "schedule":         "0 2 * * 0",   # weekly, Sunday 02:00
        "params": {
            "url":     "https://guianotarial.notariado.org/guianotarial/rest/buscar/notarios",
            "method":  "POST",
            "payload_template": '{"nombre":"","apellidos":"","direccion":"","codigoPostal":"","codigoProvincia":"{pivot}","municipio":"","codigoSituacionNotario":"","idiomaExtranjero":""}',
            "id_field": "codigoNotaria",
            "delay":    "3",
            "timeout":  "60",
        },
    },
]


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _upsert_fetcher(db, defn: dict) -> Fetcher:
    """Create or update a Fetcher by code."""
    ft = db.query(Fetcher).filter(Fetcher.code == defn["code"]).first()
    if not ft:
        ft = Fetcher(id=uuid.uuid4(), code=defn["code"])
        db.add(ft)
    ft.class_path = defn["class_path"]
    ft.description = defn.get("description")
    ft.name = defn["code"]
    db.flush()

    # Sync param definitions (add missing ones, don't delete existing)
    existing_params = {p.param_name for p in (ft.params_def or [])}
    for pd in defn.get("params", []):
        if pd["param_name"] not in existing_params:
            fp = FetcherParams(
                id=uuid.uuid4(),
                fetcher_id=ft.id,
                param_name=pd["param_name"],
                data_type=pd.get("data_type", "string"),
                required=pd.get("required", False),
                default_value=pd.get("default_value"),
            )
            db.add(fp)
    return ft


def _upsert_publisher(db, defn: dict) -> Publisher:
    """Create or update a Publisher by acronimo."""
    pub = db.query(Publisher).filter(Publisher.acronimo == defn["acronimo"]).first()
    if not pub:
        pub = Publisher(id=uuid.uuid4())
        db.add(pub)
    for k, v in defn.items():
        setattr(pub, k, v)
    db.flush()
    return pub


def _upsert_resource(db, defn: dict, fetchers: dict, publishers: dict) -> Resource:
    """Create or update a Resource by name."""
    ft = fetchers[defn["fetcher_code"]]
    pub = publishers.get(defn["publisher_acronimo"])

    res = db.query(Resource).filter(Resource.name == defn["name"]).first()
    if not res:
        res = Resource(id=uuid.uuid4(), name=defn["name"])
        db.add(res)

    res.fetcher_id = ft.id
    res.publisher_id = pub.id if pub else None
    res.publisher = pub.nombre if pub else None
    res.target_table = defn.get("target_table")
    res.schedule = defn.get("schedule")
    res.active = True
    db.flush()

    # Sync params: replace all (these are foundation resources, params are authoritative)
    existing = {p.key: p for p in (res.params or [])}
    seen = set()
    for key, value in defn.get("params", {}).items():
        seen.add(key)
        if key in existing:
            existing[key].value = str(value)
        else:
            db.add(ResourceParam(id=uuid.uuid4(), resource_id=res.id, key=key, value=str(value)))

    # Remove params no longer in definition
    for key, param in existing.items():
        if key not in seen:
            db.delete(param)

    return res


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def seed():
    db = SessionLocal()
    try:
        print("[seed] Syncing fetchers...")
        fetchers = {}
        for defn in FETCHER_DEFS:
            ft = _upsert_fetcher(db, defn)
            fetchers[defn["code"]] = ft
            print(f"  ✓ {defn['code']}")

        print("[seed] Syncing publishers...")
        publishers = {}
        for defn in PUBLISHER_DEFS:
            pub = _upsert_publisher(db, defn)
            publishers[defn["acronimo"]] = pub
            print(f"  ✓ {defn['acronimo']} — {defn['nombre']}")

        print("[seed] Syncing foundation resources...")
        for defn in RESOURCE_DEFS:
            res = _upsert_resource(db, defn, fetchers, publishers)
            print(f"  ✓ {defn['name']} → {defn['target_table']}")

        db.commit()
        print("[seed] Done.")
    except Exception as e:
        db.rollback()
        print(f"[seed] ERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
